import zipfile
import logging
import oracledb
import oci
import os
import logging
import re
from datetime import datetime
import numpy as np
from typing import List, Dict, Any


logger = logging.getLogger(__name__)

_wallet_downloaded = False
_WALLET_PATH = "/tmp/wallet"

_oracle_pool_singleton = None


def getOracleConnection():
    global _oracle_pool_singleton

    if _oracle_pool_singleton is None:
        wallet_path = download_and_extract_wallet()
        _oracle_pool_singleton = oracledb.SessionPool(
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            dsn=os.environ["DB_DSN"],
            config_dir=wallet_path,
            wallet_location=wallet_path,
            wallet_password=os.environ["WALLET_PASSWORD"],
            min=1,
            max=5,
            increment=1,
            homogeneous=True
        )
        logger.info("Session pool created for Oracle ATP")

    return _oracle_pool_singleton.acquire()



def download_and_extract_wallet():
    global _wallet_downloaded
    if _wallet_downloaded:
        return _WALLET_PATH

    logger.info("Downloading wallet from OCI Object Storage...")
    namespace = os.environ.get("OCI_BUCKET_NAMESPACE")
    bucket = os.environ.get("OCI_BUCKET_NAME_WALLET")
    object_name = os.environ.get("OCI_WALLET_OBJECT_NAME")
    if not all([namespace, bucket, object_name]):
        raise EnvironmentError("Missing OCI bucket environment variables")


    config_path = os.path.expanduser("~/.oci/config")
    if os.path.exists(config_path):
        logger.info("Connecting using Local OCI Config....")
        config = oci.config.from_file("~/.oci/config",profile_name=os.environ.get("OCI_CLI_PROFILE"))
        client = oci.object_storage.ObjectStorageClient(config=config)
    else:
        logger.info("Connecting using Instance Principal...")
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
        

    response = client.get_object(namespace, bucket, object_name)

    with open("/tmp/wallet.zip", "wb") as f:
        f.write(response.data.content)
    os.makedirs(_WALLET_PATH, exist_ok=True)
    with zipfile.ZipFile("/tmp/wallet.zip", "r") as zip_ref:
        zip_ref.extractall(_WALLET_PATH)

    _wallet_downloaded = True
    logger.info(f"WALLET_PATH updated to {_WALLET_PATH}")
    return _WALLET_PATH


def execute_query(sql, params=None):
    try:
        conn = getOracleConnection()
        cursor = conn.cursor()
        cursor.execute(sanitize_sql(sql), params or {})
        
        if cursor.description is None:            
            conn.commit()
            return {"status": "success", "rows": 0}
        
        columns = [col[0].lower() for col in cursor.description]
        rows = [
            {
                col: val.read() if isinstance(val, oracledb.LOB) else val
                for col, val in zip(columns, row)
            } for row in cursor.fetchall()
        ]
        return rows
    except Exception as e:
        logger.exception(f"Error running query e:{e}")
        raise


def execute_query_single_value(sql, params=None):
    try:
        conn = getOracleConnection()
        cursor = conn.cursor()
        cursor.execute(sanitize_sql(sql), params or {})
        values = [
            val.read() if isinstance(val, oracledb.LOB) else val
            for val, *_ in cursor.fetchall()
        ]
        return values
    except Exception as e:
        logger.exception(f"Error running query e:{e}")
        raise


def sanitize_sql(sql: str) -> str:
    sql = sql.strip()
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = sql.replace("```", "").replace("`", "")
    sql = re.sub(r";\s*$", "", sql)
    sql = re.sub(r"\s+", " ", sql)
    return sql.strip()



def parse_date(date_str):
    if not date_str:
        return None
    input_formats = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")
    for fmt in input_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    logger.warning(f"Invalid date format: {date_str}")
    return None


def parse_date_old(date_str):
    if not date_str:
        return None
    input_formats = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")
    for fmt in input_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Escolhe o formato de saída com ou sem hora
            if fmt == "%Y-%m-%d":
                return dt.strftime("%Y-%m-%d")
            else:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    logger.warning(f"Invalid date format: {date_str}")
    return None


def execute_ddl(sql):
    try:
        conn = getOracleConnection()
        cursor = conn.cursor()
        
        # Split multiple statements and execute each one
        statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
        
        for statement in statements:
            logger.info(f"Executing DDL: {statement[:100]}...")
            cursor.execute(statement)
        
        conn.commit()
        logger.info(f"Successfully executed {len(statements)} DDL statement(s)")
        return {"status": "success", "statements_executed": len(statements)}
    except Exception as e:
        logger.exception(f"Error executing DDL: {e}")
        raise


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def filter_outliers_by_std_dev(data: List[Dict[str, Any]], column_name: str) -> List[Dict[str, Any]]:


    weight_value = 1.5

    if not data:
        return []
    
    ## if there is 5 or less records, then just return it! (few records is not good for outlier detection)
    if len(data) <= 5:
        return data


    valid_data = [item for item in data if safe_float(item.get(column_name)) is not None]
    if not valid_data:
        return []

    distances = [safe_float(item.get(column_name)) for item in valid_data]

    mean_distance = np.mean(distances)
    std_dev_distance = np.std(distances)
    outlier_threshold = mean_distance - weight_value * std_dev_distance

    outlier_results = [
        item for item, dist in zip(valid_data, distances) if dist < outlier_threshold
    ]

    return outlier_results
