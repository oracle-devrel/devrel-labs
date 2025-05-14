# Oracle DB 23ai Integration

The Agentic RAG system now supports Oracle DB 23ai as a vector store backend, providing enhanced performance, scalability, and enterprise-grade database features.

## Overview

Oracle Database 23ai is used as the default vector storage system when available, with ChromaDB serving as a fallback option. This integration leverages Oracle's vector database capabilities for efficient semantic search and retrieval.

## Requirements

To use the Oracle DB integration, you need:

1. **Oracle Database 23ai**: With vector extensions enabled
2. **Python Packages**:
   - `oracledb`: For database connectivity
   - `sentence-transformers`: For generating embeddings

## Installation

1. Install the required packages:

```bash
pip install oracledb sentence-transformers
```

2. Configure your Oracle Database connection in `config.yaml`:

```yaml
# Oracle DB Configuration
ORACLE_DB_USERNAME: ADMIN
ORACLE_DB_PASSWORD: your_password_here
ORACLE_DB_DSN: >-
  (description= (retry_count=20)(retry_delay=3)
  (address=(protocol=tcps)(port=1522)(host=your-oracle-db-host.com))
  (connect_data=(service_name=your-service-name))
  (security=(ssl_server_dn_match=yes)))
```

The system will automatically look for these credentials in your `config.yaml` file. If not found, it will raise an error and fall back to ChromaDB.

## How It Works

The system automatically determines which database to use:

1. First tries to connect to Oracle DB 23ai
2. If connection succeeds, uses Oracle for all vector operations
3. If Oracle DB is unavailable, falls back to ChromaDB

## Database Structure

The Oracle DB integration creates the following tables:

- `PDFCollection`: Stores chunks from PDF documents
- `WebCollection`: Stores chunks from web content
- `RepoCollection`: Stores chunks from code repositories
- `GeneralCollection`: Stores general knowledge chunks

Each table has the following structure:
- `id`: Primary key identifier
- `text`: The text content of the chunk
- `metadata`: JSON string containing metadata (source, page, etc.)
- `embedding`: Vector representation of the text

## Testing

You can test the Oracle DB integration using:

```bash
python test_oradb.py
```

Or test both systems using:

```bash
./test_db_systems.sh
```

## Switching Between Databases

You can force the system to use ChromaDB instead of Oracle DB by setting the `use_oracle_db` parameter to `False`:

```python
agent = LocalRAGAgent(use_oracle_db=False)
```

## Gradio Interface

The Gradio web interface displays which database system is active at the top of the page:

- Green banner: Oracle DB 23ai is active
- Red banner: ChromaDB is being used (Oracle DB not available)

## Troubleshooting

If you encounter database connection issues:

1. Verify your Oracle DB credentials and connection string
2. Check that the Oracle DB 23ai instance is running
3. Ensure you have the required Python packages installed
4. Check network connectivity to the database server

If Oracle DB connection fails, the system will automatically fall back to ChromaDB without requiring any user intervention. 