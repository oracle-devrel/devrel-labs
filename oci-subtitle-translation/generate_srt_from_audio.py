#!/usr/bin/env python3
"""
OCI Speech Audio Transcription

Transcribe audio files to SRT subtitles using OCI Speech service.
Supports both local files and Object Storage inputs.
"""

import oci
import yaml
import argparse
import sys
import time
import os
from datetime import datetime
from pathlib import Path


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
        sys.exit(1)
    except Exception as e:
        log_step(f"Failed to load configuration: {str(e)}", True)
        sys.exit(1)


def upload_audio_file(object_storage_client, config, local_file_path):
    """Upload local audio file to Object Storage"""
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"Audio file not found: {local_file_path}")
    
    file_name = os.path.basename(local_file_path)
    namespace = config['speech']['namespace']
    bucket_name = config['speech']['bucket_name']
    object_name = f"audio/{file_name}"
    
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
        log_step(f"Failed to upload file: {str(e)}", True)
        raise


def wait_for_transcription_job(ai_speech_client, job_id, check_interval=30):
    """Wait for transcription job to complete and return job information"""
    log_step(f"Waiting for transcription job {job_id} to complete...")
    
    while True:
        try:
            job_response = ai_speech_client.get_transcription_job(transcription_job_id=job_id)
            status = job_response.data.lifecycle_state
            
            if status == "SUCCEEDED":
                log_step("Transcription job completed successfully")
                
                if hasattr(job_response.data, 'output_location') and hasattr(job_response.data.output_location, 'prefix'):
                    output_prefix = job_response.data.output_location.prefix
                    input_file = job_response.data.input_location.object_locations[0].object_names[0]
                    input_file_name = input_file.split("/")[-1]
                    
                    return {
                        'job_id': job_id,
                        'output_prefix': output_prefix,
                        'input_file_name': input_file_name,
                        'namespace': job_response.data.output_location.namespace_name,
                        'bucket': job_response.data.output_location.bucket_name if hasattr(job_response.data.output_location, 'bucket_name') else None
                    }
                else:
                    log_step("Could not get output location from job response", True)
                    raise Exception("Could not get output location from job response")
            
            elif status == "FAILED":
                log_step("Transcription job failed", True)
                raise Exception("Transcription job failed")
            elif status in ["CANCELED", "DELETED"]:
                log_step(f"Transcription job was {status.lower()}", True)
                raise Exception(f"Transcription job was {status.lower()}")
            else:
                log_step(f"Job status: {status}. Waiting {check_interval} seconds...")
                time.sleep(check_interval)
                
        except Exception as e:
            if "Transcription job" in str(e) or "Could not get output location" in str(e):
                raise
            log_step(f"Error checking job status: {str(e)}", True)
            raise


def find_srt_file_in_bucket(object_storage_client, namespace, bucket_name, output_prefix, job_id, input_file_name):
    """Find the actual SRT file in the bucket by listing objects"""
    try:
        log_step(f"Searching for SRT file in bucket with prefix: {output_prefix}")
        
        # List objects with the output prefix
        list_response = object_storage_client.list_objects(
            namespace_name=namespace,
            bucket_name=bucket_name,
            prefix=output_prefix
        )
        
        # Look for SRT files
        srt_files = []
        for obj in list_response.data.objects:
            if obj.name.endswith('.srt') and input_file_name.replace('.mp3', '') in obj.name:
                srt_files.append(obj.name)
                log_step(f"Found SRT file: {obj.name}")
        
        if srt_files:
            # Return the first matching SRT file (there should only be one)
            return srt_files[0]
        else:
            log_step(f"No SRT files found with prefix {output_prefix}", True)
            return None
            
    except Exception as e:
        log_step(f"Error searching for SRT file: {str(e)}", True)
        return None


