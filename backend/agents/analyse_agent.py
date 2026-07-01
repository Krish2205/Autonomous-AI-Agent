"""
JARVIS — Analyse Agent
RAG over local documents using FAISS + Vision LLM for images.
Refactored from analyse.py.
"""

import os
from functools import lru_cache

import cohere
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

from backend.agents.base import BaseAgent
from backend.config import (
    llm, vision_llm, EMBEDDING_MODEL, FAISS_SEARCH_K, CHUNK_SIZE, CHUNK_OVERLAP,
    get_user_documents_dir, get_user_faiss_dir, COHERE_API_KEY, RERANK_TOP_N,
    SEMANTIC_WEIGHT, KEYWORD_WEIGHT
)
from backend.tools.document_loader import load_and_parse_file
from backend.logger import get_logger

logger = get_logger("agents.analyse")


class CustomCohereEmbeddings(Embeddings):
    """Custom wrapper for Cohere Embeddings to avoid PyTorch dependency issues."""
    def __init__(self, api_key: str, model: str = "embed-english-v3.0"):
        self.client = cohere.Client(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            res = self.client.embed(texts=texts, model=self.model, input_type="search_document")
            return [list(map(float, emb)) for emb in res.embeddings]
        except Exception as e:
            logger.error(f"Cohere document embedding error: {e}")
            raise e

    def embed_query(self, text: str) -> list[float]:
        try:
            res = self.client.embed(texts=[text], model=self.model, input_type="search_query")
            return list(map(float, res.embeddings[0]))
        except Exception as e:
            logger.error(f"Cohere query embedding error: {e}")
            raise e


class AnalyseAgent(BaseAgent):
    name = "analyse"
    description = "Analyze local files, documents, images, PDFs, or query information stored in local documents and databases."

    def __init__(self):
        try:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"local_files_only": True}
            )
        except Exception as e:
            logger.warning(f"Could not load HuggingFaceEmbeddings offline: {e}. Trying online HuggingFace embeddings...")
            try:
                self._embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            except Exception as e2:
                logger.error(f"Failed to load HuggingFaceEmbeddings: {e2}. Falling back to Cohere API embeddings...")
                cohere_key = COHERE_API_KEY or os.environ.get("COHERE_API_KEY")
                if cohere_key:
                    try:
                        self._embeddings = CustomCohereEmbeddings(api_key=cohere_key)
                        logger.info("Successfully fell back to Cohere API embeddings!")
                    except Exception as e3:
                        logger.critical(f"Cohere embeddings fallback also failed: {e3}")
                        raise e2
                else:
                    logger.critical("No Cohere API key available for fallback.")
                    raise e2

    def _build_vector_db(self) -> FAISS | None:
        """Scan the documents folder and build a FAISS vector index."""
        docs_dir = get_user_documents_dir()
        faiss_dir = get_user_faiss_dir()
        
        logger.info(f"Scanning documents folder '{docs_dir}' to build database...")
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir, exist_ok=True)
            
        files = [
            f for f in os.listdir(docs_dir)
            if os.path.isfile(os.path.join(docs_dir, f))
        ]

        if not files:
            logger.warning(f"No files found in '{docs_dir}' folder.")
            return None

        all_texts = []
        metadata_list = []

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

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        docs = text_splitter.create_documents(texts=all_texts, metadatas=metadata_list)

        logger.info(f"Creating embeddings and indexing {len(docs)} chunks...")
        db = FAISS.from_documents(docs, self._embeddings)
        db.save_local(faiss_dir)
        logger.info(f"Database built and saved successfully to '{faiss_dir}'!")
        return db

    def _get_db(self) -> FAISS | None:
        """Load or build the FAISS database."""
        faiss_dir = get_user_faiss_dir()
        if os.path.exists(faiss_dir) and os.listdir(faiss_dir):
            try:
                return FAISS.load_local(
                    faiss_dir, self._embeddings, allow_dangerous_deserialization=True
                )
            except Exception as e:
                logger.error(f"Failed to load FAISS index from {faiss_dir}: {e}. Rebuilding...")
        return self._build_vector_db()

    def rebuild_index(self) -> None:
        """Force rebuild and update of the FAISS vector database."""
        logger.info("Forcing rebuild of vector database index...")
        self._build_vector_db()

    def run(self, query: str) -> str:
        logger.info(f"Analysing documents for: {query[:80]}...")

        db = self._get_db()
        if not db:
            return "INFORMATION_NOT_AVAILABLE"

        # 1. Hybrid Search Setup
        try:
            # Extract all documents loaded in FAISS docstore to fit BM25Retriever
            faiss_docs = list(db.docstore._dict.values())
            if not faiss_docs:
                logger.warning("No documents found in FAISS docstore. Falling back to semantic search.")
                retriever = db.as_retriever(search_kwargs={"k": FAISS_SEARCH_K})
                matched_docs = retriever.invoke(query)
            else:
                # We request a larger candidate pool from both retrievers to allow reranking to filter down
                candidate_k = max(FAISS_SEARCH_K * 2, RERANK_TOP_N * 2)
                
                faiss_retriever = db.as_retriever(search_kwargs={"k": candidate_k})
                bm25_retriever = BM25Retriever.from_documents(faiss_docs)
                bm25_retriever.k = candidate_k
                
                logger.info("Initializing Hybrid Ensemble Retriever (FAISS + BM25)...")
                ensemble_retriever = EnsembleRetriever(
                    retrievers=[faiss_retriever, bm25_retriever],
                    weights=[SEMANTIC_WEIGHT, KEYWORD_WEIGHT]
                )
                matched_docs = ensemble_retriever.invoke(query)
        except Exception as e:
            logger.error(f"Error initializing Hybrid Search: {e}. Falling back to standard semantic search.")
            retriever = db.as_retriever(search_kwargs={"k": FAISS_SEARCH_K})
            matched_docs = retriever.invoke(query)

        if not matched_docs:
            return "INFORMATION_NOT_AVAILABLE"

        # 2. Cohere Reranking
        final_docs = matched_docs
        cohere_key = COHERE_API_KEY or os.environ.get("COHERE_API_KEY")
        if cohere_key:
            try:
                logger.info("Initializing Cohere Rerank...")
                co = cohere.Client(api_key=cohere_key)
                # Prepare documents for cohere SDK (requires a list of strings)
                doc_contents = [doc.page_content for doc in matched_docs]
                
                if doc_contents:
                    # Run Cohere rerank using 'rerank-english-v3.0'
                    rerank_response = co.rerank(
                        model="rerank-english-v3.0",
                        query=query,
                        documents=doc_contents,
                        top_n=RERANK_TOP_N
                    )
                    
                    reranked_docs = []
                    for result in rerank_response.results:
                        idx = result.index
                        score = result.relevance_score
                        doc = matched_docs[idx]
                        logger.info(f"Rerank match - Source: {doc.metadata.get('source')} | Score: {score:.4f}")
                        reranked_docs.append(doc)
                    
                    if reranked_docs:
                        final_docs = reranked_docs
            except Exception as e:
                logger.error(f"Error during Cohere reranking: {e}. Falling back to raw ensemble results.")
                final_docs = matched_docs[:FAISS_SEARCH_K]
        else:
            logger.info("COHERE_API_KEY not configured. Skipping reranking stage.")
            # If skipping reranking, limit final docs to FAISS_SEARCH_K
            final_docs = matched_docs[:FAISS_SEARCH_K]

        context = "\n\n".join([
            f"Source: {doc.metadata.get('source')}\nContent: {doc.page_content}"
            for doc in final_docs
        ])

        qa_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Chief Knowledge Officer & Multimodal Vector RAG Specialist for JARVIS.\n"
                "You specialize in semantic search indexing, reranked context extraction, data matrix synthesis, and document intelligence.\n\n"
                "<execution_guidelines>\n"
                "1. Synthesize the provided context to deliver authoritative, highly accurate insights.\n"
                "2. Format tabular data, spreadsheets, and structured matrices using clean Markdown tables.\n"
                "3. HARD FALLBACK REQUIREMENT: If the required answer cannot be logically derived from the provided document context, you MUST reply with EXACTLY: INFORMATION_NOT_AVAILABLE (with zero extra text or punctuation).\n"
                "</execution_guidelines>",
            ),
            ("human", "Context:\n{context}\n\nQuery: {query}"),
        ])

        chain = qa_prompt | llm | StrOutputParser()
        response = chain.invoke({"context": context, "query": query})
        logger.info("Analysis completed.")
        return response.strip()
