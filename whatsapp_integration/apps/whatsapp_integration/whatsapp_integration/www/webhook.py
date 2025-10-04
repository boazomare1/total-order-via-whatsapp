#!/usr/bin/env python3
"""
WhatsApp Webhook Handler
"""

import frappe

def get_context(context):
    """Handle webhook verification"""
    if frappe.request.method == "GET":
        # Get verification parameters
        VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
        mode = frappe.request.args.get("hub.mode")
        verify_token = frappe.request.args.get("hub.verify_token")
        challenge = frappe.request.args.get("hub.challenge")
        
        frappe.logger().info(f"Webhook verification: mode={mode}, verify_token={verify_token}, challenge={challenge}")
        
        if mode and verify_token:
            if mode == "subscribe" and verify_token == VERIFY_TOKEN:
                # Return the challenge as the page content
                context.challenge = challenge
                return context
            else:
                context.error = "Verification token mismatch"
                return context
        
        # Default response
        context.message = "Hello world"
        return context
    
    # POST requests
    context.status = "OK"
    return context