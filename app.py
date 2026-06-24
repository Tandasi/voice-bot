"""
Flask application for Twilio voice bot.

This module sets up the main Flask app that:
- Handles incoming/outgoing Twilio calls
- Manages webhooks for call events (answered, transcription complete, etc.)
- Initiates calls to test numbers
- Routes call logic to the voice bot
- Manages TwiML (Twilio Markup Language) responses
"""

import os
import sys
import json
import random
from datetime import datetime
from flask import Flask, request, render_template_string
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from dotenv import load_dotenv

from bot import ConversationBot
from scenarios import SCENARIOS

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Validate required environment variables
required_vars = {
    "TWILIO_ACCOUNT_SID": "Twilio Account SID",
    "TWILIO_AUTH_TOKEN": "Twilio Auth Token",
    "TWILIO_PHONE_NUMBER": "Twilio Phone Number",
    "OPENAI_API_KEY": "OpenAI API Key",
    "TEST_PHONE_NUMBER": "Test Phone Number (who the bot will call)",
    "BASE_URL": "Base URL for Twilio webhooks (e.g., https://yourapp.onrender.com)"
}

missing_vars = []
for var, description in required_vars.items():
    if not os.getenv(var):
        missing_vars.append(f"  - {var}: {description}")

if missing_vars:
    error_msg = "\nERROR: Missing required environment variables:\n" + "\n".join(missing_vars)
    error_msg += "\n\nPlease set these variables in your .env file or environment and try again."
    print(error_msg, file=sys.stderr)
    sys.exit(1)

# Twilio credentials from environment
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TARGET_NUMBER = os.getenv("TEST_PHONE_NUMBER")

# Base URL for webhooks
BASE_URL = os.getenv("BASE_URL")

# Initialize Twilio client
twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Store active conversation bots keyed by CallSid
active_conversations = {}

# Transcript directory
TRANSCRIPT_DIR = os.path.join(os.getenv("TRANSCRIPT_DIR", "./transcripts"))
if not os.path.exists(TRANSCRIPT_DIR):
    os.makedirs(TRANSCRIPT_DIR)


@app.route("/call/start", methods=["POST"])
def start_call():
    """
    Initiate an outbound call to the test number.
    
    Optionally accepts scenario_id in request JSON to use specific scenario,
    otherwise picks a random one.
    
    Returns:
        JSON response with call SID and status
    """
    try:
        # Get scenario_id from request or pick random
        data = request.get_json() or {}
        scenario_id = data.get("scenario_id")
        
        if scenario_id:
            scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
            if not scenario:
                return {"error": f"Scenario {scenario_id} not found"}, 404
        else:
            scenario = random.choice(SCENARIOS)
        
        # Create the outbound call with recording enabled
        call = twilio_client.calls.create(
            to=TARGET_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{BASE_URL}/call/answer",
            record=True,
            timeout=60,
            status_callback=f"{BASE_URL}/call/status",
            status_callback_method="POST"
        )
        
        # Initialize conversation bot for this call
        active_conversations[call.sid] = {
            "bot": ConversationBot(scenario),
            "scenario": scenario,
            "start_time": datetime.now().isoformat()
        }
        
        return {
            "call_sid": call.sid,
            "scenario": scenario["name"],
            "patient": scenario["patient_name"],
            "status": "initiated"
        }, 200
    
    except Exception as e:
        print(f"Error starting call: {e}")
        return {"error": str(e)}, 500


@app.route("/call/answer", methods=["POST"])
def answer_call():
    """
    Handle incoming webhook when Twilio connects the call.
    
    Returns TwiML that:
    1. Speaks the patient's opening line using Polly voice
    2. Uses Gather to listen for the agent's response
    """
    call_sid = request.form.get("CallSid")
    
    if call_sid not in active_conversations:
        response = VoiceResponse()
        response.say("Sorry, I couldn't initialize the conversation. Goodbye.")
        response.hangup()
        return str(response)
    
    try:
        bot = active_conversations[call_sid]["bot"]
        opening_line = bot.get_opening_line()
        
        response = VoiceResponse()
        response.say(opening_line, voice="Polly.Joanna")
        
        # Gather speech input (30 second timeout, 1 digit to end recording)
        gather = response.gather(
            input="speech",
            timeout=10,
            speech_timeout="auto",
            action=f"{BASE_URL}/call/gather",
            method="POST"
        )
        
        return str(response)
    
    except Exception as e:
        print(f"Error in answer_call: {e}")
        response = VoiceResponse()
        response.say("Sorry, there was an error. Goodbye.")
        response.hangup()
        return str(response)