def download_srt_file(object_storage_client, config, job_info, local_path=None):
    """Download SRT file from Object Storage to local filesystem"""
    
    # First, find the actual SRT file in the bucket
    srt_object_name = find_srt_file_in_bucket(
        object_storage_client,
        job_info['namespace'] or config['speech']['namespace'],
        job_info['bucket'] or config['speech']['bucket_name'],
        job_info['output_prefix'],
        job_info['job_id'],
        job_info['input_file_name']
    )
    
    if not srt_object_name:
        raise Exception(f"Could not find SRT file in bucket for job {job_info['job_id']}")
    
    if local_path is None:
        filename = srt_object_name.split("/")[-1]
        output_dir = config.get('output', {}).get('local_directory', './output')
        # Use a simpler filename for local storage
        simple_filename = f"{os.path.splitext(job_info['input_file_name'])[0]}.srt"
        local_path = os.path.join(output_dir, simple_filename)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    try:
        log_step(f"Downloading SRT file to: {local_path}")
        
        get_response = object_storage_client.get_object(
            namespace_name=job_info['namespace'] or config['speech']['namespace'],
            bucket_name=job_info['bucket'] or config['speech']['bucket_name'],
            object_name=srt_object_name
        )
        
        with open(local_path, 'wb') as f:
            for chunk in get_response.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)
        
        log_step(f"Successfully downloaded SRT file: {local_path}")
        return local_path
        
    except Exception as e:
        log_step(f"Failed to download SRT file: {str(e)}", True)
        raise

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Generate SRT file from audio using OCI Speech service',
        epilog="""
Examples:
  # Transcribe local audio file
  python generate_srt_from_audio.py --input-file /path/to/audio.mp3

  # Transcribe audio file already in Object Storage
  python generate_srt_from_audio.py --input-file "audio/myfile.mp3"

  # Specify language and output options
  python generate_srt_from_audio.py --input-file audio.mp3 --language es-ES --output-type local
        """
    )
    
    parser.add_argument('--input-file', required=True,
                       help='Audio file path (local file or Object Storage object name)')
    parser.add_argument('--language', type=str, default=None,
                       help='Language code for transcription (default: from config)')
    parser.add_argument('--output-type', choices=['local', 'object_storage', 'both'], default=None,
                       help='Where to store output (default: from config)')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='Configuration file path (default: config.yaml)')
    
    args = parser.parse_args()

    log_step(f"Starting transcription process for: {args.input_file}")

    # Load configuration
    config = load_config(args.config)
    
    # Override config with command line arguments
    if args.language:
        config['speech']['language_code'] = args.language
    if args.output_type:
        config.setdefault('output', {})['storage_type'] = args.output_type
    
    # Set defaults
    language_code = config['speech'].get('language_code', 'en-US')
    storage_type = config.get('output', {}).get('storage_type', 'both')
    
    # Load OCI config
    profile_name = config.get("profile", "DEFAULT")
    try:
        oci_config = oci.config.from_file(profile_name=profile_name)
        log_step(f"Successfully loaded OCI configuration for profile: {profile_name}")
    except Exception as e:
        log_step(f"Failed to load OCI configuration: {str(e)}", True)
        sys.exit(1)

    # Initialize service clients
    try:
        ai_speech_client = oci.ai_speech.AIServiceSpeechClient(oci_config)
        object_storage_client = oci.object_storage.ObjectStorageClient(oci_config)
        log_step("Successfully initialized OCI clients")
    except Exception as e:
        log_step(f"Failed to initialize OCI clients: {str(e)}", True)
        sys.exit(1)

    # Determine if input_file is local file or object storage path
    if os.path.exists(args.input_file):
        # Local file - upload to object storage first
        try:
            object_name = upload_audio_file(object_storage_client, config, args.input_file)
            file_name = os.path.basename(args.input_file)
        except Exception as e:
            log_step(f"Failed to upload audio file: {str(e)}", True)
            sys.exit(1)
    else:
        # Assume it's already in object storage
        object_name = args.input_file
        file_name = object_name.split("/")[-1]
        log_step(f"Using audio file from Object Storage: {object_name}")

    # Create output directory if needed
    if storage_type in ['local', 'both']:
        output_dir = config.get('output', {}).get('local_directory', './output')
        os.makedirs(output_dir, exist_ok=True)

    # Log transcription settings
    log_step("Creating transcription job with settings:")
    log_step(f"  • Input file: {object_name}")
    log_step(f"  • Language: {language_code}")
    log_step(f"  • Output format: SRT")
    log_step(f"  • Diarization: Enabled (2 speakers)")
    log_step(f"  • Profanity filter: Enabled (TAG mode)")
    log_step(f"  • Storage type: {storage_type}")

    try:
        create_transcription_job_response = ai_speech_client.create_transcription_job(
            create_transcription_job_details=oci.ai_speech.models.CreateTranscriptionJobDetails(
                compartment_id=config['speech']['compartment_id'],
                input_location=oci.ai_speech.models.ObjectListInlineInputLocation(
                    location_type="OBJECT_LIST_INLINE_INPUT_LOCATION", 
                    object_locations=[oci.ai_speech.models.ObjectLocation(
                        namespace_name=config['speech']['namespace'],
                        bucket_name=config['speech']['bucket_name'],
                        object_names=[object_name])]),
                output_location=oci.ai_speech.models.OutputLocation(
                    namespace_name=config['speech']['namespace'],
                    bucket_name=config['speech']['bucket_name'],
                    prefix=f"transcriptions/{file_name}"),
                additional_transcription_formats=["SRT"],
                model_details=oci.ai_speech.models.TranscriptionModelDetails(
                    domain="GENERIC",
                    language_code=language_code,
                    transcription_settings=oci.ai_speech.models.TranscriptionSettings(
                        diarization=oci.ai_speech.models.Diarization(
                            is_diarization_enabled=True,
                            number_of_speakers=2))),
                normalization=oci.ai_speech.models.TranscriptionNormalization(
                    is_punctuation_enabled=True,
                    filters=[
                        oci.ai_speech.models.ProfanityTranscriptionFilter(
                            type="PROFANITY",
                            mode="TAG")]),
                freeform_tags={},
                defined_tags={}))
        
        job_id = create_transcription_job_response.data.id
        log_step(f"Successfully created transcription job with ID: {job_id}")
        
        # Wait for job completion and get job info
        job_info = wait_for_transcription_job(ai_speech_client, job_id)
        
        log_step("Transcription completed successfully!")
        log_step(f"Job output prefix: {job_info['output_prefix']}")
        
        result = {'job_info': job_info}
        
        # Download to local if configured
        if storage_type in ['local', 'both']:
            local_srt_path = download_srt_file(object_storage_client, config, job_info)
            result['local_srt_path'] = local_srt_path
            log_step(f"Local SRT file: {local_srt_path}")
        
        log_step("Transcription workflow completed successfully!")
        
    except Exception as e:
        log_step(f"Transcription failed: {str(e)}", True)
        sys.exit(1)


if __name__ == "__main__":
    main()
