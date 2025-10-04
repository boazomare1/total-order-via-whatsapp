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
                # Meta expects just the plain challenge string, not JSON
                # Use frappe.response to set headers and return plain text
                frappe.response["http_status_code"] = 200
                frappe.response["headers"] = {"Content-Type": "text/plain"}
                frappe.local.response = challenge
                return challenge
            else:
                frappe.response["http_status_code"] = 403
                frappe.response["headers"] = {"Content-Type": "text/plain"}
                frappe.local.response = "Verification token mismatch"
                return "Verification token mismatch"
        return "Hello world"

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
    """Process incoming WhatsApp message and create order"""
    try:
        from_phone = message.get("from")
        message_text = message.get("text", {}).get("body", "")
        message_id = message.get("id")
        
        frappe.logger().info(f"Processing message from {from_phone}: {message_text}")
        
        # Check if message contains order information
        if "order" in message_text.lower() or "buy" in message_text.lower():
            create_order_from_message(from_phone, message_text, message_id)
        else:
            # Send menu or help message
            send_menu_message(from_phone)
            
    except Exception as e:
        frappe.logger().error(f"Error processing message: {str(e)}")


def create_order_from_message(from_phone, message_text, message_id):
    """Create order from WhatsApp message"""
    try:
        # Parse order details from message
        # This is a simplified example - you can enhance this based on your needs
        
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
                        order_item.unit_price = 10.0  # Default price - you can lookup from variants
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


# Test functions for development
@frappe.whitelist(allow_guest=True)
def test_order():
    """Test function to create a sample order"""
    try:
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_phone = "+1234567890"
        order_doc.order_status = "Pending"
        order_doc.order_date = frappe.utils.now()
        order_doc.raw_message = "Test order"
        
        # Add sample item
        item = order_doc.append("order_items", {})
        item.item_name = "Pizza Margherita"
        item.quantity = 2
        item.unit_price = 15.0
        item.total_price = 30.0
        
        order_doc.total_amount = 30.0
        order_doc.save()
        
        return {"status": "success", "order_id": order_doc.name}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Test WhatsApp notification
