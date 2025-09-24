"""
WhatsApp Integration API
Handles incoming WhatsApp messages and creates orders in ERPNext
"""

import frappe
import requests
import json
import re
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def whatsapp_webhook():
    """
    Webhook endpoint for receiving WhatsApp messages from Meta
    GET: Verification handshake
    POST: Process incoming messages
    """
    if frappe.request.method == "GET":
        # Verification handshake
        VERIFY_TOKEN = frappe.conf.get("whatsapp_verify_token", "frappe_verify_token")
        mode = frappe.form_dict.get("hub.mode")
        verify_token = frappe.form_dict.get("hub.verify_token")
        challenge = frappe.form_dict.get("hub.challenge")
        
        if mode and verify_token:
            if mode == "subscribe" and verify_token == VERIFY_TOKEN:
                return challenge, 200
            else:
                return "Verification token mismatch", 403
        return "Hello world", 200

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
    
    return {"status": "received"}


def process_incoming_message(message):
    """Process individual WhatsApp message"""
    from_phone = message.get("from")
    if not from_phone:
        return
    
    # Extract message text
    user_text = ""
    if message.get("type") == "text":
        user_text = message.get("text", {}).get("body", "").strip()
    elif "interactive" in message:
        interactive = message["interactive"]
        button_reply = interactive.get("button", {})
        list_reply = interactive.get("list_reply", {})
        user_text = button_reply.get("text") or list_reply.get("title") or list_reply.get("id") or ""
    
    if not user_text:
        return
    
    frappe.logger().info(f"Message from {from_phone}: {user_text}")
    
    # Get or create session
    session = get_or_create_session(from_phone)
    
    # Handle different commands
    user_text_lower = user_text.lower()
    
    if user_text_lower in ["order", "menu", "start"]:
        start_order_flow(from_phone, session)
    elif user_text_lower in ["cancel", "stop", "quit"]:
        cancel_order(from_phone, session)
    elif session.get("status") == "awaiting_item":
        handle_item_selection(from_phone, session, user_text)
    elif session.get("status") == "awaiting_quantity":
        handle_quantity_selection(from_phone, session, user_text)
    elif session.get("status") == "awaiting_address":
        handle_address_input(from_phone, session, user_text)
    elif session.get("status") == "awaiting_confirmation":
        handle_confirmation(from_phone, session, user_text)
    else:
        send_whatsapp_message(from_phone, "Hi! Type 'order' to start placing an order. Type 'cancel' to stop anytime.")


def get_or_create_session(from_phone):
    """Get existing session or create new one"""
    session_doc = frappe.db.get_value("WhatsApp Session", {"phone_number": from_phone, "status": ["!=", "completed"]}, "name")
    
    if session_doc:
        return frappe.get_doc("WhatsApp Session", session_doc)
    else:
        # Create new session
        session = frappe.get_doc({
            "doctype": "WhatsApp Session",
            "phone_number": from_phone,
            "status": "active",
            "current_step": "awaiting_command"
        })
        session.insert(ignore_permissions=True)
        return session


def start_order_flow(from_phone, session):
    """Start the order process by showing menu"""
    # Reset session
    session.current_step = "awaiting_item"
    session.status = "active"
    session.item_selected = ""
    session.quantity = 0
    session.delivery_address = ""
    session.save(ignore_permissions=True)
    
    # Get available items from ERPNext
    items = get_available_items()
    
    menu_text = "🍕 Welcome! Here's our menu:\n\n"
    for i, item in enumerate(items[:10], 1):  # Limit to 10 items
        menu_text += f"{i}. {item.get('item_name')} - ${item.get('standard_rate', 0)}\n"
    
    menu_text += "\nReply with the number (1-10) or item name to select."
    
    send_whatsapp_message(from_phone, menu_text)


def get_available_items():
    """Get items from ERPNext Item doctype"""
    try:
        items = frappe.db.sql("""
            SELECT name as item_code, item_name, standard_rate, description
            FROM `tabItem` 
            WHERE disabled = 0 AND is_sales_item = 1 
            ORDER BY item_name 
            LIMIT 10
        """, as_dict=True)
        return items
    except Exception as e:
        frappe.logger().error(f"Error fetching items: {str(e)}")
        return []


