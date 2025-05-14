#!/usr/bin/env python3

"""
Batch Translation Limitations:
- Maximum 100 records/documents per batch
- Each document must be less than 5000 characters
- Total character limit across all documents: 20,000 characters
- Supported file formats: plain text
"""

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
            return config
    except Exception as e:
        print(f"✗ Error loading config.yaml: {str(e)}")
        sys.exit(1)

def load_sample_texts(filename="sample_texts.txt"):
    """Load text documents from file, one per line"""
    try:
        print(f"\nLoading texts from {filename}...")
        with open(filename, 'r', encoding='utf-8') as file:
            # Filter out empty lines and strip whitespace
            texts = [line.strip() for line in file if line.strip()]
            print(f"✓ Successfully loaded {len(texts)} texts")
            
            # Print character count statistics
            total_chars = sum(len(text) for text in texts)
            avg_chars = total_chars / len(texts) if texts else 0
            print(f"  • Total characters: {total_chars:,}")
            print(f"  • Average characters per text: {avg_chars:.1f}")
            
            # Check against limitations
            if len(texts) > 100:
                print("⚠ Warning: Number of texts exceeds 100 limit")
            if total_chars > 20000:
                print("⚠ Warning: Total characters exceed 20,000 limit")
            for i, text in enumerate(texts, 1):
                if len(text) > 5000:
                    print(f"⚠ Warning: Text {i} exceeds 5,000 character limit")
            
            return texts
    except Exception as e:
        print(f"✗ Error loading sample texts: {str(e)}")
        print("Using default sample texts instead...")
        return [
            "This is the first document to translate.",
            "Here is another document that needs translation.",
            "And a third document with some more text."
        ]

def init_client():
    """Initialize OCI AI Language client"""
    try:
        print("\nInitializing OCI AI Language client...")
        config = oci.config.from_file(profile_name="comm")
        client = oci.ai_language.AIServiceLanguageClient(config=config)
        print("✓ Client initialized successfully")
        return client
    except Exception as e:
        print(f"✗ Error initializing OCI client: {str(e)}")
        sys.exit(1)

def translate_batch_documents(ai_client, documents, source_language, target_language, compartment_id):
    """Translate a batch of documents using OCI Language service"""
    try:
        start_time = time.time()
        print(f"\nPreparing {len(documents)} documents for translation...")
        print(f"  • Source language: {source_language}")
        print(f"  • Target language: {target_language}")
        
        # Prepare the documents for translation
        text_documents = [
            oci.ai_language.models.TextDocument(
                key=f"doc_{i}",
                text=doc,
                language_code=source_language
            ) for i, doc in enumerate(documents)
        ]
        print("✓ Documents prepared successfully")

        # Create batch translation request
        batch_translation_details = oci.ai_language.models.BatchLanguageTranslationDetails(
            documents=text_documents,
            compartment_id=compartment_id,
            target_language_code=target_language
        )

        # Send translation request
        print("\nSending batch translation request...")
        response = ai_client.batch_language_translation(
            batch_language_translation_details=batch_translation_details
        )
        print("✓ Translation request sent successfully")

        # Process results
        results = []
        if response and response.data and response.data.documents:
            success_count = 0
            for doc in response.data.documents:
                if doc.translated_text:
                    success_count += 1
                results.append(doc.translated_text if doc.translated_text else None)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"\n✓ Translation completed in {duration:.1f} seconds")
            print(f"  • Successfully translated: {success_count}/{len(documents)} documents")
            print(f"  • Success rate: {(success_count/len(documents))*100:.1f}%")
            
            return results
        else:
            print("\n✗ No translation results received")
            return None

    except Exception as e:
        print(f"\n✗ Error during batch translation: {str(e)}")
        return None

def main():
    try:
        start_time = time.time()
        print("=" * 60)
        print("OCI Language Batch Text Translation".center(60))
        print("=" * 60)
        
        # Load configuration
        config = load_config()
        
        # Get configuration values
        compartment_id = config["language_translation"]["compartment_id"]
        source_language = config["language_translation"]["source_language"]
        target_language = config["language_translation"]["target_language"]

        # Initialize client
        ai_client = init_client()

        # Load documents from file
        documents = load_sample_texts()

        # Translate documents
        translated_texts = translate_batch_documents(
            ai_client, 
            documents, 
            source_language, 
            target_language, 
            compartment_id
        )

        # Print results
        if translated_texts:
            print("\nDetailed Translation Results:")
            print("-" * 60)
            for i, (original, translated) in enumerate(zip(documents, translated_texts), 1):
                print(f"\nDocument {i}:")
                print(f"Original  ({source_language}): {original}")
                if translated:
                    print(f"Translated ({target_language}): {translated}")
                else:
                    print("✗ Translation failed")
                print("-" * 60)
        else:
            print("\n✗ Translation process failed")
        
        end_time = time.time()
        total_duration = end_time - start_time
        print(f"\nTotal execution time: {total_duration:.1f} seconds")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 