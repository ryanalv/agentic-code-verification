import os
from typing import List, Dict, Optional
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from src.utils.logger import logger

class ProjectRAG:
    """
    Utility class to handle Retrieval-Augmented Generation for reading project files
    and domain knowledge. Uses Chroma for local vector storage.
    """
    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings()
        self.vector_store: Optional[Chroma] = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len,
        )

    def _get_ignore_prefixes(self) -> List[str]:
        return [
            ".git", "__pycache__", "node_modules", "venv", ".venv", "env", ".env", 
            "dist", "build", ".idea", ".vscode", "target", "bin", "obj", "lib", 
            "out", "coverage", ".mypy_cache", ".pytest_cache", "site-packages"
        ]

    def _load_documents_from_dir(self, directory: str) -> List:
        """Loads non-ignored documents from a directory."""
        if not os.path.exists(directory):
            logger.warning(f"RAG: Directory {directory} does not exist.")
            return []

        # We use a custom loading loop to respect ignore patterns
        # DirectoryLoader from Langchain can be tricky with complex ignores
        docs = []
        ignore_prefixes = self._get_ignore_prefixes()
        ignore_extensions = {
            ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin", 
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".bmp", ".tiff", ".webp",
            ".zip", ".tar", ".gz", ".rar", ".7z", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac",
            ".db", ".sqlite", ".sqlite3", ".parquet", ".h5", ".hdf5", ".pkl", ".iso"
        }

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ignore_prefixes and not d.startswith('.')]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ignore_extensions or file.startswith('.'):
                    continue
                
                filepath = os.path.join(root, file)
                try:
                    loader = TextLoader(filepath, encoding='utf-8')
                    loaded_docs = loader.load()
                    # Add relative path to metadata for easier context tracking
                    rel_path = os.path.relpath(filepath, directory)
                    for d in loaded_docs:
                        d.metadata["source_relative"] = rel_path
                    docs.extend(loaded_docs)
                except Exception as e:
                    logger.debug(f"RAG: Skipping file {filepath} during load: {e}")
                    
        return docs

    def build_index(self, project_path: str, domain_knowledge_path: Optional[str] = None):
        """
        Loads project files and domain knowledge, splits them, and builds the Chroma index.
        """
        logger.info("--- RAG: Building Index ---")
        all_docs = []

        logger.info(f"Loading project files from {project_path}")
        project_docs = self._load_documents_from_dir(project_path)
        all_docs.extend(project_docs)

        if domain_knowledge_path:
            logger.info(f"Loading domain knowledge from {domain_knowledge_path}")
            domain_docs = self._load_documents_from_dir(domain_knowledge_path)
            # Tag domain docs differently if needed
            for d in domain_docs:
                d.metadata["type"] = "domain_knowledge"
            all_docs.extend(domain_docs)

        if not all_docs:
            logger.warning("RAG: No documents found to index.")
            return

        logger.info("RAG: Splitting documents...")
        splits = self.text_splitter.split_documents(all_docs)
        
        # By passing persist_directory as None, Chroma runs ephemerally in-memory for this CLI execution.
        self.vector_store = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory=self.persist_directory
        )
        logger.info("RAG: Index built successfully in memory.")

    def query(self, query_text: str, k: int = 5) -> str:
        """
        Queries the vector store for the most relevant context.
        Returns a formatted string containing the top chunks.
        """
        if not self.vector_store:
            return "Erro: O índice RAG não foi construído. Execute build_index primeiro."

        logger.info(f"RAG: Querying for: {query_text[:50]}...")
        results = self.vector_store.similarity_search(query_text, k=k)
        
        if not results:
             return "RAG: Nenhum contexto relevante encontrado para a query."

        context_parts = []
        for i, doc in enumerate(results):
            source = doc.metadata.get("source_relative", doc.metadata.get("source", "Unknown"))
            doc_type = doc.metadata.get("type", "project_file")
            context_parts.append(f"=== RELEVANT CONTEXT {i+1} ({doc_type}): {source} ===\n{doc.page_content}\n")

        return "\n".join(context_parts)
