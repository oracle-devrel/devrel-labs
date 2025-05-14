# OCI Language Translation Tools

## Introduction

This repository contains two powerful tools for leveraging OCI Language Translation services:

1. **Bulk Document Translation**: Automatically translate multiple documents stored in an OCI Object Storage bucket. This tool supports various document formats and maintains the original file structure in the target bucket.

2. **CSV/JSON Field Translation**: Selectively translate specific columns in CSV files or keys in JSON documents while preserving the original structure. This is particularly useful for localizing data files while maintaining their format and untranslated fields.

## Prerequisites

- Python 3.8 or higher
- OCI Account with Language Translation service enabled
- Required IAM Policies and Permissions
- Object Storage buckets (for document translation)
- OCI CLI configured with proper credentials

### OCI Setup Requirements

1. Create an OCI account if you don't have one
2. Enable Language Translation service in your tenancy
3. Set up OCI CLI and create API keys:
   ```bash
   # Install OCI CLI
   bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
   
   # Configure OCI CLI (this will create ~/.oci/config)
   oci setup config
   ```
4. Set up appropriate IAM policies
5. Create source and target buckets in Object Storage (for document translation)
6. Note your Object Storage namespace (visible in the OCI Console under Object Storage)

## Getting Started

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd oci-language-translation
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the environment (optional - can be set in config.yaml instead):
   ```bash
   # Optional - all these values can be set in config.yaml
   export OCI_COMPARTMENT_ID="ocid1.compartment.oc1..your-compartment-id"
   export OCI_SOURCE_LANG="en"
   export OCI_TARGET_LANG="es"
   ```

4. Update `config.yaml` with your translation and storage settings:
   ```yaml
   # Language Translation Service Configuration
   language_translation:
     compartment_id: "ocid1.compartment.oc1..your-compartment-id"
     source_bucket: "source-bucket-name"
     target_bucket: "target-bucket-name"
     source_language: "en"  # ISO language code
     target_language: "es"  # ISO language code

   # Object Storage Configuration
   object_storage:
     namespace: "your-namespace"  # Your tenancy's Object Storage namespace
     bucket_name: "your-bucket-name"  # Bucket for CSV/JSON translations
   ```

5. For bulk document translation:
   ```bash
   python bucket_translation.py
   ```

6. For CSV/JSON translation:
   ```bash
   # For CSV files (column numbers start from 1)
   python csv_json_translation.py csv input.csv output.csv 1 2 3

   # For JSON files
   python csv_json_translation.py json input.json output.json key1 key2
   ```

## Usage Examples

### Bulk Document Translation
```bash
# Translate all documents from source bucket to target bucket
python bucket_translation.py
```

### CSV Translation
```bash
# Translate columns 1, 3, and 5 from English to Spanish
python csv_json_translation.py csv products.csv products_es.csv 1 3 5
```

### JSON Translation
```bash
# Translate 'name' and 'details' fields in a JSON file
python csv_json_translation.py json catalog.json catalog_es.json name details
```

## Configuration

The project uses three types of configuration:

1. **OCI Configuration** (`~/.oci/config`):
   - Created automatically by `oci setup config`
   - Contains your OCI authentication details
   - Used for API authentication

2. **Translation Configuration** (`config.yaml`):
   ```yaml
   # Language Translation Service Configuration
   language_translation:
     compartment_id: "ocid1.compartment.oc1..your-compartment-id"
     source_bucket: "source-bucket-name"
     target_bucket: "target-bucket-name"
     source_language: "en"
     target_language: "es"

   # Object Storage Configuration
   object_storage:
     namespace: "your-namespace"  # Your tenancy's Object Storage namespace
     bucket_name: "your-bucket-name"  # Bucket for CSV/JSON translations
   ```

3. **Environment Variables** (optional, override config.yaml):
   - `OCI_COMPARTMENT_ID`: Your OCI compartment OCID
   - `OCI_SOURCE_LANG`: Source language code
   - `OCI_TARGET_LANG`: Target language code

### Configuration Priority

The configuration values are loaded in the following priority order:
1. Environment variables (if set)
2. Values from config.yaml
3. Default values (for language codes only: en -> es)

## Supported Languages

The service supports a wide range of languages. Common language codes include:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Chinese Simplified (zh-CN)
- Japanese (ja)

For a complete list of supported languages, refer to [the OCI Documentation](https://docs.oracle.com/en-us/iaas/language/using/translate.htm#supported-langs).

## Error Handling

Both tools include comprehensive error handling:
- Configuration validation
- Service availability checks
- File format validation
- Translation status monitoring

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.