def handle_item_selection(from_phone, session, user_text):
    """Handle item selection from user"""
    items = get_available_items()
    
    # Check if user entered a number
    try:
        item_index = int(user_text) - 1
        if 0 <= item_index < len(items):
            selected_item = items[item_index]
            session.item_selected = selected_item.get("item_code")
            session.item_name = selected_item.get("item_name")
            session.item_rate = selected_item.get("standard_rate", 0)
            session.current_step = "awaiting_quantity"
            session.save(ignore_permissions=True)
            
            send_whatsapp_message(from_phone, f"Great! You selected: {session.item_name}\n\nHow many would you like? (Enter a number)")
            return
    except ValueError:
        pass
    
    # Check if user typed item name
    for item in items:
        if item.get("item_name", "").lower() in user_text.lower():
            session.item_selected = item.get("item_code")
            session.item_name = item.get("item_name")
            session.item_rate = item.get("standard_rate", 0)
            session.current_step = "awaiting_quantity"
            session.save(ignore_permissions=True)
            
            send_whatsapp_message(from_phone, f"Great! You selected: {session.item_name}\n\nHow many would you like? (Enter a number)")
            return
    
    # Invalid selection
    send_whatsapp_message(from_phone, "Sorry, I didn't understand. Please reply with a number (1-10) or type the item name.")


def handle_quantity_selection(from_phone, session, user_text):
    """Handle quantity input"""
    try:
        quantity = int(user_text)
        if 1 <= quantity <= 20:
            session.quantity = quantity
            session.current_step = "awaiting_address"
            session.save(ignore_permissions=True)
            
            total = session.item_rate * quantity
            send_whatsapp_message(from_phone, f"Perfect! {quantity}x {session.item_name}\nTotal: ${total}\n\nPlease enter your delivery address:")
        else:
            send_whatsapp_message(from_phone, "Please enter a quantity between 1 and 20.")
    except ValueError:
        send_whatsapp_message(from_phone, "Please enter a valid number for quantity.")


def handle_address_input(from_phone, session, user_text):
    """Handle delivery address input"""
    if len(user_text.strip()) < 5:
        send_whatsapp_message(from_phone, "Please enter a complete delivery address (at least 5 characters).")
        return
    
    session.delivery_address = user_text.strip()
    session.current_step = "awaiting_confirmation"
    session.save(ignore_permissions=True)
    
    total = session.item_rate * session.quantity
    order_summary = f"""📋 Order Summary:
    
Item: {session.quantity}x {session.item_name}
Price per item: ${session.item_rate}
Total: ${total}
Delivery to: {session.delivery_address}

Confirm this order? Reply 'yes' to place order or 'no' to cancel."""
    
    send_whatsapp_message(from_phone, order_summary)


def handle_confirmation(from_phone, session, user_text):
    """Handle order confirmation"""
    if user_text.lower() in ["yes", "y", "confirm"]:
        # Create the order
        try:
            order_doc = create_whatsapp_order(session)
            session.status = "completed"
            session.order_created = order_doc.name
            session.save(ignore_permissions=True)
            
            send_whatsapp_message(from_phone, f"✅ Order placed successfully!\n\nOrder Number: {order_doc.name}\nEstimated delivery: 30 minutes\n\nThank you for your order! 🎉")
            
        except Exception as e:
            frappe.logger().error(f"Error creating order: {str(e)}")
            send_whatsapp_message(from_phone, "Sorry, there was an error placing your order. Please try again later.")
            
    elif user_text.lower() in ["no", "n", "cancel"]:
        cancel_order(from_phone, session)
    else:
        send_whatsapp_message(from_phone, "Please reply 'yes' to confirm or 'no' to cancel.")


def create_whatsapp_order(session):
    """Create WhatsApp Order in ERPNext"""
    # Create customer if doesn't exist
    customer = get_or_create_customer(session.phone_number, session.delivery_address)
    
    # Create the order
    order_doc = frappe.get_doc({
        "doctype": "WhatsApp Order",
        "naming_series": "WOR-.YYYY.-.#####",
        "customer_name": f"WhatsApp Customer {session.phone_number}",
        "phone_number": session.phone_number,
        "item": session.item_name,
        "quantity": session.quantity,
        "delivery_address": session.delivery_address,
        "order_status": "Pending",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    })
    
    order_doc.insert(ignore_permissions=True)
    return order_doc


