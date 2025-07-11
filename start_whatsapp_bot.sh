#!/bin/bash
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
