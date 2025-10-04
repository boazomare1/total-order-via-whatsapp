"""
Simple webhook verification endpoint that returns plain text
This bypasses Frappe's API system to return exactly what Meta expects
"""
import frappe
import json

def get_context(context):
    # This is a simple GET request handler
    if frappe.request.method == "GET":
        # Get verification parameters
        mode = frappe.form_dict.get("hub.mode")
        verify_token = frappe.form_dict.get("hub.verify_token")
        challenge = frappe.form_dict.get("hub.challenge")
        
        # Get the configured verify token
        VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
        
        # Log the verification attempt
        frappe.logger().info(f"Webhook verification: mode={mode}, verify_token={verify_token}, challenge={challenge}")
        
        # Check if this is a verification request
        if mode and verify_token:
            if mode == "subscribe" and verify_token == VERIFY_TOKEN:
                # Meta expects just the plain challenge string
                context.response = challenge
                context.http_status_code = 200
                context.headers = {"Content-Type": "text/plain"}
                return
            else:
                context.response = "Verification token mismatch"
                context.http_status_code = 403
                context.headers = {"Content-Type": "text/plain"}
                return
        
        # Default response
        context.response = "Hello world"
        context.http_status_code = 200
        context.headers = {"Content-Type": "text/plain"}
        return
    
    # POST requests - handle WhatsApp messages
    try:
        data = frappe.request.get_json()
        frappe.logger().info(f"Incoming WhatsApp webhook: {json.dumps(data, indent=2)}")
        
        # Parse WhatsApp webhook format
        if "entry" in data:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    for message in messages:
                        process_incoming_message(message)
                        
    except Exception as e:
        frappe.logger().error(f"Error processing WhatsApp webhook: {str(e)}")
    
    # Return plain text response
    context.response = "OK"
    context.http_status_code = 200
    context.headers = {"Content-Type": "text/plain"}
    return

def process_incoming_message(message):
    """Process incoming WhatsApp message and create order"""
    try:
        from_phone = message.get("from")
        message_text = message.get("text", {}).get("body", "")
        message_id = message.get("id")
        
        frappe.logger().info(f"Processing message from {from_phone}: {message_text}")
        
        # Check if message contains order information
        if "order" in message_text.lower() or "buy" in message_text.lower():
            frappe.logger().info(f"Creating order for message: {message_text}")
            create_order_from_message(from_phone, message_text, message_id)
        else:
            # Send menu or help message
            frappe.logger().info(f"Sending menu to {from_phone}")
            send_menu_message(from_phone)
            
    except Exception as e:
        frappe.logger().error(f"Error processing message: {str(e)}")

def create_order_from_message(from_phone, message_text, message_id):
    """Create order from WhatsApp message"""
    try:
        # Create WhatsApp Order
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_name = f"Customer {from_phone}"
        order_doc.phone_number = from_phone
        order_doc.item = "Parsed from message"
        order_doc.quantity = 1
        order_doc.unit_price = 10.0
        order_doc.total_price = 10.0
        order_doc.order_status = "Pending"
        order_doc.delivery_address = "To be confirmed"
        order_doc.created_at = frappe.utils.now()
        order_doc.updated_at = frappe.utils.now()
        
        order_doc.save(ignore_permissions=True)
        
        # Send confirmation message
        send_order_confirmation(from_phone, order_doc.name, 10.0)
        
    except Exception as e:
        frappe.logger().error(f"Error creating order: {str(e)}")

def send_menu_message(to_phone):
    """Send menu to customer"""
    try:
        menu_text = """
🍕 Welcome to our WhatsApp Ordering System!

Here's our menu:
• Pizza Margherita - $15
• Pizza Pepperoni - $18
• Burger - $12
• Fries - $6

To order, just send:
"Order 2 Pizza Margherita, 1 Burger"

Or reply with your order details!
        """
        
        frappe.logger().info(f"Sending menu to {to_phone}")
        send_whatsapp_message(to_phone, menu_text)
        
    except Exception as e:
        frappe.logger().error(f"Error sending menu: {str(e)}")

def send_order_confirmation(to_phone, order_id, total_amount):
    """Send order confirmation"""
    try:
        confirmation_text = f"""
✅ Order Confirmed!

Order ID: {order_id}
Total Amount: ${total_amount}

Thank you for your order! We'll prepare it right away.
        """
        
        frappe.logger().info(f"Sending order confirmation to {to_phone}")
        send_whatsapp_message(to_phone, confirmation_text)
        
    except Exception as e:
        frappe.logger().error(f"Error sending confirmation: {str(e)}")

def send_whatsapp_message(to_phone, message_text):
    """Send WhatsApp message via Meta API"""
    try:
        phone_id = frappe.conf.get("whatsapp_phone_id")
        access_token = frappe.conf.get("whatsapp_token")
        
        frappe.logger().info(f"Sending WhatsApp message to {to_phone}")
        
        if not phone_id or not access_token:
            frappe.logger().error("WhatsApp credentials not configured")
            return
        
        url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message_text}
        }
        
        import requests
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            frappe.logger().info(f"Message sent successfully to {to_phone}")
        else:
            frappe.logger().error(f"Failed to send message: {response.text}")
            
    except Exception as e:
        frappe.logger().error(f"Error sending WhatsApp message: {str(e)}")