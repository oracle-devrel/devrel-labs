"""
Agent Tools Package
Specialized tools for the document search LLM agent
"""

from .search_tools import search_documents
from .document_stats import get_document_statistics

__all__ = ['search_documents', 'get_document_statistics']