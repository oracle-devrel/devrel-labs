import oci
import datetime
import time

# Change this to create a job name automatically based on your own convention
def generate_job_name():
    current_date = datetime.date.today()
    current_time = datetime.datetime.now()
    # Create a unique file name with the current timestamp
    return f"job_{current_date.strftime('%Y-%m-%d')}T{current_time.strftime('%H-%M-%S')}"

# Use your own auth info .
oci_config = {
    "user": 'ocid1.user.oc1..aaaaaaaa3gj6ljlcbe37ua2dh6dcbhcrpuy7z4jqhrlvviz3qseuns75c',
    "key_file": '~/.oci/oci_api_key.pem',
    "fingerprint": 'c8:e8:5f:61:eb:f7:c0:14:46:fd:a1:63:3b:b8:78',
    "tenancy": 'ocid1.tenancy.oc1..aaaaaaaaawihvxgba2bzuk5lgauuvled5663n5n24mtulyup2ftfcghmk',
    "region": 'us-ashburn-1'
}
# OCID of the compartment where your job is going to be created
compartmentId = "ocid1.compartment.oc1..aaaaaaaapyjqsd6a7qg2nkubqlefmj7gvkcx7mjbggiacl6dirid5py6b"


## Upload your files to a bucket.
namespace_name = 'axecxhcuzme'
bucket_name = 'oci_file_translation_test'
# Input CSV files are here. Max size of single file is 20M, so you might need to split a file (1000 lines max for example)
prefix="source/synthetic"
# Translated CSV files are going to be stored in this folder
target_prefix="output/synthetic_multiple/"

# CSV column name start from 1. SYNTHETIC_VARIABLE_DICT_converted (Column M) is 13th for example.
translation_config = "{\"translation\":{\"csv\":{\"columnsToTranslate\":[13,22],\"csvDntHeaderRowCount\":true}}}"
source_lang = "en"
target_langs="fr,es"  # Any more languages?


oci.config.validate_config(oci_config)
print(f'imported oci version {oci.__version__}')
ai_client = oci.ai_language.AIServiceLanguageClient(config=oci_config)

# If you want to translate a specific file
#input_location = oci.ai_language.models.ObjectStorageFileNameLocation(
#    namespace_name=namespace_name, bucket_name=bucket_name,
#    object_names=[prefix+"/"+"synthetic_data_textgen_command_r_fusion_small.csv"])

# Or all files in a specific bucket (or a specific folder)
input_location = oci.ai_language.models.ObjectStoragePrefixLocation(
    namespace_name=namespace_name, bucket_name=bucket_name,
    prefix=prefix)

# Give the index of your column to translate (English version of local text)  - starting from 1 (not 0)

# Change the target language code
# nl for Dutch, de for German, ar for Arabic, fr for French, it for Italian
model_metadata_details = oci.ai_language.models.ModelMetadataDetails(
    model_type="PRE_TRAINED_TRANSLATION", language_code=source_lang,
    configuration = {"targetLanguageCodes":
                         oci.ai_language.models.ConfigurationDetails(configuration_map={"languageCodes":target_langs}),
                     "properties":
                         oci.ai_language.models.ConfigurationDetails(configuration_map={
                             "advancedProperties":translation_config})})

# Give the output location.
# Can be a different bucket or a different folder in the same bucket
output_location = oci.ai_language.models.ObjectPrefixOutputLocation(
    namespace_name=namespace_name, bucket_name=bucket_name, prefix=target_prefix)

createJobDetails = oci.ai_language.models.CreateJobDetails(display_name=generate_job_name(), description=None,
                                                            compartment_id=compartmentId,
                                                            input_location=input_location,
                                                            model_metadata_details=[model_metadata_details],
                                                            output_location=output_location)

createJobOutput = ai_client.create_job(create_job_details=createJobDetails)
print(f"created a job {createJobOutput.data.display_name}")


# Just quick using Control-C if your job is going to take long (i.e. thousands of lines)
# You can check the output of the translation job in the OCI console
#  Console ==> Choose region ==> AI ==> Language ==> Job ==> Choose a right compartment
getJobOutput = ai_client.get_job(job_id=createJobOutput.data.id)
while getJobOutput.data.lifecycle_state  in ('ACCEPTED', 'IN_PROGRESS'):
    print(f"{datetime.datetime.now()}: waiting for the job to complete")
    time.sleep(5);
    getJobOutput = ai_client.get_job(job_id=createJobOutput.data.id)
print(f'{datetime.datetime.now()}: job {getJobOutput.data.display_name} for {getJobOutput.data.total_documents} files completed. status is: {getJobOutput.data.lifecycle_state}');
