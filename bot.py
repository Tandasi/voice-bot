"""
Voice bot logic for handling patient conversations.

This module contains:
- Conversation state management
- Integration with OpenAI GPT-4o for realistic patient dialogue
- Speech-to-text input processing
- Text-to-speech output generation
- Call recording management
- Conversation flow control (greeting, questions, responses, conclusion)
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ConversationBot:
    """
    Voice bot that simulates patient conversations using OpenAI GPT-4o.
    
    Maintains conversation state, tracks turns, and generates natural patient responses
    based on agent input and the patient scenario context.
    """
    
    MAX_TURNS = 15
    GOODBYE_KEYWORDS = ["goodbye", "bye", "take care", "thanks for calling", "thanks so much", "appreciate it"]
    
    def __init__(self, scenario):
        """
        Initialize the conversation bot with a patient scenario.
        
        Args:
            scenario (dict): Patient scenario with id, name, patient_name, system_prompt, goal, opening_line
        """
        self.scenario = scenario
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        
        # Conversation history for maintaining context
        self.conversation_history = []
        
        # Track number of conversation turns
        self.turn_count = 0
        
        # System prompt with instructions for natural, brief responses
        self.system_prompt = f"""{scenario['system_prompt']}

IMPORTANT: Keep your responses short and natural - maximum 1-3 sentences.
Speak like a real person in a phone conversation, not a script.
Respond directly to what the agent says. Push toward your goal but naturally.
When you feel the conversation has reached its conclusion, end it gracefully with a goodbye."""
    
    def get_opening_line(self):
        """
        Get the patient's opening line when the call connects.
        
        Returns:
            str: The scenario's opening line spoken by the patient
        """
        self.add_to_history("assistant", self.scenario["opening_line"])
        return self.scenario["opening_line"]
    
    def add_to_history(self, role, content):
        """
        Add a message to the conversation history.
        
        Args:
            role (str): "user" (agent) or "assistant" (patient)
            content (str): The message content
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def get_response(self, agent_speech):
        """
        Generate the patient's next response based on agent input.
        
        Sends the full conversation history to GPT-4o to maintain context,
        then returns the patient's natural response.
        
        Args:
            agent_speech (str): The speech/input from the agent/healthcare provider
            
        Returns:
            str: The patient's next response (1-3 sentences, natural speech)
        """
        # Add agent's latest message to history
        self.add_to_history("user", agent_speech)
        self.turn_count += 1
        
        try:
            # Call GPT-4o with full conversation context
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                temperature=0.7,  # Some randomness for natural conversation
                max_tokens=150  # Limit response length
            )
            
            # Extract the response text
            patient_response = response.choices[0].message.content.strip()
            
            # Add patient response to history
            self.add_to_history("assistant", patient_response)
            
            return patient_response
            
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return "I'm sorry, I didn't catch that. Could you repeat?"
    
    def is_conversation_complete(self):
        """
        Determine if the conversation should end.
        
        Conversation completes if:
        - Max turns (15) have been reached
        - Patient response indicates goodbye/conclusion
        
        Returns:
            bool: True if conversation should end, False otherwise
        """
        # Check max turns limit
        if self.turn_count >= self.MAX_TURNS:
            return True
        
        # Check if last patient message indicates goodbye
        if self.conversation_history and self.conversation_history[-1]["role"] == "assistant":
            last_response = self.conversation_history[-1]["content"].lower()
            if any(keyword in last_response for keyword in self.GOODBYE_KEYWORDS):
                return True
        
        return False
    
    def get_conversation_summary(self):
        """
        Get a summary of the conversation so far.
        
        Returns:
            dict: Summary with turn count, scenario info, and full history
        """
        return {
            "scenario_id": self.scenario["id"],
            "scenario_name": self.scenario["name"],
            "patient_name": self.scenario["patient_name"],
            "goal": self.scenario["goal"],
            "turn_count": self.turn_count,
            "conversation_history": self.conversation_history,
            "is_complete": self.is_conversation_complete()
        }
