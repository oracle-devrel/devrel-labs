# OCI Subtitle Translation

## Introduction

In today's global digital landscape, making audio and video content accessible across different languages is crucial. This solution leverages OCI's AI services to automatically generate and translate subtitles for audio content into multiple languages.

The solution combines two powerful OCI services:
- **OCI Speech** to transcribe audio into text and generate SRT subtitle files
- **OCI Language** to translate the generated subtitles into multiple target languages

This automated approach significantly reduces the time and effort required to create multilingual subtitles, making content more accessible to a global audience.

## Features

- **Flexible Input Sources**: Accept both local audio files (MP3, WAV, etc.) and files already stored in OCI Object Storage
- **Multiple Output Options**: Store generated SRT files locally, in Object Storage, or both
- **Complete Workflow**: Single command to transcribe audio and translate to multiple languages
- **Standalone Scripts**: Individual scripts for transcription-only or translation-only workflows
- **Translation Methods**: 
  - Synchronous translation for smaller files (subtitle-by-subtitle)
  - Batch translation for larger files (up to 20MB)
- **Language Support**: 30+ supported languages for translation
- **Configurable**: Comprehensive YAML configuration with sensible defaults

## 0. Prerequisites and setup

### Prerequisites

- Python 3.8 or higher
- OCI Account with Speech and Language services enabled
- Required IAM Policies and Permissions
- Object Storage bucket for input/output files
- OCI CLI configured with proper credentials

### Setup

1. Create an OCI account if you don't have one
2. Enable OCI Speech and Language services in your tenancy
3. Set up OCI CLI and create API keys:
   ```bash
   # Install OCI CLI
   bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
   
   # Configure OCI CLI (this will create ~/.oci/config)
   oci setup config
   ```
4. Set up the appropriate IAM policies to use both OCI Speech and Language services
5. Create a bucket in OCI Object Storage for your audio files and generated subtitles
6. Take note of your Object Storage namespace (visible in the OCI Console under Object Storage)

### Docs

- [OCI Speech Service Documentation](https://docs.oracle.com/en-us/iaas/api/#/en/speech/20220101)
- [OCI Language Translation Documentation](https://docs.oracle.com/en-us/iaas/language)
- [OCI SDK Documentation](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm)

## 1. Getting Started

1. Clone this repository:
   ```bash
   git clone https://github.com/oracle-devrel/devrel-labs.git
   cd oci-subtitle-translation
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example configuration and update with your settings:
   ```bash
   cp config_example.yaml config.yaml
   # Edit config.yaml with your OCI details
   ```

## 2. Usage

The solution provides three main ways to use it:

### Option 1: Complete Workflow (Recommended)

Use the main workflow script to transcribe audio and translate in one command:

```bash
# Transcribe local audio file and translate to multiple languages
python workflow.py --audio-source audio.mp3 --target-languages es fr de

# Use audio file already in Object Storage
python workflow.py --audio-source "audio/myfile.mp3" --target-languages es fr de pt

# Transcribe only (no translation)
python workflow.py --transcribe-only --audio-source audio.mp3

# Translate only (use existing SRT file)
python workflow.py --translate-only --srt-file subtitles.srt --target-languages es fr
```

### Option 2: Individual Scripts

Use individual scripts for specific tasks:

#### Transcription Only

```bash
# Transcribe local audio file
python generate_srt_from_audio.py --input-file audio.mp3

# Transcribe with specific language
python generate_srt_from_audio.py --input-file audio.mp3 --language es-ES

# Output to local only
python generate_srt_from_audio.py --input-file audio.mp3 --output-type local
```

#### Translation Only

```bash
# Translate local SRT file to multiple languages
python translate_srt.py --input-file subtitles.srt --target-languages es fr de

# Use synchronous translation method
python translate_srt.py --input-file subtitles.srt --target-languages es --method sync

# Translate SRT file in Object Storage
python translate_srt.py --input-file "srt_files/subtitles.srt" --target-languages es fr
```

## 3. Configuration

The `config.yaml` file controls all aspects of the workflow. Key sections include:

### Speech Configuration
```yaml
speech:
  compartment_id: "ocid1.compartment.oc1..your-compartment-id"
  bucket_name: "your-speech-bucket-name"
  namespace: "your-namespace"
  language_code: "en-US"  # Default transcription language
```

### Output Configuration
```yaml
output:
  storage_type: "both"  # "local", "object_storage", or "both"
  local_directory: "./output"
  object_storage_prefix: "translations"
```

### Translation Configuration
```yaml
translation:
  target_languages:
    - "es"    # Spanish
    - "fr"    # French
    - "de"    # German
  method: "batch"  # "batch" or "sync"
```

## 4. Supported Languages

### Speech-to-Text (Transcription)

The following language codes are supported for audio transcription:

| Language | Code |
|----------|------|
| US English | en-US |
| British English | en-GB |
| Australian English | en-AU |
| Indian English | en-IN |
| Spanish (Spain) | es-ES |
| Brazilian Portuguese | pt-BR |
| Hindi (India) | hi-IN |
| French (France) | fr-FR |
| German (Germany) | de-DE |
| Italian (Italy) | it-IT |

### Translation

The solution supports translation to the following languages:

| Language | Language Code |
|----------|------|
| Arabic | ar |
| Croatian | hr |
| Czech | cs |
| Danish | da |
| Dutch | nl |
| English | en |
| Finnish | fi |
| French | fr |
| French Canadian | fr-CA |
| German | de |
| Greek | el |
| Hebrew | he |
| Hungarian | hu |
| Italian | it |
| Japanese | ja |
| Korean | ko |
| Norwegian | no |
| Polish | pl |
| Portuguese | pt |
| Portuguese Brazilian | pt-BR |
| Romanian | ro |
| Russian | ru |
| Simplified Chinese | zh-CN |
| Slovak | sk |
| Slovenian | sl |
| Spanish | es |
| Swedish | sv |
| Thai | th |
| Traditional Chinese | zh-TW |
| Turkish | tr |
| Vietnamese | vi |

For an updated list of supported languages, refer to [the OCI Documentation](https://docs.oracle.com/en-us/iaas/language/using/translate.htm#supported-langs).

## 5. Advanced Usage

### Custom Configuration Files

```bash
# Use a different configuration file
python workflow.py --config my-config.yaml --audio-source audio.mp3
```

### Working with Object Storage

```bash
# Use files already in Object Storage (no local upload needed)
python workflow.py --audio-source "audio/recording.mp3" --target-languages es fr

# Store output only in Object Storage
python generate_srt_from_audio.py --input-file audio.mp3 --output-type object_storage
```

### Translation Methods

**Batch Translation** (default):
- Best for larger files (up to 20MB)
- More efficient for multiple languages
- Uses OCI Language batch processing

**Synchronous Translation**:
- Best for smaller files or individual subtitles
- Processes subtitle by subtitle
- More reliable for very small files

```bash
# Force synchronous translation
python translate_srt.py --input-file subtitles.srt --target-languages es --method sync
```

### Troubleshooting

1. **Authentication Issues**: Ensure your OCI CLI is properly configured
   ```bash
   oci iam user get --user-id $(oci iam user list --query 'data[0].id' --raw-output)
   ```

2. **File Size Limits**: 
   - Audio files: No specific limit for OCI Speech
   - SRT files for batch translation: 20MB maximum
   - Large files automatically fall back to synchronous translation

3. **Output Directory**: The solution automatically creates output directories as needed

## 6. Architecture

The solution consists of modular components:

- **workflow.py**: Main orchestration script
- **generate_srt_from_audio.py**: OCI Speech service integration
- **translate_srt.py**: OCI Language service integration

This modular design allows you to:
- Use individual components as needed
- Integrate with existing workflows
- Customize functionality for specific requirements

## Supported Language Codes

For the Speech-to-Text transcription service with GENERIC domain, the following language codes are supported:

| Language | Code |
|----------|------|
| US English | en-US |
| British English | en-GB |
| Australian English | en-AU |
| Indian English | en-IN |
| Spanish (Spain) | es-ES |
| Brazilian Portuguese | pt-BR |
| Hindi (India) | hi-IN |
| French (France) | fr-FR |
| German (Germany) | de-DE |
| Italian (Italy) | it-IT |

Note: When using the service, make sure to use the exact language code format as shown above. Simple codes like 'en' or 'es' will not work.

## Contributing

This project is open source. Please submit your contributions by forking this repository and submitting a pull request! Oracle appreciates any contributions that are made by the open source community.

## License

Copyright (c) 2024 Oracle and/or its affiliates.

Licensed under the Universal Permissive License (UPL), Version 1.0.

See [LICENSE](../LICENSE) for more details.

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK. 
