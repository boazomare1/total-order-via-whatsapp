#!/bin/bash

echo "🚀 WhatsApp Integration - Smart Start"
echo "====================================="
echo "This script checks your token and helps you refresh if needed"
echo ""

# Function to check if token is expired
check_token() {
    echo "🔍 Checking access token status..."
    
    # Try to make a test API call
    if curl -s "https://graph.facebook.com/v18.0/me" \
        -H "Authorization: Bearer $(grep 'WHATSAPP_TOKEN = ' standalone_webhook.py | cut -d'"' -f2)" \
        >/dev/null 2>&1; then
        echo "✅ Access token is valid"
        return 0
    else
        echo "❌ Access token is expired or invalid"
        return 1
    fi
}

# Function to update token
update_token() {
    echo "🔑 Token needs to be updated"
    echo ""
    echo "🌐 Opening Meta Developer Console..."
    python3 -c "import webbrowser; webbrowser.open('https://developers.facebook.com/apps/')"
    
    echo ""
    echo "📋 Follow these steps:"
    echo "1. Select your WhatsApp Business app"
    echo "2. Go to WhatsApp > API Setup"
    echo "3. Copy the 'Temporary access token'"
    echo "4. Paste it below when ready"
    echo ""
    
    read -p "Press Enter when you have copied the new token..."
    
    read -p "Paste your new access token: " new_token
    
    if [ -n "$new_token" ]; then
        # Update the token in the file
        sed -i "s/WHATSAPP_TOKEN = \"[^\"]*\"/WHATSAPP_TOKEN = \"$new_token\"/" standalone_webhook.py
        echo "✅ Token updated successfully!"
    else
        echo "❌ No token provided"
        exit 1
    fi
}

# Main script
echo "📋 Step 1: Checking access token..."
if ! check_token; then
    update_token
fi

echo ""
echo "📋 Step 2: Starting services..."
echo "==============================="

# Kill existing processes
echo "🔧 Cleaning up previous sessions..."
pkill -f standalone_webhook.py 2>/dev/null || true
pkill -f ngrok 2>/dev/null || true
lsof -ti :5000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start webhook
echo "🚀 Starting WhatsApp webhook..."
cd /home/boaz/test-bench/apps/whatsapp_integration/whatsapp_integration
/home/boaz/test-bench/env/bin/python standalone_webhook.py &
sleep 3

# Check if webhook is running
if curl -s http://localhost:5000/health >/dev/null 2>&1; then
    echo "✅ Webhook started successfully"
else
    echo "❌ Failed to start webhook"
    exit 1
fi

# Start ngrok
echo "🌐 Starting ngrok tunnel..."
ngrok http 5000 --log=stdout > /tmp/ngrok.log 2>&1 &
sleep 5

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    print('')
" 2>/dev/null)

if [ -n "$NGROK_URL" ]; then
    echo "✅ ngrok tunnel: $NGROK_URL"
    echo ""
    echo "📋 Update Meta Developer Console:"
    echo "   Webhook URL: $NGROK_URL/webhook"
    echo ""
    echo "📱 Test your WhatsApp integration!"
else
    echo "❌ Failed to get ngrok URL"
fi

echo "🛑 Press Ctrl+C to stop all services"
wait




