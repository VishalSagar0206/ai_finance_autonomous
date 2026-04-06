import chromadb
from chromadb.config import Settings
import os
import uuid
import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class AlphaMemoryClient:
    """
    Long-Term 'Alpha Memory' for the Hedge Fund.
    Persists successful strategies in a vector database for historical retrieval.
    """

    def __init__(self, persist_directory: str = "./alpha_memory"):
        self.persist_directory = persist_directory
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)
        
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="historical_strategies")

    def save_strategy(self, strategy_id: str, rationale: str, parameters: Dict[str, Any], results: Dict[str, Any]):
        """Saves a strategy rationale and its performance metrics to the vector store."""
        try:
            # Metadata must be simple types for Chroma
            metadata = {
                "strategy_id": strategy_id,
                "parameters": json.dumps(parameters),
                "results": json.dumps(results),
                "sharpe_ratio": float(results.get("sharpe_ratio", 0.0))
            }
            
            self.collection.add(
                documents=[rationale],
                metadatas=[metadata],
                ids=[str(uuid.uuid4())]
            )
            logger.info(f"Alpha Memory: Saved strategy {strategy_id}.")
        except Exception as e:
            logger.error(f"Alpha Memory: Failed to save strategy. Error: {str(e)}")

    def retrieve_similar_strategies(self, query_rationale: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Retrieves historical strategies with similar rationales to inform the current generation."""
        try:
            results = self.collection.query(
                query_texts=[query_rationale],
                n_results=n_results
            )
            
            output = []
            if results and 'documents' in results:
                for i in range(len(results['documents'][0])):
                    output.append({
                        "rationale": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else None
                    })
            return output
        except Exception as e:
            logger.warning(f"Alpha Memory: Retrieval failed or empty. Error: {str(e)}")
            return []

# Singleton instance
alpha_memory = AlphaMemoryClient()
