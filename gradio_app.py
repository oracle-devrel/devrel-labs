#!/usr/bin/env python
"""
Launcher script for the planeLLM Gradio interface.

This script provides a simple way to launch the Gradio interface
without having to import the module directly.

Usage:
    python gradio_app.py
"""

# Import directly from the modules in the root directory
import os
import gradio as gr
import time
from typing import Dict, List, Tuple, Any, Optional
import json

# Import planeLLM components
from topic_explorer import TopicExplorer
from lesson_writer import PodcastWriter
from tts_generator import TTSGenerator

# Create resources directory if it doesn't exist
os.makedirs('./resources', exist_ok=True)

class PlaneLLMInterface:
    """Main class for the Gradio interface of planeLLM."""
    
    def __init__(self):
        """Initialize the interface components."""
        # Initialize components
        self.topic_explorer = TopicExplorer()
        self.podcast_writer = PodcastWriter()
        
        # We'll initialize the TTS generator only when needed to save memory
        self.tts_generator = None
        
        # Track available files
        self.update_available_files()
    
    def update_available_files(self) -> Dict[str, List[str]]:
        """Update and return lists of available files by type."""
        resources_dir = './resources'
        
        # Ensure directory exists
        os.makedirs(resources_dir, exist_ok=True)
        
        # Get all files in resources directory
        all_files = os.listdir(resources_dir)
        
        # Filter by type
        self.available_files = {
            'content': [f for f in all_files if f.endswith('.txt') and ('content' in f or 'raw_lesson' in f)],
            'questions': [f for f in all_files if f.endswith('.txt') and 'questions' in f],
            'transcripts': [f for f in all_files if f.endswith('.txt') and 'podcast' in f],
            'audio': [f for f in all_files if f.endswith('.mp3')]
        }
        
        return self.available_files
    
    def generate_topic_content(self, topic: str, progress=gr.Progress()) -> Tuple[str, str, str]:
        """Generate educational content about a topic.
        
        Args:
            topic: The topic to explore
            progress: Gradio progress indicator
            
        Returns:
            Tuple of (questions, content, status message)
        """
        if not topic:
            return "", "", "Error: Please enter a topic"
        
        try:
            progress(0, desc="Initializing...")
            
            # Generate timestamp for file naming
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            questions_file = f"questions_{timestamp}.txt"
            content_file = f"content_{timestamp}.txt"
            
            progress(0.1, desc="Generating questions...")
            questions = self.topic_explorer.generate_questions(topic)
            
            # Save questions to file
            with open(f"./resources/{questions_file}", 'w', encoding='utf-8') as f:
                questions_text = f"# Questions for {topic}\n\n"
                for i, q in enumerate(questions, 1):
                    questions_text += f"{i}. {q}\n"
                f.write(questions_text)
            
            progress(0.3, desc="Exploring questions...")
            # Generate content for each question
            results = {}
            for i, question in enumerate(questions):
                progress(0.3 + (0.6 * (i / len(questions))), 
                         desc=f"Exploring question {i+1}/{len(questions)}")
                response = self.topic_explorer.explore_question(question)
                results[question] = response
            
            # Combine content
            full_content = f"# {topic}\n\n"
            for question, response in results.items():
                full_content += f"# {question}\n\n{response}\n\n"
            
            # Save content to file
            with open(f"./resources/{content_file}", 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            progress(1.0, desc="Done!")
            self.update_available_files()
            
            return questions_text, full_content, f"Content generated successfully and saved to {content_file}"
            
        except Exception as e:
            return "", "", f"Error: {str(e)}"
    
    def create_podcast_transcript(self, content_file: str, detailed_transcript: bool, progress=gr.Progress()) -> Tuple[str, str]:
        """Create podcast transcript from content file.
        
        Args:
            content_file: Name of content file to use
            detailed_transcript: Whether to use detailed question-by-question processing
            progress: Gradio progress indicator
            
        Returns:
            Tuple of (transcript, status message)
        """
        if not content_file:
            return "", "Error: Please select a content file"
        
        try:
            progress(0, desc="Reading content file...")
            
            # Generate timestamp for file naming
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # Read content from file
            with open(f"./resources/{content_file}", 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Initialize podcast writer
            self.podcast_writer = PodcastWriter()
            
            if detailed_transcript:
                progress(0.2, desc="Generating detailed podcast transcript (processing each question individually)...")
                transcript = self.podcast_writer.create_detailed_podcast_transcript(content)
                transcript_type = "detailed"
            else:
                progress(0.2, desc="Generating standard podcast transcript...")
                transcript = self.podcast_writer.create_podcast_transcript(content)
                transcript_type = "standard"
            
            # Transcript is saved by the PodcastWriter class
            # Find the most recently created transcript file
            transcript_files = [f for f in os.listdir('./resources') 
                              if f.startswith('podcast_transcript_') and f.endswith(f'{timestamp}.txt')]
            
            if transcript_files:
                transcript_file = transcript_files[0]
            else:
                # Fallback - save transcript to file
                transcript_file = f"podcast_transcript_{transcript_type}_{timestamp}.txt"
                with open(f"./resources/{transcript_file}", 'w', encoding='utf-8') as f:
                    f.write(transcript)
            
            progress(1.0, desc="Done!")
            self.update_available_files()
            
            return transcript, f"Transcript generated successfully and saved to {transcript_file}"
            
        except Exception as e:
            return "", f"Error: {str(e)}"
    
    def generate_podcast_audio(self, transcript_file: str, model_type: str, progress=gr.Progress()) -> Tuple[str, str]:
        """Generate podcast audio from transcript.
        
        Args:
            transcript_file: Name of transcript file to use
            model_type: TTS model to use ('bark' or 'parler')
            progress: Gradio progress indicator
            
        Returns:
            Tuple of (audio path, status message)
        """
        if not transcript_file:
            return "", "Error: Please select a transcript file"
        
        try:
            progress(0, desc=f"Initializing {model_type} model...")
            
            # Initialize TTS generator if needed
            if self.tts_generator is None or self.tts_generator.model_type != model_type:
                self.tts_generator = TTSGenerator(model_type=model_type)
            
            # Generate timestamp for file naming
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            audio_file = f"podcast_{timestamp}.mp3"
            audio_path = f"./resources/{audio_file}"
            
            progress(0.1, desc="Generating podcast audio...")
            
            # Read transcript from file
            with open(f"./resources/{transcript_file}", 'r', encoding='utf-8') as f:
                transcript = f.read()
            
            # Generate podcast audio
            self.tts_generator.generate_podcast(transcript, output_path=audio_path)
            
            progress(1.0, desc="Done!")
            self.update_available_files()
            
            return audio_path, f"Podcast audio generated successfully and saved to {audio_file}"
            
        except Exception as e:
            return "", f"Error: {str(e)}"

def create_interface():
    """Create and launch the Gradio interface."""
    # Initialize the interface
    interface = PlaneLLMInterface()
    
    # Define the interface
    with gr.Blocks(title="planeLLM Interface") as app:
        gr.Markdown("# planeLLM: Educational Content Generation System")
        
        # Create tabs for different components
        with gr.Tabs():
            # Topic Explorer Tab
            with gr.Tab("Topic Explorer"):
                gr.Markdown("## Generate Educational Content")
                
                with gr.Row():
                    topic_input = gr.Textbox(label="Topic", placeholder="Enter a topic (e.g., Ancient Rome, Quantum Physics)")
                    generate_button = gr.Button("Generate Content")
                
                with gr.Row():
                    with gr.Column():
                        questions_output = gr.Textbox(label="Generated Questions", lines=10, interactive=False)
                    with gr.Column():
                        content_output = gr.Textbox(label="Generated Content", lines=20, interactive=False)
                
                status_output = gr.Textbox(label="Status", interactive=False)
                
                # Connect the button to the function
                generate_button.click(
                    fn=interface.generate_topic_content,
                    inputs=[topic_input],
                    outputs=[questions_output, content_output, status_output]
                )
            
            # Lesson Writer Tab
            with gr.Tab("Lesson Writer"):
                gr.Markdown("## Create Podcast Transcript")
                
                with gr.Row():
                    # Dropdown for selecting content file
                    content_file_dropdown = gr.Dropdown(
                        label="Select Content File",
                        choices=interface.available_files['content'],
                        interactive=True
                    )
                    refresh_content_button = gr.Button("Refresh Files")
                
                with gr.Row():
                    detailed_transcript = gr.Checkbox(
                        label="Detailed Processing",
                        value=True,
                        info="Process each question individually for more detailed content (recommended)"
                    )
                
                create_transcript_button = gr.Button("Create Transcript")
                
                transcript_output = gr.Textbox(label="Generated Transcript", lines=20, interactive=False)
                transcript_status = gr.Textbox(label="Status", interactive=False)
                
                # Connect buttons to functions
                refresh_content_button.click(
                    fn=lambda: gr.Dropdown(choices=interface.update_available_files()['content']),
                    inputs=[],
                    outputs=[content_file_dropdown]
                )
                
                create_transcript_button.click(
                    fn=interface.create_podcast_transcript,
                    inputs=[content_file_dropdown, detailed_transcript],
                    outputs=[transcript_output, transcript_status]
                )
            
            # TTS Generator Tab
            with gr.Tab("TTS Generator"):
                gr.Markdown("## Generate Podcast Audio")
                
                with gr.Row():
                    # Dropdown for selecting transcript file
                    transcript_file_dropdown = gr.Dropdown(
                        label="Select Transcript File",
                        choices=interface.available_files['transcripts'],
                        interactive=True
                    )
                    refresh_transcript_button = gr.Button("Refresh Files")
                
                with gr.Row():
                    model_type = gr.Radio(
                        label="TTS Model",
                        choices=["bark", "parler"],
                        value="bark",
                        info="Bark: Higher quality but slower, Parler: Faster but lower quality"
                    )
                
                generate_audio_button = gr.Button("Generate Audio")
                
                with gr.Row():
                    audio_output = gr.Audio(label="Generated Audio", interactive=False)
                
                audio_status = gr.Textbox(label="Status", interactive=False)
                
                # Connect buttons to functions
                refresh_transcript_button.click(
                    fn=lambda: gr.Dropdown(choices=interface.update_available_files()['transcripts']),
                    inputs=[],
                    outputs=[transcript_file_dropdown]
                )
                
                generate_audio_button.click(
                    fn=interface.generate_podcast_audio,
                    inputs=[transcript_file_dropdown, model_type],
                    outputs=[audio_output, audio_status]
                )
        
        # Add a footer
        gr.Markdown("---\n*planeLLM: Bite-sized podcasts to learn about anything powered by the OCI GenAI Service*")
    
    # Launch the interface
    return app

if __name__ == "__main__":
    app = create_interface()
    app.launch(share=True) 