"""
WhatsApp Integration API
Handles incoming WhatsApp messages and creates orders in ERPNext
"""

import frappe
import requests
import json
import re
from datetime import datetime

# User state management for conversation flow
user_states = {}

@frappe.whitelist(allow_guest=True)
def whatsapp_webhook():
    """
    Webhook endpoint for receiving WhatsApp messages from Meta
    GET: Verification handshake
    POST: Process incoming messages
    """
    if frappe.request.method == "GET":
        # Get verification parameters
        mode = frappe.form_dict.get("hub.mode")
        verify_token = frappe.form_dict.get("hub.verify_token")
        challenge = frappe.form_dict.get("hub.challenge")
        
        # Get configured verify token
        VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
        
        # Debug logging
        frappe.logger().info(f"Webhook verification request:")
        frappe.logger().info(f"  mode: {mode}")
        frappe.logger().info(f"  verify_token: {verify_token}")
        frappe.logger().info(f"  challenge: {challenge}")
        frappe.logger().info(f"  configured_token: {VERIFY_TOKEN}")
        
        # Check if this is a verification request
        if mode == "subscribe" and verify_token == VERIFY_TOKEN:
            frappe.logger().info(f"✅ Verification successful! Returning challenge: {challenge}")
            # Return the challenge string directly as plain text
            frappe.local.response = frappe._dict()
            frappe.local.response["http_status_code"] = 200
            frappe.local.response["headers"] = {"Content-Type": "text/plain"}
            frappe.local.response["type"] = "download"
            frappe.local.response["filename"] = "challenge.txt"
            frappe.local.response["filecontent"] = challenge
            return challenge
        else:
            frappe.logger().error(f"❌ Verification failed:")
            frappe.logger().error(f"  mode check: {mode == 'subscribe'}")
            frappe.logger().error(f"  token check: {verify_token == VERIFY_TOKEN}")
            frappe.local.response = frappe._dict()
            frappe.local.response["http_status_code"] = 403
            frappe.local.response["headers"] = {"Content-Type": "text/plain"}
            frappe.local.response["type"] = "download"
            frappe.local.response["filename"] = "error.txt"
            frappe.local.response["filecontent"] = "Verification token mismatch"
            return "Verification token mismatch"
    
    # Default response for other requests
    return "OK"

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


def process_incoming_message(message):
    """Process incoming WhatsApp message with intelligent bot responses"""
    try:
        from_phone = message.get("from")
        message_text = message.get("text", {}).get("body", "")
        message_id = message.get("id")
        
        frappe.logger().info(f"Processing message from {from_phone}: {message_text}")
        
        # Get user state
        user_state = user_states.get(from_phone, {"state": "idle", "data": {}})
        message_lower = message_text.lower().strip()
        
        # Debug logging
        frappe.logger().info(f"User state: {user_state['state']}, Data: {user_state['data']}")
        
        # Handle different user states
        if user_state["state"] == "selecting_item":
            handle_item_selection(from_phone, message_text, user_state)
        elif user_state["state"] == "selecting_variant":
            handle_variant_selection(from_phone, message_text, user_state)
        elif user_state["state"] == "entering_quantity":
            handle_quantity_input(from_phone, message_text, user_state)
        elif user_state["state"] == "entering_address":
            handle_address_input(from_phone, message_text, user_state)
        else:
            # Handle commands in idle state
            handle_main_commands(from_phone, message_text, user_state)
            
    except Exception as e:
        frappe.logger().error(f"Error processing message: {str(e)}")
        send_whatsapp_message(from_phone, "Sorry, something went wrong. Please try again.")


def handle_main_commands(from_phone, message_text, user_state):
    """Handle main commands in idle state"""
    message_lower = message_text.lower().strip()
    
    # Check for specific phrases first
    if any(phrase in message_lower for phrase in ["my orders", "my order", "order history"]):
        show_customer_orders(from_phone)
    elif any(phrase in message_lower for phrase in ["reorder", "repeat order"]):
        handle_reorder(from_phone, message_text)
    elif "status" in message_lower:
        handle_status_check(from_phone, message_text)
    elif any(word in message_lower for word in ["menu", "food", "order", "buy", "hi", "hello", "start"]):
        # Check if this is a direct order request
        if any(word in message_lower for word in ["order", "buy", "want", "need", "get", "take"]) and any(word in message_lower for word in ["pizza", "burger", "fries", "juice", "food"]):
            # This looks like a direct order - create it immediately
            create_order_from_message(from_phone, message_text, "direct_order")
        else:
            show_main_menu(from_phone)
    elif any(word in message_lower for word in ["orders", "history"]):
        show_customer_orders(from_phone)
    else:
        # Check if this is a direct order request even without keywords
        if any(word in message_lower for word in ["pizza", "burger", "fries", "juice", "food", "2", "3", "4", "5"]):
            # This looks like a direct order - create it immediately
            create_order_from_message(from_phone, message_text, "direct_order")
        else:
            show_main_menu(from_phone)


