#!/usr/bin/env python3
"""
Script to help refresh WhatsApp access token
"""

import os
import webbrowser
import time

def refresh_token():
    """Help user refresh their access token"""
    print("🔑 WhatsApp Access Token Refresh Helper")
    print("=====================================")
    print("")
    print("Access tokens expire every 24 hours.")
    print("This script will help you get a new token quickly.")
    print("")
    
    # Open Meta Developer Console
    print("🌐 Opening Meta Developer Console...")
    webbrowser.open("https://developers.facebook.com/apps/")
    
    print("")
    print("📋 Follow these steps:")
    print("1. Select your WhatsApp Business app")
    print("2. Go to WhatsApp > API Setup")
    print("3. Copy the 'Temporary access token'")
    print("4. Paste it below when ready")
    print("")
    
    # Wait for user to get token
    input("Press Enter when you have copied the new token...")
    
    # Get new token
    new_token = input("Paste your new access token: ").strip()
    
    if not new_token:
        print("❌ No token provided")
        return
    
    # Update the webhook file
    webhook_file = "standalone_webhook.py"
    if not os.path.exists(webhook_file):
        print(f"❌ {webhook_file} not found")
        return
    
    try:
        with open(webhook_file, 'r') as f:
            content = f.read()
        
        # Find and replace the token
        import re
        pattern = r'WHATSAPP_TOKEN = "[^"]*"'
        replacement = f'WHATSAPP_TOKEN = "{new_token}"'
        
        if re.search(pattern, content):
            new_content = re.sub(pattern, replacement, content)
            
            with open(webhook_file, 'w') as f:
                f.write(new_content)
            
            print("✅ Token updated successfully!")
            print("🔄 Restart your webhook to use the new token")
            print("")
            print("💡 Tip: Use './quick_start.sh' to restart everything")
        else:
            print("❌ Could not find WHATSAPP_TOKEN in the file")
            
    except Exception as e:
        print(f"❌ Error updating token: {e}")

if __name__ == "__main__":
    refresh_token()




