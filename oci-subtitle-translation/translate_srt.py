import oci
import yaml
import argparse
import os
import time
from pathlib import Path

def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def get_language_client():
    """Initialize and return the OCI Language client"""
    config = oci.config.from_file()
    return oci.ai_language.AIServiceLanguageClient(config)

def upload_to_object_storage(object_storage_client, namespace, bucket_name, file_path):
    """Upload file to OCI Object Storage"""
    file_name = os.path.basename(file_path)
    
    with open(file_path, 'rb') as f:
        object_storage_client.put_object(
            namespace,
            bucket_name,
            file_name,
            f
        )
    return file_name

def wait_for_job_completion(client, job_id, compartment_id, max_wait_seconds=1800, wait_interval_seconds=30):
    """Wait for the translation job to complete"""
    for _ in range(0, max_wait_seconds, wait_interval_seconds):
        get_job_response = client.get_job(
            job_id=job_id,
            compartment_id=compartment_id
        )
        
        status = get_job_response.data.lifecycle_state
        if status == "SUCCEEDED":
            return True
        elif status in ["FAILED", "CANCELED"]:
            print(f"Job failed with status: {status}")
            return False
            
        time.sleep(wait_interval_seconds)
    
    return False

def translate_srt(client, object_storage_client, config, input_file, source_lang='en', target_lang='es'):
    """Translate an SRT file using OCI Language Async Document Translation"""
    try:
        # Validate file size (20MB limit)
        file_size = os.path.getsize(input_file)
        if file_size > 20 * 1024 * 1024:  # 20MB in bytes
            raise ValueError("Input file exceeds 20MB limit")

        # Upload file to Object Storage
        input_object_name = upload_to_object_storage(
            object_storage_client,
            config['speech']['namespace'],
            config['speech']['bucket_name'],
            input_file
        )

        # Create document details
        document_details = oci.ai_language.models.ObjectLocation(
            namespace_name=config['speech']['namespace'],
            bucket_name=config['speech']['bucket_name'],
            object_names=[input_object_name]
        )

        # Create job details
        create_job_details = oci.ai_language.models.CreateBatchLanguageTranslationJobDetails(
            compartment_id=config['language']['compartment_id'],
            display_name=f"Translate_{os.path.basename(input_file)}_{target_lang}",
            source_language_code=source_lang,
            target_language_code=target_lang,
            input_location=document_details,
            output_location=document_details,
            model_id="PRETRAINED_LANGUAGE_TRANSLATION"
        )

        # Create translation job
        response = client.create_job(
            create_job_details=create_job_details
        )

        job_id = response.data.id
        print(f"Translation job created with ID: {job_id}")

        # Wait for job completion
        if wait_for_job_completion(client, job_id, config['language']['compartment_id']):
            print(f"Successfully translated to {target_lang}")
            return True
        else:
            print("Translation job failed or timed out")
            return False

    except Exception as e:
        print(f"Error translating to {target_lang}: {str(e)}")
        return False

def main():
    # Define supported languages
    SUPPORTED_LANGUAGES = {
        'ar': 'Arabic', 'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish',
        'nl': 'Dutch', 'en': 'English', 'fi': 'Finnish', 'fr': 'French',
        'fr-CA': 'French Canadian', 'de': 'German', 'el': 'Greek',
        'he': 'Hebrew', 'hu': 'Hungarian', 'it': 'Italian', 'ja': 'Japanese',
        'ko': 'Korean', 'no': 'Norwegian', 'pl': 'Polish', 'pt': 'Portuguese',
        'pt-BR': 'Portuguese Brazilian', 'ro': 'Romanian', 'ru': 'Russian',
        'zh-CN': 'Simplified Chinese', 'sk': 'Slovak', 'sl': 'Slovenian',
        'es': 'Spanish', 'sv': 'Swedish', 'th': 'Thai', 'zh-TW': 'Traditional Chinese',
        'tr': 'Turkish', 'vi': 'Vietnamese'
    }

    parser = argparse.ArgumentParser(description='Translate SRT files using OCI Language')
    parser.add_argument('--input-file', required=True, help='Input SRT file path')
    parser.add_argument('--source-lang', default='en', help='Source language code')
    parser.add_argument('--target-langs', nargs='+', help='Target language codes (space-separated)')
    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file {args.input_file} not found")
        return

    # Load configuration
    config = load_config()

    # Initialize clients
    language_client = get_language_client()
    object_storage_client = oci.object_storage.ObjectStorageClient(oci.config.from_file())

    # If no target languages specified, translate to all supported languages
    target_langs = args.target_langs if args.target_langs else SUPPORTED_LANGUAGES.keys()

    # Translate to each target language
    for lang in target_langs:
        if lang not in SUPPORTED_LANGUAGES:
            print(f"Warning: Unsupported language code '{lang}', skipping...")
            continue
        
        if lang != args.source_lang:
            print(f"Translating to {SUPPORTED_LANGUAGES[lang]} ({lang})...")
            translate_srt(
                language_client,
                object_storage_client,
                config,
                args.input_file,
                args.source_lang,
                lang
            )

if __name__ == "__main__":
    main() 