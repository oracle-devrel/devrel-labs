"""
Script for validation of database indexed data.
This script helps you to perform some queries on the database.
"""


import sys
import os
import logging
from jlibspython.oracledb_utils import filter_outliers_by_std_dev
from dotenv import load_dotenv
load_dotenv()

from jlibspython.proxy_embedding_helper import generate_embeddings_batch
from jlibspython.oracledb_utils import execute_query


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


OCI_COMPARTMENT_ID = os.environ["OCI_COMPARTMENT_ID"]

## In case you decide to use a GenAI MODEL for Embedding instead of local embeedding, you must setup this variable 
if "OCI_EMBEDDING_MODEL_NAME" in os.environ:
    OCI_EMBEDDING_MODEL_NAME = os.environ["OCI_EMBEDDING_MODEL_NAME"]
else:
    OCI_EMBEDDING_MODEL_NAME = ""
## In case you decide to use a GenAI MODEL for Embedding instead of local embeedding, you must setup this variable 
if "OCI_EMBEDDING_ENDPOINT" in os.environ:
    OCI_EMBEDDING_ENDPOINT = os.environ["OCI_EMBEDDING_ENDPOINT"]
else:
    OCI_EMBEDDING_ENDPOINT = ""


def display_document_stats():
    """Display document statistics by type and category"""
    try:
        sql = "SELECT COUNT(*), DOC_TYPE, CATEGORY FROM DOCUMENT_VECTORS GROUP BY DOC_TYPE, CATEGORY ORDER BY 1,2"
        results = execute_query(sql)
        
        print("\n DOCUMENT STATISTICS")
        print("=" * 50)
        print(f"{'Count':<8} {'Document Type':<20} {'Category':<20}")
        print("-" * 50)
        
        for row in results:
            count = row['count(*)'] if row.get('count(*)') else 0
            doc_type = row['doc_type'] if row.get('doc_type') else 'N/A'
            category = row['category'] if row.get('category') else 'N/A'
            print(f"{count:<8} {doc_type:<20} {category:<20}")
        
        print("-" * 50)
        print()
        
    except Exception as e:
        logger.error(f"Error displaying document statistics: {e}")

def display_available_names():
    """Display available person names in the database"""
    try:
        sql = "SELECT UPPER(LISTAGG(PERSON_NAME, ', ') WITHIN GROUP (ORDER BY PERSON_NAME)) AS available_name FROM DOCUMENT_VECTORS"
        results = execute_query(sql)
        
        print("AVAILABLE PERSON NAMES")
        print("=" * 50)
        
        if results and results[0] and results[0].get('available_name'):
            names = results[0]['available_name']
            print(f"{names}")
        else:
            print("No person names found in the database.")
        
        print("=" * 50)
        print()
        
    except Exception as e:
        logger.error(f"Error displaying available names: {e}")

def main():

    display_document_stats()
    display_available_names()


    if len(sys.argv) < 3:
        print("Usage: python validation.py <column_name> 'your text here'")
        print("Available columns: SUMMARY_EMBEDDING, DOC_TYPE_EMBEDDING, CATEGORY_EMBEDDING, PERSON_NAME_EMBEDDING")
        sys.exit(1)
    
    
    column_name = sys.argv[1]
    text = sys.argv[2]
    text = text.lower()
    
    try:
        embeddings = generate_embeddings_batch(
            [text], 
            compartment_id=OCI_COMPARTMENT_ID, 
            embedding_model=OCI_EMBEDDING_MODEL_NAME, 
            genai_endpoint=OCI_EMBEDDING_ENDPOINT
        )
        
        embedding_vector = embeddings[0]
        emb_str = "[" + ",".join(str(x) for x in embedding_vector) + "]"
        
        sql = f"""
        SELECT SOURCE_FILE, PERSON_NAME, DOC_TYPE, CATEGORY, CHUNK_TEXT, SUMMARY, 
               VECTOR_DISTANCE({column_name}, VECTOR(:embedding)) as DISTANCE 
        FROM DOCUMENT_VECTORS
        ORDER BY DISTANCE
        """
        
        results = execute_query(sql, {"embedding": emb_str})
        
        logger.info(f"Embedding: {emb_str}")
        
        print(f"{'File':<30} {'Person':<20} {'Doc Type':<20} {'Category':<15} {'Distance':<10} {'Summary':<50}")
        print("-" * 145)
        
        for row in results:
            distance = f"{row['distance']:.4f}" if row['distance'] is not None else 999
            file_name = row['source_file'].split('/')[-1] if row['source_file'] else 'N/A'
            person = row['person_name'] or 'N/A'
            doc_type = row['doc_type'] or 'N/A'
            category = row['category'] or 'N/A'
            #distance = f"{row['distance']:.4f}"            
            summary = (row['summary'] or 'N/A')[:47] + "..." if row['summary'] and len(row['summary']) > 50 else (row['summary'] or 'N/A')
            
            print(f"{file_name:<30} {person:<20} {doc_type:<20} {category:<15} {distance:<10} {summary:<50}")
        
        outliers = filter_outliers_by_std_dev(results, 'distance')

        for outlier in outliers:
            print(f"- File: {outlier['source_file']}, Distance: {outlier['distance']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()