def get_or_create_customer(phone_number, address):
    """Get or create customer from phone number"""
    existing_customer = frappe.db.get_value("Customer", {"mobile_no": phone_number}, "name")
    if existing_customer:
        return existing_customer
    
    # Create new customer
    customer_doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": f"WhatsApp Customer {phone_number}",
        "mobile_no": phone_number,
        "customer_group": "Individual",
        "territory": "All Territories",
        "customer_type": "Individual"
    })
    customer_doc.insert(ignore_permissions=True)
    
    # Create address
    if address:
        address_doc = frappe.get_doc({
            "doctype": "Address",
            "address_title": f"{customer_doc.name} Address",
            "address_line1": address,
            "city": "Unknown",
            "country": "Kenya",
            "links": [{"link_doctype": "Customer", "link_name": customer_doc.name}]
        })
        address_doc.insert(ignore_permissions=True)
    
    return customer_doc.name


def cancel_order(from_phone, session):
    """Cancel the current order"""
    session.status = "cancelled"
    session.save(ignore_permissions=True)
    send_whatsapp_message(from_phone, "Order cancelled. Type 'order' to start a new order anytime! 👋")


def send_whatsapp_message(to_phone, message_text):
    """Send WhatsApp message using Meta API"""
    try:
        token = frappe.conf.get("whatsapp_token")
        phone_id = frappe.conf.get("whatsapp_phone_id")
        
        if not token or not phone_id:
            frappe.logger().error("WhatsApp credentials not configured")
            return
        
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message_text}
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        frappe.logger().info(f"WhatsApp message sent successfully to {to_phone}")
        return response.json()
        
    except Exception as e:
        frappe.logger().error(f"Failed to send WhatsApp message: {str(e)}")
        raise


# SIMPLIFIED API FOR TESTING (No Meta API Required)
# ================================================

