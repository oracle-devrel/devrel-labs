# https://docs.oracle.com/en-us/iaas/api/#/en/speech/20220101/TranscriptionJob/CreateTranscriptionJob

import oci
import yaml
import argparse
import sys
import time
import os
import json
from datetime import datetime

def log_step(message, is_error=False):
    """Print a formatted log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "ERROR" if is_error else "INFO"
    print(f"[{timestamp}] {prefix}: {message}")

def wait_for_job_completion(ai_speech_client, job_id, check_interval=15):
    """Wait for the transcription job to complete and return the output file name"""
    while True:
        try:
            job_response = ai_speech_client.get_transcription_job(job_id)
            status = job_response.data.lifecycle_state
            
            if status == "SUCCEEDED":
                log_step("Transcription job completed successfully")
                # Get the output file name from the job details
                input_file = job_response.data.input_location.object_locations[0].object_names[0]
                input_file_name = input_file.split("/")[-1]  # Get the filename after last slash
                output_prefix = job_response.data.output_location.prefix
                # Extract just the job ID part (before the first slash)
                job_id_part = job_id.split("/")[0]
                output_file = f"{output_prefix}/{job_id_part}/{input_file_name}.srt"
                return output_file
            
            elif status == "FAILED":
                log_step("Transcription job failed", True)
                sys.exit(1)
            elif status in ["CANCELED", "DELETED"]:
                log_step(f"Transcription job was {status.lower()}", True)
                sys.exit(1)
            else:
                log_step(f"Job status: {status}. Waiting {check_interval} seconds...")
                time.sleep(check_interval)
                
        except Exception as e:
            log_step(f"Error checking job status: {str(e)}", True)
            sys.exit(1)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate SRT file from audio using OCI Speech service')
parser.add_argument('--input-file', required=True, help='Input audio file name in the configured bucket')
args = parser.parse_args()

log_step(f"Starting transcription process for file: {args.input_file}")

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

# Load config based on the profile specificied in the YAML file
try:
    config = oci.config.from_file(profile_name=config_yaml.get("profile", "DEFAULT"))
    log_step("Successfully loaded OCI configuration")
except Exception as e:
    log_step(f"Failed to load OCI configuration: {str(e)}", True)
    sys.exit(1)

# Initialize service client with default config file
try:
    ai_speech_client = oci.ai_speech.AIServiceSpeechClient(config)
    log_step("Successfully initialized AI Speech client")
except Exception as e:
    log_step(f"Failed to initialize AI Speech client: {str(e)}", True)
    sys.exit(1)

# Send the request to service
log_step("Creating transcription job with following settings:")
log_step(f"  • Input file: {args.input_file}")
log_step(f"  • Output format: SRT")
log_step(f"  • Language: en-US")
log_step(f"  • Diarization: Enabled (2 speakers)")
log_step(f"  • Profanity filter: Enabled (TAG mode)")

file_name = args.input_file.split("/")[-1]

try:
    create_transcription_job_response = ai_speech_client.create_transcription_job(
        create_transcription_job_details=oci.ai_speech.models.CreateTranscriptionJobDetails(
            compartment_id=config_yaml['speech']['compartment_id'],
            input_location=oci.ai_speech.models.ObjectListInlineInputLocation(
                location_type="OBJECT_LIST_INLINE_INPUT_LOCATION", 
                object_locations=[oci.ai_speech.models.ObjectLocation(
                    namespace_name=config_yaml['speech']['namespace'],
                    bucket_name=config_yaml['speech']['bucket_name'],
                    object_names=[args.input_file])]),
            output_location=oci.ai_speech.models.OutputLocation(
                namespace_name=config_yaml['speech']['namespace'],
                bucket_name=config_yaml['speech']['bucket_name'],
                prefix=f"transcriptions/{file_name}"),
            additional_transcription_formats=["SRT"],
            model_details=oci.ai_speech.models.TranscriptionModelDetails(
                domain="GENERIC",
                language_code="en-US",
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
    
    log_step("Successfully created transcription job")
    log_step("Job details:")
    log_step(f"  • Job ID: {create_transcription_job_response.data.id}")
    log_step(f"  • Output location: {create_transcription_job_response.data.output_location}")
    log_step(f"  • Status: {create_transcription_job_response.data.lifecycle_state}")
    log_step(f"  • Output will be saved to: {create_transcription_job_response.data.output_location.prefix}{config_yaml['speech']['namespace']}_{config_yaml['speech']['bucket_name']}_{file_name}.srt")
    
    # Wait for job completion and get output file name
    output_file = wait_for_job_completion(ai_speech_client, create_transcription_job_response.data.id)
    log_step(f"Generated SRT file: {output_file}")
    
except Exception as e:
    log_step(f"Failed to create transcription job: {str(e)}", True)
    sys.exit(1)
