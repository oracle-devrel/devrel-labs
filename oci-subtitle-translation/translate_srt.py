#!/usr/bin/env python3
"""
OCI Language Translation for SRT Files

Translate SRT subtitle files to multiple languages using OCI Language service.
Supports both local files and Object Storage inputs/outputs.
"""

import oci
import yaml
import argparse
import sys
import os
import time
import tempfile
from datetime import datetime


# Supported languages mapping
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


def log_step(message, is_error=False):
    """Print a formatted log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "ERROR" if is_error else "INFO"
    print(f"[{timestamp}] {prefix}: {message}")


def load_config(config_file='config.yaml'):
    """Load configuration from YAML file"""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        log_step(f"Successfully loaded configuration from {config_file}")
        return config
    except FileNotFoundError:
        log_step(f"Configuration file {config_file} not found", True)
        log_step("Please copy config_example.yaml to config.yaml and update with your settings", True)
        return None
    except Exception as e:
        log_step(f"Failed to load configuration: {str(e)}", True)
        return None


def get_translation_namespace_bucket(config):
    """Get namespace and bucket for translations"""
    namespace = config.get('language', {}).get('namespace') or config['speech']['namespace']
    bucket_name = config.get('language', {}).get('bucket_name') or config['speech']['bucket_name']
    return namespace, bucket_name


def upload_srt_file(object_storage_client, config, local_file_path):
    """Upload local SRT file to Object Storage"""
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"SRT file not found: {local_file_path}")
    
    file_name = os.path.basename(local_file_path)
    namespace, bucket_name = get_translation_namespace_bucket(config)
    object_name = f"srt_files/{file_name}"
    
    log_step(f"Uploading {local_file_path} to Object Storage...")
    
    try:
        with open(local_file_path, 'rb') as f:
            object_storage_client.put_object(
                namespace_name=namespace,
                bucket_name=bucket_name,
                object_name=object_name,
                put_object_body=f
            )
        
        log_step(f"Successfully uploaded to: {object_name}")
        return object_name
        
    except Exception as e:
        log_step(f"Failed to upload SRT file: {str(e)}", True)
        raise


def wait_for_translation_job(language_client, job_id, compartment_id, max_wait_seconds=1800, wait_interval_seconds=30):
    """Wait for the translation job to complete"""
    for _ in range(0, max_wait_seconds, wait_interval_seconds):
        try:
            get_job_response = language_client.get_job(
                job_id=job_id,
                compartment_id=compartment_id
            )
            
            status = get_job_response.data.lifecycle_state
            if status == "SUCCEEDED":
                log_step("Translation job completed successfully")
                return True
            elif status in ["FAILED", "CANCELED"]:
                log_step(f"Translation job failed with status: {status}", True)
                return False
            else:
                log_step(f"Translation job status: {status}. Waiting {wait_interval_seconds} seconds...")
                
            time.sleep(wait_interval_seconds)
            
        except Exception as e:
            log_step(f"Error checking translation job status: {str(e)}", True)
            return False
    
    log_step("Translation job timed out", True)
    return False


def parse_srt_file(file_path):
    """Parse SRT file and return list of subtitle entries"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    entries = []
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            entry = {
                'number': lines[0],
                'timestamp': lines[1],
                'text': '\n'.join(lines[2:])
            }
            entries.append(entry)
    
    return entries


def search_for_actual_srt_file(object_storage_client, config, expected_object_name):
    """Search for the actual SRT file in Object Storage when the expected path doesn't exist"""
    namespace, bucket_name = get_translation_namespace_bucket(config)
    
    path_parts = expected_object_name.split('/')
    if len(path_parts) >= 3 and path_parts[0] == 'transcriptions':
        audio_filename = path_parts[1]
        base_name = os.path.splitext(path_parts[-1])[0]
        
        search_prefix = f"transcriptions/{audio_filename}"
        
        try:
            log_step(f"Searching for SRT file with prefix: {search_prefix}")
            
            list_response = object_storage_client.list_objects(
                namespace_name=namespace,
                bucket_name=bucket_name,
                prefix=search_prefix,
                limit=1000
            )
            
            srt_files = []
            for obj in list_response.data.objects:
                if obj.name.endswith('.srt') and base_name in obj.name:
                    srt_files.append(obj.name)
            
            if srt_files:
                srt_files.sort()
                found_file = srt_files[-1]
                log_step(f"Found actual SRT file: {found_file}")
                return found_file
            else:
                log_step(f"No SRT file found with prefix {search_prefix}")
                return None
                
        except Exception as e:
            log_step(f"Error searching for SRT file: {str(e)}", True)
            return None
    
    return None


