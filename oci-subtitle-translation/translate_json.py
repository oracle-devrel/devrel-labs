import oci
import yaml
import argparse
import sys
import json
import os
from datetime import datetime

def log_step(message, is_error=False):
    """Print a formatted log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "ERROR" if is_error else "INFO"
    print(f"[{timestamp}] {prefix}: {message}")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Translate a JSON subtitle file using OCI AI Translation')
parser.add_argument('--input-file', required=True, help='Input JSON file in the configured bucket')
parser.add_argument('--target-language', required=True, help='Target language code (e.g., fr, es, de)')
args = parser.parse_args()

# Generate output filename
input_filename = os.path.splitext(args.input_file)[0]  # Remove extension
output_file = f"{input_filename}_{args.target_language}.json"

log_step(f"Starting translation of {args.input_file} to {args.target_language}")

# Create a default config using DEFAULT profile in default location
try:
    config = oci.config.from_file(profile_name="DEVRELCOMM")
    log_step("Successfully loaded OCI configuration")
except Exception as e:
    log_step(f"Failed to load OCI configuration: {str(e)}", True)
    sys.exit(1)

# Initialize service client with default config file
try:
    ai_language_client = oci.ai_language.AIServiceLanguageClient(config)
    log_step("Successfully initialized AI Translation client")
except Exception as e:
    log_step(f"Failed to initialize AI Translation client: {str(e)}", True)
    sys.exit(1)

# Load config from yaml file
def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            log_step("Successfully loaded config.yaml")
            log_step(f"Using bucket: {config['speech']['bucket_name']}")
            log_step(f"Using namespace: {config['speech']['namespace']}")
            return config
    except Exception as e:
        log_step(f"Failed to load config.yaml: {str(e)}", True)
        sys.exit(1)

config_yaml = load_config()
object_storage_client = oci.object_storage.ObjectStorageClient(config)

# Reads the JSON file
try:
    namespace = config_yaml['speech']['namespace']
    bucket_name = config_yaml['speech']['bucket_name']
    object_name = args.input_file

    get_object_response = object_storage_client.get_object(namespace, bucket_name, object_name)
    json_data = json.loads(get_object_response.data.text)  # Read and parse JSON data
    log_step(f"Loaded JSON file from OCI with {len(json_data.get('transcriptions', []))} transcriptions.")
    

    log_step(f"Loaded {len(json_data)} subtitles from {args.input_file}")
except Exception as e:
    log_step(f"Failed to read JSON file from OCI Object Storage: {str(e)}", True)
    sys.exit(1)
    
translated_data = []
for item in json_data["transcriptions"]:
    if "transcription" in item:
        try:
            document = oci.ai_language.models.Document(
                language="en",  
                text=item["transcription"]
            )

            request_details = oci.ai_language.models.BatchTranslateTextDetails(
                documents=[document], 
                target_language=args.target_language
            )

            response = ai_language_client.batch_translate_text(request_details)
            translated_text = response.data[0].translated_text  

        except Exception as e:
            print(f"Error during translation: {str(e)}", file=sys.stderr)
            translated_text = item['transcription']  

        # Update item with translated text
        translated_item = item.copy()
        translated_item['transcription'] = translated_text
        translated_data.append(translated_item)
    else:
        print(f"Skipping invalid item: {item}")

log_step(f"Translation completed successfully with {len(translated_data)} items translated")

translated_json = json.dumps(translated_data, ensure_ascii=False, indent=4)

try:
    # Convert translated data back to JSON format
    translated_json = json.dumps(translated_data, ensure_ascii=False, indent=4)

    # Use a temporary file to upload
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(translated_json)
        
    object_storage_client.put_object(namespace, bucket_name, output_file, translated_json.encode('utf-8'))
    log_step(f"Translated JSON uploaded to OCI Object Storage as {output_file}")
except Exception as e:
    log_step(f"Failed to upload translated JSON to OCI: {str(e)}", True)
    sys.exit(1)
