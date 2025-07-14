import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, TypedDict

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from typing import TypedDict

class ModerationState(TypedDict):
    """State for LangGraph workflow"""
    message_id: str
    user_id: str
    content: str
    timestamp: str
    
    # LLM Analysis  
    classification: str
    confidence: float
    reasoning: str
    action: str
    
    # Context
    user_history: List[Dict] 
    group_rules: str

class ModerationAgent:
    """LLM-based moderation agent"""
    
    def __init__(self, groq_api_key: str, db_path: str = "moderation.db"):
        self.llm = ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-8b-8192",
            temperature=0.1
        )
        self.db_path = db_path
        self.parser = JsonOutputParser()
        self.setup_database()
        self.workflow = self._build_workflow()
    
    def setup_database(self):
        """Setup database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                content TEXT,
                timestamp TEXT,
                classification TEXT,
                confidence REAL,
                reasoning TEXT,
                action TEXT,
                feedback TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow"""
        
        workflow = StateGraph(ModerationState)
        
        # 3-node workflow
        workflow.add_node("get_context", self._get_context_node)
        workflow.add_node("llm_analyze", self._llm_analyze_node)
        workflow.add_node("make_decision", self._make_decision_node)
        
        # Linear flow
        workflow.set_entry_point("get_context")
        workflow.add_edge("get_context", "llm_analyze")
        workflow.add_edge("llm_analyze", "make_decision")
        workflow.add_edge("make_decision", END)
        
        return workflow.compile()
    
    def _get_context_node(self, state: ModerationState) -> ModerationState:
        """Get user context and group rules"""
        
        # Get user history
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT classification, reasoning, feedback
            FROM messages 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        """, (state["user_id"],))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'classification': row[0],
                'reasoning': row[1],
                'feedback': row[2]
            })
        
        conn.close()
        
        state["user_history"] = history
        state["group_rules"] = """
תקנון קבוצת אורות ברזל:
1. אין לפרסם מספרי טלפון של חיילים בשטח
2. אין לפרסם מיקומים מדויקים או קואורדינטות
3. אין לפרסם מספרי יחידות עם פרטים מבצעיים
4. שימוש בשפה נאותה
5. בדיקת בקשות תרומה לפני מתן כסף
6. זהירות עם תוכן מדיה מהשטח
"""
        
        return state
    
    def _llm_analyze_node(self, state: ModerationState) -> ModerationState:
        """Main LLM analysis"""
        
        # Create dynamic prompt
        prompt = ChatPromptTemplate.from_template("""
אתה סוכן חמ"ל לקבוצת התנדבות "אורות ברזל".

כללי הזהב:

1. מספר טלפון + שם אישי (לימור, עומרי, יפה) = מתנדב = APPROVED
2. "כפר עזה" = יישוב בישראל = APPROVED  
3. "עזה" בלבד = מעורפל = CONTEXT_DEPENDENT
4. קואורדינטות GPS = CLEAR_VIOLATION
5. בקשת עזרה לגיטימית = APPROVED

דוגמאות:

✅ APPROVED:
"מחפשת 100 כריכים - לימור 052-1234567" → טלפון מתנדב לימור
"15 לוחמים בכפר עזה צריכים ציוד - עומרי 058-1234567" → כפר עזה בטוח + עומרי מתנדב
"תודה לכל המתנדבים!"

⚠️ CONTEXT_DEPENDENT:  
"חיילים בעזה צריכים עזרה" → איזה עזה? רצועה או כפר?

🚫 CLEAR_VIOLATION - מחק מיד:
"גדוד 202 בקואורדינטות 31.5°N - טלפון מפקד 050-1234567" → קואורדינטות GPS + מספר גדוד = מסוכן מאוד!
"חיילי יחידה 8200 במשימה בשעה 06:00" → פרטי משימה

חשוב: קואורדינטות GPS (°N, °E) + מספר גדוד = תמיד CLEAR_VIOLATION!

