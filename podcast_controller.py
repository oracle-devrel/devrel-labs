#!/usr/bin/env python
"""
Podcast Controller for planeLLM.

This script orchestrates the entire podcast generation pipeline, from topic exploration
to audio generation. It provides a simple command-line interface to generate educational
podcasts on any topic.

Examples:
    python podcast_controller.py --topic "Ancient Rome"
    python podcast_controller.py --topic "Quantum Physics" --tts-model parler
    python podcast_controller.py --topic "Machine Learning" --config my_config.yaml
    python podcast_controller.py --topic "Artificial Intelligence" --detailed-transcript

"""

import os
import time
import argparse
from topic_explorer import TopicExplorer
from lesson_writer import PodcastWriter
from tts_generator import TTSGenerator

def main():
    """Run the podcast generation pipeline."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate an educational podcast on any topic')
    parser.add_argument('--topic', required=True, help='Topic to generate a podcast about')
    parser.add_argument('--tts-model', default='bark', choices=['bark', 'parler'], 
                        help='TTS model to use (default: bark)')
    parser.add_argument('--config', default='config.yaml', 
                        help='Path to configuration file (default: config.yaml)')
    parser.add_argument('--output', help='Output path for the audio file')
    parser.add_argument('--detailed-transcript', action='store_true',
                        help='Process each question individually for more detailed content')
    
    args = parser.parse_args()
    
    # Create resources directory if it doesn't exist
    os.makedirs('./resources', exist_ok=True)
    
    # Generate timestamp for file naming
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Step 1: Generate educational content
    print(f"\n=== Step 1: Exploring topic '{args.topic}' ===")
    explorer = TopicExplorer(config_file=args.config)
    questions = explorer.generate_questions(args.topic)
    
    # Save questions to file
    questions_file = f"questions_{timestamp}.txt"
    with open(f'./resources/{questions_file}', 'w', encoding='utf-8') as file:
        file.write("\n".join(questions))
    print(f"Questions saved to ./resources/{questions_file}")
    
    # Generate content for each question
    print("\nGenerating educational content...")
    content = ""
    for i, question in enumerate(questions[:2]):  # Limit to first 2 questions for brevity
        print(f"Exploring question {i+1}/{len(questions[:2])}: {question}")
        question_content = explorer.explore_question(question)
        content += f"# {question}\n\n{question_content}\n\n"
    
    # Save raw content to file
    content_file = f"content_{timestamp}.txt"
    with open(f'./resources/{content_file}', 'w', encoding='utf-8') as file:
        file.write(content)
    print(f"Raw content saved to ./resources/{content_file}")
    
    # Step 2: Create podcast transcript
    print(f"\n=== Step 2: Creating podcast transcript ===")
    writer = PodcastWriter(config_file=args.config)
    
    if args.detailed_transcript:
        print("Using detailed transcript generation (processing each question individually)")
        transcript = writer.create_detailed_podcast_transcript(content)
    else:
        transcript = writer.create_podcast_transcript(content)
    
    # Transcript is saved by the PodcastWriter class
    transcript_file = [f for f in os.listdir('./resources') 
                      if f.startswith('podcast_transcript_') and f.endswith(f'{timestamp}.txt')]
    if transcript_file:
        transcript_path = f"./resources/{transcript_file[0]}"
    else:
        transcript_path = f"./resources/podcast_transcript_{timestamp}.txt"
    
    # Step 3: Generate audio
    print(f"\n=== Step 3: Generating podcast audio ===")
    tts = TTSGenerator(model_type=args.tts_model, config_file=args.config)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = f"./resources/podcast_{timestamp}.mp3"
    
    # Generate audio
    audio_path = tts.generate_podcast(transcript, output_path=output_path)
    
    # Print summary
    print("\n=== Podcast Generation Complete ===")
    print(f"Questions: ./resources/{questions_file}")
    print(f"Content: ./resources/{content_file}")
    print(f"Transcript: {transcript_path}")
    print(f"Audio: {audio_path}")
    print("\nThank you for using planeLLM!")

if __name__ == "__main__":
    main() 