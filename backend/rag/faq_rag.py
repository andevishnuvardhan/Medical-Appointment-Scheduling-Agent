import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from .vector_store import VectorStore
from .embeddings import EmbeddingModel

logger = logging.getLogger(__name__)


class FAQRAG:
    """RAG system for clinic FAQ and information retrieval"""

    def __init__(
        self,
        data_path: str = "./data/clinic_info.json",
        vector_store_path: str = "./data/vectordb"
    ):
        """
        Initialize the FAQ RAG system

        Args:
            data_path: Path to clinic information JSON file
            vector_store_path: Path to vector database directory
        """
        self.data_path = data_path
        self.vector_store = VectorStore(persist_directory=vector_store_path)
        self.embedding_model = EmbeddingModel()

        # Load clinic data
        self.clinic_data = self._load_clinic_data()

        # Initialize vector store if empty
        if self.vector_store.collection.count() == 0:
            logger.info("Vector store is empty. Initializing with clinic data...")
            self._initialize_vector_store()

    def _load_clinic_data(self) -> Dict:
        """Load clinic information from JSON file"""
        logger.info(f"Loading clinic data from {self.data_path}")
        with open(self.data_path, 'r') as f:
            data = json.load(f)
        return data

    def _initialize_vector_store(self):
        """Initialize vector store with clinic information"""
        documents = []
        metadatas = []
        ids = []

        # Add clinic details
        clinic_details = self.clinic_data.get("clinic_details", {})

        # Location and directions
        documents.append(
            f"Clinic Location: {clinic_details.get('address', '')}. "
            f"Directions: {clinic_details.get('location_and_directions', '')}"
        )
        metadatas.append({"category": "location", "type": "clinic_details"})
        ids.append("clinic_location")

        # Parking information
        documents.append(f"Parking Information: {clinic_details.get('parking_information', '')}")
        metadatas.append({"category": "parking", "type": "clinic_details"})
        ids.append("clinic_parking")

        # Hours of operation
        hours = clinic_details.get('hours_of_operation', {})
        hours_text = "Clinic Hours of Operation: " + ", ".join([
            f"{day.capitalize()}: {time}" for day, time in hours.items()
        ])
        documents.append(hours_text)
        metadatas.append({"category": "hours", "type": "clinic_details"})
        ids.append("clinic_hours")

        # Insurance and billing
        insurance = self.clinic_data.get("insurance_and_billing", {})

        accepted_insurance = ", ".join(insurance.get("accepted_insurance", []))
        documents.append(f"Accepted Insurance Providers: {accepted_insurance}")
        metadatas.append({"category": "insurance", "type": "billing"})
        ids.append("accepted_insurance")

        payment_methods = ", ".join(insurance.get("payment_methods", []))
        documents.append(f"Payment Methods: {payment_methods}")
        metadatas.append({"category": "payment", "type": "billing"})
        ids.append("payment_methods")

        documents.append(f"Billing Policies: {insurance.get('billing_policies', '')}")
        metadatas.append({"category": "billing", "type": "billing"})
        ids.append("billing_policies")

        # Visit preparation
        visit_prep = self.clinic_data.get("visit_preparation", {})

        required_docs = ", ".join(visit_prep.get("required_documents", []))
        documents.append(f"Required Documents for Visit: {required_docs}")
        metadatas.append({"category": "preparation", "type": "visit_prep"})
        ids.append("required_documents")

        documents.append(f"First Visit Procedures: {visit_prep.get('first_visit_procedures', '')}")
        metadatas.append({"category": "preparation", "type": "visit_prep"})
        ids.append("first_visit_procedures")

        what_to_bring = ", ".join(visit_prep.get("what_to_bring", []))
        documents.append(f"What to Bring to Appointment: {what_to_bring}")
        metadatas.append({"category": "preparation", "type": "visit_prep"})
        ids.append("what_to_bring")

        # Policies
        policies = self.clinic_data.get("policies", {})

        documents.append(f"Cancellation Policy: {policies.get('cancellation_policy', '')}")
        metadatas.append({"category": "policy", "type": "policies"})
        ids.append("cancellation_policy")

        documents.append(f"Late Arrival Policy: {policies.get('late_arrival_policy', '')}")
        metadatas.append({"category": "policy", "type": "policies"})
        ids.append("late_arrival_policy")

        documents.append(f"COVID-19 Protocols: {policies.get('covid_19_protocols', '')}")
        metadatas.append({"category": "policy", "type": "policies"})
        ids.append("covid_protocols")

        # Appointment types
        apt_types = self.clinic_data.get("appointment_types", {})
        for apt_name, apt_info in apt_types.items():
            doc_text = (
                f"{apt_info.get('description', '')} "
                f"Duration: {apt_info.get('duration')} minutes. "
                f"Preparation: {apt_info.get('preparation', '')}"
            )
            documents.append(doc_text)
            metadatas.append({"category": "appointment_type", "type": apt_name})
            ids.append(f"apt_type_{apt_name}")

        # FAQs
        faqs = self.clinic_data.get("faqs", [])
        for idx, faq in enumerate(faqs):
            doc_text = f"Q: {faq.get('question', '')} A: {faq.get('answer', '')}"
            documents.append(doc_text)
            metadatas.append({"category": "faq", "type": "faq", "question": faq.get('question', '')})
            ids.append(f"faq_{idx}")

        # Add all documents to vector store
        self.vector_store.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Initialized vector store with {len(documents)} documents")

    def query(self, question: str, n_results: int = 3) -> List[Dict]:
        """
        Query the FAQ system

        Args:
            question: User's question
            n_results: Number of relevant documents to retrieve

        Returns:
            List of relevant information chunks with metadata
        """
        logger.info(f"Querying FAQ: '{question}'")

        results = self.vector_store.query(
            query_text=question,
            n_results=n_results
        )

        # Format results
        formatted_results = []
        if results and results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None
                })

        logger.debug(f"Found {len(formatted_results)} relevant documents")
        return formatted_results

    def get_context_for_question(self, question: str, n_results: int = 3) -> str:
        """
        Get formatted context string for a question

        Args:
            question: User's question
            n_results: Number of relevant documents to retrieve

        Returns:
            Formatted context string to include in LLM prompt
        """
        results = self.query(question, n_results=n_results)

        if not results:
            return "No relevant information found in the knowledge base."

        context_parts = []
        for idx, result in enumerate(results, 1):
            context_parts.append(f"[Source {idx}] {result['content']}")

        return "\n\n".join(context_parts)