def show_main_menu(from_phone):
    """Show the main menu with categories"""
    menu_text = """
🍕 *Welcome to Our Restaurant!*

*Main Menu:*

*🍕 PIZZAS*
• 1. Margherita - KES 800
• 2. Pepperoni - KES 950
• 3. Hawaiian - KES 900
• 4. BBQ Chicken - KES 1000

*🍔 BURGERS*
• 5. Classic Beef - KES 650
• 6. Chicken Burger - KES 600
• 7. Veggie Burger - KES 550

*🍟 SIDES*
• 8. French Fries - KES 300
• 9. Chicken Wings - KES 700
• 10. Onion Rings - KES 350

*🥤 DRINKS*
• 11. Soda (Coke/Pepsi) - KES 150
• 12. Juice - KES 200
• 13. Water - KES 100

*Commands:*
• Type *1-13* to select an item
• Type *"My Orders"* to view your orders
• Type *"Status [Order ID]"* to check order status
• Type *"Reorder [Order ID]"* to reorder

*Payment:* Pay on delivery to *0742356449*
    """
    
    send_whatsapp_message(from_phone, menu_text)
    
    # Set user state to selecting item
    user_states[from_phone] = {"state": "selecting_item", "data": {}}


def handle_item_selection(from_phone, message_text, user_state):
    """Handle item selection"""
    message_lower = message_text.lower().strip()
    
    # Menu items with variants
    menu_items = {
        "1": {"name": "Margherita Pizza", "price": 800, "variants": ["Small", "Medium", "Large"]},
        "2": {"name": "Pepperoni Pizza", "price": 950, "variants": ["Small", "Medium", "Large"]},
        "3": {"name": "Hawaiian Pizza", "price": 900, "variants": ["Small", "Medium", "Large"]},
        "4": {"name": "BBQ Chicken Pizza", "price": 1000, "variants": ["Small", "Medium", "Large"]},
        "5": {"name": "Classic Beef Burger", "price": 650, "variants": ["Single", "Double"]},
        "6": {"name": "Chicken Burger", "price": 600, "variants": ["Regular", "Spicy"]},
        "7": {"name": "Veggie Burger", "price": 550, "variants": ["Regular", "Deluxe"]},
        "8": {"name": "French Fries", "price": 300, "variants": ["Small", "Large"]},
        "9": {"name": "Chicken Wings", "price": 700, "variants": ["6 pieces", "12 pieces"]},
        "10": {"name": "Onion Rings", "price": 350, "variants": ["Small", "Large"]},
        "11": {"name": "Soda", "price": 150, "variants": ["Coke", "Pepsi", "Fanta"]},
        "12": {"name": "Juice", "price": 200, "variants": ["Orange", "Apple", "Mango"]},
        "13": {"name": "Water", "price": 100, "variants": ["500ml", "1L"]}
    }
    
    if message_text in menu_items:
        item = menu_items[message_text]
        
        if len(item["variants"]) > 1:
            # Show variants
            variants_text = f"*{item['name']}* - KES {item['price']}\n\n*Select Variant:*\n"
            for i, variant in enumerate(item["variants"], 1):
                variants_text += f"• {i}. {variant}\n"
            variants_text += "\nType the variant number (1, 2, etc.)"
            
            send_whatsapp_message(from_phone, variants_text)
            
            # Store item info and wait for variant selection
            user_state["data"]["selected_item"] = item
            user_state["state"] = "selecting_variant"
            user_states[from_phone] = user_state
            frappe.logger().info(f"State changed to selecting_variant for {from_phone}")
        else:
            # No variants, proceed to quantity
            user_state["data"]["selected_item"] = item
            user_state["data"]["selected_variant"] = item["variants"][0]
            user_state["state"] = "entering_quantity"
            user_states[from_phone] = user_state
            
            send_whatsapp_message(from_phone, f"*{item['name']}* selected!\n\nHow many would you like? (Type a number)")
    
    else:
        send_whatsapp_message(from_phone, "Please select a valid item number (1-13) or type 'menu' to see the menu again.")


