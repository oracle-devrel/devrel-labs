import os
import logging
from dotenv import load_dotenv
load_dotenv()


from jlibspython.oracledb_utils import execute_ddl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database by running the DOCUMENT_VECTORS.sql DDL script"""
    
    # Get the absolute path to the SQL file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file_path = os.path.join(script_dir, "db", "DOCUMENT_VECTORS.sql")
    
    if not os.path.exists(sql_file_path):
        logger.error(f"SQL file not found: {sql_file_path}")
        return False
    
    try:
        # Read the SQL file
        with open(sql_file_path, 'r') as file:
            sql_content = file.read()
        
        logger.info(f"Reading DDL script from: {sql_file_path}")
        logger.info("Executing database initialization...")
        
        # Execute the DDL
        result = execute_ddl(sql_content)
        
        logger.info("Database initialization completed successfully!")
        logger.info(f"Result: {result}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    exit(0 if success else 1)