#!/usr/bin/env python3
"""
Simple test script to verify WhatsApp webhook is working
Run this after setting up ngrok to test the webhook endpoint
"""

import requests
import json

# Replace with your ngrok URL
WEBHOOK_URL = "http://localhost:8000/api/method/whatsapp_integration.api.whatsapp_webhook"

def test_webhook_verification():
    """Test webhook verification (GET request)"""
    print("Testing webhook verification...")
    
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "frappe_verify_token",
        "hub.challenge": "test_challenge_123"
    }
    
    response = requests.get(WEBHOOK_URL, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200 and response.text == "test_challenge_123":
        print("✅ Webhook verification working!")
    else:
        print("❌ Webhook verification failed!")

def test_webhook_message():
    """Test webhook with sample WhatsApp message"""
    print("\nTesting webhook with sample message...")
    
    sample_message = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "1234567890",
                                "phone_number_id": "123456789"
                            },
                            "messages": [
                                {
                                    "from": "254712345678",
                                    "id": "wamid.123456789",
                                    "timestamp": "1234567890",
                                    "text": {
                                        "body": "order"
                                    },
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(WEBHOOK_URL, json=sample_message, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Webhook message processing working!")
    else:
        print("❌ Webhook message processing failed!")

if __name__ == "__main__":
    print("WhatsApp Webhook Test")
    print("=" * 30)
    
    # Test verification first
    test_webhook_verification()
    
    # Test message processing
    test_webhook_message()
    
    print("\n" + "=" * 30)
    print("Test completed!")
    print("\nTo test with real WhatsApp messages:")
    print("1. Start your ERPNext site: bench start")
    print("2. Run ngrok: ngrok http 8000")
    print("3. Update WEBHOOK_URL in this script with your ngrok URL")
    print("4. Configure Meta webhook with the ngrok URL")
    print("5. Send 'order' message from WhatsApp to your test number")