"""
Ultra-simple webhook that returns exactly what Meta expects
"""
import frappe
import json

def get_context(context):
    # Get the request parameters
    mode = frappe.form_dict.get("hub.mode")
    verify_token = frappe.form_dict.get("hub.verify_token")
    challenge = frappe.form_dict.get("hub.challenge")
    
    # Get the configured verify token
    VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
    
    # Log everything for debugging
    frappe.logger().info(f"Webhook verification: mode={mode}, verify_token={verify_token}, challenge={challenge}")
    frappe.logger().info(f"Configured token: {VERIFY_TOKEN}")
    
    # Check if this is a verification request
    if mode and verify_token:
        if mode == "subscribe" and verify_token == VERIFY_TOKEN:
            # Meta expects JUST the challenge string, nothing else
            frappe.logger().info(f"Verification successful, returning challenge: {challenge}")
            context.response = challenge
            return
        else:
            frappe.logger().error(f"Verification failed: mode={mode}, token_match={verify_token == VERIFY_TOKEN}")
            context.response = "Verification failed"
            return
    
    # Default response
    context.response = "Hello"
    return