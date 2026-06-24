# Twilio Voice Bot for Healthcare Patient Conversations

A Python-based voice bot that uses Twilio and OpenAI GPT-4o to simulate realistic healthcare patient conversations. The bot calls a test number and engages in conversation while recording and transcribing both sides of the call.

## Features

- **Automated calling**: Initiates calls to test numbers using Twilio
- **AI-powered conversations**: Uses OpenAI GPT-4o to generate realistic patient dialogue
- **Call recording**: Records both bot and patient audio
- **Transcription**: Converts call audio to text for analysis and review
- **Scenario-based testing**: Supports multiple patient scenarios and personas
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

- Python 3.8+
- Twilio account with phone number
- OpenAI API key (for GPT-4o access)
- Google Cloud Speech-to-Text credentials (optional, for transcription)

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
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number
- `OPENAI_API_KEY` - Your OpenAI API key
- `TEST_PHONE_NUMBER` - The number to call (default: +18054398008)

## Usage

Start the application:
```bash
python app.py
```

The Flask server will start on the configured port (default: 5000).

## Scenarios

The bot supports multiple healthcare patient scenarios including:
- Initial consultation calls
- Follow-up appointment calls
- Prescription refill requests
- Insurance inquiry calls
- Appointment scheduling

## Recording and Transcription

All calls are automatically:
- Recorded to `./recordings/`
- Transcribed to `./transcripts/`

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