def handle_variant_selection(from_phone, message_text, user_state):
    """Handle variant selection"""
    try:
        frappe.logger().info(f"Handling variant selection: {message_text}")
        variant_num = int(message_text)
        selected_item = user_state["data"]["selected_item"]
        frappe.logger().info(f"Selected item: {selected_item}, Variant num: {variant_num}")
        
        if 1 <= variant_num <= len(selected_item["variants"]):
            selected_variant = selected_item["variants"][variant_num - 1]
            user_state["data"]["selected_variant"] = selected_variant
            user_state["state"] = "entering_quantity"
            user_states[from_phone] = user_state
            
            send_whatsapp_message(from_phone, f"*{selected_item['name']} - {selected_variant}* selected!\n\nHow many would you like? (Type a number)")
        else:
            send_whatsapp_message(from_phone, f"Please select a valid variant number (1-{len(selected_item['variants'])})")
    except ValueError:
        send_whatsapp_message(from_phone, "Please type a valid number for the variant.")


def handle_quantity_input(from_phone, message_text, user_state):
    """Handle quantity input"""
    try:
        quantity = int(message_text)
        if quantity > 0:
            user_state["data"]["quantity"] = quantity
            user_state["state"] = "entering_address"
            user_states[from_phone] = user_state
            
            # Check if this is a reorder
            if "reorder_item" in user_state["data"]:
                reorder_item = user_state["data"]["reorder_item"]
                reorder_price = user_state["data"]["reorder_price"]
                total_price = reorder_price * quantity
                
                confirm_text = f"""
*Reorder Summary:*
• Item: {reorder_item}
• Quantity: {quantity}
• Unit Price: KES {reorder_price}
• Total: KES {total_price}

*Please provide your delivery address:*
(Include area, street name, and any landmarks)
                """
            else:
                selected_item = user_state["data"]["selected_item"]
                selected_variant = user_state["data"]["selected_variant"]
                total_price = selected_item["price"] * quantity
                
                confirm_text = f"""
*Order Summary:*
• Item: {selected_item['name']} - {selected_variant}
• Quantity: {quantity}
• Unit Price: KES {selected_item['price']}
• Total: KES {total_price}

*Please provide your delivery address:*
(Include area, street name, and any landmarks)
                """
            
            send_whatsapp_message(from_phone, confirm_text)
        else:
            send_whatsapp_message(from_phone, "Please enter a valid quantity (1 or more)")
    except ValueError:
        send_whatsapp_message(from_phone, "Please type a valid number for quantity.")


def handle_address_input(from_phone, message_text, user_state):
    """Handle delivery address input"""
    if len(message_text.strip()) < 10:
        send_whatsapp_message(from_phone, "Please provide a complete delivery address with area and street details.")
        return
    
    user_state["data"]["delivery_address"] = message_text.strip()
    
    # Create the order
    create_complete_order(from_phone, user_state)
    
    # Reset user state
    user_states[from_phone] = {"state": "idle", "data": {}}


def create_complete_order(from_phone, user_state):
    """Create a complete order from user state"""
    try:
        frappe.set_user("Administrator")
        
        quantity = user_state["data"]["quantity"]
        delivery_address = user_state["data"]["delivery_address"]
        
        # Create WhatsApp Order
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_name = "WhatsApp Customer"
        order_doc.phone_number = from_phone
        order_doc.quantity = quantity
        order_doc.delivery_address = delivery_address
        order_doc.order_status = "Pending"
        
        # Check if this is a reorder
        if "reorder_item" in user_state["data"]:
            reorder_item = user_state["data"]["reorder_item"]
            reorder_price = user_state["data"]["reorder_price"]
            
            order_doc.item = reorder_item
            order_doc.unit_price = reorder_price
            order_doc.total_price = reorder_price * quantity
        else:
            selected_item = user_state["data"]["selected_item"]
            selected_variant = user_state["data"]["selected_variant"]
            
            order_doc.item = f"{selected_item['name']} - {selected_variant}"
            order_doc.unit_price = selected_item["price"]
            order_doc.total_price = selected_item["price"] * quantity
        
        order_doc.save()
        
        # Send confirmation
        if "reorder_item" in user_state["data"]:
            order_type = "Reorder"
            item_display = order_doc.item
        else:
            order_type = "Order"
            item_display = order_doc.item
        
        confirmation_text = f"""
✅ *{order_type} Confirmed!*

*Order Details:*
• Order ID: {order_doc.name}
• Item: {item_display}
• Quantity: {quantity}
• Total: KES {order_doc.total_price}
• Delivery Address: {delivery_address}

*Payment Instructions:*
Pay KES {order_doc.total_price} on delivery to:
📱 *0742356449*

*Order Status:* Pending
We'll notify you when your order is being prepared!

*Commands:*
• Type *"My Orders"* to view all orders
• Type *"Status {order_doc.name}"* to check this order
        """
        
        send_whatsapp_message(from_phone, confirmation_text)
        
    except Exception as e:
        frappe.logger().error(f"Error creating complete order: {str(e)}")
        send_whatsapp_message(from_phone, "Sorry, there was an error creating your order. Please try again.")


