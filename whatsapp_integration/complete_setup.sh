#!/bin/bash

echo "🚀 WhatsApp Integration - Complete Setup & Monitoring"
echo "====================================================="
echo "This script will guide you through everything and monitor the process"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to wait for user input
wait_for_user() {
    echo ""
    read -p "Press Enter when you're ready to continue..."
    echo ""
}

# Function to check if a port is in use
kill_port() {
    echo "🔧 Cleaning up port $1..."
    lsof -ti :$1 | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Function to check webhook health
check_webhook_health() {
    if curl -s http://localhost:5000/health >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to get ngrok URL
get_ngrok_url() {
    curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    print('')
" 2>/dev/null
}

# Function to test webhook with Meta
test_webhook_with_meta() {
    local webhook_url="$1"
    echo "🧪 Testing webhook with Meta..."
    
    # Test the webhook URL
    if curl -s "$webhook_url" >/dev/null 2>&1; then
        print_status "Webhook URL is accessible"
        return 0
    else
        print_error "Webhook URL is not accessible"
        return 1
    fi
}

# Function to monitor logs
monitor_logs() {
    echo ""
    echo "📊 Monitoring webhook logs..."
    echo "============================="
    echo "Watch for incoming messages and any errors"
    echo "Press Ctrl+C to stop monitoring"
    echo ""
    
    # Show recent logs
    if [ -f "/tmp/ngrok.log" ]; then
        echo "📋 Recent ngrok logs:"
        tail -5 /tmp/ngrok.log
        echo ""
    fi
    
    echo "📱 Send a test message to your WhatsApp Business number now!"
    echo "   Type 'menu' to test the ordering system"
    echo ""
    echo "🔍 Monitoring for activity..."
    
    # Monitor for activity
    while true; do
        if curl -s http://localhost:5000/health >/dev/null 2>&1; then
            echo -n "."
            sleep 5
        else
            print_error "Webhook stopped responding!"
            break
        fi
    done
}

# Main script
echo "📋 Step 1: Cleaning up previous sessions..."
echo "==========================================="
kill_port 5000
pkill -f ngrok 2>/dev/null || true
pkill -f standalone_webhook.py 2>/dev/null || true
sleep 3
print_status "Cleanup complete"

echo ""
echo "📋 Step 2: Starting WhatsApp webhook..."
echo "======================================"
cd /home/boaz/test-bench/apps/whatsapp_integration/whatsapp_integration
/home/boaz/test-bench/env/bin/python standalone_webhook.py &
WEBHOOK_PID=$!
sleep 5

if check_webhook_health; then
    print_status "Webhook started successfully"
else
    print_error "Failed to start webhook"
    exit 1
fi

echo ""
echo "📋 Step 3: Starting ngrok tunnel..."
echo "==================================="
ngrok http 5000 --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
sleep 5

NGROK_URL=$(get_ngrok_url)
if [ -n "$NGROK_URL" ]; then
    print_status "ngrok tunnel created: $NGROK_URL"
else
    print_error "Failed to get ngrok URL"
    exit 1
fi

echo ""
echo "📋 Step 4: Meta Developer Console Setup"
echo "======================================="
print_info "Now you need to update your Meta Developer Console"
echo ""
echo "🌐 Opening Meta Developer Console..."
python3 -c "import webbrowser; webbrowser.open('https://developers.facebook.com/apps/')"
echo ""
echo "📋 Follow these steps:"
echo "1. Select your WhatsApp Business app"
echo "2. Go to WhatsApp > Configuration"
echo "3. Update Webhook URL to: $NGROK_URL/webhook"
echo "4. Click 'Verify and Save'"
echo ""
wait_for_user

echo ""
echo "📋 Step 5: Access Token Update"
echo "============================="
print_warning "Check if you need a new access token"
echo ""
echo "🔍 Current token status:"
if curl -s "https://graph.facebook.com/v18.0/me" \
    -H "Authorization: Bearer $(grep 'WHATSAPP_TOKEN = ' standalone_webhook.py | cut -d'"' -f2)" \
    >/dev/null 2>&1; then
    print_status "Current token is valid"
else
    print_warning "Token may be expired or invalid"
    echo ""
    echo "🔑 Get a new access token:"
    echo "1. Go to: https://developers.facebook.com/apps/"
    echo "2. Select your app > WhatsApp > API Setup"
    echo "3. Copy the 'Temporary access token'"
    echo "4. Paste it below when ready"
    echo ""
    read -p "Enter your new access token: " new_token
    
    if [ -n "$new_token" ]; then
        # Update the token in the file
        sed -i "s/WHATSAPP_TOKEN = \"[^\"]*\"/WHATSAPP_TOKEN = \"$new_token\"/" standalone_webhook.py
        print_status "Token updated successfully!"
        echo ""
        echo "🔄 Restarting webhook with new token..."
        kill $WEBHOOK_PID 2>/dev/null || true
        sleep 3
        /home/boaz/test-bench/env/bin/python standalone_webhook.py &
        WEBHOOK_PID=$!
        sleep 5
        
        if check_webhook_health; then
            print_status "Webhook restarted with new token"
        else
            print_error "Failed to restart webhook"
            exit 1
        fi
    else
        print_warning "No token provided, continuing with current token"
    fi
fi

echo ""
echo "📋 Step 6: Testing Webhook with Meta"
echo "===================================="
if test_webhook_with_meta "$NGROK_URL/webhook"; then
    print_status "Webhook is accessible from Meta"
else
    print_error "Webhook is not accessible from Meta"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "1. Check if ngrok is running: http://localhost:4040"
    echo "2. Check if webhook is running: http://localhost:5000/health"
    echo "3. Verify the webhook URL in Meta Console"
    echo ""
    wait_for_user
fi

echo ""
echo "📋 Step 7: Final Verification"
echo "============================="
print_info "Testing complete setup..."

# Test webhook health
if check_webhook_health; then
    print_status "✅ Webhook is healthy"
else
    print_error "❌ Webhook health check failed"
fi

# Test ngrok tunnel
if curl -s "$NGROK_URL/health" >/dev/null 2>&1; then
    print_status "✅ ngrok tunnel is working"
else
    print_error "❌ ngrok tunnel test failed"
fi

# Test Meta webhook
if test_webhook_with_meta "$NGROK_URL/webhook"; then
    print_status "✅ Meta webhook is accessible"
else
    print_error "❌ Meta webhook test failed"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
print_status "WhatsApp webhook: http://localhost:5000"
print_status "Public URL: $NGROK_URL"
print_status "Meta webhook URL: $NGROK_URL/webhook"
echo ""
print_info "Your WhatsApp integration is ready!"
echo ""

# Start monitoring
monitor_logs




