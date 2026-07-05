"""
JARVIS — Analyse Agent
RAG over local documents using:
  - Embeddings : BAAI/bge-m3     (HuggingFace Inference API)
  - Reranking  : BAAI/bge-reranker-v2-m3 (HuggingFace Inference API)
  - LLM Synth  : Qwen/Qwen3-32B-Instruct (HuggingFace, via config llm)
  - Vision OCR : Qwen/Qwen2.5-VL-72B-Instruct (HuggingFace, via config vision_llm)
Fallbacks: HuggingFaceEmbeddings (local), Cohere reranker, Cohere embeddings.
"""

import os

import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
try:
    from langchain_classic.retrievers import EnsembleRetriever
except ImportError:
    from langchain_community.retrievers import EnsembleRetriever

from backend.agents.base import BaseAgent
from backend.config import (
    llm, vision_llm,
    FAISS_SEARCH_K, CHUNK_SIZE, CHUNK_OVERLAP,
    get_user_documents_dir, get_user_faiss_dir,
    COHERE_API_KEY, RERANK_TOP_N, SEMANTIC_WEIGHT, KEYWORD_WEIGHT,
    HF_EMBEDDING_MODEL, HF_RERANKER_MODEL, HF_TOKEN_AVAILABLE,
    HUGGINGFACE_API_TOKEN, HF_INFERENCE_URL,
)
from backend.tools.document_loader import load_and_parse_file
from backend.logger import get_logger

logger = get_logger("agents.analyse")


# ── HuggingFace bge-m3 Embeddings ──────────────────────────────────────────
class HFBGEEmbeddings(Embeddings):
    """
    Embeddings using BAAI/bge-m3 via HuggingFace Inference API.
    Falls back to local HuggingFaceEmbeddings if HF token is not set.
    """
    def __init__(self):
        self._hf_available = HF_TOKEN_AVAILABLE
        self._local_model = None
        if not self._hf_available:
            logger.warning("[bge-m3] HF token not set — using local HuggingFaceEmbeddings.")
            self._init_local()

    def _init_local(self):
        from langchain_huggingface import HuggingFaceEmbeddings
        try:
            self._local_model = HuggingFaceEmbeddings(
                model_name=HF_EMBEDDING_MODEL,
                model_kwargs={"local_files_only": True},
            )
        except Exception:
            try:
                self._local_model = HuggingFaceEmbeddings(model_name=HF_EMBEDDING_MODEL)
            except Exception as e:
                logger.error(f"[bge-m3] Local load also failed: {e}. Using all-MiniLM fallback.")
                self._local_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def _call_hf_api(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        url = f"{HF_INFERENCE_URL}/{HF_EMBEDDING_MODEL}"
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
            "Content-Type": "application/json",
        }
        # bge-m3 supports passage/query instructions for better retrieval quality
        if is_query:
            processed = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]
        else:
            processed = texts

        payload = {"inputs": processed, "options": {"wait_for_model": True}}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                # HF returns a list of embeddings
                if isinstance(result, list) and result:
                    if isinstance(result[0], list):
                        return result
                    # Some models return nested structure
                    return [r if isinstance(r, list) else r.get("embedding", []) for r in result]
            logger.warning(f"[bge-m3 API] status {resp.status_code}: {resp.text[:100]} — using local fallback")
        except Exception as e:
            logger.warning(f"[bge-m3 API] Request failed: {e} — using local fallback")

        # Fallback to local if API call fails
        if self._local_model is None:
            self._init_local()
        return self._local_model.embed_documents(texts)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._hf_available:
            return self._call_hf_api(texts, is_query=False)
        return self._local_model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        result = self._call_hf_api([text], is_query=True) if self._hf_available else None
        if result and isinstance(result, list) and result:
            return result[0]
        if self._local_model is None:
            self._init_local()
        return self._local_model.embed_query(text)


