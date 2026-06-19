"""
JARVIS — Analyse Agent
RAG over local documents using FAISS + Vision LLM for images.
Refactored from analyse.py.
"""

import os
from functools import lru_cache

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.agents.base import BaseAgent
from backend.config import llm, vision_llm, EMBEDDING_MODEL, FAISS_SEARCH_K, CHUNK_SIZE, CHUNK_OVERLAP, get_user_documents_dir, get_user_faiss_dir
from backend.tools.document_loader import load_and_parse_file
from backend.logger import get_logger

logger = get_logger("agents.analyse")


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
            logger.warning(f"Could not load HuggingFaceEmbeddings offline: {e}. Falling back to online mode...")
            self._embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

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

        retriever = db.as_retriever(search_kwargs={"k": FAISS_SEARCH_K})
        matched_docs = retriever.invoke(query)

        if not matched_docs:
            return "INFORMATION_NOT_AVAILABLE"

        context = "\n\n".join([
            f"Source: {doc.metadata.get('source')}\nContent: {doc.page_content}"
            for doc in matched_docs
        ])

        qa_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an expert document analyzer. Use the provided context to answer the user query. "
                "If the user query asks for tables, spreadsheets, or data matrices, extract them from the context "
                "and format them clearly as markdown tables or matrices. "
                "If the answer cannot be found or logically inferred from the provided context, "
                "you MUST reply with exactly: INFORMATION_NOT_AVAILABLE "
                "Do not add any explanations or warnings if the information is missing. "
                "Just output: INFORMATION_NOT_AVAILABLE",
            ),
            ("human", "Context:\n{context}\n\nQuery: {query}"),
        ])

        chain = qa_prompt | llm | StrOutputParser()
        response = chain.invoke({"context": context, "query": query})
        logger.info("Analysis completed.")
        return response.strip()
