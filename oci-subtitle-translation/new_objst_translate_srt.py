import oci
import yaml
import argparse
import os
import time
from pathlib import Path

# --- Helper Functions ---

def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def upload_to_object_storage(object_storage_client, namespace, bucket_name, file_path):
    """Upload file to OCI Object Storage and return its name."""
    file_name = os.path.basename(file_path)
    print(f"INFO: Uploading '{file_name}' to bucket '{bucket_name}'...")
    with open(file_path, 'rb') as f:
        object_storage_client.put_object(namespace, bucket_name, file_name, f)
    print("INFO: Upload complete.")
    return file_name

def wait_for_job_completion(client, job_id, compartment_id, check_interval=30):
    """Polls the status of a job until it completes or fails."""
    while True:
        try:
            get_job_response = client.get_job(job_id=job_id)
            status = get_job_response.data.lifecycle_state
            
            if status == oci.ai_language.models.Job.LIFECYCLE_STATE_SUCCEEDED:
                print("INFO: Job succeeded.")
                return True
            elif status in [
                oci.ai_language.models.Job.LIFECYCLE_STATE_FAILED,
                oci.ai_language.models.Job.LIFECYCLE_STATE_CANCELED,
            ]:
                print(f"ERROR: Job failed with status: {status}")
                return False
            else:
                print(f"INFO: Job status: {status}. Waiting {check_interval} seconds...")
                time.sleep(check_interval)
        except oci.exceptions.ServiceError as e:
            print(f"ERROR: Error checking job status: {e}")
            return False

# --- Model Discovery (with caching) ---
model_cache = {}

def get_translation_model_id(language_client, tenancy_id, source_lang, target_lang):
    """Finds the OCID of the pre-trained translation model for a given language pair."""
    # OCI uses 2-letter codes for this model format, e.g., 'en-es'
    source = source_lang.split('-')[0]
    target = target_lang.split('-')[0]
    model_name = f"Pre-trained Translation model {source}-{target}"
    
    if model_name in model_cache:
        return model_cache[model_name]

    print(f"INFO: Searching for model '{model_name}'...")
    try:
        # Pre-trained models are in the root compartment of the tenancy
        list_models_response = language_client.list_models(compartment_id=tenancy_id)
        
        for model in list_models_response.data.items:
            if model.display_name == model_name:
                print(f"INFO: Found model ID: {model.id}")
                model_cache[model_name] = model.id
                return model.id

        print(f"ERROR: Pre-trained translation model not found for {source_lang} -> {target_lang}")
        return None
    except oci.exceptions.ServiceError as e:
        print(f"ERROR: Could not list models. Check permissions for the root compartment. {e}")
        return None

# --- Main Translation Logic ---

def translate_srt_async(language_client, object_storage_client, config_yaml, model_id, input_file):
    """
    Creates an asynchronous job to translate a file from Object Storage.
    """
    namespace = config_yaml['speech']['namespace']
    bucket_name = config_yaml['speech']['bucket_name']
    compartment_id = config_yaml['language']['compartment_id']
    target_lang = model_id.split('-')[-1] # Infer from model OCID if needed, or pass as arg

    try:
        # 1. Upload the source file to Object Storage
        object_name = upload_to_object_storage(object_storage_client, namespace, bucket_name, input_file)

        # 2. Define input and output locations in Object Storage
        input_location = oci.ai_language.models.ObjectStorageFileNameLocation(
            namespace_name=namespace,
            bucket_name=bucket_name,
            object_names=[object_name]
        )
        
        output_location = oci.ai_language.models.ObjectPrefixOutputLocation(
            namespace_name=namespace,
            bucket_name=bucket_name,
            prefix=f"translated_output/{Path(input_file).stem}/"
        )
        
        # 3. Define the job details, referencing the pre-trained model ID
        create_job_details = oci.ai_language.models.CreateJobDetails(
            display_name=f"Translate_{object_name}_to_{target_lang}",
            compartment_id=compartment_id,
            input_location=input_location,
            output_location=output_location,
            model_metadata_details=[
                oci.ai_language.models.ModelMetadataDetails(model_id=model_id)
            ]
        )
        
        # 4. Create the job
        create_job_response = language_client.create_job(create_job_details=create_job_details)
        job_id = create_job_response.data.id
        print(f"INFO: Job created with ID: {job_id}")

        # 5. Wait for the job to complete
        return wait_for_job_completion(language_client, job_id, compartment_id)

    except oci.exceptions.ServiceError as e:
        print(f"ERROR: Failed to create translation job: {e}")
        return False


def main():
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
    parser = argparse.ArgumentParser(description='Translate SRT files using OCI Language (Async Object Storage Method)')
    parser.add_argument('--input-file', required=True, help='Input SRT file path')
    parser.add_argument('--source-lang', default='en', help='Source language code (e.g., en)')
    parser.add_argument('--target-langs', nargs='+', help='Target language codes (e.g., es fr de)')
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file {args.input_file} not found")
        return

    config_yaml = load_config()
    profile_name = config_yaml.get("profile", "DEFAULT")
    try:
        oci_config = oci.config.from_file(profile_name=profile_name)
        tenancy_id = oci_config.get("tenancy")
        print(f"INFO: Loaded OCI profile '{profile_name}' for tenancy '{tenancy_id}'")
    except Exception as e:
        print(f"ERROR: Failed to load OCI configuration: {e}")
        return

    language_client = oci.ai_language.AIServiceLanguageClient(oci_config)
    object_storage_client = oci.object_storage.ObjectStorageClient(oci_config)
    
    target_langs = args.target_langs if args.target_langs else SUPPORTED_LANGUAGES.keys()

    for lang_code in target_langs:
        if lang_code == args.source_lang:
            continue
        print("-" * 50)
        print(f"Starting translation process for {args.source_lang} -> {lang_code}")
        
        # 1. Find the correct pre-trained model for this language pair
        model_id = get_translation_model_id(language_client, tenancy_id, args.source_lang, lang_code)
        
        if model_id:
            # 2. If model is found, start the asynchronous translation job
            translate_srt_async(
                language_client,
                object_storage_client,
                config_yaml,
                model_id,
                args.input_file
            )
        print("-" * 50)

if __name__ == "__main__":
    main()