@frappe.whitelist(allow_guest=True)
def test_order():
    """
    Simple test endpoint to create orders without WhatsApp setup
    Usage: POST to /api/method/whatsapp_integration.api.test_order
    """
    try:
        # Get data from request
        data = frappe.request.get_json() or {}
        
        # Extract order details
        customer_name = data.get("customer_name", "Test Customer")
        phone_number = data.get("phone_number", "254712345678")
        item = data.get("item", "Pizza")
        quantity = int(data.get("quantity", 1))
        delivery_address = data.get("delivery_address", "123 Test Street")
        
        # Create the order
        order_doc = frappe.get_doc({
            "doctype": "WhatsApp Order",
            "naming_series": "WOR-.YYYY.-.#####",
            "customer_name": customer_name,
            "phone_number": phone_number,
            "item": item,
            "quantity": quantity,
            "delivery_address": delivery_address,
            "order_status": "Pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        
        order_doc.insert(ignore_permissions=True)
        
        return {
            "status": "success",
            "message": f"Order {order_doc.name} created successfully!",
            "order_id": order_doc.name,
            "data": {
                "name": order_doc.name,
                "customer_name": order_doc.customer_name,
                "item": order_doc.item,
                "quantity": order_doc.quantity,
                "total": "Calculated in ERPNext",
                "delivery_address": order_doc.delivery_address,
                "order_status": order_doc.order_status
            }
        }
        
    except Exception as e:
        frappe.logger().error(f"Error creating test order: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create order: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def simulate_whatsapp_conversation():
    """
    Simulate a complete WhatsApp conversation flow
    Usage: GET /api/method/whatsapp_integration.api.simulate_whatsapp_conversation
    """
    try:
        # Simulate the conversation flow
        conversation_steps = [
            "User: order",
            "Bot: 🍕 Welcome! Here's our menu:",
            "Bot: 1. Pizza - $10",
            "Bot: 2. Burger - $8", 
            "Bot: Reply with the number (1-10) or item name to select.",
            "",
            "User: 1",
            "Bot: Great! You selected: Pizza",
            "Bot: How many would you like? (Enter a number)",
            "",
            "User: 2",
            "Bot: Perfect! 2x Pizza",
            "Bot: Total: $20",
            "Bot: Please enter your delivery address:",
            "",
            "User: 123 Main Street, Nairobi",
            "Bot: 📋 Order Summary:",
            "Bot: Item: 2x Pizza",
            "Bot: Price per item: $10",
            "Bot: Total: $20",
            "Bot: Delivery to: 123 Main Street, Nairobi",
            "Bot: Confirm this order? Reply 'yes' to place order or 'no' to cancel.",
            "",
            "User: yes"
        ]
        
        # Create the order as if user confirmed
        order_doc = frappe.get_doc({
            "doctype": "WhatsApp Order",
            "naming_series": "WOR-.YYYY.-.#####",
            "customer_name": "Simulated Customer",
            "phone_number": "254700000000",
            "item": "Pizza",
            "quantity": 2,
            "delivery_address": "123 Main Street, Nairobi",
            "order_status": "Pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        
        order_doc.insert(ignore_permissions=True)
        
        conversation_steps.append(f"Bot: ✅ Order placed successfully!")
        conversation_steps.append(f"Bot: Order Number: {order_doc.name}")
        conversation_steps.append("Bot: Estimated delivery: 30 minutes")
        conversation_steps.append("Bot: Thank you for your order! 🎉")
        
        return {
            "status": "success",
            "message": "WhatsApp conversation simulated successfully!",
            "order_created": order_doc.name,
            "conversation": conversation_steps
        }
        
    except Exception as e:
        frappe.logger().error(f"Error simulating conversation: {str(e)}")
        return {
            "status": "error", 
            "message": f"Failed to simulate conversation: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_menu():
    """
    Get available items from ERPNext
    Usage: GET /api/method/whatsapp_integration.api.get_menu
    """
    try:
        items = frappe.db.sql("""
            SELECT name as item_code, item_name, standard_rate, description
            FROM `tabItem` 
            WHERE disabled = 0 AND is_sales_item = 1 
            ORDER BY item_name 
            LIMIT 10
        """, as_dict=True)
        
        menu_text = "🍕 Available Items:\n\n"
        for i, item in enumerate(items, 1):
            menu_text += f"{i}. {item.get('item_name')} - ${item.get('standard_rate', 0)}\n"
        
        return {
            "status": "success",
            "menu_text": menu_text,
            "items": items
        }
        
    except Exception as e:
        frappe.logger().error(f"Error fetching menu: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to fetch menu: {str(e)}"
        }


# CUSTOMER ORDER MANAGEMENT APIs
# =============================

@frappe.whitelist(allow_guest=True)
def get_customer_orders(phone_number=None, customer_name=None):
    """
    Get all orders for a specific customer
    Usage: GET /api/method/whatsapp_integration.api.get_customer_orders?phone_number=254712345678
    """
    try:
        # Build filters
        filters = {}
        if phone_number:
            filters["phone_number"] = phone_number
        if customer_name:
            filters["customer_name"] = ["like", f"%{customer_name}%"]
        
        if not filters:
            return {
                "status": "error",
                "message": "Please provide phone_number or customer_name"
            }
        
        # Get orders
        orders = frappe.get_all("WhatsApp Order",
            filters=filters,
            fields=["name", "customer_name", "phone_number", "item", "quantity", 
                   "delivery_address", "order_status", "created_at", "updated_at"],
            order_by="creation desc"
        )
        
        if not orders:
            return {
                "status": "success",
                "message": "No orders found for this customer",
                "orders": [],
                "total_orders": 0
            }
        
        return {
            "status": "success",
            "message": f"Found {len(orders)} orders",
            "orders": orders,
            "total_orders": len(orders),
            "customer_info": {
                "customer_name": orders[0].customer_name,
                "phone_number": orders[0].phone_number
            }
        }
        
    except Exception as e:
        frappe.logger().error(f"Error fetching customer orders: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to fetch orders: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_order_status(order_id):
    """
    Get status of a specific order
    Usage: GET /api/method/whatsapp_integration.api.get_order_status?order_id=WOR-2025-00001
    """
    try:
        if not order_id:
            return {
                "status": "error",
                "message": "Please provide order_id"
            }
        
        # Get order details
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        if not order:
            return {
                "status": "error",
                "message": f"Order {order_id} not found"
            }
        
        return {
            "status": "success",
            "order": {
                "order_id": order.name,
                "customer_name": order.customer_name,
                "phone_number": order.phone_number,
                "item": order.item,
                "quantity": order.quantity,
                "delivery_address": order.delivery_address,
                "order_status": order.order_status,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "status_message": get_status_message(order.order_status)
            }
        }
        
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": f"Order {order_id} not found"
        }
    except Exception as e:
        frappe.logger().error(f"Error fetching order status: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to fetch order status: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def update_order_status(order_id, new_status, notes=None):
    """
    Update order status (for admin use)
    Usage: POST /api/method/whatsapp_integration.api.update_order_status
    Body: {"order_id": "WOR-2025-00001", "new_status": "Confirmed", "notes": "Optional notes"}
    """
    try:
        if not order_id or not new_status:
            return {
                "status": "error",
                "message": "Please provide order_id and new_status"
            }
        
        # Valid statuses
        valid_statuses = ["Pending", "Confirmed", "Preparing", "Out for Delivery", "Delivered", "Cancelled"]
        if new_status not in valid_statuses:
            return {
                "status": "error",
                "message": f"Invalid status. Valid options: {', '.join(valid_statuses)}"
            }
        
        # Get and update order
        order = frappe.get_doc("WhatsApp Order", order_id)
        old_status = order.order_status
        order.order_status = new_status
        order.updated_at = datetime.now()
        
        if notes:
            order.add_comment("Comment", f"Status changed from {old_status} to {new_status}. Notes: {notes}")
        
        order.save(ignore_permissions=True)
        
        # Send WhatsApp notification if configured
        try:
            send_status_update_notification(order)
        except:
            pass  # Don't fail if WhatsApp notification fails
        
        return {
            "status": "success",
            "message": f"Order {order_id} status updated from {old_status} to {new_status}",
            "order": {
                "order_id": order.name,
                "old_status": old_status,
                "new_status": new_status,
                "updated_at": order.updated_at,
                "status_message": get_status_message(new_status)
            }
        }
        
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": f"Order {order_id} not found"
        }
    except Exception as e:
        frappe.logger().error(f"Error updating order status: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to update order status: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def cancel_order(order_id, reason=None):
    """
    Cancel an order
    Usage: POST /api/method/whatsapp_integration.api.cancel_order
    Body: {"order_id": "WOR-2025-00001", "reason": "Customer requested cancellation"}
    """
    try:
        if not order_id:
            return {
                "status": "error",
                "message": "Please provide order_id"
            }
        
        # Get order
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        # Check if order can be cancelled
        if order.order_status in ["Delivered", "Cancelled"]:
            return {
                "status": "error",
                "message": f"Cannot cancel order with status: {order.order_status}"
            }
        
        # Cancel order
        old_status = order.order_status
        order.order_status = "Cancelled"
        order.updated_at = datetime.now()
        
        cancel_reason = reason or "Customer requested cancellation"
        order.add_comment("Comment", f"Order cancelled. Reason: {cancel_reason}")
        
        order.save(ignore_permissions=True)
        
        return {
            "status": "success",
            "message": f"Order {order_id} has been cancelled",
            "order": {
                "order_id": order.name,
                "old_status": old_status,
                "new_status": "Cancelled",
                "cancellation_reason": cancel_reason,
                "cancelled_at": order.updated_at
            }
        }
        
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": f"Order {order_id} not found"
        }
    except Exception as e:
        frappe.logger().error(f"Error cancelling order: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to cancel order: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_order_history(phone_number, limit=10):
    """
    Get order history for a customer with pagination
    Usage: GET /api/method/whatsapp_integration.api.get_order_history?phone_number=254712345678&limit=5
    """
    try:
        if not phone_number:
            return {
                "status": "error",
                "message": "Please provide phone_number"
            }
        
        # Get orders with pagination
        orders = frappe.get_all("WhatsApp Order",
            filters={"phone_number": phone_number},
            fields=["name", "item", "quantity", "order_status", "created_at", "updated_at"],
            order_by="creation desc",
            limit=limit
        )
        
        # Format order history
        order_history = []
        for order in orders:
            order_history.append({
                "order_id": order.name,
                "item": order.item,
                "quantity": order.quantity,
                "status": order.order_status,
                "status_message": get_status_message(order.order_status),
                "ordered_at": order.created_at,
                "last_updated": order.updated_at
            })
        
        return {
            "status": "success",
            "message": f"Found {len(order_history)} recent orders",
            "customer_phone": phone_number,
            "order_history": order_history,
            "total_returned": len(order_history)
        }
        
    except Exception as e:
        frappe.logger().error(f"Error fetching order history: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to fetch order history: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def search_orders(query=None, status=None, date_from=None, date_to=None):
    """
    Search orders with various filters
    Usage: GET /api/method/whatsapp_integration.api.search_orders?query=pizza&status=Pending
    """
    try:
        # Build filters
        filters = {}
        
        if query:
            # Search in customer name, item, or order ID
            filters["name"] = ["like", f"%{query}%"]
        
        if status:
            filters["order_status"] = status
        
        if date_from:
            filters["created_at"] = [">=", date_from]
        
        if date_to:
            if "created_at" in filters:
                filters["created_at"].append("<=")
                filters["created_at"].append(date_to)
            else:
                filters["created_at"] = ["<=", date_to]
        
        # Get orders
        orders = frappe.get_all("WhatsApp Order",
            filters=filters,
            fields=["name", "customer_name", "phone_number", "item", "quantity", 
                   "order_status", "created_at"],
            order_by="creation desc",
            limit=50
        )
        
        return {
            "status": "success",
            "message": f"Found {len(orders)} orders matching criteria",
            "search_criteria": {
                "query": query,
                "status": status,
                "date_from": date_from,
                "date_to": date_to
            },
            "orders": orders,
            "total_found": len(orders)
        }
        
    except Exception as e:
        frappe.logger().error(f"Error searching orders: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to search orders: {str(e)}"
        }

# HELPER FUNCTIONS
# ===============

def get_status_message(status):
    """Get user-friendly status message"""
    status_messages = {
        "Pending": "Your order is being processed",
        "Confirmed": "Order confirmed! We're preparing your order",
        "Preparing": "Your order is being prepared",
        "Out for Delivery": "Your order is on its way!",
        "Delivered": "Order delivered successfully!",
        "Cancelled": "Order has been cancelled"
    }
    return status_messages.get(status, "Unknown status")

def send_status_update_notification(order):
    """Send WhatsApp notification when order status changes"""
    try:
        token = frappe.conf.get("whatsapp_token")
        phone_id = frappe.conf.get("whatsapp_phone_id")
        
        if not token or not phone_id:
            return  # Skip if WhatsApp not configured
        
        status_message = get_status_message(order.order_status)
        notification_text = f"""📱 Order Update

Order: {order.name}
Status: {order.order_status}
Message: {status_message}

Thank you for choosing us! 🎉"""
        
        send_whatsapp_message(order.phone_number, notification_text)
        
    except Exception as e:
        frappe.logger().error(f"Failed to send status update notification: {str(e)}")

@frappe.whitelist(allow_guest=True)
def get_orders_by_date(date=None, date_from=None, date_to=None):
    """
    Get orders by specific date or date range
    Usage: 
    - GET /api/method/whatsapp_integration.api.get_orders_by_date?date=2025-09-24
    - GET /api/method/whatsapp_integration.api.get_orders_by_date?date_from=2025-09-20&date_to=2025-09-24
    """
    try:
        if not date and not date_from and not date_to:
            return {
                "status": "error",
                "message": "Please provide either 'date' or 'date_from' and/or 'date_to' parameters"
            }
        
        filters = {}
        
        if date:
            # Single date - get orders for that specific date
            filters["creation"] = ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
        else:
            # Date range
            if date_from:
                filters["creation"] = [">=", f"{date_from} 00:00:00"]
            if date_to:
                if "creation" in filters:
                    filters["creation"].append("<=")
                    filters["creation"].append(f"{date_to} 23:59:59")
                else:
                    filters["creation"] = ["<=", f"{date_to} 23:59:59"]
        
        # Get orders with all details
        orders = frappe.get_all("WhatsApp Order",
            filters=filters,
            fields=["name", "customer_name", "phone_number", "item", "quantity", 
                   "order_status", "delivery_address", "creation", "modified"],
            order_by="creation desc"
        )
        
        return {
            "status": "success",
            "message": f"Found {len(orders)} orders for the specified date(s)",
            "search_criteria": {
                "date": date,
                "date_from": date_from,
                "date_to": date_to
            },
            "orders": orders,
            "total_found": len(orders)
        }
        
    except Exception as e:
        frappe.logger().error(f"Error getting orders by date: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get orders by date: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_order_products(order_id):
    """
    Get products and quantities for a specific order
    Usage: GET /api/method/whatsapp_integration.api.get_order_products?order_id=WOR-2025-00001
    """
    try:
        if not order_id:
            return {
                "status": "error",
                "message": "Please provide order_id parameter"
            }
        
        # Get the order details
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        # For WhatsApp orders, we currently have single item per order
        # But this API is designed to be extensible for multiple items
        products = [{
            "item_name": order.item,
            "quantity": order.quantity,
            "unit_price": 0,  # Can be added to DocType later
            "total_price": 0  # Can be calculated later
        }]
        
        return {
            "status": "success",
            "order_id": order_id,
            "order_status": order.order_status,
            "customer_name": order.customer_name,
            "phone_number": order.phone_number,
            "delivery_address": order.delivery_address,
            "created_at": order.creation,
            "products": products,
            "total_items": len(products),
            "total_quantity": sum(product["quantity"] for product in products)
        }
        
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": f"Order {order_id} not found"
        }
    except Exception as e:
        frappe.logger().error(f"Error getting order products: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get order products: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_daily_order_summary(date=None):
    """
    Get daily order summary with products and quantities
    Usage: GET /api/method/whatsapp_integration.api.get_daily_order_summary?date=2025-09-24
    """
    try:
        if not date:
            date = frappe.utils.today()
        
        # Get all orders for the date
        filters = {
            "creation": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]
        }
        
        orders = frappe.get_all("WhatsApp Order",
            filters=filters,
            fields=["name", "item", "quantity", "order_status", "creation"]
        )
        
        # Group by products and calculate totals
        product_summary = {}
        status_summary = {}
        total_orders = len(orders)
        total_quantity = 0
        
        for order in orders:
            # Product summary
            if order.item not in product_summary:
                product_summary[order.item] = {
                    "item_name": order.item,
                    "total_quantity": 0,
                    "order_count": 0,
                    "orders": []
                }
            
            product_summary[order.item]["total_quantity"] += order.quantity
            product_summary[order.item]["order_count"] += 1
            product_summary[order.item]["orders"].append({
                "order_id": order.name,
                "quantity": order.quantity,
                "status": order.order_status
            })
            
            # Status summary
            status = order.order_status
            if status not in status_summary:
                status_summary[status] = 0
            status_summary[status] += 1
            
            total_quantity += order.quantity
        
        return {
            "status": "success",
            "date": date,
            "summary": {
                "total_orders": total_orders,
                "total_quantity": total_quantity,
                "status_breakdown": status_summary
            },
            "products": list(product_summary.values()),
            "orders": orders
        }
        
    except Exception as e:
        frappe.logger().error(f"Error getting daily order summary: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get daily order summary: {str(e)}"
        }

# PRODUCT AND VARIANT MANAGEMENT APIs
# ===================================

@frappe.whitelist(allow_guest=True)
def get_product_variants(product_name=None):
    """
    Get all product variants or variants for a specific product
    Usage: 
    - GET /api/method/whatsapp_integration.api.get_product_variants
    - GET /api/method/whatsapp_integration.api.get_product_variants?product_name=Pizza
    """
    try:
        filters = {"is_available": 1}  # Only available variants
        
        if product_name:
            filters["product_name"] = ["like", f"%{product_name}%"]
        
        variants = frappe.get_all("WhatsApp Product Variant",
            filters=filters,
            fields=["name", "variant_name", "product_name", "variant_type", 
                    "unit_price", "currency", "stock_quantity", "is_available"],
            order_by="product_name asc, variant_name asc"
        )
        
        return {
            "status": "success",
            "message": f"Found {len(variants)} product variants",
            "product_name_filter": product_name,
            "variants": variants,
            "total_found": len(variants)
        }
        
    except Exception as e:
        frappe.logger().error(f"Error getting product variants: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get product variants: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_products_menu():
    """
    Get an organized menu of products with their variants and prices.
    Usage: GET /api/method/whatsapp_integration.api.get_products_menu
    """
    try:
        variants = frappe.get_all("WhatsApp Product Variant",
            filters={"is_available": 1},
            fields=["product_name", "variant_name", "unit_price", "currency"],
            order_by="product_name asc, unit_price asc"
        )
        
        menu = {}
        for v in variants:
            if v.product_name not in menu:
                menu[v.product_name] = []
            menu[v.product_name].append({
                "variant_name": v.variant_name,
                "unit_price": v.unit_price,
                "currency": v.currency
            })
        
        formatted_menu = []
        for product, var_list in menu.items():
            formatted_menu.append(f"*{product}*:")
            for var in var_list:
                formatted_menu.append(f"  - {var.variant_name}: {var.currency} {var.unit_price}")
        
        return {
            "status": "success",
            "message": "Current menu with variants",
            "menu_data": menu,
            "formatted_menu": "\n".join(formatted_menu)
        }
    except Exception as e:
        frappe.logger().error(f"Error getting products menu: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get products menu: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_variant_details(variant_id):
    """
    Get details for a specific product variant.
    Usage: GET /api/method/whatsapp_integration.api.get_variant_details?variant_id=Pizza%20Margherita%20-%20Large
    """
    try:
        variant = frappe.get_doc("WhatsApp Product Variant", variant_id)
        return {
            "status": "success",
            "variant_details": variant.as_dict()
        }
    except frappe.DoesNotExistError:
        return {
            "status": "error",
            "message": f"Variant {variant_id} not found."
        }
    except Exception as e:
        frappe.logger().error(f"Error getting variant details: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get variant details: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def create_order_with_variant(customer_name, phone_number, variant_id, quantity, delivery_address):
    """
    Create a WhatsApp Order with a specific product variant and calculate total price.
    Usage: POST /api/method/whatsapp_integration.api.create_order_with_variant
    Payload: {
        "customer_name": "John Doe",
        "phone_number": "254712345678",
        "variant_id": "Pizza Margherita - Large",
        "quantity": 2,
        "delivery_address": "123 Main Street"
    }
    """
    try:
        if not all([customer_name, phone_number, variant_id, quantity, delivery_address]):
            return {"status": "error", "message": "All fields (customer_name, phone_number, variant_id, quantity, delivery_address) are required."}

        quantity = frappe.parse_json(quantity) if isinstance(quantity, str) else quantity
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            return {"status": "error", "message": "Quantity must be a positive number."}

        # Fetch variant details
        variant = frappe.get_doc("WhatsApp Product Variant", variant_id)
        if not variant.is_available:
            return {"status": "error", "message": f"Variant {variant_id} is currently not available."}
        if variant.stock_quantity < quantity:
            return {"status": "error", "message": f"Insufficient stock for {variant_id}. Available: {variant.stock_quantity}"}

        # Create customer if doesn't exist (reusing existing logic)
        customer_doc = get_or_create_customer(phone_number, delivery_address)

        order_doc = frappe.get_doc({
            "doctype": "WhatsApp Order",
            "naming_series": "WOR-.YYYY.-.#####",
            "customer_name": customer_name,
            "phone_number": phone_number,
            "item": variant.product_name,  # Main product name
            "item_code": variant.name,  # Using variant name as item_code for simplicity
            "variant_id": variant.name,  # Link to the variant
            "variant_name": variant.variant_name,
            "quantity": quantity,
            "unit_price": variant.unit_price,
            "currency": variant.currency,
            "total_price": variant.unit_price * quantity,
            "delivery_address": delivery_address,
            "order_status": "Pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })
        
        order_doc.insert(ignore_permissions=True)

        # Update stock (decrement)
        variant.stock_quantity -= quantity
        variant.save(ignore_permissions=True)

        return {
            "status": "success",
            "message": f"Order {order_doc.name} placed successfully for {quantity} x {variant.variant_name} of {variant.product_name}.",
            "order_id": order_doc.name,
            "total_price": order_doc.total_price,
            "currency": order_doc.currency
        }

    except frappe.DoesNotExistError:
        return {"status": "error", "message": f"Product variant {variant_id} not found."}
    except Exception as e:
        frappe.logger().error(f"Error creating order with variant: {str(e)}")
        return {"status": "error", "message": f"Failed to create order with variant: {str(e)}"}

@frappe.whitelist(allow_guest=True)
def get_order_with_pricing(order_id):
    """
    Get a specific WhatsApp Order with complete pricing details.
    Usage: GET /api/method/whatsapp_integration.api.get_order_with_pricing?order_id=WOR-2025-00001
    """
    try:
        if not order_id:
            return {"status": "error", "message": "Please provide order_id parameter."}
        
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        return {
            "status": "success",
            "order_details": {
                "order_id": order.name,
                "customer_name": order.customer_name,
                "phone_number": order.phone_number,
                "item": order.item,
                "variant_name": order.variant_name,
                "quantity": order.quantity,
                "unit_price": order.unit_price,
                "currency": order.currency,
                "total_price": order.total_price,
                "delivery_address": order.delivery_address,
                "order_status": order.order_status,
                "created_at": order.creation,
                "updated_at": order.modified
            }
        }
    except frappe.DoesNotExistError:
        return {"status": "error", "message": f"Order {order_id} not found."}
    except Exception as e:
        frappe.logger().error(f"Error getting order with pricing: {str(e)}")
        return {"status": "error", "message": f"Failed to get order with pricing: {str(e)}"}