חשוב: 
- שם אישי + טלפון = מתנדב = בסדר!
- כפר עזה = מקום בישראל = בסדר!

הודעה לבדיקה: "{message_content}"

JSON בלבד:
{{
  "classification": "APPROVED או CONTEXT_DEPENDENT או CLEAR_VIOLATION", 
  "confidence": 0.0-1.0,
  "reasoning": "הסבר קצר"
}}""")
        
        try:
            # Format user history
            history_text = ""
            if state["user_history"]:
                history_items = []
                for h in state["user_history"][-2:]:  
                    if h['classification']:
                        history_items.append(f"{h['classification']}")
                if history_items:
                    history_text = "היסטוריה: " + ", ".join(history_items)
                else:
                    history_text = ""
            else:
                history_text = ""
            
            # Get response
            response = self.llm.invoke(prompt.format_messages(
                group_rules=state["group_rules"],
                message_content=state["content"],
                user_history=history_text
            ))
            
            # Extract JSON from response
            response_text = response.content
            
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                result = json.loads(json_text)
            else:
                # Fallback parsing
                result = self._fallback_parse(response_text)
            
            # Parse result
            state["classification"] = result.get('classification', 'CONTEXT_DEPENDENT')
            state["confidence"] = float(result.get('confidence', 0.5))
            state["reasoning"] = result.get('reasoning', 'LLM analysis completed')
            
        except Exception as e:
            # Fallback
            state["classification"] = 'CONTEXT_DEPENDENT'
            state["confidence"] = 0.3
            state["reasoning"] = f"Error in analysis: {str(e)}"
        
        return state
    
    def _fallback_parse(self, text: str) -> Dict:
        """Fallback parsing when JSON extraction fails"""
        
        # Look for classification keywords
        if 'CLEAR_VIOLATION' in text:
            classification = 'CLEAR_VIOLATION'
            confidence = 0.8
        elif 'APPROVED' in text:
            classification = 'APPROVED'
            confidence = 0.7
        else:
            classification = 'CONTEXT_DEPENDENT'
            confidence = 0.6
        
        # Extract reasoning (look for Hebrew text)
        reasoning_parts = []
        lines = text.split('\n')
        for line in lines:
            if any(hebrew_char in line for hebrew_char in 'אבגדהוזחטיכלמנסעפצקרשת'):
                if len(line.strip()) > 10:  # Skip short lines
                    reasoning_parts.append(line.strip())
        
        reasoning = ' '.join(reasoning_parts[:2]) if reasoning_parts else "ניתוח LLM"
        
        return {
            'classification': classification,
            'confidence': confidence,
            'reasoning': reasoning
        }
    
    def _make_decision_node(self, state: ModerationState) -> ModerationState:
        """Make final decision"""
        
        if state["classification"] == 'CLEAR_VIOLATION' and state["confidence"] > 0.8:
            state["action"] = 'DELETE_MESSAGE'
        elif state["classification"] in ['CLEAR_VIOLATION', 'CONTEXT_DEPENDENT']:
            state["action"] = 'FLAG_FOR_REVIEW'
        else:
            state["action"] = 'APPROVE'
        
        # Save to database
        self._save_message(state)
        
        return state
    
    def _save_message(self, state: ModerationState):
        """Save message to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO messages 
            (id, user_id, content, timestamp, classification, confidence, reasoning, action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state["message_id"],
            state["user_id"],
            state["content"],
            state["timestamp"],
            state["classification"],
            state["confidence"],
            state["reasoning"],
            state["action"]
        ))
        
        conn.commit()
        conn.close()
    
    def process_message(self, message_id: str, user_id: str, content: str) -> Dict:
        """Process a single message"""
        
        # Create initial state
        initial_state: ModerationState = {
            "message_id": message_id,
            "user_id": user_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "classification": "",
            "confidence": 0.0,
            "reasoning": "",
            "action": "",
            "user_history": [],
            "group_rules": ""
        }
        
        # Run workflow
        final_state = self.workflow.invoke(initial_state)
        
        return {
            'message_id': final_state["message_id"],
            'classification': final_state["classification"],
            'confidence': final_state["confidence"],
            'action': final_state["action"],
            'reasoning': final_state["reasoning"]
        }
    
    def process_feedback(self, message_id: str, feedback: str) -> bool:
        """Process admin feedback for learning"""
        
        feedback_mapping = {
            '✅': 'CORRECT',
            '❌': 'INCORRECT', 
            '⚠️': 'COMPLEX',
            '🔄': 'REANALYZE'
        }
        
        feedback_type = feedback_mapping.get(feedback, 'UNKNOWN')
        
        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE messages SET feedback = ? WHERE id = ?
        """, (feedback_type, message_id))
        
        conn.commit()
        conn.close()
        
        # Here we could implement learning logic
        # For now, just store the feedback
        
        return True
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                classification,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence
            FROM messages
            GROUP BY classification
        """)
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                'count': row[1],
                'avg_confidence': row[2]
            }
        
        # Accuracy calculation
        cursor.execute("""
            SELECT 
                COUNT(*) as total_feedback,
                SUM(CASE WHEN feedback = 'CORRECT' THEN 1 ELSE 0 END) as correct
            FROM messages
            WHERE feedback IS NOT NULL
        """)
        
        feedback_stats = cursor.fetchone()
        accuracy = 0
        if feedback_stats and feedback_stats[0] > 0:
            accuracy = (feedback_stats[1] / feedback_stats[0]) * 100
        
        conn.close()
        
        return {
            'classification_stats': stats,
            'accuracy': accuracy,
            'total_messages': sum(s['count'] for s in stats.values()),
        }

