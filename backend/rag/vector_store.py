import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages vector storage and retrieval using ChromaDB"""

    def __init__(self, persist_directory: str = "./data/vectordb"):
        """
        Initialize ChromaDB vector store

        Args:
            persist_directory: Directory to persist the vector database
        """
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        logger.info(f"Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(path=persist_directory)

        # Create or get collection for clinic FAQs
        self.collection = self.client.get_or_create_collection(
            name="clinic_faq",
            metadata={"description": "Clinic information and FAQs"}
        )
        logger.info(f"Collection 'clinic_faq' initialized with {self.collection.count()} documents")

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ):
        """
        Add documents to the vector store

        Args:
            documents: List of text documents
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
        """
        logger.info(f"Adding {len(documents)} documents to vector store")
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Successfully added documents. Total count: {self.collection.count()}")

    def query(
        self,
        query_text: str,
        n_results: int = 3,
        where: Optional[Dict] = None
    ) -> Dict:
        """
        Query the vector store for similar documents

        Args:
            query_text: Query text to search for
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Dictionary with query results containing documents, metadatas, and distances
        """
        logger.debug(f"Querying vector store: '{query_text[:50]}...'")
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        return results

    def delete_collection(self):
        """Delete the entire collection"""
        logger.warning("Deleting collection 'clinic_faq'")
        self.client.delete_collection(name="clinic_faq")

    def reset(self):
        """Reset the vector store by deleting and recreating the collection"""
        self.delete_collection()
        self.collection = self.client.get_or_create_collection(
            name="clinic_faq",
            metadata={"description": "Clinic information and FAQs"}
        )
        logger.info("Vector store reset complete")