# ── HuggingFace bge-reranker-v2-m3 ────────────────────────────────────────
def hf_rerank(query: str, documents: list[str], top_n: int = RERANK_TOP_N) -> list[int]:
    """
    Rerank documents using BAAI/bge-reranker-v2-m3 via HuggingFace Inference API.
    Returns list of original document indices sorted by relevance (highest first).
    Falls back to Cohere reranker if HF API is unavailable.
    """
    if HF_TOKEN_AVAILABLE:
        url = f"{HF_INFERENCE_URL}/{HF_RERANKER_MODEL}"
        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}",
            "Content-Type": "application/json",
        }
        # bge-reranker expects pairs of [query, passage]
        pairs = [[query, doc] for doc in documents]
        payload = {"inputs": pairs, "options": {"wait_for_model": True}}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                scores = resp.json()
                if isinstance(scores, list):
                    # scores is list of floats — pair with original indices and sort
                    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
                    top_indices = [i for i, _ in indexed[:top_n]]
                    logger.info(f"[bge-reranker] Reranked {len(documents)} docs → top {top_n}")
                    return top_indices
            logger.warning(f"[bge-reranker] API status {resp.status_code} — falling back to Cohere")
        except Exception as e:
            logger.warning(f"[bge-reranker] Request failed: {e} — falling back to Cohere")

    # Fallback: Cohere reranker
    cohere_key = COHERE_API_KEY or os.environ.get("COHERE_API_KEY", "")
    if cohere_key:
        try:
            import cohere
            co = cohere.Client(api_key=cohere_key)
            result = co.rerank(
                model="rerank-english-v3.0",
                query=query,
                documents=documents,
                top_n=top_n,
            )
            indices = [r.index for r in result.results]
            logger.info(f"[Cohere reranker] Reranked {len(documents)} → top {top_n}")
            return indices
        except Exception as e:
            logger.warning(f"[Cohere reranker] Failed: {e}")

    # Last resort: return first top_n as-is
    return list(range(min(top_n, len(documents))))


