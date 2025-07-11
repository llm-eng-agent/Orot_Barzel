"""
Setup script for WhatsApp integration
"""
import os
import json
import subprocess
import sys
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 בודק דרישות מערכת...")
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"❌ נדרש Python 3.8+. גרסה נוכחית: {python_version.major}.{python_version.minor}")
        return False
    
    print(f"✅ Python {python_version.major}.{python_version.minor} מתאים")
    
    # Check Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js {version} מותקן")
        else:
            print("❌ Node.js לא מותקן")
            return False
    except FileNotFoundError:
        print("❌ Node.js לא מותקן")
        return False
    
    # Check environment variables
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        print("❌ GROQ_API_KEY לא מוגדר")
        print("הגדר עם: export GROQ_API_KEY='your_key_here'")
        return False
    
    print("✅ GROQ_API_KEY מוגדר")
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 מתקין תלויות...")
    
    # Python dependencies
    python_deps = [
        'langgraph',
        'langchain-groq', 
        'langchain-core'
    ]
    
    for dep in python_deps:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep], 
                         check=True, capture_output=True)
            print(f"✅ {dep} הותקן")
        except subprocess.CalledProcessError as e:
            print(f"❌ נכשל בהתקנת {dep}: {e}")
            return False
    
    # Node.js dependencies
    if not Path('package.json').exists():
        # Create package.json
        package_json = {
            "name": "whatsapp-moderation-bot",
            "version": "1.0.0",
            "description": "WhatsApp moderation bot for Orot Barzel",
            "main": "whatsapp_bot.js",
            "scripts": {
                "start": "node whatsapp_bot.js",
                "test": "echo \"No tests yet\" && exit 0"
            },
            "dependencies": {
                "whatsapp-web.js": "^1.21.0",
                "qrcode-terminal": "^0.12.0"
            },
            "keywords": ["whatsapp", "moderation", "bot"],
            "author": "Orot Barzel Team",
            "license": "MIT"
        }
        
        with open('package.json', 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2, ensure_ascii=False)
        
        print("✅ package.json נוצר")
    
    # Install Node.js dependencies
    try:
        subprocess.run(['npm', 'install'], check=True, capture_output=True)
        print("✅ Node.js dependencies הותקנו")
    except subprocess.CalledProcessError as e:
        print(f"❌ נכשל בהתקנת Node.js dependencies: {e}")
        return False
    
    return True

def create_startup_script():
    """Create startup script"""
    startup_script = """#!/bin/bash
# start_whatsapp_bot.sh

echo "🚀 מפעיל WhatsApp Moderation Bot..."

# Check environment
if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ GROQ_API_KEY לא מוגדר"
    echo "הגדר עם: export GROQ_API_KEY='your_key'"
    exit 1
fi

# Check Python moderation agent
if [ ! -f "llm_moderation_agent.py" ]; then
    echo "❌ llm_moderation_agent.py לא נמצא"
    exit 1
fi

# Start the bot
echo "🤖 מפעיל את הbот..."
node whatsapp_bot.js
"""
    
    with open('start_whatsapp_bot.sh', 'w', encoding='utf-8') as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod('start_whatsapp_bot.sh', 0o755)
    
    print("✅ startup script נוצר")

def create_config_files():
    """Create configuration files"""
    
    # .env template
    env_template = """# Environment variables for WhatsApp Moderation Bot

# GROQ API Key (required)
GROQ_API_KEY=your_groq_api_key_here

# Optional settings
WHATSAPP_SESSION_NAME=orot-barzel-moderation
TARGET_GROUP_NAME=אורות ברזל
LOG_LEVEL=INFO
"""
    
    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_template)
    
    print("✅ .env.example נוצר")
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    print("✅ תיקיית logs נוצרה")

def main():
    """Main setup function"""
    print("🛠️ מתחיל התקנת WhatsApp Moderation Bot...")
    print("="*50)
    
    if not check_requirements():
        print("\n❌ יש בעיות בדרישות המערכת")
        return False
    
    if not install_dependencies():
        print("\n❌ נכשל בהתקנת תלויות")
        return False
    
    create_startup_script()
    create_config_files()
    
    print("\n" + "="*50)
    print("🎉 ההתקנה הושלמה בהצלחה!")
    print("\nשלבים הבאים:")
    print("1. וודא ש-GROQ_API_KEY מוגדר: export GROQ_API_KEY='your_key'")
    print("2. וודא שקובץ llm_moderation_agent.py קיים")
    print("3. הרץ: ./start_whatsapp_bot.sh")
    print("4. סרוק QR code בWhatsApp")
    print("\n🤖 הבוט יתחיל לפקח על הקבוצה!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)