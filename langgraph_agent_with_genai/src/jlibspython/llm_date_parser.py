"""
LLM-based intelligent date parsing utility
Converts natural language date expressions to structured date ranges
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
from langchain_oci.chat_models import ChatOCIGenAI


logger = logging.getLogger(__name__)

def get_current_date_context() -> Dict[str, str]:
    """Get current date context for LLM parsing"""
    now = datetime.now()
    last_month = now.replace(day=1) - timedelta(days=1)
    
    return {
        "current_date": now.strftime("%d/%m/%Y"),
        "current_month": now.strftime("%B %Y"),
        "current_year": str(now.year),
        "last_month": last_month.strftime("%B %Y"),
        "last_year": str(now.year - 1)
    }

def validate_date_format(date_str: str) -> bool:
    """Validate if date string is in DD/MM/YYYY format"""
    try:
        datetime.strptime(date_str, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def parse_llm_json_response(json_input: str) -> dict:
    """
    Parse JSON response from LLM with cleanup strategies
    Reuses logic from search_tools but focused on date parsing
    """
    if not json_input or not json_input.strip():
        return {}
    
    # List of cleanup strategies
    strategies = [
        lambda x: json.loads(x),                                    
        lambda x: json.loads(x.strip().strip('"')),                
        lambda x: json.loads(x.replace('\\"', '"')),              
        lambda x: json.loads(x.strip().strip('"').replace('\\"', '"')),
        lambda x: json.loads(x.strip().strip("'").replace("\\'", "'")),
    ]
    
    for i, strategy in enumerate(strategies, 1):
        try:
            result = strategy(json_input)
            if isinstance(result, dict):
                logger.debug(f"Date JSON parsed successfully (strategy {i}): {result}")
                return result
        except (json.JSONDecodeError, Exception):
            continue
    
    logger.error(f"Failed to parse date JSON: {json_input}")
    return {}

def parse_date_with_llm(user_query: str, current_date: Optional[str] = None) -> Dict[str, str]:
    """
    Uses LLM to extract date ranges from natural language queries.
    
    Args:
        user_query: Natural language query containing date references
        current_date: Optional current date context (defaults to today)
    
    Returns:
        Dict with keys "event_date_start" and "event_date_end" in DD/MM/YYYY format
        Empty dict if no dates found or parsing fails
    
    Examples:
        "documents from 2024" -> {"event_date_start": "01/01/2024", "event_date_end": "31/12/2024"}
        "files from April 2024" -> {"event_date_start": "01/04/2024", "event_date_end": "30/04/2024"}
        "last month reports" -> {"event_date_start": "01/02/2024", "event_date_end": "29/02/2024"}
    """
    try:
        # Get date context
        date_context = get_current_date_context()
        if current_date:
            date_context["current_date"] = current_date
        
        # Create focused prompt for date extraction
        prompt = f"""You are a date extraction expert. Extract date ranges from queries and return ONLY valid JSON.

CONTEXT:
- Current date: {date_context['current_date']}
- Current month: {date_context['current_month']}
- Current year: {date_context['current_year']}
- Last month: {date_context['last_month']}
- Last year: {date_context['last_year']}

RULES:
- Always return dates in DD/MM/YYYY format
- For year only: start = 01/01/YYYY, end = 31/12/YYYY
- For month/year: start = first day, end = last day of month
- For single dates: start = end = same date
- If no date found, return empty JSON: {{}}

EXAMPLES:
"documents from 2024" → {{"event_date_start": "01/01/2024", "event_date_end": "31/12/2024"}}
"files from April 2024" → {{"event_date_start": "01/04/2024", "event_date_end": "30/04/2024"}}
"docs from January 15, 2024" → {{"event_date_start": "15/01/2024", "event_date_end": "15/01/2024"}}
"reports from last year" → {{"event_date_start": "01/01/{date_context['last_year']}", "event_date_end": "31/12/{date_context['last_year']}"}}
"contracts from Q1 2024" → {{"event_date_start": "01/01/2024", "event_date_end": "31/03/2024"}}

QUERY: {user_query}

Return only the JSON object:"""

        
        llm = ChatOCIGenAI(
            model_id=os.environ.get("OCI_GENAI_REASONING_MODEL_NAME"),
            service_endpoint=os.environ.get("OCI_GENAI_ENDPOINT"),
            compartment_id=os.environ.get("OCI_COMPARTMENT_ID"),
            auth_type="API_KEY",
            model_kwargs={
                "temperature": 0.1,  # Low temperature for consistent parsing
                "max_tokens": 150
            }
        )
        
        # Get LLM response
        response = llm.invoke(prompt)
        logger.debug(f"LLM date parsing response: {response.content}")
        
        # Parse JSON response
        result = parse_llm_json_response(response.content.strip())
        
        # Validate result structure and format
        if result and "event_date_start" in result and "event_date_end" in result:
            start_date = result["event_date_start"]
            end_date = result["event_date_end"]
            
            # Validate date formats
            if validate_date_format(start_date) and validate_date_format(end_date):
                logger.info(f"LLM successfully parsed dates from '{user_query}': {start_date} to {end_date}")
                return {
                    "event_date_start": start_date,
                    "event_date_end": end_date
                }
            else:
                logger.warning(f"LLM returned invalid date format: {result}")
        
        logger.info(f"No valid dates extracted from: '{user_query}'")
        return {}
        
    except Exception as e:
        logger.error(f"Error in LLM date parsing for query '{user_query}': {e}")
        return {}

# Convenience function for quick testing
def test_date_parsing():
    """Test function to validate date parsing with common queries"""
    test_queries = [
        "documents from 2024",
        "files from April 2024", 
        "reports from last month",
        "contracts from Q1 2024",
        "docs from January 15, 2024",
        "files from last year",
        "documents from 15/01/2024 to 30/01/2024"
    ]
    
    for query in test_queries:
        result = parse_date_with_llm(query)
        print(f"Query: '{query}' -> {result}")

if __name__ == "__main__":
    # Enable testing when run directly
    logging.basicConfig(level=logging.INFO)
    test_date_parsing()