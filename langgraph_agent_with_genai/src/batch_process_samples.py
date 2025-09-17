import logging
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from tzlocal import get_localzone
from file_processor import processFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_all_samples():
    samples_dir = "samples"
    
    if not os.path.exists(samples_dir):
        print(f"Directory not found: {samples_dir}")
        sys.exit(1)
    
    files = [f for f in os.listdir(samples_dir) if os.path.isfile(os.path.join(samples_dir, f))]
    
    if not files:
        print(f"File not found on: {samples_dir}")
        return
    
    local_tz = get_localzone()
    results = []
    
    logger.info(f"Found {len(files)} files to process")
    
    for filename in files:
        file_path = os.path.join(samples_dir, filename)
        local_file = os.path.abspath(file_path)
        
        logger.info(f"Processing file: {filename}")
        
        try:
            created_on_ts = os.path.getctime(local_file)
            modified_on_ts = os.path.getmtime(local_file)
            
            created_on_dt = datetime.fromtimestamp(created_on_ts, tz=local_tz)
            modified_on_dt = datetime.fromtimestamp(modified_on_ts, tz=local_tz)
            
            print(f"\n=== Processing: {filename} ===")
            print(f"Created on: {created_on_dt}")
            print(f"Last modified on: {modified_on_dt}")
            
            result = processFile(local_file, created_on_dt, modified_on_dt)
            
            results.append({
                "file": filename,
                "result": result
            })
            
            logger.info(f"Results for {filename}: {result}")
            print(f"Status: {result.get('status', 'unknown')}")
            
        except Exception as e:
            error_msg = f"Error on processing files {filename}: {str(e)}"
            logger.error(error_msg)
            results.append({
                "file": filename,
                "result": {"status": "failed", "reason": error_msg}
            })
    
    # Summary
    print(f"\n=== FINAL ===")
    successful = sum(1 for r in results if r["result"].get("status") == "success")
    failed = len(results) - successful
    
    print(f"Total processed files: {len(results)}")
    print(f"Success: {successful}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\n Failed files:")
        for r in results:
            if r["result"].get("status") != "success":
                print(f"- {r['file']}: {r['result'].get('reason', 'Unkwnon erros')}")

if __name__ == "__main__":
    process_all_samples()