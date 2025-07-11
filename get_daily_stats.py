"""
Generate daily statistics for WhatsApp reporting
"""
import json
import os
from datetime import datetime, timedelta
from llm_moderation_agent import ModerationAgent

def get_daily_statistics():
    """Get comprehensive daily statistics"""
    
    try:
        groq_api_key = os.getenv('GROQ_API_KEY', 'dummy')
        agent = ModerationAgent(
            groq_api_key=groq_api_key,
            db_path="whatsapp_moderation.db"
        )
        
        # Get basic stats
        stats = agent.get_stats()
        
        # Calculate daily specific metrics
        today = datetime.now().date()
        
        # Get today's messages from database
        import sqlite3
        conn = sqlite3.connect("whatsapp_moderation.db")
        cursor = conn.cursor()
        
        # Today's messages
        cursor.execute("""
            SELECT classification, action 
            FROM messages 
            WHERE date(timestamp) = date('now')
        """)
        
        today_results = cursor.fetchall()
        
        # Count by category
        approved = sum(1 for r in today_results if r[0] == 'APPROVED')
        flagged = sum(1 for r in today_results if r[0] == 'CONTEXT_DEPENDENT')
        deleted = sum(1 for r in today_results if r[1] == 'DELETE_MESSAGE')
        
        # Calculate improvement (week over week accuracy)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_feedback,
                SUM(CASE WHEN feedback = 'CORRECT' THEN 1 ELSE 0 END) as correct
            FROM messages 
            WHERE date(timestamp) = date('now') 
            AND feedback IS NOT NULL
        """)
        
        today_feedback = cursor.fetchone()
        today_accuracy = 0
        if today_feedback and today_feedback[0] > 0:
            today_accuracy = (today_feedback[1] / today_feedback[0]) * 100
        
        # Week ago accuracy
        cursor.execute("""
            SELECT 
                COUNT(*) as total_feedback,
                SUM(CASE WHEN feedback = 'CORRECT' THEN 1 ELSE 0 END) as correct
            FROM messages 
            WHERE date(timestamp) = date('now', '-7 days')
            AND feedback IS NOT NULL
        """)
        
        week_ago_feedback = cursor.fetchone()
        week_ago_accuracy = 0
        if week_ago_feedback and week_ago_feedback[0] > 0:
            week_ago_accuracy = (week_ago_feedback[1] / week_ago_feedback[0]) * 100
        
        improvement = today_accuracy - week_ago_accuracy
        
        conn.close()
        
        daily_stats = {
            "daily_messages": len(today_results),
            "approved": approved,
            "flagged": flagged,
            "deleted": deleted,
            "accuracy": round(stats.get('accuracy', 0), 1),
            "improvement": round(improvement, 1),
            "total_messages_processed": stats.get('total_messages', 0)
        }
        
        return daily_stats
        
    except Exception as e:
        return {
            "error": str(e),
            "daily_messages": 0,
            "approved": 0,
            "flagged": 0,
            "deleted": 0,
            "accuracy": 0,
            "improvement": 0
        }

def main():
    """Main function for command line usage"""
    try:
        stats = get_daily_statistics()
        print(json.dumps(stats, ensure_ascii=False))
    except Exception as e:
        error_stats = {
            "error": str(e),
            "daily_messages": 0,
            "approved": 0,
            "flagged": 0,
            "deleted": 0,
            "accuracy": 0,
            "improvement": 0
        }
        print(json.dumps(error_stats, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