@app.route("/call/gather", methods=["POST"])
def gather_response():
    """
    Handle speech input from the agent.
    
    Gets agent speech, sends to ConversationBot to generate patient response,
    and returns TwiML that:
    1. Speaks the patient's response
    2. Gathers the next agent input (or hangs up if conversation complete)
    """
    call_sid = request.form.get("CallSid")
    speech_result = request.form.get("SpeechResult", "").strip()
    
    if call_sid not in active_conversations:
        response = VoiceResponse()
        response.say("Conversation not found. Goodbye.")
        response.hangup()
        return str(response)
    
    try:
        conversation_data = active_conversations[call_sid]
        bot = conversation_data["bot"]
        
        # If no speech detected, prompt again
        if not speech_result:
            response = VoiceResponse()
            response.say("Sorry, I didn't catch that. Could you please repeat?", voice="Polly.Joanna")
            gather = response.gather(
                input="speech",
                timeout=10,
                speech_timeout="auto",
                action=f"{BASE_URL}/call/gather",
                method="POST"
            )
            return str(response)
        
        # Get patient's response from bot
        patient_response = bot.get_response(speech_result)
        
        response = VoiceResponse()
        response.say(patient_response, voice="Polly.Joanna")
        
        # Check if conversation is complete
        if bot.is_conversation_complete():
            response.hangup()
            # Save transcript after call ends
            save_transcript(call_sid, conversation_data)
            # Clean up conversation
            del active_conversations[call_sid]
        else:
            # Gather next agent input
            gather = response.gather(
                input="speech",
                timeout=10,
                speech_timeout="auto",
                action=f"{BASE_URL}/call/gather",
                method="POST"
            )
        
        return str(response)
    
    except Exception as e:
        print(f"Error in gather_response: {e}")
        response = VoiceResponse()
        response.say("Sorry, there was an error.", voice="Polly.Joanna")
        response.hangup()
        if call_sid in active_conversations:
            save_transcript(call_sid, active_conversations[call_sid])
            del active_conversations[call_sid]
        return str(response)


@app.route("/call/status", methods=["POST"])
def call_status():
    """
    Handle Twilio status callbacks for call events.
    
    Tracks call state and cleans up if needed.
    """
    call_sid = request.form.get("CallSid")
    call_status = request.form.get("CallStatus")
    
    print(f"Call {call_sid} status: {call_status}")
    
    # Clean up if call ended unexpectedly
    if call_status in ["completed", "failed", "busy", "no-answer"]:
        if call_sid in active_conversations:
            save_transcript(call_sid, active_conversations[call_sid])
            del active_conversations[call_sid]
    
    response = VoiceResponse()
    return str(response)


@app.route("/transcripts", methods=["GET"])
def list_transcripts():
    """
    List all saved transcript files.
    
    Returns:
        JSON list of transcript filenames and metadata
    """
    try:
        transcripts = []
        
        if os.path.exists(TRANSCRIPT_DIR):
            for filename in os.listdir(TRANSCRIPT_DIR):
                if filename.endswith(".json"):
                    filepath = os.path.join(TRANSCRIPT_DIR, filename)
                    file_size = os.path.getsize(filepath)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                    
                    transcripts.append({
                        "filename": filename,
                        "size_bytes": file_size,
                        "modified": file_mtime
                    })
        
        # Sort by modification time (newest first)
        transcripts.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "count": len(transcripts),
            "transcripts": transcripts
        }, 200
    
    except Exception as e:
        print(f"Error listing transcripts: {e}")
        return {"error": str(e)}, 500


@app.route("/transcripts/<filename>", methods=["GET"])
def get_transcript(filename):
    """
    Retrieve a specific transcript file.
    
    Args:
        filename: Name of the transcript file
        
    Returns:
        JSON transcript content
    """
    try:
        filepath = os.path.join(TRANSCRIPT_DIR, filename)
        
        # Security: ensure file is in transcript directory
        if not os.path.abspath(filepath).startswith(os.path.abspath(TRANSCRIPT_DIR)):
            return {"error": "Invalid file path"}, 403
        
        if not os.path.exists(filepath):
            return {"error": "File not found"}, 404
        
        with open(filepath, "r") as f:
            transcript = json.load(f)
        
        return transcript, 200
    
    except Exception as e:
        print(f"Error retrieving transcript: {e}")
        return {"error": str(e)}, 500


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        JSON status
    """
    return {
        "status": "healthy",
        "active_conversations": len(active_conversations),
        "twilio_configured": bool(ACCOUNT_SID and AUTH_TOKEN)
    }, 200


def save_transcript(call_sid, conversation_data):
    """
    Save a conversation transcript to JSON file.
    
    Args:
        call_sid (str): Twilio call SID
        conversation_data (dict): Conversation data with bot and scenario
    """
    try:
        bot = conversation_data["bot"]
        summary = bot.get_conversation_summary()
        
        transcript = {
            "call_sid": call_sid,
            "scenario_id": summary["scenario_id"],
            "scenario_name": summary["scenario_name"],
            "patient_name": summary["patient_name"],
            "goal": summary["goal"],
            "start_time": conversation_data["start_time"],
            "end_time": datetime.now().isoformat(),
            "turns": summary["turn_count"],
            "conversation": summary["conversation_history"]
        }
        
        # Save to file
        filename = f"{call_sid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(TRANSCRIPT_DIR, filename)
        
        with open(filepath, "w") as f:
            json.dump(transcript, f, indent=2)
        
        print(f"Transcript saved: {filepath}")
    
    except Exception as e:
        print(f"Error saving transcript: {e}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
