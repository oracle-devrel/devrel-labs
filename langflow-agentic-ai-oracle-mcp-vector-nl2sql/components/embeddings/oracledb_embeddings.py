"""
Oracle Database Local Embeddings Component

This component provides local SentenceTransformer embeddings optimized for Oracle Database
vector storage, ensuring consistent embedding dimensions and models.

Author: Paul Parkinson
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langflow.base.models.model import LCModelComponent
from langflow.io import DropdownInput, IntInput, BoolInput, Output
from langflow.field_typing import Embeddings


class OracleDatabaseEmbeddingsComponent(LCModelComponent):
    """
    Local SentenceTransformer embeddings optimized for Oracle Database vector storage
    """

    display_name = "Oracle Database Local Embeddings"
    description = "Local SentenceTransformer embeddings for Oracle 23ai (384 dimensions, no cloud dependencies)"

    inputs = [
        DropdownInput(
            name="model_name",
            display_name="Embedding Model",
            info="Choose the SentenceTransformer model for embeddings",
            options=[
                "sentence-transformers/all-MiniLM-L12-v2",
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-mpnet-base-v2",
                "sentence-transformers/paraphrase-MiniLM-L6-v2",
                "sentence-transformers/distiluse-base-multilingual-cased",
            ],
            value="sentence-transformers/all-MiniLM-L12-v2",
        ),
        IntInput(
            name="max_length",
            display_name="Max Sequence Length",
            info="Maximum length of input sequences",
            value=512,
            advanced=True,
        ),
        BoolInput(
            name="normalize_embeddings",
            display_name="Normalize Embeddings",
            info="Whether to normalize embeddings to unit length",
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="show_progress",
            display_name="Show Progress",
            info="Whether to show download progress for models",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Embeddings", name="embeddings", method="build_embeddings"),
    ]

    def build_embeddings(self) -> Embeddings:
        """
        Build the HuggingFace embeddings model
        """
        try:
            # Configure model kwargs
            model_kwargs = {
                'device': 'cpu',  # Use CPU for local deployment
            }

            # Configure encode kwargs - remove show_progress_bar to avoid conflicts
            encode_kwargs = {
                'normalize_embeddings': self.normalize_embeddings,
            }

            embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
                show_progress=self.show_progress,  # Use show_progress instead
            )

            self.status = f"✅ Local embeddings loaded: {self.model_name}"
            return embeddings

        except Exception as e:
            error_msg = f"Failed to load embeddings model: {str(e)}"
            self.status = f"❌ {error_msg}"
            raise RuntimeError(error_msg)

    def get_model_info(self) -> dict:
        """
        Get information about the selected model
        """
        model_info = {
            "sentence-transformers/all-MiniLM-L12-v2": {
                "dimensions": 384,
                "description": "Fast and efficient, great for general purpose (recommended for Oracle DB)",
                "size": "133MB"
            },
            "sentence-transformers/all-MiniLM-L6-v2": {
                "dimensions": 384,
                "description": "Smaller and faster version",
                "size": "91MB"
            },
            "sentence-transformers/all-mpnet-base-v2": {
                "dimensions": 768,
                "description": "Higher quality but larger",
                "size": "438MB"
            },
            "sentence-transformers/paraphrase-MiniLM-L6-v2": {
                "dimensions": 384,
                "description": "Optimized for paraphrase detection",
                "size": "91MB"
            },
            "sentence-transformers/distiluse-base-multilingual-cased": {
                "dimensions": 512,
                "description": "Multilingual support",
                "size": "540MB"
            }
        }
        return model_info.get(self.model_name, {"dimensions": "Unknown"})

    def validate_for_oracle_db(self) -> bool:
        """
        Validate that the model is suitable for Oracle Database vector storage
        """
        model_info = self.get_model_info()

        # Oracle 23ai works best with these dimensions
        recommended_dims = [384, 512, 768]
        model_dims = model_info.get("dimensions", 0)

        if model_dims not in recommended_dims:
            self.status = f"⚠️ Warning: {model_dims} dimensions may not be optimal for Oracle DB"
            return False

        self.status = f"✅ Model validated: {model_dims} dimensions, Oracle DB compatible"
        return True
