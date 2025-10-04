"""
Test webhook to verify it's working
"""
import frappe

def get_context(context):
    # Get request parameters
    mode = frappe.form_dict.get("hub.mode")
    verify_token = frappe.form_dict.get("hub.verify_token") 
    challenge = frappe.form_dict.get("hub.challenge")
    
    # Get configured verify token
    VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
    
    # Simple test - always return the challenge
    frappe.logger().info(f"TEST WEBHOOK: mode={mode}, verify_token={verify_token}, challenge={challenge}")
    frappe.logger().info(f"TEST WEBHOOK: Configured token: {VERIFY_TOKEN}")
    
    if challenge:
        context.response = f"CHALLENGE:{challenge}"
        context.http_status_code = 200
        context.headers = {"Content-Type": "text/plain"}
    else:
        context.response = "NO_CHALLENGE"
        context.http_status_code = 200
        context.headers = {"Content-Type": "text/plain"}
    
    return context