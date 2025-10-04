#!/bin/bash

echo "🚀 WhatsApp Integration - Quick Start"
echo "====================================="
echo ""

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




