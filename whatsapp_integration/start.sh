#!/bin/bash

echo "🚀 WhatsApp Integration - Complete Setup & Monitoring"
echo "====================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_step() { echo -e "${PURPLE}📋 $1${NC}"; }

# Function to check webhook health
check_webhook() {
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

# Function to test token
test_token() {
    local token="$1"
    if curl -s "https://graph.facebook.com/v18.0/me" \
        -H "Authorization: Bearer $token" \
        >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to update token in file
update_token() {
    local new_token="$1"
    sed -i "s/WHATSAPP_TOKEN = \"[^\"]*\"/WHATSAPP_TOKEN = \"$new_token\"/" standalone_webhook.py
}

# Main script
print_step "Step 1: Cleaning up previous sessions..."
pkill -f standalone_webhook.py 2>/dev/null || true
pkill -f ngrok 2>/dev/null || true
lsof -ti :5000 | xargs kill -9 2>/dev/null || true
sleep 3
print_status "Cleanup complete"

print_step "Step 2: Starting WhatsApp webhook..."
cd /home/boaz/test-bench/apps/whatsapp_integration/whatsapp_integration
/home/boaz/test-bench/env/bin/python standalone_webhook.py &
WEBHOOK_PID=$!
sleep 5

if check_webhook; then
    print_status "Webhook started successfully"
else
    print_error "Failed to start webhook"
    exit 1
fi

print_step "Step 3: Starting ngrok tunnel..."
ngrok http 5000 --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
sleep 5

NGROK_URL=$(get_ngrok_url)
if [ -n "$NGROK_URL" ]; then
    print_status "ngrok tunnel: $NGROK_URL"
else
    print_error "Failed to get ngrok URL"
    exit 1
fi

print_step "Step 4: Meta Developer Console Setup"
echo ""
print_info "🌐 Opening Meta Developer Console..."
python3 -c "import webbrowser; webbrowser.open('https://developers.facebook.com/apps/')"
echo ""
echo "📋 Update your webhook URL:"
echo "   $NGROK_URL/webhook"
echo ""
echo "📋 Steps to follow:"
echo "1. Select your WhatsApp Business app"
echo "2. Go to WhatsApp > Configuration"
echo "3. Update Webhook URL to: $NGROK_URL/webhook"
echo "4. Click 'Verify and Save'"
echo ""
echo "⏳ WAIT: Don't press Enter yet!"
echo "📱 Test the webhook URL first by sending a message to your WhatsApp Business number"
echo "✅ When you see 'Verification successful' in the logs, THEN press Enter"
echo ""
read -p "Press Enter ONLY after you've tested the webhook and seen verification success..."

print_step "Step 5: Access Token Update (REQUIRED)"
echo ""
print_warning "🔑 You MUST get a NEW access token from Meta"
print_error "❌ Current token is EXPIRED (401 error detected)"
echo ""
print_info "🌐 Opening Meta Console for token..."
python3 -c "import webbrowser; webbrowser.open('https://developers.facebook.com/apps/')"
echo ""
echo "📋 Get your new access token:"
echo "1. Go to: https://developers.facebook.com/apps/"
echo "2. Select your app > WhatsApp > API Setup"
echo "3. Copy the 'Temporary access token'"
echo "4. Paste it below"
echo ""
echo "⚠️  THIS STEP IS MANDATORY - NO TOKEN = NO WHATSAPP MESSAGES"
echo "⚠️  Your current token is EXPIRED - you MUST get a new one"
echo ""
read -p "Enter your new access token: " new_token

# Force token input - ask once, then exit if empty
if [ -z "$new_token" ]; then
    print_error "❌ NO TOKEN PROVIDED!"
    echo ""
    print_warning "You MUST provide an access token to continue"
    echo ""
    print_info "🌐 Opening Meta Console for token..."
    python3 -c "import webbrowser; webbrowser.open('https://developers.facebook.com/apps/')"
    echo ""
    echo "📋 Get your access token:"
    echo "1. Go to: https://developers.facebook.com/apps/"
    echo "2. Select your app > WhatsApp > API Setup"
    echo "3. Copy the 'Temporary access token'"
    echo "4. Paste it below"
    echo ""
    read -p "Enter your access token (REQUIRED): " new_token
    
    if [ -z "$new_token" ]; then
        print_error "❌ No token provided. Exiting."
        exit 1
    fi
fi

print_info "Updating access token..."
update_token "$new_token"
print_status "Token updated successfully!"

# Restart webhook with new token
print_info "Restarting webhook with new token..."
kill $WEBHOOK_PID 2>/dev/null || true
sleep 3
/home/boaz/test-bench/env/bin/python standalone_webhook.py &
WEBHOOK_PID=$!
sleep 5

if check_webhook; then
    print_status "Webhook restarted with new token"
else
    print_error "Failed to restart webhook"
    exit 1
fi

# Test the new token
print_info "Testing new access token..."
if test_token "$new_token"; then
    print_status "✅ New access token is valid"
else
    print_error "❌ New access token is invalid"
    echo ""
    print_warning "Please check your token and try again"
    exit 1
fi

print_step "Step 6: Final Verification"
echo ""
print_info "Testing complete setup..."

# Test webhook health
if check_webhook; then
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
if curl -s "$NGROK_URL/webhook" >/dev/null 2>&1; then
    print_status "✅ Meta webhook is accessible"
else
    print_error "❌ Meta webhook test failed"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
print_status "WhatsApp webhook: http://localhost:5000"
print_status "Public URL: $NGROK_URL"
print_status "Meta webhook URL: $NGROK_URL/webhook"
echo ""
print_info "Your WhatsApp integration is ready!"
echo ""

print_step "Step 7: Real-time Monitoring"
echo ""
print_info "📱 Send a test message to your WhatsApp Business number"
print_info "   Type 'menu' to test the ordering system"
echo ""
print_info "🔍 Monitoring logs... (Press Ctrl+C to stop)"
echo ""

# Monitor
while true; do
    if check_webhook; then
        echo -n "."
        sleep 5
    else
        print_error "Webhook stopped!"
        break
    fi
done

