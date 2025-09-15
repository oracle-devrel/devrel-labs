import logging
from jlibspython.oracledb_utils import execute_query, parse_date
from jlibspython.proxy_embedding_helper import generate_embeddings_batch
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def file_already_exists(source_file: str) -> bool:
    try:
        sql = "SELECT COUNT(*) as count FROM document_vectors WHERE source_file = :source_file"
        result = execute_query(sql, {"source_file": source_file})
        
        if result and len(result) > 0 and result[0]['count'] > 0:
            logger.info(f"File is already indexed, skipped: {source_file}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking is file already indexed: {e}")
        return False

def store_document_in_oracledb(
    source_file: str,
    chunk_text: str,
    embedding_list: list[float],
    metadata: dict,
    created_on: datetime,
    modified_on: datetime,
    embedding_model: str,
    compartment_id: str,
    genai_endpoint: str
):
    logger.info("Storing data into Oracle")
    try:
        embedding_vector = embedding_list[0]
        emb_str = "[" + ",".join(str(x) for x in embedding_vector) + "]"

        sql = """
            INSERT INTO document_vectors (                
                source_file,
                chunk_text,
                embedding,
                summary,
                doc_type,
                category,
                person_name,
                event_date,
                created_on,
                modified_on, 
                full_metadata,
                DOC_TYPE_EMBEDDING,
                CATEGORY_EMBEDDING,
                PERSON_NAME_EMBEDDING,
                SUMMARY_EMBEDDING
            ) VALUES (
                    :source_file,
                    :chunk_text,
                    :embedding, 
                    :summary,
                    :doc_type,
                    :category,
                    :person_name,
                    :event_date,
                    :created_on,
                    :modified_on, 
                    :full_metadata,
                    :doc_type_embedding,
                    :category_embedding,
                    :person_name_embedding,
                    :summary_embedding
                    )
        """

        logger.info(f"Detected metadata: {metadata}")
        full_metadata_json = json.dumps(metadata, ensure_ascii=False)

        summary = metadata.get("summary").lower() or None
        doc_type = metadata.get("type").lower() or None
        category = metadata.get("category").lower() or None
        event_date = parse_date(metadata.get("eventdate"))
        person_name = metadata.get("person").lower() or None
                
        logger.info("Embedding selected columns...")

        doc_type_embed_str = ""
        category_embed_str = ""
        summary_embed_str = ""
        person_name_embed_str = ""

        if doc_type:
            doc_type_embed = generate_embeddings_batch([doc_type], compartment_id=compartment_id, embedding_model=embedding_model, genai_endpoint=genai_endpoint)[0]
            doc_type_embed_str = "[" + ",".join(str(x) for x in doc_type_embed) + "]"
        
        if category:
            category_embed = generate_embeddings_batch([category], compartment_id=compartment_id, embedding_model=embedding_model, genai_endpoint=genai_endpoint)[0]
            category_embed_str = "[" + ",".join(str(x) for x in category_embed) + "]"
        
        if summary:
            summary_embed = generate_embeddings_batch([summary], compartment_id=compartment_id, embedding_model=embedding_model, genai_endpoint=genai_endpoint)[0]
            summary_embed_str = "[" + ",".join(str(x) for x in summary_embed) + "]"

        if person_name:
            person_name_embed = generate_embeddings_batch([person_name], compartment_id=compartment_id, embedding_model=embedding_model, genai_endpoint=genai_endpoint)[0]
            person_name_embed_str = "[" + ",".join(str(x) for x in person_name_embed) + "]"


        execute_query(sql, {
            "source_file": source_file,
            "chunk_text": chunk_text,
            "embedding": emb_str,
            "summary": summary,
            "doc_type": doc_type, 
            "category": category,
            "person_name":person_name ,
            "event_date":event_date ,
            "created_on": created_on, 
            "modified_on": modified_on,
            "full_metadata": full_metadata_json,
            "doc_type_embedding": doc_type_embed_str,
            "category_embedding": category_embed_str,
            "person_name_embedding": person_name_embed_str,
            "summary_embedding": summary_embed_str
        })


        return {
            "status": "success",
            **metadata
        }

    except Exception as e:
        logger.error(f"Failed to store in Oracle DB: {str(e)}")
        return {"status": "failed", "reason": f"SQL execution failed: {str(e)}"}
    
