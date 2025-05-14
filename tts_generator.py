import warnings
# Suppress all warnings
warnings.filterwarnings('ignore')

# Specifically suppress the attention mask warnings
warnings.filterwarnings('ignore', message='.*The attention mask.*')
warnings.filterwarnings('ignore', message='.*The pad token id is not set.*')
warnings.filterwarnings('ignore', message='.*You have modified the pretrained model configuration.*')
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

import os
import torch
# Suppress Flash Attention 2 warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "true"
# Suppress HF text generation warnings
os.environ["HF_SUPPRESS_GENERATION_WARNINGS"] = "true"
# Additional environment variables to suppress warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import time
import yaml
import re
import shutil
from typing import Dict, List, Optional, Union, Tuple
from pydub import AudioSegment
import tempfile
import tqdm

# Disable logging from transformers
import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("transformers.generation_utils").setLevel(logging.ERROR)

class TTSGenerator:
    """Class for generating podcast audio from transcripts."""
    
    def __init__(self, model_type: str = "bark", config_file: str = 'config.yaml') -> None:
        """Initialize the TTS generator.
        
        Args:
            model_type: Type of TTS model to use ('bark', 'parler', or 'coqui')
            config_file: Path to configuration file
            
        Raises:
            ValueError: If model_type is not supported
        """
        self.model_type = model_type.lower()
        
        if self.model_type not in ["bark", "parler", "coqui"]:
            raise ValueError("Unsupported TTS model type. Choose 'bark', 'parler', or 'coqui'")
        
        # Check for FFmpeg dependencies
        self.ffmpeg_available = self._check_ffmpeg()
        if not self.ffmpeg_available:
            print("WARNING: FFmpeg/ffprobe not found. Audio export may fail.")
            print("Please install FFmpeg: https://ffmpeg.org/download.html")
        
        # Load configuration
        with open(config_file, 'r', encoding='utf-8') as file:
            self.config = yaml.safe_load(file)
        
        # Initialize model-specific components
        if self.model_type == "bark":
            self._init_bark()
        elif self.model_type == "parler":
            self._init_parler()
        else:  # coqui
            self._init_coqui()
        
        # Initialize execution time tracking
        self.execution_times = {
            'start_time': 0,
            'total_time': 0,
            'segments': []
        }
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg and ffprobe are available."""
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        return ffmpeg is not None and ffprobe is not None
    
    def _init_bark(self) -> None:
        """Initialize the Bark TTS model."""
        print("Initializing Bark TTS model...")
        from transformers import AutoProcessor, BarkModel
        
        # Load model and processor
        self.processor = AutoProcessor.from_pretrained("suno/bark")
        self.model = BarkModel.from_pretrained("suno/bark")
        
        # Set pad token ID to avoid warnings
        self.model.config.pad_token_id = self.model.config.eos_token_id
        
        # Move model to GPU if available
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")
            print("Bark model loaded on GPU")
        else:
            print("Bark model loaded on CPU")
        
        # Define speaker presets
        self.speakers = {
            "Speaker 1": "v2/en_speaker_6",  # Male expert
            "Speaker 2": "v2/en_speaker_9",  # Female student
            "Speaker 3": "v2/en_speaker_3"   # Second expert
        }
    
    def _init_parler(self) -> None:
        """Initialize the Parler TTS model."""
        print("Initializing Parler TTS model...")
        try:
            # Try both import paths for compatibility
            try:
                from parler_tts import ParlerTTS
            except ImportError:
                from parler.tts import ParlerTTS
            
            # Initialize Parler TTS
            self.model = ParlerTTS()
            
            # Define speaker presets (speaker IDs for Parler)
            self.speakers = {
                "Speaker 1": 0,  # Male expert
                "Speaker 2": 1,  # Female student
                "Speaker 3": 2   # Second expert
            }
            self.parler_available = True
        except ImportError:
            print("WARNING: Parler TTS module not found. Using fallback TTS instead.")
            print("To install Parler TTS, run: pip install git+https://github.com/huggingface/parler-tts.git")
            # Fall back to Bark if Parler is not available
            self.model_type = "bark"
            self._init_bark()
            self.parler_available = False

    def _init_coqui(self) -> None:
        """Initialize the Coqui TTS model."""
        print("Initializing Coqui TTS model...")
        try:
            from TTS.api import TTS
            
            # Initialize Coqui TTS with a multi-speaker model
            # Using VITS model which supports multi-speaker synthesis
            self.model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            
            # Define speaker presets (speaker names for Coqui XTTS)
            self.speakers = {
                "Speaker 1": "p326",  # Male expert
                "Speaker 2": "p225",  # Female student
                "Speaker 3": "p330"   # Second expert
            }
            self.coqui_available = True
            
            # Store sample rate for later use
            self.sample_rate = 24000  # Default for XTTS
            
        except ImportError:
            print("WARNING: Coqui TTS module not found. Using fallback TTS instead.")
            print("To install Coqui TTS, run: pip install TTS")
            # Fall back to Bark if Coqui is not available
            self.model_type = "bark"
            self._init_bark()
            self.coqui_available = False
        except Exception as e:
            print(f"WARNING: Error initializing Coqui TTS: {str(e)}. Using fallback TTS instead.")
            # Fall back to Bark if there's an error with Coqui
            self.model_type = "bark"
            self._init_bark()
            self.coqui_available = False

    def _generate_audio_bark(self, text: str, speaker: str) -> AudioSegment:
        """Generate audio using Bark TTS.
        
        Args:
            text: Text to convert to speech
            speaker: Speaker identifier
            
        Returns:
            AudioSegment containing the generated speech
        """
        try:
            # Prepare inputs
            inputs = self.processor(
                text=text,
                voice_preset=self.speakers[speaker],
                return_tensors="pt"
            )
            
            # Create attention mask if not present
            if "attention_mask" not in inputs:
                # Create attention mask (all 1s, same shape as input_ids)
                inputs["attention_mask"] = torch.ones_like(inputs["input_ids"])
            
            # Move inputs to GPU if available
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # Generate audio with specific generation parameters
            generation_kwargs = {
                "pad_token_id": self.model.config.pad_token_id,
                "do_sample": True,
                "temperature": 0.7,
                "max_new_tokens": 250
            }
            
            # Make a clean copy of inputs without any generation parameters
            # to avoid conflicts with generation_kwargs
            model_inputs = {}
            for k, v in inputs.items():
                if k not in ["max_new_tokens", "do_sample", "temperature", "pad_token_id"]:
                    model_inputs[k] = v
            
            # Generate the audio
            speech_output = self.model.generate(**model_inputs, **generation_kwargs)
            
            # Convert to audio segment
            audio_array = speech_output.cpu().numpy().squeeze()
            
            # Save to temporary file and load as AudioSegment
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Save as WAV
            import scipy.io.wavfile as wavfile
            wavfile.write(temp_path, rate=24000, data=audio_array)
            
            # Load as AudioSegment
            if not self.ffmpeg_available:
                print("WARNING: FFmpeg not available. Using silent audio as fallback.")
                audio_segment = AudioSegment.silent(duration=len(audio_array) * 1000 // 24000)
            else:
                try:
                    audio_segment = AudioSegment.from_wav(temp_path)
                except Exception as e:
                    print(f"Error loading audio segment: {str(e)}")
                    # Fallback to silent audio
                    audio_segment = AudioSegment.silent(duration=len(audio_array) * 1000 // 24000)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_path}: {str(e)}")
            
            return audio_segment
        except Exception as e:
            print(f"Error in _generate_audio_bark: {str(e)}")
            # Return a silent segment as fallback
            return AudioSegment.silent(duration=1000)

    def _generate_audio_coqui(self, text: str, speaker: str) -> AudioSegment:
        """Generate audio using Coqui TTS.
        
        Args:
            text: Text to convert to speech
            speaker: Speaker identifier
            
        Returns:
            AudioSegment containing the generated speech
        """
        try:
            # Create a temporary file to save the audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate audio with Coqui TTS
            # For XTTS, we need to provide a reference audio file for the speaker
            # Since we don't have that, we'll use the built-in speaker IDs
            self.model.tts_to_file(
                text=text,
                file_path=temp_path,
                speaker=self.speakers[speaker],
                language="en"
            )
            
            # Load as AudioSegment
            if not self.ffmpeg_available:
                print("WARNING: FFmpeg not available. Using silent audio as fallback.")
                # Estimate duration based on text length (rough approximation)
                estimated_duration = len(text) * 60  # ~60ms per character
                audio_segment = AudioSegment.silent(duration=estimated_duration)
            else:
                try:
                    audio_segment = AudioSegment.from_wav(temp_path)
                except Exception as e:
                    print(f"Error loading audio segment: {str(e)}")
                    # Fallback to silent audio
                    estimated_duration = len(text) * 60  # ~60ms per character
                    audio_segment = AudioSegment.silent(duration=estimated_duration)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_path}: {str(e)}")
            
            return audio_segment
        except Exception as e:
            print(f"Error generating audio with Coqui: {str(e)}")
            # Return a silent segment as fallback
            return AudioSegment.silent(duration=1000) 