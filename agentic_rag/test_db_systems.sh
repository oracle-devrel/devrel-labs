#!/bin/bash
# Script to test both Oracle DB and ChromaDB for the Agentic RAG system

echo "===== Agentic RAG Database Systems Test ====="
echo

# Check for required packages
echo "Checking for required Python packages..."
pip list | grep -E "oracledb|sentence-transformers|chromadb" || echo "Some required packages may be missing"

echo
echo "===== Testing Oracle DB ====="
echo "Running Oracle DB connection test..."
python test_oradb.py

echo
echo "===== Testing ChromaDB ====="
echo "Creating a test query using ChromaDB as fallback..."
python -c '
from local_rag_agent import LocalRAGAgent
agent = LocalRAGAgent(use_oracle_db=False)
print("ChromaDB initialized successfully")
print("Querying with test prompt...")
result = agent.process_query("What is machine learning?")
print(f"Response generated successfully. Length: {len(result['answer'])}")
'

echo
echo "===== Testing Done ====="
echo "If both tests passed, your system is correctly configured for dual database support."
echo "Oracle DB will be used by default, with ChromaDB as fallback." 