#!/usr/bin/env python3
"""
Script to update WhatsApp access token in standalone_webhook.py
"""

import os
import sys

def update_token():
    """Update the WhatsApp access token"""
    print("🔑 WhatsApp Access Token Updater")
    print("=================================")
    print("")
    print("Access tokens expire every 24 hours.")
    print("Get a new token from: https://developers.facebook.com/apps/")
    print("")
    
    # Get new token from user
    new_token = input("Enter your new WhatsApp access token: ").strip()
    
    if not new_token:
        print("❌ No token provided")
        return
    
    # Read the current file
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
        else:
            print("❌ Could not find WHATSAPP_TOKEN in the file")
            
    except Exception as e:
        print(f"❌ Error updating token: {e}")

if __name__ == "__main__":
    update_token()