def show_customer_orders(from_phone):
    """Show customer's order history"""
    try:
        orders = frappe.get_all("WhatsApp Order", 
                               filters={"phone_number": from_phone}, 
                               fields=["name", "item", "quantity", "total_price", "order_status", "created_at"],
                               order_by="creation desc",
                               limit=5)
        
        if not orders:
            send_whatsapp_message(from_phone, "You haven't placed any orders yet. Type 'menu' to start ordering!")
            return
        
        orders_text = "*Your Recent Orders:*\n\n"
        for order in orders:
            orders_text += f"• *{order.name}* - {order.item}\n"
            orders_text += f"  Qty: {order.quantity} | Total: KES {order.total_price}\n"
            orders_text += f"  Status: {order.order_status}\n"
            orders_text += f"  Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        orders_text += "*Commands:*\n"
        orders_text += "• Type *'Status [Order ID]'* to check specific order\n"
        orders_text += "• Type *'Reorder [Order ID]'* to reorder\n"
        orders_text += "• Type *'menu'* to place new order"
        
        send_whatsapp_message(from_phone, orders_text)
        
    except Exception as e:
        frappe.logger().error(f"Error getting customer orders: {str(e)}")
        send_whatsapp_message(from_phone, "Sorry, couldn't retrieve your orders. Please try again.")


def handle_status_check(from_phone, message_text):
    """Handle order status check"""
    try:
        # Extract order ID from message
        words = message_text.split()
        order_id = None
        
        for i, word in enumerate(words):
            if word.lower() == "status" and i + 1 < len(words):
                order_id = words[i + 1]
                break
        
        if not order_id:
            send_whatsapp_message(from_phone, "Please provide an order ID. Example: 'Status WOR-2025-00001'")
            return
        
        # Get order details
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        if order.phone_number != from_phone:
            send_whatsapp_message(from_phone, "This order doesn't belong to you.")
            return
        
        status_text = f"""
*Order Status: {order_id}*

• Item: {order.item}
• Quantity: {order.quantity}
• Total: KES {order.total_price}
• Status: {order.order_status}
• Order Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}
• Delivery Address: {order.delivery_address}

*Payment:* Pay on delivery to *0742356449*
        """
        
        send_whatsapp_message(from_phone, status_text)
        
    except Exception as e:
        frappe.logger().error(f"Error checking order status: {str(e)}")
        send_whatsapp_message(from_phone, "Order not found. Please check the order ID and try again.")


def handle_reorder(from_phone, message_text):
    """Handle reorder request"""
    try:
        # Extract order ID from message
        words = message_text.split()
        order_id = None
        
        for i, word in enumerate(words):
            if word.lower() in ["reorder", "repeat"] and i + 1 < len(words):
                order_id = words[i + 1]
                break
        
        if not order_id:
            send_whatsapp_message(from_phone, "Please provide an order ID. Example: 'Reorder WOR-2025-00001'")
            return
        
        # Get order details
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        if order.phone_number != from_phone:
            send_whatsapp_message(from_phone, "This order doesn't belong to you.")
            return
        
        # Start reorder process
        user_state = user_states.get(from_phone, {"state": "idle", "data": {}})
        user_state["data"]["reorder_item"] = order.item
        user_state["data"]["reorder_price"] = order.unit_price
        user_state["state"] = "entering_quantity"
        user_states[from_phone] = user_state
        
        reorder_text = f"""
*Reordering: {order.item}*

Previous quantity: {order.quantity}
Previous total: KES {order.total_price}

How many would you like this time? (Type a number)
        """
        
        send_whatsapp_message(from_phone, reorder_text)
        
    except Exception as e:
        frappe.logger().error(f"Error handling reorder: {str(e)}")
        send_whatsapp_message(from_phone, "Order not found. Please check the order ID and try again.")


