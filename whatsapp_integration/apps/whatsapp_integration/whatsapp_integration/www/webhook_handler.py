#!/usr/bin/env python3
"""
Direct webhook handler for WhatsApp verification
This bypasses Frappe's JSON wrapping for whitelisted methods
"""

import frappe
from werkzeug.wrappers import Response

def handle_webhook():
    """Handle WhatsApp webhook verification"""
    if frappe.request.method == "GET":
        # Verification handshake
        VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
        mode = frappe.request.args.get("hub.mode")
        verify_token = frappe.request.args.get("hub.verify_token")
        challenge = frappe.request.args.get("hub.challenge")
        
        if mode and verify_token:
            if mode == "subscribe" and verify_token == VERIFY_TOKEN:
                # Return plain text response
                response = Response(challenge, mimetype="text/plain")
                response.status_code = 200
                return response
            else:
                response = Response("Verification token mismatch", mimetype="text/plain")
                response.status_code = 403
                return response
        
        response = Response("Hello world", mimetype="text/plain")
        response.status_code = 200
        return response
    
    # POST - handle incoming messages
    response = Response("OK", mimetype="text/plain")
    response.status_code = 200
    return response