# ── Cohere Embeddings fallback ─────────────────────────────────────────────
class CustomCohereEmbeddings(Embeddings):
    def __init__(self, api_key: str, model: str = "embed-english-v3.0"):
        import cohere
        self.client = cohere.Client(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        res = self.client.embed(texts=texts, model=self.model, input_type="search_document")
        return [list(map(float, emb)) for emb in res.embeddings]

    def embed_query(self, text: str) -> list[float]:
        res = self.client.embed(texts=[text], model=self.model, input_type="search_query")
        return list(map(float, res.embeddings[0]))


class AnalyseAgent(BaseAgent):
    name = "analyse"
    description = (
        "Analyze local files, documents, images, PDFs, or query information stored "
        "in local documents and databases. Uses bge-m3 embeddings + bge-reranker-v2-m3 "
        "for high-quality multilingual retrieval."
    )

    def __init__(self):
        # Primary: bge-m3 via HuggingFace
        try:
            self._embeddings = HFBGEEmbeddings()
            logger.info(f"[AnalyseAgent] Embeddings: {'bge-m3 (HuggingFace API)' if HF_TOKEN_AVAILABLE else 'bge-m3 (local)'}")
        except Exception as e:
            logger.warning(f"[AnalyseAgent] bge-m3 init failed: {e}. Falling back to Cohere...")
            cohere_key = COHERE_API_KEY or os.environ.get("COHERE_API_KEY", "")
            if cohere_key:
                self._embeddings = CustomCohereEmbeddings(api_key=cohere_key)
                logger.info("[AnalyseAgent] Embeddings: Cohere embed-english-v3.0")
            else:
                raise RuntimeError("No embedding model available. Set HUGGINGFACE_API_TOKEN or COHERE_API_KEY.")

    def _build_vector_db(self) -> FAISS | None:
        import uuid
        from backend.core.database import get_db_connection
        from backend.config import current_user_id

        docs_dir = get_user_documents_dir()
        faiss_dir = get_user_faiss_dir()
        user_id = current_user_id.get() or "default"

        logger.info(f"[AnalyseAgent] Scanning documents in '{docs_dir}'...")
        os.makedirs(docs_dir, exist_ok=True)

        files = [f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))]
        if not files:
            logger.warning(f"[AnalyseAgent] No files in '{docs_dir}'.")
            return None

        # Clean existing chunks tracking for this user before rebuilding
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM document_chunks WHERE user_id = ?", (user_id,))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to clear old document chunks mapping: {e}")
        finally:
            conn.close()

        all_texts, metadata_list = [], []
        for filename in files:
            file_path = os.path.join(docs_dir, filename)
            logger.info(f"Parsing: {filename}...")
            try:
                content = load_and_parse_file(file_path, vision_llm=vision_llm)
                if content.strip():
                    all_texts.append(content)
                    metadata_list.append({"source": filename})
            except Exception as e:
                logger.error(f"Error parsing {filename}: {e}")

        if not all_texts:
            return None

        splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        docs = splitter.create_documents(texts=all_texts, metadatas=metadata_list)

        # Generate unique ids for each chunk
        chunk_ids = [str(uuid.uuid4()) for _ in docs]

        logger.info(f"[AnalyseAgent] Indexing {len(docs)} chunks with bge-m3...")
        db = FAISS.from_documents(docs, self._embeddings, ids=chunk_ids)

        # Save chunk mapping to SQLite database
        conn = get_db_connection()
        try:
            for doc, cid in zip(docs, chunk_ids):
                filename = doc.metadata.get("source")
                conn.execute(
                    "INSERT INTO document_chunks (user_id, filename, chunk_id) VALUES (?, ?, ?)",
                    (user_id, filename, cid)
                )
            conn.commit()
            logger.info("Chunk mappings successfully saved to SQLite.")
        except Exception as e:
            logger.error(f"Failed to save document chunk mappings to SQLite: {e}")
            conn.rollback()
        finally:
            conn.close()

        db.save_local(faiss_dir)
        logger.info(f"[AnalyseAgent] FAISS index saved to '{faiss_dir}'.")
        return db

    def delete_document_index(self, filename: str) -> None:
        """Incrementally removes a document's chunks from the FAISS index and the database."""
        from backend.core.database import get_db_connection
        from backend.config import current_user_id

        user_id = current_user_id.get() or "default"
        faiss_dir = get_user_faiss_dir()

        logger.info(f"[AnalyseAgent] Deleting index entries for document '{filename}'...")

        conn = get_db_connection()
        chunk_ids = []
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT chunk_id FROM document_chunks WHERE user_id = ? AND filename = ?",
                (user_id, filename)
            )
            chunk_ids = [row["chunk_id"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch chunk IDs for deletion: {e}")
        finally:
            conn.close()

        if not chunk_ids:
            logger.info(f"No indexed chunks found for '{filename}'.")
            return

        # Load FAISS index, remove matching chunk IDs, and resave
        db = self._get_db()
        if db:
            try:
                db.delete(chunk_ids)
                db.save_local(faiss_dir)
                logger.info(f"Successfully deleted {len(chunk_ids)} chunks from FAISS index.")
            except Exception as e:
                logger.error(f"Failed to remove chunks from FAISS index: {e}")

        # Delete database records
        conn = get_db_connection()
        try:
            conn.execute(
                "DELETE FROM document_chunks WHERE user_id = ? AND filename = ?",
                (user_id, filename)
            )
            conn.commit()
            logger.info(f"Successfully deleted chunks from SQLite database tracking.")
        except Exception as e:
            logger.error(f"Failed to delete document chunks tracker from SQLite: {e}")
            conn.rollback()
        finally:
            conn.close()

    def add_document_to_index(self, filename: str) -> None:
        """Incrementally parses and appends chunks of a new document to the FAISS index."""
        import uuid
        from backend.core.database import get_db_connection
        from backend.config import current_user_id

        user_id = current_user_id.get() or "default"
        docs_dir = get_user_documents_dir()
        faiss_dir = get_user_faiss_dir()

        file_path = os.path.join(docs_dir, filename)
        if not os.path.exists(file_path):
            logger.warning(f"Uploaded file '{filename}' not found. Cannot add to RAG index.")
            return

        logger.info(f"[AnalyseAgent] Incrementally indexing file: {filename}...")

        # Parse file
        try:
            content = load_and_parse_file(file_path, vision_llm=vision_llm)
            if not content.strip():
                logger.info(f"File '{filename}' was empty. Skipping indexing.")
                return
        except Exception as e:
            logger.error(f"Failed to parse '{filename}' during incremental update: {e}")
            return

        # Split content
        splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        docs = splitter.create_documents(texts=[content], metadatas=[{"source": filename}])
        chunk_ids = [str(uuid.uuid4()) for _ in docs]

        # Load FAISS index or create new if not existing
        db = self._get_db()
        if db is None:
            # Create a new FAISS vector store
            logger.info("Initializing new FAISS index for user.")
            db = FAISS.from_documents(docs, self._embeddings, ids=chunk_ids)
        else:
            # First, clean any stale chunks for this filename to prevent duplicate entries
            self.delete_document_index(filename)
            # Re-fetch index in case delete resaved it
            db = self._get_db()
            logger.info(f"Adding {len(docs)} chunks to existing FAISS index.")
            db.add_documents(docs, ids=chunk_ids)

        # Save chunk ids in database
        conn = get_db_connection()
        try:
            for doc, cid in zip(docs, chunk_ids):
                conn.execute(
                    "INSERT INTO document_chunks (user_id, filename, chunk_id) VALUES (?, ?, ?)",
                    (user_id, filename, cid)
                )
            conn.commit()
            logger.info("New chunk mappings successfully saved to SQLite.")
        except Exception as e:
            logger.error(f"Failed to save dynamic document chunk mappings to SQLite: {e}")
            conn.rollback()
        finally:
            conn.close()

        # Save FAISS index
        db.save_local(faiss_dir)
        logger.info(f"[AnalyseAgent] FAISS index saved incrementally to '{faiss_dir}'.")

    def _get_db(self) -> FAISS | None:
        faiss_dir = get_user_faiss_dir()
        if os.path.exists(faiss_dir) and os.listdir(faiss_dir):
            try:
                return FAISS.load_local(faiss_dir, self._embeddings, allow_dangerous_deserialization=True)
            except Exception as e:
                logger.error(f"[AnalyseAgent] FAISS load failed: {e}. Rebuilding...")
        return self._build_vector_db()

    def rebuild_index(self) -> None:
        logger.info("[AnalyseAgent] Forcing rebuild of vector database index...")
        self._build_vector_db()

    def run(self, query: str) -> str:
        logger.info(f"[AnalyseAgent] Query: {query[:80]}...")

        db = self._get_db()
        if not db:
            return "INFORMATION_NOT_AVAILABLE"

        # ── Hybrid Search (FAISS semantic + BM25 keyword) ──────────────────
        try:
            faiss_docs = list(db.docstore._dict.values())
            candidate_k = max(FAISS_SEARCH_K * 2, RERANK_TOP_N * 2)
            if faiss_docs:
                faiss_retriever = db.as_retriever(search_kwargs={"k": candidate_k})
                bm25_retriever = BM25Retriever.from_documents(faiss_docs)
                bm25_retriever.k = candidate_k
                ensemble = EnsembleRetriever(
                    retrievers=[faiss_retriever, bm25_retriever],
                    weights=[SEMANTIC_WEIGHT, KEYWORD_WEIGHT],
                )
                matched_docs = ensemble.invoke(query)
                logger.info(f"[AnalyseAgent] Hybrid search returned {len(matched_docs)} candidates.")
            else:
                matched_docs = db.as_retriever(search_kwargs={"k": FAISS_SEARCH_K}).invoke(query)
        except Exception as e:
            logger.error(f"[AnalyseAgent] Hybrid search error: {e}. Using semantic-only fallback.")
            matched_docs = db.as_retriever(search_kwargs={"k": FAISS_SEARCH_K}).invoke(query)

        if not matched_docs:
            return "INFORMATION_NOT_AVAILABLE"

        # ── Reranking: bge-reranker-v2-m3 → Cohere fallback ───────────────
        doc_contents = [doc.page_content for doc in matched_docs]
        top_indices = hf_rerank(query, doc_contents, top_n=RERANK_TOP_N)
        final_docs = [matched_docs[i] for i in top_indices if i < len(matched_docs)]

        for doc in final_docs:
            logger.info(f"[AnalyseAgent] Reranked match: {doc.metadata.get('source', 'unknown')}")

        context = "\n\n".join([
            f"Source: {doc.metadata.get('source')}\nContent: {doc.page_content}"
            for doc in final_docs
        ])

        # ── RAG Synthesis: Qwen3-32B-Instruct ──────────────────────────────
        qa_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Chief Knowledge Officer & Multimodal Vector RAG Specialist for JARVIS.\n"
                "You use BAAI/bge-m3 embeddings and BAAI/bge-reranker-v2-m3 reranking for retrieval, "
                "and synthesize answers with Qwen3-32B-Instruct.\n\n"
                "<execution_guidelines>\n"
                "1. Synthesize the provided context to deliver authoritative, accurate insights.\n"
                "2. Format tabular data using clean Markdown tables.\n"
                "3. HARD FALLBACK: If the answer cannot be derived from the context, "
                "reply with EXACTLY: INFORMATION_NOT_AVAILABLE\n"
                "</execution_guidelines>",
            ),
            ("human", "Context:\n{context}\n\nQuery: {query}"),
        ])

        chain = qa_prompt | llm | StrOutputParser()
        response = chain.invoke({"context": context, "query": query})
        logger.info("[AnalyseAgent] Analysis complete.")
        return response.strip()
