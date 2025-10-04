"""
Ultra-simple webhook that returns plain text for Meta verification
"""
import frappe

def get_context(context):
    # Get request parameters
    mode = frappe.form_dict.get("hub.mode")
    verify_token = frappe.form_dict.get("hub.verify_token") 
    challenge = frappe.form_dict.get("hub.challenge")
    
    # Get configured verify token
    VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
    
    # Log for debugging
    frappe.logger().info(f"Plain webhook: mode={mode}, verify_token={verify_token}, challenge={challenge}")
    frappe.logger().info(f"Configured token: {VERIFY_TOKEN}")
    
    # Check verification
    if mode and verify_token and challenge:
        if mode == "subscribe" and verify_token == VERIFY_TOKEN:
            # Return plain text challenge - Meta expects this exact format
            frappe.logger().info(f"Verification successful, returning: {challenge}")
            context.response = challenge
            context.http_status_code = 200
            context.headers = {"Content-Type": "text/plain"}
            return
        else:
            frappe.logger().error(f"Verification failed: mode={mode}, token_match={verify_token == VERIFY_TOKEN}")
            context.response = "Verification failed"
            context.http_status_code = 403
            context.headers = {"Content-Type": "text/plain"}
            return
    
    # Default response
    context.response = "Hello Meta"
    context.http_status_code = 200
    context.headers = {"Content-Type": "text/plain"}