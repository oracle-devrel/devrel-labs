"""
Search tools for LLM agent
Contains specific tools for searching documents in the DOCUMENT_VECTORS table
"""

import logging
from typing import Optional, List
from langchain.tools import tool
from jlibspython.oracledb_utils import execute_query, filter_outliers_by_std_dev
from jlibspython.proxy_embedding_helper import generate_embeddings_batch
from jlibspython.llm_date_parser import parse_date_with_llm

import os

# Logging configuration
logger = logging.getLogger(__name__)

OCI_COMPARTMENT_ID = os.environ.get("OCI_COMPARTMENT_ID")
OCI_EMBEDDING_ENDPOINT = os.environ.get("OCI_EMBEDDING_ENDPOINT")
OCI_EMBEDDING_MODEL_NAME = os.environ.get("OCI_EMBEDDING_MODEL_NAME")
FILTER_VECTOR_THRESHOLD = 0.08
FILTER_VECTOR_THRESHOLD_PERSON = 0.21
FILTER_VECTOR_THRESHOLD_EMBEDDING_TEXT = 0.4


#@tool(return_direct=True)
@tool()
def search_documents(argumentos: str) -> List[str]:
    """
    Searches documents in the DOCUMENT_VECTORS table based on search criteria.
    
    This tool allows filtering documents using different vector search criteria.
    Arguments must be passed as JSON string containing the desired criteria.
    
    Available criteria:
    - summary: Document content summary
    - person: Name of person associated with document  
    - doc_type: Document type
    - category: Document category
    - event_date_start: Start date in DD/MM/YYYY format
    - event_date_end: End date in DD/MM/YYYY format
    - original_query: Original user query for intelligent date parsing
    
    Returns a list of source files (SOURCE_FILE) that match the search criteria.
    
    
    Args:
        argumentos: JSON string with search criteria. 
                   Example: '{"doc_type": "receipt"}' or '{"summary": "contracts", "original_query": "show me contracts from last year"}'
    
    Returns:
        List of structured information from found documents
    """
    try:        
        logger.info(f"Current arguments: {argumentos}")
        params_dict = parse_llm_json(argumentos)

        sql, params = build_sql(params_dict, 'exact')

        if len(params) == 0:
            logger.info("There are no filter specified, returning 0 documents.")
            return []
        
        results_raw = execute_query(sql, params)
        logger.info(f"Query returned {len(results_raw)} documents")

        if len(results_raw) == 0:
            logger.info("Query returned no records, falling back to semantic search...")
            sql, params = build_sql(params_dict, 'semantic')
            results_raw = execute_query(sql, params)


        # If there is summary distance, capture the most relevant documents removing the outliers on distance
        if params_dict.get("summary"):
            logger.info("Filtering outliers...")
            results = filter_outliers_by_std_dev(results_raw,'distance_summary')
        else:
            results = results_raw

        
        # Format structured return with all information
        formatted_results = []
        for row in results:
            if row.get('source_file'):
                result_text = (
                    f"file_name: {row.get('source_file', '')}\n"
                    f"Summary: {row.get('summary', '')}\n" 
                    f"Doc Type: {row.get('doc_type', '')}\n"
                    f"Category: {row.get('category', '')}\n"
                    f"Person: {row.get('person_name', '')}\n"
                    f"Event Date: {row.get('event_date', '')}\n"
                    f"Distance: {row.get('distance_summary', 'N/A')}\n"
                )
                
                result_text += "---"
                formatted_results.append(result_text)
        
        logger.info(f"Found {len(formatted_results)} documents")
        
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return [f"Search error: {str(e)}"]
    

def _embed_literal(text: str) -> Optional[str]:
    try:
        vec = generate_embeddings_batch(
            [text],
            compartment_id=OCI_COMPARTMENT_ID,
            embedding_model=OCI_EMBEDDING_MODEL_NAME,
            genai_endpoint=OCI_EMBEDDING_ENDPOINT
        )[0]
        return "[" + ",".join(str(x) for x in vec) + "]"
    except Exception as e:
        logger.error(f"Embedding error for '{text}': {e}")
        return None


