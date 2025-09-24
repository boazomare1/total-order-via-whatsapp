"""
Simplified WhatsApp API for Testing - No Meta API Required
This version simulates WhatsApp messages for easy testing
"""

import frappe
import json
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def test_order():
    """
    Simple test endpoint to create orders without WhatsApp setup
    Usage: POST to /api/method/whatsapp_integration.api_simple.test_order
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
    Usage: GET /api/method/whatsapp_integration.api_simple.simulate_whatsapp_conversation
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
    Usage: GET /api/method/whatsapp_integration.api_simple.get_menu
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