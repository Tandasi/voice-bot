# Twilio Voice Bot for Healthcare Patient Conversations

A Python-based voice bot that uses Twilio and OpenAI GPT-4o to simulate realistic healthcare patient conversations. The bot plays the **patient role**, making outbound calls to a test number where a real agent responds. Calls are recorded and transcribed using Twilio recording + OpenAI Whisper for analysis.

## Features

- **Automated calling**: Initiates outbound calls to test numbers using Twilio
- **AI-powered patient conversations**: Uses OpenAI GPT-4o to generate realistic patient dialogue
- **Voice synthesis**: Uses Amazon Polly for natural-sounding patient voice
- **Call recording**: Records both bot (patient) and agent audio
- **Transcription**: Uses OpenAI Whisper to convert call audio to text for analysis
- **Scenario-based testing**: Supports 10+ healthcare patient scenarios and personas
- **Conversation state management**: Maintains context throughout the call
- **Flask API**: REST endpoints for call management and monitoring

## Project Structure

- `app.py` - Main Flask application and Twilio webhook handlers
- `bot.py` - Voice bot logic and conversation management
- `scenarios.py` - Patient scenario definitions and personas
- `transcriber.py` - Call recording and transcription handling
- `requirements.txt` - Python package dependencies
- `.env.example` - Example environment variables file

## Setup

### Prerequisites

- Python 3.11+
- Twilio account with phone number and API credentials
- OpenAI API key (for GPT-4o and Whisper transcription)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd voice-bot
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

Update `.env` with your credentials:

- `TWILIO_ACCOUNT_SID` - Your Twilio account SID
- `TWILIO_AUTH_TOKEN` - Your Twilio auth token
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number (bot calls FROM this number)
- `OPENAI_API_KEY` - Your OpenAI API key (for GPT-4o and Whisper)
- `TEST_PHONE_NUMBER` - The phone number to call (agent picks up here)
- `BASE_URL` - Base URL for Twilio webhooks (e.g., https://yourapp.onrender.com)

## Usage

Start the application:
```bash
python app.py
```

The Flask server will start on the configured port (default: 5000).

## Scenarios

The bot supports 10 diverse healthcare patient scenarios:
1. Appointment scheduling
2. Appointment rescheduling
3. Appointment cancellation
4. Prescription refill requests
5. Office hours inquiry
6. Insurance and billing questions
7. Urgent symptom reporting
8. New patient registration
9. Confused/confused patient
10. Topic-jumping patient

Each scenario includes a unique patient persona, medical context, and conversation goal.

## Recording and Transcription

All calls are automatically:
- **Recorded** by Twilio to `./recordings/` (MP3 format)
- **Transcribed** by OpenAI Whisper to `./transcripts/` (JSON format with full conversation history and metadata)

## API Endpoints

- `POST /call/start` - Initiate an outbound call to a test number
- `POST /call/answer` - Twilio webhook when call connects (patient speaks opening line)
- `POST /call/gather` - Twilio webhook to handle speech input from agent
- `POST /call/status` - Twilio webhook for call status updates
- `GET /health` - Health check endpoint
- `GET /transcripts` - List all saved transcripts
- `GET /transcripts/<filename>` - Retrieve a specific transcript file

## License

MIT

## Safety and Compliance

This tool is designed for testing and development purposes only. Ensure compliance with:
- Telecom regulations (TCPA, FCC rules)
- Data privacy laws (HIPAA for healthcare data)
- Twilio terms of service
