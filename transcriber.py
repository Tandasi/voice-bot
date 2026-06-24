"""
Call transcription and recording management.

This module handles:
- Recording audio from both sides of the call (bot and patient)
- Converting audio to text using speech-to-text APIs
- Managing transcription timestamps
- Storing and retrieving call recordings
- Generating conversation transcripts
"""

import os
import requests
from datetime import datetime
from twilio.rest import Client
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Transcriber:
    """
    Handles downloading Twilio call recordings and transcribing them using OpenAI Whisper.
    
    Manages storage of recordings and transcripts in local directories.
    """
    
    def __init__(self):
        """
        Initialize the transcriber with Twilio and OpenAI clients.
        
        Creates recording and transcript directories if they don't exist.
        """
        # Initialize Twilio client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_client = Client(account_sid, auth_token)
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Set up directories
        self.recordings_dir = os.path.join(os.getenv("RECORDINGS_DIR", "./recordings"))
        self.transcripts_dir = os.path.join(os.getenv("TRANSCRIPT_DIR", "./transcripts"))
        
        # Create directories if they don't exist
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)
    
    def download_recording(self, call_sid):
        """
        Download a recording from Twilio for a given call SID.
        
        Fetches the recording URL from Twilio, downloads the audio file,
        and saves it locally as an MP3.
        
        Args:
            call_sid (str): The Twilio call SID
            
        Returns:
            str: Path to the downloaded recording file, or None if no recording found
        """
        try:
            # Get recordings for this call
            recordings = self.twilio_client.recordings.stream(limit=20)
            
            recording_url = None
            for recording in recordings:
                if recording.call_sid == call_sid:
                    recording_url = recording.uri
                    break
            
            if not recording_url:
                print(f"No recording found for call {call_sid}")
                return None
            
            # Download the recording
            # Twilio API returns .json, but we want .mp3
            mp3_url = recording_url.replace(".json", ".mp3")
            
            # Add account SID and auth token for authentication
            response = requests.get(
                mp3_url,
                auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
            )
            
            if response.status_code != 200:
                print(f"Failed to download recording: {response.status_code}")
                return None
            
            # Save the recording
            recording_path = os.path.join(self.recordings_dir, f"{call_sid}.mp3")
            with open(recording_path, "wb") as f:
                f.write(response.content)
            
            print(f"Recording saved: {recording_path}")
            return recording_path
        
        except Exception as e:
            print(f"Error downloading recording for {call_sid}: {e}")
            return None
    
    def get_transcript_from_recording(self, recording_path):
        """
        Transcribe audio from a recording file using OpenAI Whisper API.
        
        Opens the audio file and sends it to Whisper for transcription.
        
        Args:
            recording_path (str): Path to the recording file (MP3, WAV, etc.)
            
        Returns:
            str: The transcribed text, or empty string if transcription fails
        """
        try:
            if not os.path.exists(recording_path):
                print(f"Recording file not found: {recording_path}")
                return ""
            
            # Open the audio file
            with open(recording_path, "rb") as audio_file:
                # Call Whisper API
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            
            transcript_text = transcript.text
            print(f"Transcription complete: {len(transcript_text)} characters")
            return transcript_text
        
        except Exception as e:
            print(f"Error transcribing recording {recording_path}: {e}")
            return ""
    
    def save_transcript_text(self, call_sid, transcript_text, scenario_name):
        """
        Save a transcript as a plain text file.
        
        Creates a file with metadata header followed by the transcript text.
        
        Args:
            call_sid (str): The Twilio call SID
            transcript_text (str): The transcribed conversation text
            scenario_name (str): Name of the scenario for this call
            
        Returns:
            str: Path to the saved transcript file
        """
        try:
            # Create transcript content with header
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            content = f"""================================================================================
CALL TRANSCRIPT
================================================================================
Call SID: {call_sid}
Scenario: {scenario_name}
Timestamp: {timestamp}
================================================================================

{transcript_text}

================================================================================
END OF TRANSCRIPT
================================================================================
"""
            
            # Save to file
            transcript_path = os.path.join(self.transcripts_dir, f"{call_sid}.txt")
            with open(transcript_path, "w") as f:
                f.write(content)
            
            print(f"Transcript saved: {transcript_path}")
            return transcript_path
        
        except Exception as e:
            print(f"Error saving transcript for {call_sid}: {e}")
            return None
    
    def process_call(self, call_sid, scenario_name):
        """
        Process a call completely: download recording, transcribe, and save transcript.
        
        Orchestrates the full workflow of retrieving a call's recording,
        transcribing it with Whisper, and saving the transcript.
        
        Args:
            call_sid (str): The Twilio call SID
            scenario_name (str): Name of the scenario for this call
            
        Returns:
            dict: Contains recording_path, transcript_path, and transcript_text
                  Returns None for missing values on error
        """
        try:
            result = {
                "call_sid": call_sid,
                "scenario_name": scenario_name,
                "recording_path": None,
                "transcript_path": None,
                "transcript_text": None
            }
            
            # Step 1: Download recording
            print(f"Downloading recording for call {call_sid}...")
            recording_path = self.download_recording(call_sid)
            if not recording_path:
                print(f"Skipping transcription - no recording found")
                return result
            result["recording_path"] = recording_path
            
            # Step 2: Transcribe recording
            print(f"Transcribing recording...")
            transcript_text = self.get_transcript_from_recording(recording_path)
            if not transcript_text:
                print(f"Warning: transcription returned empty text")
            result["transcript_text"] = transcript_text
            
            # Step 3: Save transcript
            print(f"Saving transcript...")
            transcript_path = self.save_transcript_text(call_sid, transcript_text, scenario_name)
            if transcript_path:
                result["transcript_path"] = transcript_path
            
            print(f"Call processing complete for {call_sid}")
            return result
        
        except Exception as e:
            print(f"Error processing call {call_sid}: {e}")
            return {
                "call_sid": call_sid,
                "scenario_name": scenario_name,
                "recording_path": None,
                "transcript_path": None,
                "transcript_text": None,
                "error": str(e)
            }
    
    def get_recording_path(self, call_sid):
        """
        Get the path to a saved recording for a call SID.
        
        Args:
            call_sid (str): The Twilio call SID
            
        Returns:
            str: Path to recording if it exists, None otherwise
        """
        recording_path = os.path.join(self.recordings_dir, f"{call_sid}.mp3")
        if os.path.exists(recording_path):
            return recording_path
        return None
    
    def get_transcript_path(self, call_sid):
        """
        Get the path to a saved transcript for a call SID.
        
        Args:
            call_sid (str): The Twilio call SID
            
        Returns:
            str: Path to transcript if it exists, None otherwise
        """
        transcript_path = os.path.join(self.transcripts_dir, f"{call_sid}.txt")
        if os.path.exists(transcript_path):
            return transcript_path
        return None
