"""
Document statistics tool for LLM agent
Responsible for providing totals and counts of documents in the database
"""

import logging
from typing import List
from langchain.tools import tool
from jlibspython.oracledb_utils import execute_query

# Logging configuration
logger = logging.getLogger(__name__)


def load_document_statistics():
    """
    Loads document statistics for use in the agent prompt.
    """
    try:
        stats_result = get_document_statistics.invoke({})
        return "\n".join(stats_result)
    except Exception as e:
        logger.error(f"Error loading statistics: {e}")
        return "Statistics not available"

@tool(return_direct=True)
def get_document_statistics() -> List[str]:
    """
    Returns statistics of documents available in the database.
    
    This tool provides quantitative information about stored documents:
    - Total number of documents
    - Number of documents by type (DOC_TYPE)
    - Number of documents by category (CATEGORY)
    
    Useful for answering questions like:
    - "How many documents do I have?"
    - "How many receipt type documents?"
    - "What document types are available?"
    
    Returns only totals, never specific document details.
    
    Returns:
        List with formatted document statistics
    """
    try:
        logger.info("Loading document statistics...")
        
        # Query for general total
        total_query = "SELECT COUNT(*) as total FROM DOCUMENT_VECTORS"
        total_result = execute_query(total_query)
        total_docs = total_result[0]['total'] if total_result else 0
        
        # Query for count by DOC_TYPE
        doc_type_query = """
            SELECT DOC_TYPE, COUNT(*) as quantidade 
            FROM DOCUMENT_VECTORS 
            WHERE DOC_TYPE IS NOT NULL 
            GROUP BY DOC_TYPE 
            ORDER BY quantidade DESC
        """
        doc_type_results = execute_query(doc_type_query)
        
        # Query for count by CATEGORY
        category_query = """
            SELECT CATEGORY, COUNT(*) as quantidade 
            FROM DOCUMENT_VECTORS 
            WHERE CATEGORY IS NOT NULL 
            GROUP BY CATEGORY 
            ORDER BY quantidade DESC
        """
        category_results = execute_query(category_query)
        
        # Result formatting
        stats_output = []
        
        # Header
        stats_output.append("=== DOCUMENT STATISTICS ===")
        stats_output.append("")
        
        # General total
        stats_output.append(f"TOTAL DOCUMENTS: {total_docs:,}")
        stats_output.append("")
        
        # Documents by type
        if doc_type_results:
            stats_output.append("DOCUMENTS BY TYPE:")
            for row in doc_type_results:
                doc_type = row.get('doc_type', 'N/A')
                quantidade = row.get('quantidade', 0)
                stats_output.append(f"- {doc_type}: {quantidade:,} documents")
            stats_output.append("")
        
        # Documents by category
        if category_results:
            stats_output.append("DOCUMENTS BY CATEGORY:")
            for row in category_results:
                category = row.get('category', 'N/A')
                quantidade = row.get('quantidade', 0)
                stats_output.append(f"- {category}: {quantidade:,} documents")
            stats_output.append("")
        
        # Additional information
        stats_output.append("Use the search_documents tool to find specific documents.")
        
        logger.info(f"Statistics loaded - {total_docs} total documents")
        
        return stats_output
        
    except Exception as e:
        logger.error(f"Error loading statistics: {e}")
        return [f"Error loading statistics: {str(e)}"]