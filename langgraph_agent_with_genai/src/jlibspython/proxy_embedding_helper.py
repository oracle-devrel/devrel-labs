"""
This is a proxy helper
You can modify when to use Local Embeddings or OCI Generative AI by switching the imports 
"""


import logging
from typing import List
from jlibspython.local_embedding_utils import generate_embeddings_local
#from jlibspython.oci_embedding_utils import generate_embeddings_oci

logger = logging.getLogger(__name__)

# To switch between embedding types, just uncoment parts bellow.

# Using OCI
#def generate_embeddings_batch(texts: List[str], compartment_id:str, embedding_model:str, genai_endpoint:str ) -> List[List[float]]:
#    ret = generate_embeddings_oci(texts, compartment_id=compartment_id, embedding_model=embedding_model, genai_endpoint=genai_endpoint)
#    return ret


# Using Local
def generate_embeddings_batch(texts: List[str], compartment_id:str, embedding_model:str, genai_endpoint:str ) -> List[List[float]]:
    ret = generate_embeddings_local(texts)
    return ret
