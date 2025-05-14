#!/usr/bin/env python3

import oci
import datetime
import time
import sys
import json
import yaml
import os
import pandas as pd
from pathlib import Path

import logging
# Enable debug logging
logging.getLogger('oci').setLevel(logging.DEBUG)

def generate_job_name():
    """Generate a unique job name with timestamp"""
    current_date = datetime.date.today()
    current_time = datetime.datetime.now()
    return f"translation_job_{current_date.strftime('%Y-%m-%d')}T{current_time.strftime('%H-%M-%S')}"

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config.yaml: {str(e)}")
        sys.exit(1)

def translate_csv(ai_client, input_file, output_file, columns_to_translate, source_language, target_language, compartment_id, namespace, bucket):
    """Translate specific columns in a CSV file using OCI Language service"""
    try:
        # Create the translation configuration for CSV
        translation_config = {
            "translation": {
                "csv": {
                    "columnsToTranslate": columns_to_translate,
                    "csvDntHeaderRowCount": True
                }
            }
        }

        # Create input location
        input_location = oci.ai_language.models.ObjectStorageFileNameLocation(
            namespace_name=namespace,
            bucket_name=bucket,
            object_names=[input_file]
        )

        #input_location = oci.ai_language.models.ObjectStoragePrefixLocation(
        #    namespace_name=namespace,
        #    bucket_name=bucket,
        #)

        # Set up model metadata
        model_metadata_details = oci.ai_language.models.ModelMetadataDetails(
            model_type="PRE_TRAINED_TRANSLATION",
            language_code=source_language,
            configuration={
                "targetLanguageCodes": oci.ai_language.models.ConfigurationDetails(
                    configuration_map={"languageCodes": target_language}
                ),
                "properties": oci.ai_language.models.ConfigurationDetails(
                    configuration_map={"advancedProperties": json.dumps(translation_config)}
                )
            }
        )

        # Set up output location
        output_location = oci.ai_language.models.ObjectPrefixOutputLocation(
            namespace_name=namespace,
            bucket_name=bucket,
            prefix=output_file
        )

        # Create and submit translation job
        create_job_details = oci.ai_language.models.CreateJobDetails(
            display_name=generate_job_name(),
            compartment_id=compartment_id,
            input_location=input_location,
            model_metadata_details=[model_metadata_details],
            output_location=output_location
        )

        job_response = ai_client.create_job(create_job_details=create_job_details)
        print(f"Created translation job: {job_response.data.display_name}")

        # Monitor job status
        job_id = job_response.data.id
        while True:
            job_status = ai_client.get_job(job_id=job_id)
            current_state = job_status.data.lifecycle_state
            print(f"{datetime.datetime.now()}: Job status: {current_state}")
            
            if current_state in ["SUCCEEDED", "FAILED"]:
                break
            time.sleep(5)

        if current_state == "SUCCEEDED":
            print(f"Translation completed successfully! Check {output_file} for results")
            return True
        else:
            print(f"Translation failed with status: {current_state}")
            return False

    except Exception as e:
        print(f"Error during CSV translation: {str(e)}")
        return False

def translate_json(ai_client, input_file, output_file, keys_to_translate, source_language, target_language, compartment_id, namespace, bucket):
    """Translate specific keys in a JSON file using OCI Language service"""
    try:
        # Create the translation configuration for JSON
        translation_config = {
            "translation": {
                "json": {
                    "keysToTranslate": keys_to_translate
                }
            }
        }

        # Create input location
        input_location = oci.ai_language.models.ObjectStorageFileNameLocation(
            namespace_name=namespace,
            bucket_name=bucket,
            object_names=[input_file]
        )

        # Set up model metadata
        model_metadata_details = oci.ai_language.models.ModelMetadataDetails(
            model_type="PRE_TRAINED_TRANSLATION",
            language_code=source_language,
            configuration={
                "targetLanguageCodes": oci.ai_language.models.ConfigurationDetails(
                    configuration_map={"languageCodes": target_language}
                ),
                "properties": oci.ai_language.models.ConfigurationDetails(
                    configuration_map={"advancedProperties": json.dumps(translation_config)}
                )
            }
        )

        # Set up output location
        output_location = oci.ai_language.models.ObjectPrefixOutputLocation(
            namespace_name=namespace,
            bucket_name=bucket,
            prefix=output_file
        )

        # Create and submit translation job
        create_job_details = oci.ai_language.models.CreateJobDetails(
            display_name=generate_job_name(),
            compartment_id=compartment_id,
            input_location=input_location,
            model_metadata_details=[model_metadata_details],
            output_location=output_location
        )

        job_response = ai_client.create_job(create_job_details=create_job_details)
        print(f"Created translation job: {job_response.data.display_name}")

        # Monitor job status
        job_id = job_response.data.id
        while True:
            job_status = ai_client.get_job(job_id=job_id)
            current_state = job_status.data.lifecycle_state
            print(f"{datetime.datetime.now()}: Job status: {current_state}")
            
            if current_state in ["SUCCEEDED", "FAILED"]:
                print('Job ID {}'.format(job_id))
                break
            time.sleep(5)

        if current_state == "SUCCEEDED":
            print(f"Translation completed successfully! Check {output_file} for results")
            return True
        else:
            print(f"Translation failed with status: {current_state}")
            return False

    except Exception as e:
        print(f"Error during JSON translation: {str(e)}")
        return False

def main():
    try:
        if len(sys.argv) < 5:
            print("Usage: python csv_json_translation.py <file_type> <input_file> <output_file> <items_to_translate...>")
            sys.exit(1)

        file_type = sys.argv[1].lower()
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        items_to_translate = sys.argv[4:]

        # Load configuration
        config = load_config()
        
        # Initialize OCI client using default config
        oci_config = oci.config.from_file(profile_name="comm")
        ai_client = oci.ai_language.AIServiceLanguageClient(config=oci_config)

        # Get configuration values
        source_language = os.getenv("OCI_SOURCE_LANG", config["language_translation"]["source_language"])
        target_language = os.getenv("OCI_TARGET_LANG", config["language_translation"]["target_language"])
        compartment_id = os.getenv("OCI_COMPARTMENT_ID", config["language_translation"]["compartment_id"])
        namespace = config["object_storage"]["namespace"]
        bucket = config["object_storage"]["bucket_name"]

        if not compartment_id:
            print("Error: OCI_COMPARTMENT_ID environment variable or compartment_id in config.yaml is required")
            sys.exit(1)

        if file_type == "csv":
            # Convert column numbers to integers
            columns = [int(col) for col in items_to_translate]
            success = translate_csv(ai_client, input_file, output_file, columns, 
                                 source_language, target_language, compartment_id,
                                 namespace, bucket)
        elif file_type == "json":
            success = translate_json(ai_client, input_file, output_file, items_to_translate, 
                                  source_language, target_language, compartment_id,
                                  namespace, bucket)
        else:
            print("Unsupported file type. Please use 'csv' or 'json'")
            sys.exit(1)

        if not success:
            sys.exit(1)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
