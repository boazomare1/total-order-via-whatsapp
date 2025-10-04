import frappe
import json
import requests

def get_context(context):
    if frappe.request.method == "GET":
        # Verification handshake
        VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
        mode = frappe.form_dict.get("hub.mode")
        verify_token = frappe.form_dict.get("hub.verify_token")
        challenge = frappe.form_dict.get("hub.challenge")
        
        # Debug logging
        frappe.logger().info(f"Webhook verification: mode={mode}, verify_token={verify_token}, challenge={challenge}")
        frappe.logger().info(f"Configured token: {VERIFY_TOKEN}")
        frappe.logger().info(f"Token match: {verify_token == VERIFY_TOKEN}")
        frappe.logger().info(f"Mode check: {mode == 'subscribe'}")
        
        if mode and verify_token:
            if mode == "subscribe" and verify_token == VERIFY_TOKEN:
                # Meta expects just the plain challenge string
                frappe.logger().info(f"Verification successful, returning challenge: {challenge}")
                context.response = challenge
                context.http_status_code = 200
                context.headers = {"Content-Type": "text/plain"}
                return context
            else:
                frappe.logger().error(f"Verification failed: mode={mode}, token_match={verify_token == VERIFY_TOKEN}")
                context.response = "Verification failed"
                context.http_status_code = 403
                context.headers = {"Content-Type": "text/plain"}
                return context
        
        context.response = "Hello world"
        context.http_status_code = 200
        context.headers = {"Content-Type": "text/plain"}
        return context

    # POST - handle incoming messages
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
        print(f"DEBUG: Processing message from {from_phone}: {message_text}")
        
        # Check if message contains order information
        if "order" in message_text.lower() or "buy" in message_text.lower():
            frappe.logger().info(f"Creating order for message: {message_text}")
            print(f"DEBUG: Creating order for message: {message_text}")
            create_order_from_message(from_phone, message_text, message_id)
        else:
            # Send menu or help message
            frappe.logger().info(f"Sending menu to {from_phone}")
            print(f"DEBUG: Sending menu to {from_phone}")
            send_menu_message(from_phone)
            
    except Exception as e:
        frappe.logger().error(f"Error processing message: {str(e)}")
        print(f"DEBUG ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def create_order_from_message(from_phone, message_text, message_id):
    """Create order from WhatsApp message"""
    try:
        # Create WhatsApp Order
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_phone = from_phone
        order_doc.message_id = message_id
        order_doc.raw_message = message_text
        order_doc.order_status = "Pending"
        order_doc.order_date = frappe.utils.now()
        
        # Try to extract order details
        lines = message_text.split('\n')
        total_amount = 0
        
        for line in lines:
            line = line.strip()
            if line and not line.lower().startswith(('hi', 'hello', 'order', 'buy')):
                # Simple parsing - you can enhance this
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        quantity = int(parts[0])
                        item_name = ' '.join(parts[1:])
                        
                        # Create order item
                        order_item = order_doc.append("order_items", {})
                        order_item.item_name = item_name
                        order_item.quantity = quantity
                        order_item.unit_price = 10.0  # Default price
                        order_item.total_price = quantity * 10.0
                        total_amount += order_item.total_price
                        
                    except ValueError:
                        continue
        
        order_doc.total_amount = total_amount
        order_doc.save()
        
        # Send confirmation message
        send_order_confirmation(from_phone, order_doc.name, total_amount)
        
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
        print(f"DEBUG: Sending menu to {to_phone}")
        send_whatsapp_message(to_phone, menu_text)
        
    except Exception as e:
        frappe.logger().error(f"Error sending menu: {str(e)}")
        print(f"DEBUG ERROR in send_menu_message: {str(e)}")
        import traceback
        traceback.print_exc()


def send_order_confirmation(to_phone, order_id, total_amount):
    """Send order confirmation"""
    try:
        confirmation_text = f"""
✅ Order Confirmed!

Order ID: {order_id}
Total Amount: ${total_amount}

Thank you for your order! We'll prepare it right away.
        """
        
        send_whatsapp_message(to_phone, confirmation_text)
        
    except Exception as e:
        frappe.logger().error(f"Error sending confirmation: {str(e)}")


def send_whatsapp_message(to_phone, message_text):
    """Send WhatsApp message via Meta API"""
    try:
        phone_id = frappe.conf.get("whatsapp_phone_id")
        access_token = frappe.conf.get("whatsapp_token")
        
        frappe.logger().info(f"Sending WhatsApp message to {to_phone}")
        print(f"DEBUG: Sending WhatsApp message to {to_phone}")
        print(f"DEBUG: Phone ID: {phone_id}")
        print(f"DEBUG: Access Token: {access_token[:20]}..." if access_token else "DEBUG: No access token")
        
        if not phone_id or not access_token:
            frappe.logger().error("WhatsApp credentials not configured")
            print("DEBUG ERROR: WhatsApp credentials not configured")
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
        
        print(f"DEBUG: Sending request to {url}")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            frappe.logger().info(f"Message sent successfully to {to_phone}")
            print(f"DEBUG: Message sent successfully to {to_phone}")
        else:
            frappe.logger().error(f"Failed to send message: {response.text}")
            print(f"DEBUG ERROR: Failed to send message: {response.text}")
            
    except Exception as e:
        frappe.logger().error(f"Error sending WhatsApp message: {str(e)}")
        print(f"DEBUG ERROR in send_whatsapp_message: {str(e)}")
        import traceback
        traceback.print_exc()