def download_srt_from_object_storage(object_storage_client, config, object_name):
    """Download SRT file from Object Storage to a temporary local file"""
    import tempfile
    
    namespace, bucket_name = get_translation_namespace_bucket(config)
    actual_object_name = object_name
    
    try:
        log_step(f"Downloading SRT file from Object Storage: {actual_object_name}")
        
        get_response = object_storage_client.get_object(
            namespace_name=namespace,
            bucket_name=bucket_name,
            object_name=actual_object_name
        )
        
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.srt', delete=False, encoding='utf-8') as tmp_f:
            for chunk in get_response.data.raw.stream(1024 * 1024, decode_content=False):
                tmp_f.write(chunk.decode('utf-8'))
            temp_path = tmp_f.name
        
        log_step(f"Downloaded SRT file to temporary location: {temp_path}")
        return temp_path
        
    except Exception as e:
        if "ObjectNotFound" in str(e) or "404" in str(e):
            log_step(f"SRT file not found at expected path, searching...")
            actual_object_name = search_for_actual_srt_file(object_storage_client, config, object_name)
            
            if actual_object_name:
                try:
                    log_step(f"Downloading found SRT file: {actual_object_name}")
                    
                    get_response = object_storage_client.get_object(
                        namespace_name=namespace,
                        bucket_name=bucket_name,
                        object_name=actual_object_name
                    )
                    
                    with tempfile.NamedTemporaryFile(mode='w+', suffix='.srt', delete=False, encoding='utf-8') as tmp_f:
                        for chunk in get_response.data.raw.stream(1024 * 1024, decode_content=False):
                            tmp_f.write(chunk.decode('utf-8'))
                        temp_path = tmp_f.name
                    
                    log_step(f"Downloaded SRT file to temporary location: {temp_path}")
                    return temp_path
                    
                except Exception as retry_e:
                    log_step(f"Failed to download found SRT file: {str(retry_e)}", True)
                    raise
            else:
                log_step(f"Could not find SRT file in Object Storage", True)
                raise
        else:
            log_step(f"Failed to download SRT file from Object Storage: {str(e)}", True)
            raise


def get_srt_file_for_parsing(object_storage_client, config, srt_file_path):
    """Get SRT file ready for parsing - download from Object Storage if needed"""
    if os.path.exists(srt_file_path):
        # Local file, return as-is
        return srt_file_path, False  # (file_path, is_temporary)
    else:
        # Object Storage path, download to temporary file
        temp_path = download_srt_from_object_storage(object_storage_client, config, srt_file_path)
        return temp_path, True  # (file_path, is_temporary)


def translate_text_sync(language_client, text, source_lang, target_lang, compartment_id):
    """Translate text using synchronous API"""
    try:
        documents = [oci.ai_language.models.TextDocument(
            key="1", 
            text=text, 
            language_code=source_lang
        )]

        batch_details = oci.ai_language.models.BatchLanguageTranslationDetails(
            documents=documents,
            target_language_code=target_lang,
            compartment_id=compartment_id
        )

        response = language_client.batch_language_translation(
            batch_language_translation_details=batch_details
        )
        
        if response.status == 200 and response.data.documents:
            return response.data.documents[0].translated_text
        else:
            log_step(f"Sync translation failed for {target_lang}", True)
            return None

    except Exception as e:
        log_step(f"Error in sync translation to {target_lang}: {str(e)}", True)
        return None


