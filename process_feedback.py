"""
Process admin feedback from WhatsApp reactions
"""
import sys
import json
import os
from llm_moderation_agent import ModerationAgent

def main():
    """Process feedback from admin reactions"""
    
    if len(sys.argv) != 3:
        sys.exit(1)
    
    message_id = sys.argv[1]
    reaction = sys.argv[2]
    
    try:
        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            raise Exception("GROQ_API_KEY not found")
        
        agent = ModerationAgent(
            groq_api_key=groq_api_key,
            db_path="whatsapp_moderation.db"
        )
        
        # Process the feedback
        success = agent.process_feedback(message_id, reaction)
        
        if success:
            print("Feedback processed successfully")
        else:
            print("Failed to process feedback")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error processing feedback: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
