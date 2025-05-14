# https://docs.oracle.com/en-us/iaas/api/#/en/speech/20220101/TranscriptionJob/CreateTranscriptionJob

import oci
import yaml
import argparse
import sys
from datetime import datetime

def log_step(message, is_error=False):
    """Print a formatted log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "ERROR" if is_error else "INFO"
    print(f"[{timestamp}] {prefix}: {message}")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Generate SRT file from audio using OCI Speech service')
parser.add_argument('--input-file', required=True, help='Input audio file name in the configured bucket')
args = parser.parse_args()

log_step(f"Starting transcription process for file: {args.input_file}")

# Create a default config using DEFAULT profile in default location
try:
    config = oci.config.from_file()
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

# Send the request to service
log_step("Creating transcription job with following settings:")
log_step(f"  • Input file: {args.input_file}")
log_step(f"  • Output format: SRT")
log_step(f"  • Language: en-US")
log_step(f"  • Diarization: Enabled (2 speakers)")
log_step(f"  • Profanity filter: Enabled (TAG mode)")

try:
    create_transcription_job_response = ai_speech_client.create_transcription_job(
        create_transcription_job_details=oci.ai_speech.models.CreateTranscriptionJobDetails(
            compartment_id=config_yaml['speech']['compartment_id'],
            input_location=oci.ai_speech.models.ObjectListFileInputLocation(
                location_type="OBJECT_LIST_FILE_INPUT_LOCATION", 
                object_location=oci.ai_speech.models.ObjectLocation(
                    namespace_name=config_yaml['speech']['namespace'],
                    bucket_name=config_yaml['speech']['bucket_name'],
                    object_names=[args.input_file])),  # Fixed: Use actual input file name
            output_location=oci.ai_speech.models.OutputLocation(
                namespace_name=config_yaml['speech']['namespace'],
                bucket_name=config_yaml['speech']['bucket_name'],
                prefix="transcriptions"),
            display_name=f"Transcription_{args.input_file}",
            description=f"transcription_job_{args.input_file.replace('.', '_')}",
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
    log_step(f"  • Status: {create_transcription_job_response.data.lifecycle_state}")
    log_step(f"  • Output will be saved to: {config_yaml['speech']['bucket_name']}/transcriptions/")
    
except Exception as e:
    log_step(f"Failed to create transcription job: {str(e)}", True)
    sys.exit(1)
