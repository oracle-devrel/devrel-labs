from sentence_transformers import SentenceTransformer
import logging
from typing import List
from pydantic import BaseModel


logger = logging.getLogger(__name__)

# Global cache of the model to avoid reloading
_cached_model = None
_model_name = "intfloat/multilingual-e5-large"

class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


class EmbedRequest(BaseModel):
    texts: list[str]

def _get_cached_model():
    """Return the cached model or load it if necessary"""
    global _cached_model
    
    if _cached_model is None:
        try:
            logger.info(f"Loading embedding model: {_model_name}")
            _cached_model = SentenceTransformer(_model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise RuntimeError(f"Failed to initialize embedding model: {e}")
    
    return _cached_model

def generate_embeddings_local(request_text: list[str]) -> List[List[float]]:

    if not request_text:
        raise ValueError("Text list cannot be empty")
    
    # Remove empty texts
    filtered_texts = [text.strip() for text in request_text if text and text.strip()]

    #logger.info(f"Embedding the string: {filtered_texts})")
    
    if not filtered_texts:
        raise ValueError("No valid text found after filtering")
    
    try:
        logger.info(f"Starting embedding for {len(filtered_texts)} texts...")
        
        # Get cached model
        embedding_model = _get_cached_model()
        
        # Generate embeddings
        embeddings = embedding_model.encode(filtered_texts)
        embeddings_list = embeddings.tolist()
        
        logger.info(f"Embeddings successfully generated - {len(embeddings_list)} vectors of dimension {len(embeddings_list[0])}")
        
        return embeddings_list
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise RuntimeError(f"Failed to generate embeddings: {e}")