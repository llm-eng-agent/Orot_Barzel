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
    print("🔍 Check if all requirements are met")
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        print(f"❌ Need Python 3.8+. current version is: {python_version.major}.{python_version.minor}")
        return False
    
    print(f"✅ Python {python_version.major}.{python_version.minor} fits the requirement")
    
    # Check Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js {version} installed")
        else:
            print("❌ Node.js not installed")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False
    
    # Check environment variables
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        print("❌ GROQ_API_KEY not set")
        print(" Set like this: export GROQ_API_KEY='your_key_here'")
        return False
    
    print("✅ GROQ_API_KEY is set")
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦Install required dependencies...")
    
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
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
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
        
        print("✅ package.json created")
    
    # Install Node.js dependencies
    try:
        subprocess.run(['npm', 'install'], check=True, capture_output=True)
        print("✅ Node.js dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Faild install Node.js dependencies: {e}")
        return False
    
    return True

def create_startup_script():
    """Create startup script"""
    startup_script = """#!/bin/bash
# start_whatsapp_bot.sh

echo "⬆️ Uploading WhatsApp Moderation Bot..."

# Check environment
if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ GROQ_API_KEY not set"
    echo "Set it with: export GROQ_API_KEY='your_key'"
    exit 1
fi

# Check Python moderation agent
if [ ! -f "llm_moderation_agent.py" ]; then
    echo "❌ llm_moderation_agent.py not found"
    exit 1
fi

# Start the bot
echo "🤖 Starting bот..."
node whatsapp_bot.js
"""
    
    with open('start_whatsapp_bot.sh', 'w', encoding='utf-8') as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod('start_whatsapp_bot.sh', 0o755)
    
    print("✅ startup script created: start_whatsapp_bot.sh")

def create_config_files():
    """Create configuration files"""
    
    # .env template
    env_template = """# Environment variables for WhatsApp Moderation Bot

# GROQ API Key (required)
GROQ_API_KEY=your_groq_api_key_here

# Optional settings
WHATSAPP_SESSION_NAME=orot-barzel-moderation
TARGET_GROUP_NAME=אורות ברזל התנדבויות ועזרה 🇮🇱❤️
LOG_LEVEL=INFO
"""
    
    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_template)
    
    print("✅ .env.example created")
    
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    print("✅ Logs file created in 'logs' directory")

def main():
    """Main setup function"""
    print("🛠️ Starting installing WhatsApp Moderation Bot...")
    print("="*50)
    
    if not check_requirements():
        print("\n❌ Failed to meet all requirements")
        return False
    
    if not install_dependencies():
        print("\n❌ Failed to install dependencies")
        return False
    
    create_startup_script()
    create_config_files()
    
    print("\n" + "="*50)
    print("Installation completed successfully!")
    print("\nNext steps:")
    print("1. Make sure that GROQ_API_KEY defined: export GROQ_API_KEY='your_key'")
    print("2. Aprove the file llm_moderation_agent.py exsits")
    print("3. Run: ./start_whatsapp_bot.sh")
    print("4. Scan QR code with WhatsApp")
    print("\n🤖 The bot has started monitoring the group!")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)