def build_sql(params_dict: dict, filter_mode: str) -> List[str]:
    try:        
                
        # Extract parameters from JSON and convert to lowercase
        summary = params_dict.get("summary")
        summary = summary.lower() if summary else None
        
        person = params_dict.get("person")
        person = person.lower() if person else None
        
        doc_type = params_dict.get("doc_type")
        doc_type = doc_type.lower() if doc_type else None
        
        category = params_dict.get("category")
        category = category.lower() if category else None
        
        # Enhanced date parameter handling with LLM parsing only
        event_date_start = params_dict.get("event_date_start")
        event_date_end = params_dict.get("event_date_end")
        original_query = params_dict.get("original_query")
        
        # Try LLM date parsing if no structured dates provided
        if not (event_date_start and event_date_end) and original_query:
            llm_parsed_dates = parse_date_with_llm(original_query)
            if llm_parsed_dates:
                event_date_start = llm_parsed_dates.get("event_date_start")
                event_date_end = llm_parsed_dates.get("event_date_end")
                logger.info(f"Using LLM parsed dates: {event_date_start} to {event_date_end}")

        
        logger.info(f"DEBUG - Extracted parameters:")
        logger.info(f"  summary: {summary}")
        logger.info(f"  person: {person}")
        logger.info(f"  doc_type: {doc_type}")
        logger.info(f"  category: {category}")
        logger.info(f"  event_date_start: {event_date_start}")
        logger.info(f"  event_date_end: {event_date_end}")
        logger.info(f"  original_query: {original_query}")
        
        # Build base SQL query
        where_clause = []
        params = {}
        
        if person:
            if filter_mode == 'semantic':
                emb_str = _embed_literal(person)
                where_clause.append(f"VECTOR_DISTANCE(PERSON_NAME_EMBEDDING, VECTOR(:person_embedding)) <= {FILTER_VECTOR_THRESHOLD_PERSON}")
                params["person_embedding"] = emb_str
            elif filter_mode == 'exact':
                where_clause.append(f"lower(PERSON_NAME) like :person_name")     
                params["person_name"] = f"%{person}%"

        if doc_type:
            if filter_mode == 'semantic':
                emb_str = _embed_literal(doc_type)
                where_clause.append(f"VECTOR_DISTANCE(DOC_TYPE_EMBEDDING, VECTOR(:doc_type_embedding)) <= {FILTER_VECTOR_THRESHOLD}")
                params["doc_type_embedding"] = emb_str
            elif filter_mode == 'exact':
                where_clause.append(f"lower(DOC_TYPE) = :doc_type")
                params["doc_type"] = doc_type            


        if category:
            if filter_mode == 'semantic':            
                emb_str = _embed_literal(category)
                where_clause.append(f"VECTOR_DISTANCE(CATEGORY_EMBEDDING, VECTOR(:category_embedding)) <= {FILTER_VECTOR_THRESHOLD}")
                params["category_embedding"] = emb_str
            elif filter_mode == 'exact':
                where_clause.append(f"lower(CATEGORY) = :category")
                params["category"] = category            


        # Date filter using LLM-parsed dates only
        if event_date_start and event_date_end:
            where_clause.append('EVENT_DATE BETWEEN TO_DATE(:start_date, \'DD/MM/YYYY\') AND TO_DATE(:end_date, \'DD/MM/YYYY\')')
            params["start_date"] = event_date_start
            params["end_date"] = event_date_end
            logger.info(f"Using date range filter: {event_date_start} to {event_date_end}")
        

        # Dynamic SELECT construction
        select_columns = [
            "SOURCE_FILE",
            "SUMMARY", 
            "DOC_TYPE",
            "CATEGORY",
            "PERSON_NAME",
            "EVENT_DATE"
        ]
        if summary:
            emb_str = _embed_literal(summary)
            params["summary_embedding"] = emb_str
            select_columns.append("VECTOR_DISTANCE(SUMMARY_EMBEDDING, VECTOR(:summary_embedding)) as DISTANCE_SUMMARY")        

        select_clause = ", ".join(select_columns)

        where_sql = ""
        if where_clause:
            where_sql = "AND " + " AND ".join(where_clause)

        # Conditional ORDER BY and LIMIT
        if summary:
            order_by = "ORDER BY DISTANCE_SUMMARY"
            limit = "FETCH FIRST 20 ROWS ONLY"
        else:
            order_by = "ORDER BY SOURCE_FILE"
            limit = "FETCH FIRST 20 ROWS ONLY"

        sql = f"""
                SELECT {select_clause}
                 FROM DOCUMENT_VECTORS 
                 WHERE 1=1
                 {where_sql}
                {order_by} {limit}
              """
            
        logger.info(f"Parameters: {params}")
        logger.info(f"SQL (MODE:{filter_mode} - {sql}")
        return sql, params
   
     
    except Exception as e:
        logger.error(f"Error building SQL Query: {e}")
        return [f"Error building SQL Query: {str(e)}"]

