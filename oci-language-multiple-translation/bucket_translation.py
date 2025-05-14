import oci
import yaml
import sys
import time
import datetime
from pathlib import Path

def load_config():
    """Load configuration from config.yaml file"""
    try:
        print("Loading configuration from config.yaml...")
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)
            print("✓ Configuration loaded successfully")
            print(f"  • Source bucket: {config['language_translation']['source_bucket']}")
            print(f"  • Target bucket: {config['language_translation']['target_bucket']}")
            return config
    except Exception as e:
        print(f"✗ Error loading config.yaml: {str(e)}")
        sys.exit(1)

def init_clients():
    """Initialize OCI clients"""
    try:
        print("\nInitializing OCI clients...")
        config = oci.config.from_file()
        ai_client = oci.ai_language.AIServiceLanguageClient(config=config)
        object_storage = oci.object_storage.ObjectStorageClient(config=config)
        print("✓ AI Language client initialized")
        print("✓ Object Storage client initialized")
        return ai_client, object_storage
    except Exception as e:
        print(f"✗ Error initializing OCI clients: {str(e)}")
        sys.exit(1)

def generate_job_name():
    """Generate a unique job name with timestamp"""
    current_date = datetime.date.today()
    current_time = datetime.datetime.now()
    return f"translation_job_{current_date.strftime('%Y-%m-%d')}T{current_time.strftime('%H-%M-%S')}"

def list_bucket_objects(object_storage, namespace, bucket_name):
    """List objects in a bucket"""
    try:
        print(f"\nListing objects in bucket '{bucket_name}'...")
        response = object_storage.list_objects(
            namespace_name=namespace,
            bucket_name=bucket_name
        )
        objects = [obj.name for obj in response.data.objects]
        print(f"✓ Found {len(objects)} objects:")
        for obj in objects:
            print(f"  • {obj}")
        return objects
    except Exception as e:
        print(f"✗ Error listing bucket objects: {str(e)}")
        return []

def translate_documents(ai_client, object_storage, config):
    """Translate all documents in the source bucket"""
    try:
        start_time = time.time()
        
        # Get configuration values
        compartment_id = config["language_translation"]["compartment_id"]
        source_bucket = config["language_translation"]["source_bucket"]
        target_bucket = config["language_translation"]["target_bucket"]
        source_language = config["language_translation"]["source_language"]
        target_language = config["language_translation"]["target_language"]
        
        # Get namespace
        namespace = object_storage.get_namespace().data
        print(f"\nUsing Object Storage namespace: {namespace}")
        
        # List source bucket contents
        source_objects = list_bucket_objects(object_storage, namespace, source_bucket)
        if not source_objects:
            print("✗ No files found in source bucket. Please upload some files first.")
            return False
        
        print(f"\nPreparing translation job...")
        print(f"  • Source language: {source_language}")
        print(f"  • Target language: {target_language}")
        print(f"  • Files to translate: {len(source_objects)}")
        
        # Create input location for all files in the bucket
        input_location = oci.ai_language.models.ObjectStoragePrefixLocation(
            namespace_name=namespace,
            bucket_name=source_bucket
        )

        # Set up model metadata for translation
        model_metadata_details = oci.ai_language.models.ModelMetadataDetails(
            model_type="PRE_TRAINED_TRANSLATION",
            language_code=source_language,
            configuration={
                "targetLanguageCodes": oci.ai_language.models.ConfigurationDetails(
                    configuration_map={"languageCodes": target_language}
                )
            }
        )

        # Set up output location
        output_location = oci.ai_language.models.ObjectPrefixOutputLocation(
            namespace_name=namespace,
            bucket_name=target_bucket
        )

        # Create job details
        job_name = generate_job_name()
        create_job_details = oci.ai_language.models.CreateJobDetails(
            display_name=job_name,
            compartment_id=compartment_id,
            input_location=input_location,
            model_metadata_details=[model_metadata_details],
            output_location=output_location
        )
        
        # Create and submit translation job
        print(f"\nCreating translation job '{job_name}'...")
        job_response = ai_client.create_job(
            create_job_details=create_job_details
        )
        
        job_id = job_response.data.id
        print(f"✓ Translation job created with ID: {job_id}")
        
        # Monitor job status
        print("\nMonitoring translation progress...")
        while True:
            job_status = ai_client.get_job(job_id=job_id)
            current_state = job_status.data.lifecycle_state
            print(f"  • {datetime.datetime.now().strftime('%H:%M:%S')}: Job status: {current_state}")
            
            if current_state in ["SUCCEEDED", "FAILED"]:
                break
            time.sleep(30)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if current_state == "SUCCEEDED":
            print(f"\n✓ Translation completed successfully in {duration:.1f} seconds!")
            print(f"  • Translated files will be available in the '{target_bucket}' bucket")
            print(f"  • Files will have the same names with language code suffix")
            return True
        else:
            print(f"\n✗ Translation failed after {duration:.1f} seconds")
            print(f"  • Final status: {current_state}")
            return False
        
    except Exception as e:
        print(f"\n✗ Error during translation: {str(e)}")
        return False

def main():
    try:
        start_time = time.time()
        print("=" * 70)
        print("OCI Language Multiple Document Translation".center(70))
        print("=" * 70)
        
        # Load OCI configuration
        config = load_config()
        
        # Initialize clients
        ai_client, object_storage = init_clients()
        
        # Start translation
        success = translate_documents(ai_client, object_storage, config)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print("\nSummary:")
        print("-" * 70)
        if success:
            print("✓ Translation job completed successfully")
        else:
            print("✗ Translation job failed")
        print(f"Total execution time: {total_duration:.1f} seconds")
        print("=" * 70)
            
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
