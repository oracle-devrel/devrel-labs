#!/usr/bin/env python3
"""
Complete Subtitle Workflow Script

This script provides a unified interface to:
1. Transcribe audio files to SRT subtitles using OCI Speech
2. Translate SRT files to multiple languages using OCI Language

Can be used for the complete workflow or individual steps.
"""

import argparse
import os
import sys
import yaml
import subprocess
from datetime import datetime


def log_step(message, is_error=False):
    """Print a formatted log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "ERROR" if is_error else "INFO"
    print(f"[{timestamp}] {prefix}: {message}")


def load_config(config_file='config.yaml'):
    """Load configuration from YAML file"""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        log_step(f"Configuration file {config_file} not found", True)
        log_step("Please copy config_example.yaml to config.yaml and update with your settings", True)
        return None
    except Exception as e:
        log_step(f"Failed to load configuration: {str(e)}", True)
        return None


def run_transcription(args, config):
    """Run the transcription workflow"""
    log_step("Starting transcription workflow...")
    
    cmd = [
        "python", "generate_srt_from_audio.py",
        "--input-file", args.audio_source
    ]
    
    if args.speech_language:
        cmd.extend(["--language", args.speech_language])
    
    if args.output_type:
        cmd.extend(["--output-type", args.output_type])
    
    if args.config != 'config.yaml':
        cmd.extend(["--config", args.config])
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        log_step("Transcription completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        log_step(f"Transcription failed: {e}", True)
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def run_translation(args, config):
    """Run the translation workflow"""
    log_step("Starting translation workflow...")
    
    cmd = [
        "python", "translate_srt.py",
        "--input-file", args.srt_file,
        "--source-language", args.source_language
    ]
    
    if args.target_languages:
        cmd.extend(["--target-languages"] + args.target_languages)
    
    if args.translation_method:
        cmd.extend(["--method", args.translation_method])
    
    if args.output_type:
        cmd.extend(["--output-type", args.output_type])
    
    if args.config != 'config.yaml':
        cmd.extend(["--config", args.config])
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        log_step("Translation completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        log_step(f"Translation failed: {e}", True)
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def find_generated_srt(config, audio_file):
    """Find the SRT file generated from audio transcription"""
    # Check local output directory first
    output_dir = config.get('output', {}).get('local_directory', './output')
    audio_filename = os.path.basename(audio_file)
    base_name = os.path.splitext(audio_filename)[0]
    
    # Look for SRT file with similar name
    if os.path.exists(output_dir):
        for file in os.listdir(output_dir):
            if file.endswith('.srt') and base_name in file:
                return os.path.join(output_dir, file)
    
    # If not found locally, assume it's in object storage with standard naming
    return f"transcriptions/{audio_filename}/{audio_filename}.srt"


def main():
    parser = argparse.ArgumentParser(
        description='Complete OCI Subtitle Translation Workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Complete workflow: transcribe and translate
  python workflow.py --audio-source audio.mp3 --target-languages es fr de

  # Transcription only
  python workflow.py --transcribe-only --audio-source audio.mp3

  # Translation only
  python workflow.py --translate-only --srt-file subtitles.srt --target-languages es fr

  # Use specific languages and methods
  python workflow.py --audio-source audio.mp3 --speech-language es-ES --target-languages en fr --translation-method sync
        """
    )
    
    # Workflow control
    workflow_group = parser.add_mutually_exclusive_group()
    workflow_group.add_argument('--transcribe-only', action='store_true',
                               help='Only perform transcription (no translation)')
    workflow_group.add_argument('--translate-only', action='store_true',
                               help='Only perform translation (no transcription)')
    
    # Transcription options
    parser.add_argument('--audio-source', type=str,
                       help='Audio file path (local file or Object Storage object name)')
    parser.add_argument('--speech-language', type=str,
                       help='Language code for speech transcription (default: from config)')
    
    # Translation options
    parser.add_argument('--srt-file', type=str,
                       help='SRT file path for translation (local file or Object Storage object name)')
    parser.add_argument('--source-language', type=str, default='en',
                       help='Source language code (default: en)')
    parser.add_argument('--target-languages', nargs='+', type=str,
                       help='Target language codes (default: from config)')
    parser.add_argument('--translation-method', choices=['sync', 'batch'],
                       help='Translation method (default: from config)')
    
    # General options
    parser.add_argument('--output-type', choices=['local', 'object_storage', 'both'],
                       help='Where to store output (default: from config)')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='Configuration file path (default: config.yaml)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.transcribe_only and not args.translate_only:
        # Complete workflow - need audio source
        if not args.audio_source:
            log_step("ERROR: --audio-source is required for complete workflow", True)
            parser.print_help()
            sys.exit(1)
    elif args.transcribe_only:
        if not args.audio_source:
            log_step("ERROR: --audio-source is required for transcription", True)
            parser.print_help()
            sys.exit(1)
    elif args.translate_only:
        if not args.srt_file:
            log_step("ERROR: --srt-file is required for translation only", True)
            parser.print_help()
            sys.exit(1)
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        sys.exit(1)
    
    log_step("Starting OCI Subtitle Translation workflow")
    log_step(f"Configuration: {args.config}")
    
    success = True
    
    # Execute transcription workflow
    if not args.translate_only:
        success = run_transcription(args, config)
        if not success and not args.transcribe_only:
            log_step("Transcription failed, cannot proceed with translation", True)
            sys.exit(1)
    
    # Execute translation workflow
    if not args.transcribe_only and success:
        # If we just did transcription, find the generated SRT file
        if not args.translate_only:
            args.srt_file = find_generated_srt(config, args.audio_source)
            log_step(f"Using generated SRT file: {args.srt_file}")
        
        success = run_translation(args, config)
    
    # Final summary
    log_step("\n" + "="*60)
    log_step("WORKFLOW SUMMARY")
    log_step("="*60)
    
    if args.transcribe_only:
        if success:
            log_step("✓ Transcription completed successfully")
        else:
            log_step("✗ Transcription failed", True)
    elif args.translate_only:
        if success:
            log_step("✓ Translation completed successfully")
        else:
            log_step("✗ Translation failed", True)
    else:
        if success:
            log_step("✓ Complete workflow completed successfully")
        else:
            log_step("✗ Workflow failed", True)
    
    log_step("Workflow finished!")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
