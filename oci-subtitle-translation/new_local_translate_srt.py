import oci
import yaml
import argparse
import os
from pathlib import Path

def load_config():
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def translate_text(language_client, text, source_lang, target_lang, compartment_id):
    """
    Translates a string of text using a direct, synchronous API call.
    """
    try:
        # The source language is specified inside each document.
        documents = [oci.ai_language.models.TextDocument(
            key="1", 
            text=text, 
            language_code=source_lang
        )]

        # Create the details object for the synchronous batch call.
        batch_details = oci.ai_language.models.BatchLanguageTranslationDetails(
            documents=documents,
            target_language_code=target_lang,
            compartment_id=compartment_id
        )

        # Make the API call. This is a blocking call and returns the result directly.
        response = language_client.batch_language_translation(
            batch_language_translation_details=batch_details
        )
        
        # Check for success and return the translated text.
        if response.status == 200 and response.data.documents:
            print(f"Successfully translated to {target_lang}")
            return response.data.documents[0].translated_text
        else:
            print(f"Error during translation to {target_lang}: {response.data}")
            return None

    except oci.exceptions.ServiceError as e:
        print(f"Error translating to {target_lang}: {e}")
        return None

def main():
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

    parser = argparse.ArgumentParser(description='Translate SRT files using OCI Language')
    parser.add_argument('--input-file', required=True, help='Input SRT file path')
    parser.add_argument('--source-lang', default='en', help='Source language code')
    parser.add_argument('--target-langs', nargs='+', help='Target language codes (space-separated)')
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file {args.input_file} not found")
        return

    # Load YAML configuration
    config_yaml = load_config()
    language_compartment_id = config_yaml['language']['compartment_id']

    # Load OCI config from the profile specified in the YAML
    profile_name = config_yaml.get("profile", "DEFAULT")
    try:
        oci_config = oci.config.from_file(profile_name=profile_name)
        region = oci_config.get("region", "unknown")
        print(f"INFO: Loaded OCI profile '{profile_name}' (region '{region}')")
    except Exception as e:
        print(f"ERROR: Failed to load OCI configuration: {e}")
        return

    # Initialize client
    language_client = oci.ai_language.AIServiceLanguageClient(oci_config)
    
    # Read the content of the source SRT file
    source_text = input_path.read_text(encoding='utf-8')
    
    target_langs = args.target_langs if args.target_langs else SUPPORTED_LANGUAGES.keys()

    for lang_code in target_langs:
        if lang_code not in SUPPORTED_LANGUAGES:
            print(f"Warning: Unsupported language code '{lang_code}', skipping...")
            continue
        
        if lang_code != args.source_lang:
            print(f"Translating to {SUPPORTED_LANGUAGES[lang_code]} ({lang_code})...")
            
            translated_text = translate_text(
                language_client,
                source_text,
                args.source_lang,
                lang_code,
                language_compartment_id
            )
            
            if translated_text:
                # Save the translated text to a new file
                output_filename = f"{lang_code}_{input_path.name}"
                Path(output_filename).write_text(translated_text, encoding='utf-8')
                print(f"Saved translated file to: {output_filename}")


if __name__ == "__main__":
    main()