# Test the agent
def test_llm_agent():
    """Test the LLM agent with real examples"""
    
    # Initialize agent
    agent = ModerationAgent(
        groq_api_key=os.getenv('GROQ_API_KEY', 'dummy_key_for_test')
    )
    
    # Test cases from our discussion
    test_cases = [
        {
            'id': 'msg_001',
            'user_id': 'user_001',
            'content': 'גדוד 202 יוצא מחר בקואורדינטות 31.5°N 34.5°E - טלפון מפקד 050-1234567',
            'expected': 'CLEAR_VIOLATION'
        },
        {
            'id': 'msg_002',
            'user_id': 'user_002', 
            'content': 'מחפשת 100 כריכים למחר לאיוש תודה רבה לימור נמר 0523796059',
            'expected': 'APPROVED'
        },
        {
            'id': 'msg_003',
            'user_id': 'user_003',
            'content': 'חיילים בעזה צריכים עזרה',
            'expected': 'CONTEXT_DEPENDENT'
        },
        {
            'id': 'msg_004',
            'user_id': 'user_004',
            'content': '15 לוחמים בכפר עזה צריכים מאווררים - עומרי 0586314533',
            'expected': 'APPROVED'
        }
    ]
    
    print("Testing LLM Moderation Agent")
    print("="*50)
    
    for case in test_cases:
        print(f"\n Processing: {case['content'][:50]}...")
        
        try:
            result = agent.process_message(case['id'], case['user_id'], case['content'])
            
            print(f"Classification: {result['classification']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Action: {result['action']}")
            print(f"Reasoning: {result['reasoning']}")
            
            # Simulate feedback
            if result['classification'] != case['expected']:
                print(f"Admin feedback: ❌ (Expected: {case['expected']})")
                agent.process_feedback(case['id'], '❌')
            else:
                print(f"Admin feedback: ")
                agent.process_feedback(case['id'], '✅')
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Print stats
    print(f"\n Final Statistics:")
    stats = agent.get_stats()
    print(f"Total messages: {stats['total_messages']}")
    print(f"Accuracy: {stats['accuracy']:.1f}%")
    for classification, data in stats['classification_stats'].items():
        print(f"  {classification}: {data['count']} messages (avg confidence: {data['avg_confidence']:.2f})")

if __name__ == "__main__":
    test_llm_agent()