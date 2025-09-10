"""
Local SentenceTransformer Embedding Component for Langflow
Uses the same embedding model as the investment advisor: all-MiniLM-L12-v2
"""

from langflow.custom import Component
from langflow.io import Output
from langflow.schema import Data
from langchain_community.embeddings import SentenceTransformerEmbeddings
from typing import List
class LocalSentenceTransformerComponent(Component):
    display_name = "Local SentenceTransformer Embeddings"
    description = "Local SentenceTransformer embeddings using all-MiniLM-L12-v2 (same as investment advisor)"
    documentation = "Uses the same embedding model that created your PDF vectors"
    icon = "🔗"
    name = "LocalSentenceTransformerComponent"    
    inputs = []    
    outputs = [
        Output(display_name="Embeddings", name="embeddings", method="build_embeddings"),
    ]    
    def build_embeddings(self) -> Data:
        """Build local SentenceTransformer embeddings component"""
        try:
            # Use the same model as your investment advisor
            embeddings = SentenceTransformerEmbeddings(
                model_name="all-MiniLM-L12-v2",
                # Cache directory to avoid re-downloading
                cache_folder="./.cache/sentence_transformers"
            )
            
            # Test the embeddings to make sure they work
            test_embedding = embeddings.embed_query("test")
            print(f"✅ Local embeddings working! Dimension: {len(test_embedding)}")
            
            self.status = f"✅ Local SentenceTransformer ready (dim: {len(test_embedding)})"
            
            return Data(
                value=embeddings,
                data={
                    "model_name": "all-MiniLM-L12-v2",
                    "embedding_dimension": len(test_embedding),
                    "type": "local_sentence_transformer"
                }
            )
            
        except Exception as e:
            error_msg = f"❌ Failed to load local embeddings: {str(e)}"
            print(error_msg)
            self.status = error_msg
            raise RuntimeError(error_msg)