def save_translated_srt(entries, output_path):
    """Save translated SRT entries to file"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(f"{entry['number']}\n")
            f.write(f"{entry['timestamp']}\n")
            f.write(f"{entry['text']}\n\n")


def translate_srt_sync(language_client, object_storage_client, config, srt_file_path, source_lang, target_lang):
    """Translate SRT file using synchronous translation (subtitle by subtitle)"""
    log_step(f"Translating {srt_file_path} to {target_lang} using synchronous method...")
    
    # Get the SRT file for parsing (download from Object Storage if needed)
    local_srt_path, is_temporary = get_srt_file_for_parsing(object_storage_client, config, srt_file_path)
    
    try:
        entries = parse_srt_file(local_srt_path)
        translated_entries = []
        compartment_id = config['language']['compartment_id']
        
        for i, entry in enumerate(entries):
            log_step(f"Translating subtitle {i+1}/{len(entries)}")
            translated_text = translate_text_sync(language_client, entry['text'], source_lang, target_lang, compartment_id)
            
            if translated_text:
                translated_entry = entry.copy()
                translated_entry['text'] = translated_text
                translated_entries.append(translated_entry)
            else:
                log_step(f"Failed to translate subtitle {i+1}, keeping original", True)
                translated_entries.append(entry)
        
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(srt_file_path))[0]
        output_filename = f"{base_name}_{target_lang}.srt"
        
        # Save locally if configured
        storage_type = config.get('output', {}).get('storage_type', 'both')
        result = {'target_language': target_lang}
        
        if storage_type in ['local', 'both']:
            output_dir = config.get('output', {}).get('local_directory', './output')
            local_output_path = os.path.join(output_dir, output_filename)
            save_translated_srt(translated_entries, local_output_path)
            result['local_file_path'] = local_output_path
            log_step(f"Saved translated SRT locally: {local_output_path}")
        
        # Upload to object storage if configured
        if storage_type in ['object_storage', 'both']:
            namespace, bucket_name = get_translation_namespace_bucket(config)
            prefix = config.get('output', {}).get('object_storage_prefix', 'translations')
            object_name = f"{prefix}/{output_filename}"
            
            # Create temporary file for upload
            with tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False, encoding='utf-8') as tmp_f:
                for entry in translated_entries:
                    tmp_f.write(f"{entry['number']}\n")
                    tmp_f.write(f"{entry['timestamp']}\n")
                    tmp_f.write(f"{entry['text']}\n\n")
                temp_path = tmp_f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    object_storage_client.put_object(
                        namespace_name=namespace,
                        bucket_name=bucket_name,
                        object_name=object_name,
                        put_object_body=f
                    )
                
                result['object_storage_path'] = object_name
                log_step(f"Uploaded translated SRT to object storage: {object_name}")
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
        
        return result
        
    finally:
        # Clean up temporary SRT file if we downloaded it
        if is_temporary and os.path.exists(local_srt_path):
            os.unlink(local_srt_path)


def translate_srt_batch(language_client, object_storage_client, config, srt_file_path, source_lang, target_lang):
    """Translate SRT file using batch/async translation"""
    log_step(f"Translating {srt_file_path} to {target_lang} using batch method...")
    
    # Get the actual SRT file for processing (handles both local and Object Storage)
    local_srt_path, is_temporary = get_srt_file_for_parsing(object_storage_client, config, srt_file_path)
    
    # Validate file size (20MB limit for batch translation)
    file_size = os.path.getsize(local_srt_path)
    if file_size > 20 * 1024 * 1024:  # 20MB in bytes
        log_step("File exceeds 20MB limit, falling back to synchronous translation")
        # Clean up temporary file if needed
        if is_temporary and os.path.exists(local_srt_path):
            os.unlink(local_srt_path)
        return translate_srt_sync(language_client, object_storage_client, config, srt_file_path, source_lang, target_lang)
    
    # Determine object storage path for batch processing
    if os.path.exists(srt_file_path):
        # Local file - upload to object storage first
        input_object_name = upload_srt_file(object_storage_client, config, srt_file_path)
        base_name = os.path.splitext(os.path.basename(srt_file_path))[0]
    else:
        # Already in object storage
        input_object_name = srt_file_path
        base_name = os.path.splitext(os.path.basename(srt_file_path))[0]
    
    namespace, bucket_name = get_translation_namespace_bucket(config)
    
    try:
        # Create document details for input and output locations
        input_location_details = oci.ai_language.models.ObjectStorageFileNameLocation(
            namespace_name=namespace,
            bucket_name=bucket_name,
            object_names=[input_object_name]
        )

        # Output prefix for the translated file
        output_prefix = config.get('output', {}).get('object_storage_prefix', 'translations')
        output_location_details = oci.ai_language.models.ObjectPrefixOutputLocation(
            namespace_name=namespace,
            bucket_name=bucket_name,
            prefix=f"{output_prefix}/{base_name}_{target_lang}"
        )

        # Create translation task details
        translation_task_details = oci.ai_language.models.BatchLanguageTranslationDetails(
            target_language_code=target_lang
        )

        # Create job details
        create_job_details = oci.ai_language.models.CreateJobDetails(
            compartment_id=config['language']['compartment_id'],
            display_name=f"Translate_{base_name}_{target_lang}",
            input_location=input_location_details,
            output_location=output_location_details,
            job_details=translation_task_details 
        )

        # Create translation job
        response = language_client.create_job(
            create_job_details=create_job_details
        )

        job_id = response.data.id
        log_step(f"Translation job created with ID: {job_id}")

        # Wait for job completion
        if wait_for_translation_job(language_client, job_id, config['language']['compartment_id']):
            # Construct expected output file name
            output_filename = f"{base_name}_{target_lang}.srt"
            output_object_name = f"{output_prefix}/{base_name}_{target_lang}/{output_filename}"
            
            result = {
                'target_language': target_lang,
                'object_storage_path': output_object_name
            }
            
            # Download locally if configured
            storage_type = config.get('output', {}).get('storage_type', 'both')
            if storage_type in ['local', 'both']:
                output_dir = config.get('output', {}).get('local_directory', './output')
                local_path = os.path.join(output_dir, output_filename)
                
                try:
                    get_response = object_storage_client.get_object(
                        namespace_name=namespace,
                        bucket_name=bucket_name,
                        object_name=output_object_name
                    )
                    
                    os.makedirs(output_dir, exist_ok=True)
                    with open(local_path, 'wb') as f:
                        for chunk in get_response.data.raw.stream(1024 * 1024, decode_content=False):
                            f.write(chunk)
                    
                    result['local_file_path'] = local_path
                    log_step(f"Downloaded translated file locally: {local_path}")
                    
                except Exception as e:
                    log_step(f"Failed to download translated file: {str(e)}", True)
            
            log_step(f"Successfully translated to {target_lang}")
            return result
        else:
            log_step(f"Translation job failed for {target_lang}", True)
            return None

    except Exception as e:
        log_step(f"Error in batch translation to {target_lang}: {str(e)}", True)
        # Fallback to synchronous translation for smaller files
        if os.path.exists(srt_file_path):
            log_step("Falling back to synchronous translation...")
            return translate_srt_sync(language_client, object_storage_client, config, srt_file_path, source_lang, target_lang)
        return None
    
    finally:
        # Clean up temporary SRT file if we downloaded it
        if is_temporary and os.path.exists(local_srt_path):
            os.unlink(local_srt_path)

def main():
    parser = argparse.ArgumentParser(
        description='Translate SRT files using OCI Language service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate local SRT file to multiple languages
  python translate_srt.py --input-file subtitles.srt --target-languages es fr de

  # Translate with specific source language and method
  python translate_srt.py --input-file subtitles.srt --source-language en --target-languages es --method sync

  # Translate SRT file in Object Storage
  python translate_srt.py --input-file "srt_files/subtitles.srt" --target-languages es fr

Supported languages: """ + ", ".join([f"{code} ({name})" for code, name in sorted(SUPPORTED_LANGUAGES.items())])
    )
    
    parser.add_argument('--input-file', required=True,
                       help='SRT file path (local file or Object Storage object name)')
    parser.add_argument('--source-language', type=str, default='en',
                       help='Source language code (default: en)')
    parser.add_argument('--target-languages', nargs='+', type=str,
                       help='Target language codes (space-separated)')
    parser.add_argument('--method', choices=['sync', 'batch'], default=None,
                       help='Translation method (default: from config or batch)')
    parser.add_argument('--output-type', choices=['local', 'object_storage', 'both'], default=None,
                       help='Where to store output (default: from config)')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='Configuration file path (default: config.yaml)')
    
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    if not config:
        return

    # Override config with command line arguments
    if args.method:
        config.setdefault('translation', {})['method'] = args.method
    if args.output_type:
        config.setdefault('output', {})['storage_type'] = args.output_type

    # Set defaults
    method = config.get('translation', {}).get('method', 'batch')
    storage_type = config.get('output', {}).get('storage_type', 'both')
    target_languages = args.target_languages
    if not target_languages:
        target_languages = config.get('translation', {}).get('target_languages', ['es', 'fr', 'de'])

    # Validate input file
    if os.path.exists(args.input_file):
        log_step(f"Using local SRT file: {args.input_file}")
    else:
        log_step(f"Using SRT file from Object Storage: {args.input_file}")

    # Load OCI configuration
    profile_name = config.get("profile", "DEFAULT")
    try:
        oci_config = oci.config.from_file(profile_name=profile_name)
        region = oci_config.get("region", "unknown")
        log_step(f"Loaded OCI profile '{profile_name}' (region: {region})")
    except Exception as e:
        log_step(f"Failed to load OCI configuration: {e}", True)
        return

    # Initialize clients
    try:
        language_client = oci.ai_language.AIServiceLanguageClient(oci_config)
        object_storage_client = oci.object_storage.ObjectStorageClient(oci_config)
        log_step("Successfully initialized OCI clients")
    except Exception as e:
        log_step(f"Failed to initialize OCI clients: {str(e)}", True)
        return

    # Create output directory if needed
    if storage_type in ['local', 'both']:
        output_dir = config.get('output', {}).get('local_directory', './output')
        os.makedirs(output_dir, exist_ok=True)
        log_step(f"Local output directory: {output_dir}")

    # Validate target languages
    valid_languages = []
    for lang in target_languages:
        if lang in SUPPORTED_LANGUAGES:
            if lang != args.source_language:  # Don't translate to same language
                valid_languages.append(lang)
        else:
            log_step(f"Unsupported language code '{lang}', skipping...", True)

    if not valid_languages:
        log_step("No valid target languages specified", True)
        return

    log_step(f"Translation settings:")
    log_step(f"  • SRT file: {args.input_file}")
    log_step(f"  • Source language: {args.source_language}")
    log_step(f"  • Target languages: {', '.join(valid_languages)}")
    log_step(f"  • Method: {method}")
    log_step(f"  • Storage type: {storage_type}")

    # Translate to each target language
    successful_translations = 0
    for lang in valid_languages:
        lang_name = SUPPORTED_LANGUAGES[lang]
        log_step(f"\nTranslating to {lang_name} ({lang})...")
        
        if method == 'sync':
            result = translate_srt_sync(language_client, object_storage_client, config, args.input_file, args.source_language, lang)
        else:  # batch
            result = translate_srt_batch(language_client, object_storage_client, config, args.input_file, args.source_language, lang)
        
        if result:
            successful_translations += 1
            log_step(f"✓ Successfully translated to {lang_name} ({lang})")
            if 'local_file_path' in result:
                log_step(f"  Local file: {result['local_file_path']}")
            if 'object_storage_path' in result:
                log_step(f"  Object Storage: {result['object_storage_path']}")
        else:
            log_step(f"✗ Failed to translate to {lang_name} ({lang})", True)

    log_step(f"\nTranslation completed: {successful_translations}/{len(valid_languages)} successful")


if __name__ == "__main__":
    main() 
