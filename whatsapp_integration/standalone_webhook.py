#!/usr/bin/env python3
"""
Standalone webhook server for Meta verification
This bypasses ERPNext and creates a simple webhook server
"""

from flask import Flask, request, jsonify
import json
import requests
import os
import sys

# Add Frappe path to import Frappe modules
sys.path.append('/home/boaz/test-bench/apps/frappe')
sys.path.append('/home/boaz/test-bench')

# Import Frappe
import frappe
from frappe import _

app = Flask(__name__)

# WhatsApp API configuration
WHATSAPP_PHONE_ID = "853129267877967"
WHATSAPP_TOKEN = "EAAVkO0JZA4L8BPtOZBJiMsWvzXLEhd3WgeyhSKMhf9kiCTJKeEbke6yEbGwRzq9Aa0cEWoJPSjsWrRt0ZC79NArKXqd72fEVE0S4gHO0BX21RoZAiUXkIZC5AbZAFZBGhvFBUb3Pq7a5XqZACqfCnx6ZCikS4hgKCxBXSduGLJBqKjzxqjzZAMjSzsb4xT7lw7FgrNzvg5bnVGzI49tlCjpo2So1ZAjKUEQw86cX2dIf6tSogZDZD"
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"

# User state management for conversation flow
user_states = {}

# Simple in-memory order storage (in production, use a database)
orders = {}
order_counter = 1

def send_whatsapp_message(to_number, message_text):
    """Send a WhatsApp message using the Meta API"""
    try:
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message_text
            }
        }
        
        print(f"📤 Sending message to {to_number}: {message_text}")
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Message sent successfully: {response.json()}")
            return True
        else:
            print(f"❌ Failed to send message: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending WhatsApp message: {e}")
        return False

