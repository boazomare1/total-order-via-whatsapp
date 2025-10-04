#!/bin/bash

echo "🚀 WhatsApp Integration - Complete Startup Script"
echo "=================================================="
echo "This script will help you get everything running"
echo "after powering on your laptop."
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to kill processes on a port
kill_port() {
    echo "🔧 Killing processes on port $1..."
    lsof -ti :$1 | xargs kill -9 2>/dev/null || true
    sleep 2
}

echo "📋 Step 1: Checking Prerequisites..."
echo "====================================="

# Check if ngrok is installed
if ! command_exists ngrok; then
    echo "❌ ngrok is not installed!"
    echo "Please install ngrok first:"
    echo "  - Download from: https://ngrok.com/download"
    echo "  - Or install via package manager"
    exit 1
else
    echo "✅ ngrok is installed"
fi

# Check if Python is available
if ! command_exists python3; then
    echo "❌ Python3 is not installed!"
    exit 1
else
    echo "✅ Python3 is available"
fi

# Check if we're in the right directory
if [ ! -f "standalone_webhook.py" ]; then
    echo "❌ standalone_webhook.py not found!"
    echo "Please run this script from the whatsapp_integration directory"
    exit 1
else
    echo "✅ In correct directory"
fi

echo ""
echo "📋 Step 2: Cleaning Up Previous Sessions..."
echo "==========================================="

# Kill any existing processes on our ports
kill_port 5000
kill_port 5001
kill_port 5002

# Kill any existing ngrok processes
echo "🔧 Stopping any existing ngrok tunnels..."
pkill -f ngrok 2>/dev/null || true
sleep 2

echo ""
echo "📋 Step 3: Starting ERPNext (if not running)..."
echo "==============================================="

# Check if ERPNext is running
if ! curl -s http://localhost:8002 >/dev/null 2>&1; then
    echo "🔧 Starting ERPNext..."
    cd /home/boaz/test-bench
    bench start --site totalwhatsapporder.local &
    sleep 10
    echo "✅ ERPNext started"
else
    echo "✅ ERPNext is already running"
fi

echo ""
echo "📋 Step 4: Starting WhatsApp Webhook..."
echo "======================================="

# Start the webhook
echo "🚀 Starting WhatsApp webhook server..."
cd /home/boaz/test-bench/apps/whatsapp_integration/whatsapp_integration
/home/boaz/test-bench/env/bin/python standalone_webhook.py &
WEBHOOK_PID=$!
sleep 5

# Check if webhook started successfully
if curl -s http://localhost:5000/health >/dev/null 2>&1; then
    echo "✅ WhatsApp webhook is running on port 5000"
else
    echo "❌ Failed to start webhook"
    exit 1
fi

echo ""
echo "📋 Step 5: Setting up ngrok tunnel..."
echo "====================================="

# Start ngrok tunnel
echo "🌐 Starting ngrok tunnel..."
ngrok http 5000 --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
sleep 5

# Get the ngrok URL
echo "🔍 Getting ngrok URL..."
sleep 3
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

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL"
    echo "Please check ngrok status manually"
    exit 1
else
    echo "✅ ngrok tunnel created: $NGROK_URL"
fi

echo ""
echo "📋 Step 6: Meta Developer Console Setup..."
echo "========================================="

echo "🔧 IMPORTANT: You need to update your Meta Developer Console:"
echo ""
echo "1. Go to: https://developers.facebook.com/apps/"
echo "2. Select your WhatsApp Business app"
echo "3. Go to WhatsApp > Configuration"
echo "4. Update Webhook URL to: $NGROK_URL/webhook"
echo "5. Click 'Verify and Save'"
echo ""

# Check if we need to update the access token
echo "🔍 Checking if you need a new access token..."
echo "   (Access tokens expire every 24 hours)"
echo ""
echo "If you need a new token:"
echo "1. Go to: https://developers.facebook.com/apps/"
echo "2. Select your app > WhatsApp > API Setup"
echo "3. Generate a new access token"
echo "4. Update standalone_webhook.py with the new token"
echo ""

echo ""
echo "📋 Step 7: Testing the Setup..."
echo "==============================="

echo "🧪 Testing webhook health..."
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    echo "✅ Webhook is healthy"
else
    echo "❌ Webhook health check failed"
fi

echo "🧪 Testing ngrok tunnel..."
if curl -s "$NGROK_URL/health" | grep -q "healthy"; then
    echo "✅ ngrok tunnel is working"
else
    echo "❌ ngrok tunnel test failed"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📱 WhatsApp Webhook: http://localhost:5000"
echo "🌐 Public URL: $NGROK_URL"
echo "🔍 Health Check: $NGROK_URL/health"
echo ""
echo "📋 Next Steps:"
echo "1. Update Meta Developer Console with the new webhook URL"
echo "2. Test by sending a WhatsApp message to your business number"
echo "3. Check the webhook logs for any issues"
echo ""
echo "🛑 To stop all services, run:"
echo "   pkill -f standalone_webhook.py"
echo "   pkill -f ngrok"
echo "   pkill -f bench"
echo ""
echo "📊 Monitor logs:"
echo "   tail -f /tmp/ngrok.log  # ngrok logs"
echo "   # webhook logs will show in this terminal"
echo ""

# Keep the script running to show webhook logs
echo "📱 Webhook is running... Press Ctrl+C to stop"
echo "=============================================="
wait $WEBHOOK_PID