@frappe.whitelist(allow_guest=True)
def test_whatsapp_notification():
    """Test WhatsApp notification functionality"""
    try:
        phone_id = frappe.conf.get("whatsapp_phone_id")
        access_token = frappe.conf.get("whatsapp_token")
        
        if not phone_id or not access_token:
            return {"status": "error", "message": "WhatsApp credentials not configured"}
        
        url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": "254770534365",
            "type": "text",
            "text": {"body": "Test notification from ERPNext WhatsApp Integration"}
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "message": "Test notification sent successfully",
                "response": response.text
            }
        else:
            return {
                "status": "error", 
                "message": f"Failed to send notification: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Admin API for updating order status (bypasses UI issues)
@frappe.whitelist(allow_guest=True, methods=['POST'])
def admin_update_order_status(order_id, new_status):
    """Admin API to update order status and send WhatsApp notification"""
    try:
        # Set CORS headers for frontend compatibility
        frappe.local.response.headers["Access-Control-Allow-Origin"] = "*"
        frappe.local.response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        frappe.local.response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        frappe.local.response.headers["Content-Type"] = "application/json"
        
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


def send_status_notification_manual(order_id, old_status, new_status):
    """Manually send status notification"""
    try:
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        # Create notification message
        message = f"""
🔄 Order Status Update

Order ID: {order_id}
Status: {old_status} → {new_status}
Item: {order.item}
Quantity: {order.quantity}
Total: {order.total_price}

Thank you for your order!
        """
        
        # Send WhatsApp message
        phone_id = frappe.conf.get("whatsapp_phone_id")
        access_token = frappe.conf.get("whatsapp_token")
        
        if not phone_id or not access_token:
            return {"status": "error", "message": "WhatsApp credentials not configured"}
        
        url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": order.phone_number,
            "type": "text",
            "text": {"body": message}
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return {
                "status": "success",
                "message": "Status notification sent successfully",
                "response": response.text
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to send notification: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def simulate_whatsapp_conversation():
    """Simulate a WhatsApp conversation for testing"""
    try:
        # Simulate incoming message
        test_message = {
            "from": "+1234567890",
            "text": {"body": "Hi, I want to order 2 Pizza Margherita and 1 Burger"},
            "id": "test_message_123"
        }
        
        process_incoming_message(test_message)
        
        return {"status": "success", "message": "Conversation simulated"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_menu():
    """Get the current menu for WhatsApp"""
    try:
        # You can enhance this to fetch from database
        menu = {
            "items": [
                {"name": "Pizza Margherita", "price": 15.0},
                {"name": "Pizza Pepperoni", "price": 18.0},
                {"name": "Burger", "price": 12.0},
                {"name": "Fries", "price": 6.0}
            ]
        }
        
        return menu
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Customer Order Management APIs
@frappe.whitelist(allow_guest=True)
def get_customer_orders(customer_phone=None, limit=10):
    """Get orders for a specific customer"""
    try:
        if not customer_phone:
            return {"status": "error", "message": "Customer phone required"}
        
        filters = {"customer_phone": customer_phone}
        orders = frappe.get_all("WhatsApp Order", 
                               filters=filters, 
                               fields=["name", "order_status", "total_amount", "order_date"],
                               order_by="creation desc",
                               limit=limit)
        
        return {"status": "success", "orders": orders}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_order_status(order_id):
    """Get status of a specific order"""
    try:
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        return {
            "status": "success",
            "order_id": order_id,
            "order_status": order.order_status,
            "total_amount": order.total_amount,
            "order_date": order.order_date
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def update_order_status(order_id, new_status):
    """Update order status"""
    try:
        order = frappe.get_doc("WhatsApp Order", order_id)
        order.order_status = new_status
        order.save()
        
        # Send update to customer if phone number available
        if order.customer_phone:
            message = f"Your order {order_id} status has been updated to: {new_status}"
            send_whatsapp_message(order.customer_phone, message)
        
        return {"status": "success", "message": "Order status updated"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def cancel_order(order_id):
    """Cancel an order"""
    try:
        order = frappe.get_doc("WhatsApp Order", order_id)
        order.order_status = "Cancelled"
        order.save()
        
        # Send cancellation message to customer
        if order.customer_phone:
            message = f"Your order {order_id} has been cancelled. We'll process your refund soon."
            send_whatsapp_message(order.customer_phone, message)
        
        return {"status": "success", "message": "Order cancelled"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_order_history(customer_phone=None, days=30):
    """Get order history for a customer or all orders"""
    try:
        from frappe.utils import add_days, today
        
        start_date = add_days(today(), -days)
        
        if customer_phone:
            filters = {
                "customer_phone": customer_phone,
                "order_date": [">=", start_date]
            }
        else:
            filters = {"order_date": [">=", start_date]}
        
        orders = frappe.get_all("WhatsApp Order",
                               filters=filters,
                               fields=["name", "customer_phone", "order_status", "total_amount", "order_date"],
                               order_by="order_date desc")
        
        return {"status": "success", "orders": orders}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def search_orders(search_term):
    """Search orders by phone number, order ID, or status"""
    try:
        # Search by phone number
        phone_orders = frappe.get_all("WhatsApp Order",
                                     filters={"customer_phone": ["like", f"%{search_term}%"]},
                                     fields=["name", "customer_phone", "order_status", "total_amount", "order_date"])
        
        # Search by order ID
        id_orders = frappe.get_all("WhatsApp Order",
                                  filters={"name": ["like", f"%{search_term}%"]},
                                  fields=["name", "customer_phone", "order_status", "total_amount", "order_date"])
        
        # Combine and deduplicate
        all_orders = phone_orders + id_orders
        unique_orders = []
        seen = set()
        
        for order in all_orders:
            if order.name not in seen:
                unique_orders.append(order)
                seen.add(order.name)
        
        return {"status": "success", "orders": unique_orders}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Date and Product APIs
@frappe.whitelist(allow_guest=True)
def get_orders_by_date(date=None):
    """Get orders for a specific date"""
    try:
        if not date:
            date = frappe.utils.today()
        
        filters = {"order_date": ["between", [date, date]]}
        orders = frappe.get_all("WhatsApp Order",
                               filters=filters,
                               fields=["name", "customer_phone", "order_status", "total_amount", "order_date"],
                               order_by="creation desc")
        
        return {"status": "success", "date": date, "orders": orders}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_order_products(order_id):
    """Get products/items for a specific order"""
    try:
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        items = []
        for item in order.order_items:
            items.append({
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            })
        
        return {
            "status": "success",
            "order_id": order_id,
            "items": items,
            "total_amount": order.total_amount
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_daily_order_summary(date=None):
    """Get summary of orders for a specific date"""
    try:
        if not date:
            date = frappe.utils.today()
        
        # Get all orders for the date
        filters = {"order_date": ["between", [date, date]]}
        orders = frappe.get_all("WhatsApp Order",
                               filters=filters,
                               fields=["name", "total_amount", "order_status"])
        
        # Calculate summary
        total_orders = len(orders)
        total_amount = sum(order.total_amount for order in orders)
        
        status_counts = {}
        for order in orders:
            status = order.order_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "status": "success",
            "date": date,
            "total_orders": total_orders,
            "total_amount": total_amount,
            "status_breakdown": status_counts
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Product and Variant Management APIs
@frappe.whitelist(allow_guest=True)
def get_product_variants():
    """Get all product variants with pricing"""
    try:
        variants = frappe.get_all("WhatsApp Product Variant",
                                 filters={"is_available": 1},
                                 fields=["name", "product_name", "variant_name", "variant_type", 
                                        "price", "currency", "stock_quantity"],
                                 order_by="product_name, variant_name")
        
        return {"status": "success", "variants": variants}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_products_menu():
    """Get formatted menu with variants for WhatsApp"""
    try:
        variants = frappe.get_all("WhatsApp Product Variant",
                                 filters={"is_available": 1},
                                 fields=["product_name", "variant_name", "variant_type", "price", "currency"],
                                 order_by="product_name, price")
        
        # Group by product
        menu = {}
        for variant in variants:
            product = variant.product_name
            if product not in menu:
                menu[product] = []
            
            menu[product].append({
                "variant": f"{variant.variant_name} ({variant.variant_type})",
                "price": variant.price,
                "currency": variant.currency
            })
        
        return {"status": "success", "menu": menu}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_variant_details(variant_id):
    """Get detailed information about a specific variant"""
    try:
        variant = frappe.get_doc("WhatsApp Product Variant", variant_id)
        
        return {
            "status": "success",
            "variant": {
                "id": variant.name,
                "product_name": variant.product_name,
                "variant_name": variant.variant_name,
                "variant_type": variant.variant_type,
                "price": variant.price,
                "currency": variant.currency,
                "stock_quantity": variant.stock_quantity,
                "is_available": variant.is_available
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def create_order_with_variant(customer_phone, variant_id, quantity=1):
    """Create an order with a specific product variant"""
    try:
        variant = frappe.get_doc("WhatsApp Product Variant", variant_id)
        
        if not variant.is_available:
            return {"status": "error", "message": "Variant not available"}
        
        if variant.stock_quantity < quantity:
            return {"status": "error", "message": "Insufficient stock"}
        
        # Create order
        order_doc = frappe.new_doc("WhatsApp Order")
        order_doc.customer_phone = customer_phone
        order_doc.order_status = "Pending"
        order_doc.order_date = frappe.utils.now()
        
        # Add variant details
        order_doc.item_code = variant.product_name
        order_doc.variant_id = variant_id
        order_doc.variant_name = f"{variant.variant_name} ({variant.variant_type})"
        order_doc.unit_price = variant.price
        order_doc.total_price = variant.price * quantity
        order_doc.currency = variant.currency
        
        # Add order item
        order_item = order_doc.append("order_items", {})
        order_item.item_name = order_doc.variant_name
        order_item.quantity = quantity
        order_item.unit_price = variant.price
        order_item.total_price = order_doc.total_price
        
        order_doc.total_amount = order_doc.total_price
        order_doc.save()
        
        return {
            "status": "success",
            "order_id": order_doc.name,
            "total_amount": order_doc.total_amount,
            "currency": order_doc.currency
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True)
def get_order_with_pricing(order_id):
    """Get order details with pricing information"""
    try:
        order = frappe.get_doc("WhatsApp Order", order_id)
        
        items = []
        for item in order.order_items:
            items.append({
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price
            })
        
        return {
            "status": "success",
            "order": {
                "id": order.name,
                "customer_phone": order.customer_phone,
                "order_status": order.order_status,
                "order_date": order.order_date,
                "items": items,
                "total_amount": order.total_amount,
                "currency": getattr(order, 'currency', 'USD')
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}