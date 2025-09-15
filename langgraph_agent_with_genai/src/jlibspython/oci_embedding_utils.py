
import logging
from typing import List
import oci
import os 


logger = logging.getLogger(__name__)

def generate_embeddings_oci(texts: List[str], compartment_id:str, embedding_model:str, genai_endpoint:str ) -> List[List[float]]:
    if not texts:
        raise ValueError("Text list must not be empty")
    
    # Remove textos vazios
    filtered_texts = [text.strip() for text in texts if text and text.strip()]
    
    if not filtered_texts:
        raise ValueError("No valid text after filter")
    
    try:
        
        config_path = os.path.expanduser("~/.oci/config")
        if os.path.exists(config_path):
            config = oci.config.from_file("~/.oci/config",profile_name=os.environ.get("OCI_CLI_PROFILE"))
            client = oci.generative_ai_inference.GenerativeAiInferenceClient(
                config=config,
                service_endpoint=genai_endpoint
            )
        else:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            client = oci.generative_ai_inference.GenerativeAiInferenceClient(
                config={},
                signer=signer,
                service_endpoint=genai_endpoint
            )        
        
        # Request de embedding para múltiplos textos
        embed_text_details = oci.generative_ai_inference.models.EmbedTextDetails(
            inputs=filtered_texts,
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                model_id=embedding_model
            ),
            compartment_id=compartment_id,
            is_echo=False,
            truncate="NONE"
        )
        
        # Chamada da API
        embed_text_response = client.embed_text(embed_text_details)
        
        # Extrai todos os embeddings
        embedding_vectors = []
        embeddings_data = embed_text_response.data.embeddings
        
        for embedding_data in embeddings_data:
            if hasattr(embedding_data, 'embedding'):
                embedding_vectors.append(embedding_data.embedding)
            else:
                # Se vier como lista direta
                embedding_vectors.append(embedding_data)
        
        logger.info(f"Embeddings successfully processed of  - {len(embedding_vectors)} texts")
        return embedding_vectors
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise
