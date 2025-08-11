# OCI Subtitle Translation

## Introduction

In today's global digital landscape, making audio and video content accessible across different languages is crucial. This solution leverages OCI's AI services to automatically generate and translate subtitles for audio content into multiple languages.

The solution combines two powerful OCI services:
- **OCI Speech** to transcribe audio into text and generate SRT subtitle files
- **OCI Language** to translate the generated subtitles into multiple target languages

This automated approach significantly reduces the time and effort required to create multilingual subtitles, making content more accessible to a global audience.

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

3. Update `config.yaml` with your settings:
   ```yaml
   # Speech Service Configuration
   speech:
     compartment_id: "ocid1.compartment.oc1..your-compartment-id"
     bucket_name: "your-bucket-name"
     namespace: "your-namespace"

   # Language Translation Configuration
   language:
     compartment_id: "ocid1.compartment.oc1..your-compartment-id"
   ```

## 2. Usage

> Before running the script, make sure your input `.mp3` file has already been uploaded to the OCI Object Storage **input bucket** defined in your `config.yaml`.  
> The script does **not** accept local files it looks for the file in the cloud bucket only.

This solution works in two steps:

1. First, we generate SRT from audio:

   ```bash
   python generate_srt_from_audio.py --input-file your_audio.mp3
   ```

2. Then, we translate the generated SRT file to multiple languages:

   ```bash
   python translate_srt.py --input-file input.srt
   ```

## Annex: Supported Languages

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
