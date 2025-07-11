# moderation_api.py
"""
API Bridge between JavaScript and Python moderation agent
"""
import sys
import json
import os
from datetime import datetime

# Import our moderation agent
from llm_moderation_agent import ModerationAgent

def main():
    """Main API endpoint called by JavaScript"""
    
    if len(sys.argv) != 4:
        error_response = {
            "error": "Invalid arguments. Expected: message_id user_id content",
            "classification": "CONTEXT_DEPENDENT",
            "confidence": 0.0,
            "action": "FLAG_FOR_REVIEW",
            "reasoning": "API call error"
        }
        print(json.dumps(error_response, ensure_ascii=False))
        sys.exit(1)
    
    message_id = sys.argv[1]
    user_id = sys.argv[2]
    content = sys.argv[3]
    
    try:
        # Initialize moderation agent
        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            raise Exception("GROQ_API_KEY not found in environment variables")
        
        agent = ModerationAgent(
            groq_api_key=groq_api_key,
            db_path="whatsapp_moderation.db"
        )
        
        # Process the message
        result = agent.process_message(message_id, user_id, content)
        
        # Return JSON result
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        error_response = {
            "error": str(e),
            "message_id": message_id,
            "classification": "CONTEXT_DEPENDENT",
            "confidence": 0.0,
            "action": "FLAG_FOR_REVIEW",
            "reasoning": f"Python processing error: {str(e)}"
        }
        print(json.dumps(error_response, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()

