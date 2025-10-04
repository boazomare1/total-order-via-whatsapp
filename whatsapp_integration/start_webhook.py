#!/usr/bin/env python3
"""
Simple startup script for WhatsApp Webhook
"""

import subprocess
import sys
import os

def start_webhook():
    """Start the WhatsApp webhook server"""
    print("🎯 WhatsApp Integration - Webhook Only")
    print("=====================================")
    print("📱 WhatsApp Webhook: http://localhost:5000")
    print("🔍 Health check: http://localhost:5000/health")
    print("=====================================")
    print("Press Ctrl+C to stop the webhook")
    print()
    
    try:
        # Start the webhook
        print("🚀 Starting WhatsApp webhook server...")
        subprocess.run([
            sys.executable, 
            "/home/boaz/test-bench/apps/whatsapp_integration/whatsapp_integration/standalone_webhook.py"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Webhook failed to start: {e}")
    except KeyboardInterrupt:
        print("🛑 Webhook stopped")

if __name__ == "__main__":
    start_webhook()