@frappe.whitelist(allow_guest=True)
def send_order_status_update(order_id, new_status):
    """Manually send status update notification for an order"""
    try:
        frappe.set_user("Administrator")
        
        # Get the order
        order = frappe.get_doc("WhatsApp Order", order_id)
        old_status = order.order_status
        
        # Update the status
        order.order_status = new_status
        order.save()
        
        return {"status": "success", "message": f"Order {order_id} status updated to {new_status}"}
        
    except Exception as e:
        frappe.logger().error(f"Error updating order status: {str(e)}")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def test_whatsapp_notification():
    """Test sending a WhatsApp notification directly"""
    try:
        import requests
        
        # Get WhatsApp credentials
        phone_id = frappe.conf.get("whatsapp_phone_id")
        access_token = frappe.conf.get("whatsapp_token")
        
        if not phone_id or not access_token:
            return {"status": "error", "message": "WhatsApp credentials not configured"}
        
        # Status update message
        test_message = """
*Order Status Update*

Order ID: WOR-2025-00021
Item: Juice - Apple
Quantity: 5
Total: KES 1000

Status: Out for Delivery → Delivered

🎉 Your order has been delivered! Enjoy your meal!

*Payment:* Pay on delivery to *0742356449*
        """
        
        # Send to your phone number
        phone_number = "254770534365"
        
        url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {"body": test_message}
        }
        
        frappe.logger().info(f"Sending test notification to {phone_number}")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            frappe.logger().info(f"Test notification sent successfully: {response.text}")
            return {"status": "success", "message": "Test notification sent successfully", "response": response.text}
        else:
            frappe.logger().error(f"Failed to send test notification: {response.status_code} - {response.text}")
            return {"status": "error", "message": f"Failed to send notification: {response.text}"}
            
    except Exception as e:
        frappe.logger().error(f"Error sending test notification: {str(e)}")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def send_status_notification_manual(order_id, old_status, new_status):
    """Manually send status notification for an order"""
    try:
        import requests
        
        # Get the order
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        # Get WhatsApp credentials
        phone_id = frappe.conf.get("whatsapp_phone_id")
        access_token = frappe.conf.get("whatsapp_token")
        
        if not phone_id or not access_token:
            return {"status": "error", "message": "WhatsApp credentials not configured"}
        
        # Status messages
        status_messages = {
            "Confirmed": "✅ Your order has been confirmed and is being prepared!",
            "Preparing": "👨‍🍳 Your order is being prepared! It will be ready soon.",
            "Out for Delivery": "🚚 Your order is out for delivery! Our driver is on the way.",
            "Delivered": "🎉 Your order has been delivered! Enjoy your meal!",
            "Cancelled": "❌ Your order has been cancelled. Please contact us if you have any questions."
        }
        
        # Get message for new status
        message = status_messages.get(new_status, f"Your order status has been updated to: {new_status}")
        
        # Create notification message
        notification_text = f"""
*Order Status Update*

Order ID: {order.name}
Item: {order.item}
Quantity: {order.quantity}
Total: KES {order.total_price}

Status: {old_status} → {new_status}

{message}

*Payment:* Pay on delivery to *0742356449*
        """
        
        # Send WhatsApp message
        url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": order.phone_number,
            "type": "text",
            "text": {"body": notification_text}
        }
        
        frappe.logger().info(f"Sending status notification to {order.phone_number}")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            frappe.logger().info(f"Status notification sent successfully: {response.text}")
            return {"status": "success", "message": "Status notification sent successfully", "response": response.text}
        else:
            frappe.logger().error(f"Failed to send status notification: {response.status_code} - {response.text}")
            return {"status": "error", "message": f"Failed to send notification: {response.text}"}
            
    except Exception as e:
        frappe.logger().error(f"Error sending status notification: {str(e)}")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def admin_update_order_status(order_id, new_status):
    """Admin API to update order status and send WhatsApp notification"""
    try:
        frappe.set_user("Administrator")
        
        # Get the order
        order = frappe.get_doc("WhatsApp Order", order_id)
        old_status = order.order_status
        
        # Update the status directly in database to avoid UI issues
        frappe.db.set_value("WhatsApp Order", order_id, "order_status", new_status)
        frappe.db.commit()
        
        # Send WhatsApp notification
        result = send_status_notification_manual(order_id, old_status, new_status)
        
        return {
            "status": "success", 
            "message": f"Order {order_id} status updated from {old_status} to {new_status}",
            "order_details": {
                "order_id": order_id,
                "old_status": old_status,
                "new_status": new_status,
                "customer_phone": order.phone_number,
                "item": order.item,
                "quantity": order.quantity,
                "total_price": order.total_price
            },
            "whatsapp_result": result
        }
        
    except Exception as e:
        frappe.logger().error(f"Error updating order status: {str(e)}")
        return {"status": "error", "message": str(e)}