def parse_llm_json(json_input: str) -> dict:
    """
    Handles and cleans JSON sent by LLM with different formatting issues.
    
    Common problems:
    - JSON with unnecessary escapes: "{\"category\": \"PIX\"}"
    - External double quotes: "{"category": "PIX"}"  
    - Extra spaces or characters
    
    Args:
        json_input: Potentially malformed JSON string from LLM
        
    Returns:
        dict with parsed parameters or empty dict if it fails
    """
    if not json_input or not json_input.strip():
        return {}
    
    import json
    
    # List of cleanup strategies in priority order
    strategies = [
        lambda x: json.loads(x),                                    # 1. Try direct
        lambda x: json.loads(x.strip().strip('"')),                 # 2. Remove external quotes  
        lambda x: json.loads(x.replace('\\"', '"')),               # 3. Remove escapes
        lambda x: json.loads(x.strip().strip('"').replace('\\"', '"')),  # 4. Combined
        lambda x: json.loads(x.strip().strip("'").replace("\\'", "'")),  # 5. Single quotes
    ]
    
    for i, strategy in enumerate(strategies, 1):
        try:
            result = strategy(json_input)
            if isinstance(result, dict):
                logger.info(f"JSON parsed successfully (strategy {i}): {result}")
                return result
        except json.JSONDecodeError:
            continue
        except Exception:
            continue
    
    # If no strategy worked
    logger.error(f"Failed to parse JSON with all strategies: {json_input}")
    return {}


def parse_event_date(date_input: str) -> dict:
    """
    Parses simple date formats and returns SQL condition.
    
    Supported formats:
    - "2024-01-15" or "15/01/2024" -> specific date 
    - "2024-01-15 a 2024-01-31" or "01/01/2024 até 30/05/2024" -> period between dates
    
    Returns:
        dict with 'condition' (SQL string) and 'params' (parameter dict)
        None if format not recognized
    """
    import re
    
    date_str = date_input.strip()
    
    try:
        # Format: Brazilian period "01/01/2024 a 30/05/2024" or "01/01/2024 até 30/05/2024"
        br_period_match = re.match(r'(\d{2}/\d{2}/\d{4})\s+(a|até)\s+(\d{2}/\d{2}/\d{4})', date_str)
        if br_period_match:
            start_date, _, end_date = br_period_match.groups()
            return {
                'condition': 'EVENT_DATE BETWEEN TO_DATE(:start_date, \'DD/MM/YYYY\') AND TO_DATE(:end_date, \'DD/MM/YYYY\')',
                'params': {'start_date': start_date, 'end_date': end_date}
            }
        
        # Format: ISO period "2024-01-15 a 2024-01-31" or "2024-01-15 até 2024-01-31"
        iso_period_match = re.match(r'(\d{4}-\d{2}-\d{2})\s+(a|até)\s+(\d{4}-\d{2}-\d{2})', date_str)
        if iso_period_match:
            start_date_iso, _, end_date_iso = iso_period_match.groups()
            
            # Convert ISO dates to DD/MM/YYYY format
            start_year, start_month, start_day = start_date_iso.split('-')
            end_year, end_month, end_day = end_date_iso.split('-')
            
            start_date = f"{start_day}/{start_month}/{start_year}"
            end_date = f"{end_day}/{end_month}/{end_year}"
            
            return {
                'condition': 'EVENT_DATE BETWEEN TO_DATE(:start_date, \'DD/MM/YYYY\') AND TO_DATE(:end_date, \'DD/MM/YYYY\')',
                'params': {'start_date': start_date, 'end_date': end_date}
            }
        
        # Format: specific date "15/01/2024"
        if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
            # Already in DD/MM/YYYY format
            return {
                'condition': 'EVENT_DATE = TO_DATE(:event_date, \'DD/MM/YYYY\')',
                'params': {'event_date': date_str}
            }
        
        # Format: ISO specific date "2024-01-15"
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            # Convert to DD/MM/YYYY format for Oracle
            year, month, day = date_str.split('-')
            oracle_date = f"{day}/{month}/{year}"
            return {
                'condition': 'EVENT_DATE = TO_DATE(:event_date, \'DD/MM/YYYY\')',
                'params': {'event_date': oracle_date}
            }
        
        logger.warning(f"Date format not recognized: {date_input}")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing date '{date_input}': {e}")
        return None