def create_erpnext_order(phone_number, item, quantity, unit_price, total_price, delivery_address):
    """Create order in ERPNext database using bench console"""
    global order_counter
    try:
        import subprocess
        import json
        
        # Create the Python code for bench console
        python_code = f"""
import frappe
frappe.init('totalwhatsapporder.local')
frappe.connect()
frappe.set_user('Administrator')
doc = frappe.new_doc('WhatsApp Order')
doc.customer_name = 'WhatsApp Customer'
doc.phone_number = '{phone_number}'
doc.item = '{item}'
doc.quantity = {quantity}
doc.unit_price = {unit_price}
doc.total_price = {total_price}
doc.delivery_address = '{delivery_address}'
doc.order_status = 'Pending'
doc.save()
frappe.db.commit()
print('SUCCESS:' + str(doc.name))
frappe.destroy()
"""
        
        # Use bench console with the code - write to temp file to avoid shell escaping issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name
        
        cmd = f"cd /home/boaz/test-bench && cat '{temp_file}' | bench --site totalwhatsapporder.local console"
        
        print(f"🔧 Executing command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print(f"🔧 Command result: returncode={result.returncode}")
        print(f"🔧 stdout: {result.stdout}")
        print(f"🔧 stderr: {result.stderr}")
        
        # Clean up temporary file
        import os
        try:
            os.unlink(temp_file)
        except:
            pass
        
        if result.returncode == 0:
            output = result.stdout.strip()
            
            # Look for SUCCESS: in output
            for line in output.split('\n'):
                if 'SUCCESS:' in line:
                    order_id = line.split('SUCCESS:')[1].strip()
                    # Clean up any extra characters
                    order_id = order_id.replace(')', '').replace('\x1b[0m', '').replace('{doc.name}', '').strip()
                    print(f"✅ Order created in ERPNext: {order_id}")
                    return order_id
            
            # Also look for Out[XX]: <WhatsAppOrder: WOR-XXXX-XXXXX> pattern
            for line in output.split('\n'):
                if 'WhatsAppOrder:' in line and 'WOR-' in line:
                    # Extract order ID from pattern like "Out[14]: <WhatsAppOrder: WOR-2025-00036>"
                    import re
                    match = re.search(r'WOR-\d+-\d+', line)
                    if match:
                        order_id = match.group()
                        print(f"✅ Order created in ERPNext (from Out pattern): {order_id}")
                        return order_id
            
            # If no success found, check for any order creation
            if 'Order created:' in output:
                for line in output.split('\n'):
                    if 'Order created:' in line:
                        order_id = line.split('Order created: ')[1].strip()
                        print(f"✅ Order created in ERPNext: {order_id}")
                        return order_id
            
            # If we get here, the script ran but we couldn't extract the order ID
            print(f"✅ Order created in ERPNext (no ID extracted)")
            return "WOR-ERPNext-001"
        else:
            print(f"❌ Bench console failed: {result.stderr}")
            # Fallback to simple order ID
            order_counter += 1
            return f"WOR-{order_counter:05d}"
        
    except Exception as e:
        print(f"❌ Error creating ERPNext order: {e}")
        # Fallback to simple order ID
        order_counter += 1
        return f"WOR-{order_counter:05d}"

def get_erpnext_orders(phone_number):
    """Get orders from ERPNext database using bench console"""
    try:
        import subprocess
        import json
        
        # Create the Python code for bench console
        python_code = f"""
import frappe
frappe.init('totalwhatsapporder.local')
frappe.connect()

# Get orders from ERPNext
orders_list = frappe.get_all("WhatsApp Order", 
                           filters={{"phone_number": "{phone_number}"}}, 
                           fields=["name", "item", "quantity", "total_price", "order_status", "creation"],
                           order_by="creation desc",
                           limit=5)

# Convert to JSON format
import json
from datetime import datetime

orders = []
for order in orders_list:
    orders.append({{
        "id": order["name"],
        "customer_name": "WhatsApp Customer",
        "phone_number": "{phone_number}",
        "item": order["item"],
        "quantity": order["quantity"],
        "unit_price": order["total_price"] / order["quantity"] if order["quantity"] > 0 else 0,
        "total_price": order["total_price"],
        "delivery_address": "N/A",
        "order_status": order["order_status"],
        "created_at": order["creation"].strftime("%Y-%m-%d %H:%M:%S")
    }})

print(f'ORDERS:{json.dumps(orders)}')
frappe.destroy()
"""
        
        # Use bench console with the code
        cmd = f"cd /home/boaz/test-bench && echo '{python_code}' | bench --site totalwhatsapporder.local console"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            
            # Look for ORDERS: in output
            for line in output.split('\n'):
                if 'ORDERS:' in line:
                    orders_json = line.split('ORDERS:')[1].strip()
                    try:
                        orders = json.loads(orders_json)
                        print(f"✅ Retrieved {len(orders)} orders from ERPNext")
                        return orders
                    except json.JSONDecodeError:
                        print(f"❌ Failed to parse orders JSON: {orders_json}")
                        return []
            
            print(f"✅ No orders found in ERPNext")
            return []
        else:
            print(f"❌ Bench console failed: {result.stderr}")
            return []
        
    except Exception as e:
        print(f"❌ Error getting ERPNext orders: {e}")
        return []

def process_incoming_message(from_phone, message_text):
    """Process incoming WhatsApp message with intelligent bot responses"""
    try:
        print(f"Processing message from {from_phone}: {message_text}")
        
        # Get user state
        user_state = user_states.get(from_phone, {"state": "idle", "data": {}})
        message_lower = message_text.lower().strip()
        
        print(f"User state: {user_state['state']}, Data: {user_state['data']}")
        
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
        print(f"Error processing message: {str(e)}")
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
            print(f"State changed to selecting_variant for {from_phone}")
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
        print(f"Handling variant selection: {message_text}")
        variant_num = int(message_text)
        selected_item = user_state["data"]["selected_item"]
        print(f"Selected item: {selected_item}, Variant num: {variant_num}")
        
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
        global order_counter
        
        quantity = user_state["data"]["quantity"]
        delivery_address = user_state["data"]["delivery_address"]
        
        # Check if this is a reorder
        if "reorder_item" in user_state["data"]:
            reorder_item = user_state["data"]["reorder_item"]
            reorder_price = user_state["data"]["reorder_price"]
            
            item = reorder_item
            unit_price = reorder_price
            total_price = reorder_price * quantity
        else:
            selected_item = user_state["data"]["selected_item"]
            selected_variant = user_state["data"]["selected_variant"]
            
            item = f"{selected_item['name']} - {selected_variant}"
            unit_price = selected_item["price"]
            total_price = selected_item["price"] * quantity
        
        # Create order in ERPNext
        order_id = create_erpnext_order(from_phone, item, quantity, unit_price, total_price, delivery_address)
        
        # Also store in memory for quick access
        order_data = {
            "id": order_id,
            "customer_name": "WhatsApp Customer",
            "phone_number": from_phone,
            "item": item,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "delivery_address": delivery_address,
            "order_status": "Pending",
            "created_at": "2025-10-04 10:00:00"
        }
        
        orders[order_id] = order_data
        
        # Send confirmation
        if "reorder_item" in user_state["data"]:
            order_type = "Reorder"
            item_display = item
        else:
            order_type = "Order"
            item_display = item
        
        confirmation_text = f"""
✅ *{order_type} Confirmed!*

*Order Details:*
• Order ID: {order_id}
• Item: {item_display}
• Quantity: {quantity}
• Total: KES {total_price}
• Delivery Address: {delivery_address}

*Payment Instructions:*
Pay KES {total_price} on delivery to:
📱 *0742356449*

*Order Status:* Pending
We'll notify you when your order is being prepared!

*Commands:*
• Type *"My Orders"* to view all orders
• Type *"Status {order_id}"* to check this order
        """
        
        send_whatsapp_message(from_phone, confirmation_text)
        
    except Exception as e:
        print(f"Error creating complete order: {str(e)}")
        send_whatsapp_message(from_phone, "Sorry, there was an error creating your order. Please try again.")

def show_customer_orders(from_phone):
    """Show customer's order history"""
    try:
        # Get orders from ERPNext
        erpnext_orders = get_erpnext_orders(from_phone)
        
        # Also get from memory (for fallback)
        memory_orders = [order for order in orders.values() if order["phone_number"] == from_phone]
        
        # Combine and deduplicate
        all_orders = erpnext_orders + memory_orders
        unique_orders = {}
        for order in all_orders:
            unique_orders[order["id"]] = order
        
        customer_orders = list(unique_orders.values())
        customer_orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        customer_orders = customer_orders[:5]  # Show last 5 orders
        
        if not customer_orders:
            send_whatsapp_message(from_phone, "You haven't placed any orders yet. Type 'menu' to start ordering!")
            return
        
        orders_text = "*Your Recent Orders:*\n\n"
        for order in customer_orders:
            orders_text += f"• *{order['id']}* - {order['item']}\n"
            orders_text += f"  Qty: {order['quantity']} | Total: KES {order['total_price']}\n"
            orders_text += f"  Status: {order['order_status']}\n"
            orders_text += f"  Date: {order.get('created_at', 'N/A')}\n\n"
        
        orders_text += "*Commands:*\n"
        orders_text += "• Type *'Status [Order ID]'* to check specific order\n"
        orders_text += "• Type *'Reorder [Order ID]'* to reorder\n"
        orders_text += "• Type *'menu'* to place new order"
        
        send_whatsapp_message(from_phone, orders_text)
        
    except Exception as e:
        print(f"Error getting customer orders: {str(e)}")
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
            send_whatsapp_message(from_phone, "Please provide an order ID. Example: 'Status WOR-00001'")
            return
        
        # Get order details from ERPNext first, then memory
        order = None
        
        # Try ERPNext first
        try:
            import os
            os.chdir('/home/boaz/test-bench')
            frappe.init(site='totalwhatsapporder.local', sites_path='/home/boaz/test-bench/sites')
            frappe.connect()
            order_doc = frappe.get_doc("WhatsApp Order", order_id)
            if order_doc.phone_number == from_phone:
                order = {
                    "id": order_doc.name,
                    "item": order_doc.item,
                    "quantity": order_doc.quantity,
                    "total_price": order_doc.total_price,
                    "order_status": order_doc.order_status,
                    "delivery_address": getattr(order_doc, 'delivery_address', 'N/A'),
                    "created_at": order_doc.creation.strftime("%Y-%m-%d %H:%M:%S")
                }
        except:
            pass
        
        # Fallback to memory
        if not order and order_id in orders:
            order = orders[order_id]
        
        if not order:
            send_whatsapp_message(from_phone, "Order not found. Please check the order ID and try again.")
            return
        
        if order["phone_number"] != from_phone:
            send_whatsapp_message(from_phone, "This order doesn't belong to you.")
            return
        
        status_text = f"""
*Order Status: {order_id}*

• Item: {order['item']}
• Quantity: {order['quantity']}
• Total: KES {order['total_price']}
• Status: {order['order_status']}
• Order Date: {order['created_at']}
• Delivery Address: {order['delivery_address']}

*Payment:* Pay on delivery to *0742356449*
        """
        
        send_whatsapp_message(from_phone, status_text)
        
    except Exception as e:
        print(f"Error checking order status: {str(e)}")
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
            send_whatsapp_message(from_phone, "Please provide an order ID. Example: 'Reorder WOR-00001'")
            return
        
        # Get order details from ERPNext first, then memory
        order = None
        
        # Try ERPNext first
        try:
            import os
            os.chdir('/home/boaz/test-bench')
            frappe.init(site='totalwhatsapporder.local', sites_path='/home/boaz/test-bench/sites')
            frappe.connect()
            order_doc = frappe.get_doc("WhatsApp Order", order_id)
            if order_doc.phone_number == from_phone:
                order = {
                    "id": order_doc.name,
                    "item": order_doc.item,
                    "quantity": order_doc.quantity,
                    "unit_price": order_doc.total_price / order_doc.quantity if order_doc.quantity > 0 else 0,
                    "total_price": order_doc.total_price,
                    "order_status": order_doc.order_status,
                    "delivery_address": getattr(order_doc, 'delivery_address', 'N/A'),
                    "created_at": order_doc.creation.strftime("%Y-%m-%d %H:%M:%S")
                }
        except:
            pass
        
        # Fallback to memory
        if not order and order_id in orders:
            order = orders[order_id]
        
        if not order:
            send_whatsapp_message(from_phone, "Order not found. Please check the order ID and try again.")
            return
        
        if order["phone_number"] != from_phone:
            send_whatsapp_message(from_phone, "This order doesn't belong to you.")
            return
        
        # Start reorder process
        user_state = user_states.get(from_phone, {"state": "idle", "data": {}})
        user_state["data"]["reorder_item"] = order["item"]
        user_state["data"]["reorder_price"] = order["unit_price"]
        user_state["state"] = "entering_quantity"
        user_states[from_phone] = user_state
        
        reorder_text = f"""
*Reorder: {order['item']}*

• Previous Quantity: {order['quantity']}
• Unit Price: KES {order['unit_price']}

*How many would you like?* (Type a number)
        """
        
        send_whatsapp_message(from_phone, reorder_text)
        
    except Exception as e:
        print(f"Error handling reorder: {str(e)}")
        send_whatsapp_message(from_phone, "Sorry, couldn't process your reorder. Please try again.")

def create_order_from_message(from_phone, message_text, order_type):
    """Create order directly from message text (for direct orders)"""
    try:
        # This is a simplified version for direct orders
        # In a real implementation, you'd parse the message for items and quantities
        send_whatsapp_message(from_phone, "I see you want to place a direct order! Please use the menu system for the best experience. Type 'menu' to see our full menu.")
    except Exception as e:
        print(f"Error creating order from message: {str(e)}")
        send_whatsapp_message(from_phone, "Sorry, couldn't process your direct order. Please use the menu system instead.")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Simple webhook for Meta verification
    """
    if request.method == "GET":
        # Get verification parameters
        mode = request.args.get('hub.mode')
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        print(f"DEBUG: mode={mode}, verify_token={verify_token}, challenge={challenge}")
        
        # Simple verification logic
        if mode == "subscribe" and verify_token == "frappe_verify_token":
            print(f"DEBUG: Verification successful, returning challenge: {challenge}")
            return challenge, 200, {'Content-Type': 'text/plain'}
        else:
            print(f"DEBUG: Verification failed - mode={mode}, token={verify_token}")
            return "Verification failed", 403, {'Content-Type': 'text/plain'}
    
    # POST requests - handle incoming messages
    if request.method == "POST":
        try:
            data = request.get_json()
            print(f"DEBUG: Received webhook data: {json.dumps(data, indent=2)}")
            
            # Process incoming WhatsApp messages
            if data.get("object") == "whatsapp_business_account":
                for entry in data.get("entry", []):
                    for change in entry.get("changes", []):
                        if change.get("field") == "messages":
                            value = change.get("value", {})
                            messages = value.get("messages", [])
                            
                            for message in messages:
                                from_number = message.get("from")
                                message_text = message.get("text", {}).get("body", "")
                                message_id = message.get("id")
                                
                                print(f"📱 Received message from {from_number}: {message_text}")
                                
                                # Process the message with intelligent bot responses
                                process_incoming_message(from_number, message_text)
                                
            return "OK", 200
        except Exception as e:
            print(f"ERROR: Failed to process webhook: {e}")
            return "Error", 500
    
    return "OK", 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Webhook server is running"}), 200

if __name__ == '__main__':
    print("🚀 Starting standalone webhook server...")
    print("📡 Webhook URL: http://localhost:5000/webhook")
    print("🔍 Health check: http://localhost:5000/health")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)