def create_order_from_message(from_phone, message_text, message_id):
    """Create order from WhatsApp message"""
    try:
        # Switch to Administrator user to bypass permission issues
        frappe.set_user("Administrator")
        
        # Create WhatsApp Order
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_name = "WhatsApp Customer"  # Default name since we only have phone
        order_doc.phone_number = from_phone
        order_doc.order_status = "Pending"
        order_doc.created_at = frappe.utils.now()
        order_doc.updated_at = frappe.utils.now()
        order_doc.delivery_address = "Address to be provided"  # Default address
        
        # Try to extract order details
        message_lower = message_text.lower().strip()
        
        # Menu prices
        menu_prices = {
            "pizza margherita": 15.0,
            "margherita": 15.0,
            "pizza pepperoni": 18.0,
            "pepperoni": 18.0,
            "burger": 12.0,
            "fries": 6.0
        }
        
        # Parse the message to find item and quantity
        item_name = None
        quantity = 1
        unit_price = 10.0
        
        # Check for specific items in the message
        for item, price in menu_prices.items():
            if item in message_lower:
                item_name = item
                unit_price = price
                break
        
        # If no specific item found, use the whole message as item name
        if not item_name:
            # Remove order keywords and use the rest as item name
            order_keywords = ["order", "buy", "want", "need", "get", "take"]
            for keyword in order_keywords:
                if keyword in message_lower:
                    item_name = message_lower.replace(keyword, "").strip()
                    break
            if not item_name:
                item_name = message_text.strip()
        
        # Set the order fields
        order_doc.item = item_name
        order_doc.quantity = quantity
        order_doc.unit_price = unit_price
        order_doc.total_price = quantity * unit_price
        order_doc.save()
        
        # Send confirmation message
        send_order_confirmation(from_phone, order_doc.name, order_doc.total_price)
        
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
        
        send_whatsapp_message(to_phone, confirmation_text)
        
    except Exception as e:
        frappe.logger().error(f"Error sending confirmation: {str(e)}")


def send_whatsapp_message(to_phone, message_text):
    """Send WhatsApp message via Meta API"""
    try:
        phone_id = frappe.conf.get("whatsapp_phone_id")
        access_token = frappe.conf.get("whatsapp_token")
        
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
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            frappe.logger().info(f"Message sent successfully to {to_phone}")
        else:
            frappe.logger().error(f"Failed to send message: {response.text}")
            
    except Exception as e:
        frappe.logger().error(f"Error sending WhatsApp message: {str(e)}")


# Test function
@frappe.whitelist(allow_guest=True)
def test_order():
    """Test function to create a sample order"""
    try:
        # Switch to Administrator user to bypass permission issues
        frappe.set_user("Administrator")
        
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_name = "Test Customer"
        order_doc.phone_number = "+1234567890"
        order_doc.item = "Pizza Margherita"
        order_doc.quantity = 2
        order_doc.unit_price = 15.0
        order_doc.total_price = 30.0
        order_doc.order_status = "Pending"
        order_doc.delivery_address = "123 Test Street"
        order_doc.created_at = frappe.utils.now()
        order_doc.updated_at = frappe.utils.now()
        
        order_doc.save(ignore_permissions=True)
        
        return {"status": "success", "order_id": order_doc.name}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True, methods=['POST'])
def create_custom_order(customer_name, phone_number, item, quantity, unit_price, delivery_address="Test Address"):
    """Create a custom order via API"""
    try:
        frappe.set_user("Administrator")
        
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_name = customer_name
        order_doc.phone_number = phone_number
        order_doc.item = item
        order_doc.quantity = int(quantity)
        order_doc.unit_price = float(unit_price)
        order_doc.total_price = int(quantity) * float(unit_price)
        order_doc.order_status = "Pending"
        order_doc.delivery_address = delivery_address
        
        order_doc.save(ignore_permissions=True)
        
        return {
            "status": "success", 
            "message": "Order created successfully",
            "order_id": order_doc.name,
            "order_details": {
                "customer_name": customer_name,
                "phone_number": phone_number,
                "item": item,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": order_doc.total_price,
                "status": "Pending"
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
