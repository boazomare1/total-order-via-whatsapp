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
WHATSAPP_TOKEN = "EAAVkO0JZA4L8BPjBjw05uJlESvq0gw0OFWMc3AL9YTRJ9atQ460vibrf1vNZCViXuEew5yvl75AZA9PQnifuiWABvlQUIG46mQyHXTFLZAQ7ISdzM96ZAB62QUjZAPqpyhyID5QPmCoSewqH6ZCCDPBvQw8QrEt7gPZCIXPK6NAjnTUHZBLimAhZC6eUiHTUxggPqrUytHujagSXudV0jAKNZBgIF52qoNZBoNzuACkD4ip6gwZDZD"
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
        if user_state["state"] == "selecting_category":
            handle_category_selection(from_phone, message_text, user_state)
        elif user_state["state"] == "selecting_item":
            handle_item_selection(from_phone, message_text, user_state)
        elif user_state["state"] == "selecting_variant":
            handle_variant_selection(from_phone, message_text, user_state)
        elif user_state["state"] == "entering_quantity":
            handle_quantity_input(from_phone, message_text, user_state)
        elif user_state["state"] == "entering_address":
            handle_address_input(from_phone, message_text, user_state)
        elif user_state["state"] == "adding_more":
            handle_add_more_selection(from_phone, message_text, user_state)
        elif user_state["state"] == "selecting_hose":
            handle_hose_selection(from_phone, message_text, user_state)
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
🔥 *Welcome to TotalEnergies LPG Service!*

*Choose a category:*

*🔥 LPG CYLINDERS*
• 1. LPG Cylinders

*🔧 LPG ACCESSORIES*
• 2. LPG Accessories

*Commands:*
• Type *"My Orders"* to view your orders
• Type *"Status [Order ID]"* to check order status
• Type *"Reorder [Order ID]"* to reorder

*Payment:* Pay on delivery to *0742356449*
    """
    
    send_whatsapp_message(from_phone, menu_text)
    
    # Set user state to selecting category (preserve existing cart if any)
    existing_cart = user_states.get(from_phone, {}).get("data", {}).get("cart", [])
    user_states[from_phone] = {"state": "selecting_category", "data": {"cart": existing_cart}}

def show_main_menu_with_cart(from_phone, user_state):
    """Show main menu while preserving existing cart"""
    cart = user_state["data"].get("cart", [])
    cart_count = len(cart)
    
    menu_text = f"""
🔥 *Welcome to TotalEnergies LPG Service!*

🛒 *Current Cart: {cart_count} item(s)*

*Choose a category:*

*🔥 LPG CYLINDERS*
• 1. LPG Cylinders

*🔧 LPG ACCESSORIES*
• 2. LPG Accessories

*Commands:*
• Type *"My Orders"* to view your orders
• Type *"Status [Order ID]"* to check order status
• Type *"Reorder [Order ID]"* to reorder

*Payment:* Pay on delivery to *0742356449*
    """
    
    send_whatsapp_message(from_phone, menu_text)
    
    # Set user state to selecting category but preserve cart
    user_state["state"] = "selecting_category"
    user_states[from_phone] = user_state

def handle_category_selection(from_phone, message_text, user_state):
    """Handle category selection"""
    if message_text == "1":
        user_state["current_category"] = "cylinder"
        show_lpg_cylinders_menu(from_phone, user_state)
    elif message_text == "2":
        user_state["current_category"] = "accessory"
        show_lpg_accessories_menu(from_phone, user_state)
    else:
        send_whatsapp_message(from_phone, "Please select 1 for LPG Cylinders or 2 for LPG Accessories")

def show_lpg_cylinders_menu(from_phone, user_state):
    """Show LPG cylinders menu"""
    menu_text = """
🔥 *LPG CYLINDERS*

• 1. 6kg LPG Cylinder - KES 1,200
• 2. 13kg LPG Cylinder - KES 2,400
• 3. 22kg LPG Cylinder - KES 3,600
• 4. 50kg LPG Cylinder - KES 7,200

*Commands:*
• Type *1-4* to select a cylinder
• Type *"Back"* to go back to main menu
    """
    send_whatsapp_message(from_phone, menu_text)
    user_state["state"] = "selecting_item"
    user_states[from_phone] = user_state

def show_lpg_accessories_menu(from_phone, user_state):
    """Show LPG accessories menu"""
    menu_text = """
🔧 *LPG ACCESSORIES*

• 1. LPG Regulator - KES 800
• 2. LPG Hose (1.5m) - KES 300
• 3. LPG Hose (3m) - KES 500
• 4. LPG Burner - KES 1,500
• 5. LPG Stove - KES 2,500
• 6. LPG Safety Kit - KES 1,200

*Commands:*
• Type *1-6* to select an accessory
• Type *"Back"* to go back to main menu
    """
    send_whatsapp_message(from_phone, menu_text)
    user_state["state"] = "selecting_item"
    user_states[from_phone] = user_state

def handle_item_selection(from_phone, message_text, user_state):
    """Handle item selection"""
    message_lower = message_text.lower().strip()
    
    # Handle back command
    if message_lower == "back":
        show_main_menu(from_phone)
        return
    
    # LPG Cylinder items
    cylinder_items = {
        "1": {"name": "6kg LPG Cylinder", "price": 1200, "variants": ["Standard"]},
        "2": {"name": "13kg LPG Cylinder", "price": 2400, "variants": ["Standard"]},
        "3": {"name": "22kg LPG Cylinder", "price": 3600, "variants": ["Standard"]},
        "4": {"name": "50kg LPG Cylinder", "price": 7200, "variants": ["Standard"]}
    }
    
    # LPG Accessory items
    accessory_items = {
        "1": {"name": "LPG Regulator", "price": 800, "variants": ["Standard"]},
        "2": {"name": "LPG Hose (1.5m)", "price": 300, "variants": ["Standard"]},
        "3": {"name": "LPG Hose (3m)", "price": 500, "variants": ["Standard"]},
        "4": {"name": "LPG Burner", "price": 1500, "variants": ["Standard"]},
        "5": {"name": "LPG Stove", "price": 2500, "variants": ["Standard"]},
        "6": {"name": "LPG Safety Kit", "price": 1200, "variants": ["Standard"]}
    }
    
    # Determine which menu we're in based on current state
    menu_items = {}
    if "cylinder" in user_state.get("current_category", ""):
        menu_items = cylinder_items
    elif "accessory" in user_state.get("current_category", ""):
        menu_items = accessory_items
    
    if message_text in menu_items:
        item = menu_items[message_text]
        
        # Store selected item for quantity input
        user_state["data"]["selected_item"] = item
        user_state["data"]["selected_variant"] = item["variants"][0]
        user_state["state"] = "entering_quantity"
        user_states[from_phone] = user_state
        
        send_whatsapp_message(from_phone, f"*{item['name']}* selected!\n\nHow many would you like? (Type a number)")
    
    else:
        send_whatsapp_message(from_phone, "Please select a valid item number or type 'back' to go back.")

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
            # Get selected item details
            selected_item = user_state["data"]["selected_item"]
            selected_variant = user_state["data"]["selected_variant"]
            
            # Initialize cart if not exists
            if "cart" not in user_state["data"]:
                user_state["data"]["cart"] = []
            
            # Check if item already exists in cart
            existing_item_index = None
            for i, cart_item in enumerate(user_state["data"]["cart"]):
                if (cart_item["name"] == selected_item["name"] and 
                    cart_item["variant"] == selected_variant):
                    existing_item_index = i
                    break
            
            if existing_item_index is not None:
                # Update existing item quantity
                existing_item = user_state["data"]["cart"][existing_item_index]
                existing_item["quantity"] += quantity
                existing_item["total"] = existing_item["price"] * existing_item["quantity"]
                
                send_whatsapp_message(from_phone, f"✅ Updated {selected_item['name']} quantity to {existing_item['quantity']}")
            else:
                # Add new item to cart
                cart_item = {
                    "name": selected_item["name"],
                    "variant": selected_variant,
                    "price": selected_item["price"],
                    "quantity": quantity,
                    "total": selected_item["price"] * quantity
                }
                user_state["data"]["cart"].append(cart_item)
                send_whatsapp_message(from_phone, f"✅ Added {selected_item['name']} to your cart!")
            
            user_states[from_phone] = user_state
            
            # Show cart and ask if they want to add more
            show_cart_and_ask_for_more(from_phone, user_state)
        else:
            send_whatsapp_message(from_phone, "Please enter a valid quantity (1 or more)")
    except ValueError:
        send_whatsapp_message(from_phone, "Please type a valid number for quantity.")

def show_cart_and_ask_for_more(from_phone, user_state):
    """Show current cart and ask if they want to add more items"""
    cart = user_state["data"]["cart"]
    total_amount = sum(item["total"] for item in cart)
    
    cart_text = f"🛒 *Your Cart ({len(cart)} items):*\n\n"
    for i, item in enumerate(cart, 1):
        cart_text += f"{i}. {item['name']} - {item['variant']}\n"
        cart_text += f"   Qty: {item['quantity']} × KES {item['price']} = KES {item['total']}\n\n"
    
    cart_text += f"💰 *Total: KES {total_amount}*\n\n"
    
    # Smart cross-selling based on what's in cart
    cross_sell_text = get_cross_sell_suggestions(cart)
    
    cart_text += f"*Would you like to add anything else?*\n\n"
    cart_text += f"{cross_sell_text}\n\n"
    cart_text += f"• Type *'Yes'* to browse all items\n"
    cart_text += f"• Type *'Hose'* to add LPG Hose (1.5m or 3m)\n"
    cart_text += f"• Type *'Regulator'* to add LPG Regulator\n"
    cart_text += f"• Type *'Safety'* to add LPG Safety Kit\n"
    cart_text += f"• Type *'Burner'* to add LPG Burner\n"
    cart_text += f"• Type *'Stove'* to add LPG Stove\n"
    cart_text += f"• Type *'No'* to proceed to checkout\n"
    cart_text += f"• Type *'Remove [number]'* to remove an item"
    
    send_whatsapp_message(from_phone, cart_text)
    user_state["state"] = "adding_more"
    user_states[from_phone] = user_state

def get_cross_sell_suggestions(cart):
    """Get smart cross-selling suggestions based on cart contents"""
    suggestions = []
    
    # Check if they have cylinders but no accessories
    has_cylinder = any("cylinder" in item["name"].lower() for item in cart)
    has_regulator = any("regulator" in item["name"].lower() for item in cart)
    has_hose = any("hose" in item["name"].lower() for item in cart)
    has_safety = any("safety" in item["name"].lower() for item in cart)
    has_burner = any("burner" in item["name"].lower() for item in cart)
    has_stove = any("stove" in item["name"].lower() for item in cart)
    
    if has_cylinder and not has_regulator:
        suggestions.append("🔧 *Recommended:* LPG Regulator (KES 800)")
    if has_cylinder and not has_hose:
        suggestions.append("🔧 *Recommended:* LPG Hose (1.5m - KES 300, 3m - KES 500)")
    if has_cylinder and not has_safety:
        suggestions.append("🔧 *Recommended:* LPG Safety Kit (KES 1,200)")
    if has_cylinder and not has_burner:
        suggestions.append("🔧 *Recommended:* LPG Burner (KES 1,500)")
    if has_cylinder and not has_stove:
        suggestions.append("🔧 *Recommended:* LPG Stove (KES 2,500)")
    
    if suggestions:
        return "💡 *Smart Suggestions:*\n" + "\n".join(suggestions)
    else:
        return "💡 *You might also like:* LPG Stove, LPG Burner, or Safety Kit"

def handle_add_more_selection(from_phone, message_text, user_state):
    """Handle add more items selection"""
    message_lower = message_text.lower().strip()
    
    if message_lower == "yes":
        # Go back to category selection but preserve cart
        show_main_menu_with_cart(from_phone, user_state)
    elif message_lower == "hose":
        # Show hose options directly
        show_hose_options(from_phone, user_state)
    elif message_lower == "regulator":
        # Add regulator directly
        add_regulator_directly(from_phone, user_state)
    elif message_lower == "safety":
        # Add safety kit directly
        add_safety_kit_directly(from_phone, user_state)
    elif message_lower == "burner":
        # Add burner directly
        add_burner_directly(from_phone, user_state)
    elif message_lower == "stove":
        # Add stove directly
        add_stove_directly(from_phone, user_state)
    elif message_lower == "no":
        # Proceed to checkout - ask for address
        user_state["state"] = "entering_address"
        user_states[from_phone] = user_state
        
        cart = user_state["data"]["cart"]
        total_amount = sum(item["total"] for item in cart)
        
        checkout_text = f"✅ *Ready to Checkout!*\n\n"
        checkout_text += f"🛒 *Final Order:*\n"
        for item in cart:
            checkout_text += f"• {item['name']} - {item['quantity']} × KES {item['price']} = KES {item['total']}\n"
        checkout_text += f"\n💰 *Total: KES {total_amount}*\n\n"
        checkout_text += f"*Please provide your delivery address:*\n"
        checkout_text += f"(Include area, street name, and any landmarks)"
        
        send_whatsapp_message(from_phone, checkout_text)
    elif message_lower.startswith("remove"):
        # Handle item removal
        try:
            parts = message_lower.split()
            if len(parts) > 1:
                item_num = int(parts[1])
                if 1 <= item_num <= len(user_state["data"]["cart"]):
                    removed_item = user_state["data"]["cart"].pop(item_num - 1)
                    send_whatsapp_message(from_phone, f"✅ Removed: {removed_item['name']}")
                    show_cart_and_ask_for_more(from_phone, user_state)
                else:
                    send_whatsapp_message(from_phone, "Invalid item number. Please try again.")
            else:
                send_whatsapp_message(from_phone, "Please specify which item to remove. Example: 'Remove 1'")
        except (ValueError, IndexError):
            send_whatsapp_message(from_phone, "Invalid format. Use 'Remove 1', 'Remove 2', etc.")
    else:
        send_whatsapp_message(from_phone, "Please type 'Yes' to add more items, 'No' to checkout, or 'Remove [number]' to remove an item.")

def show_hose_options(from_phone, user_state):
    """Show hose length options directly"""
    hose_text = """
🔧 *LPG Hose Options*

• 1. LPG Hose (1.5m) - KES 300
• 2. LPG Hose (3m) - KES 500

*Select length:*
• Type *1* for 1.5m hose
• Type *2* for 3m hose
• Type *'Back'* to go back
    """
    send_whatsapp_message(from_phone, hose_text)
    user_state["state"] = "selecting_hose"
    user_states[from_phone] = user_state

def add_regulator_directly(from_phone, user_state):
    """Add regulator directly to cart"""
    # Check if regulator already exists
    existing_item_index = None
    for i, cart_item in enumerate(user_state["data"]["cart"]):
        if cart_item["name"] == "LPG Regulator":
            existing_item_index = i
            break
    
    if existing_item_index is not None:
        # Update existing regulator quantity
        existing_item = user_state["data"]["cart"][existing_item_index]
        existing_item["quantity"] += 1
        existing_item["total"] = existing_item["price"] * existing_item["quantity"]
        send_whatsapp_message(from_phone, f"✅ Updated LPG Regulator quantity to {existing_item['quantity']}")
    else:
        # Add new regulator
        regulator_item = {
            "name": "LPG Regulator",
            "variant": "Standard",
            "price": 800,
            "quantity": 1,
            "total": 800
        }
        user_state["data"]["cart"].append(regulator_item)
        send_whatsapp_message(from_phone, "✅ Added LPG Regulator to your cart!")
    
    user_states[from_phone] = user_state
    show_cart_and_ask_for_more(from_phone, user_state)

def add_safety_kit_directly(from_phone, user_state):
    """Add safety kit directly to cart"""
    # Check if safety kit already exists
    existing_item_index = None
    for i, cart_item in enumerate(user_state["data"]["cart"]):
        if cart_item["name"] == "LPG Safety Kit":
            existing_item_index = i
            break
    
    if existing_item_index is not None:
        # Update existing safety kit quantity
        existing_item = user_state["data"]["cart"][existing_item_index]
        existing_item["quantity"] += 1
        existing_item["total"] = existing_item["price"] * existing_item["quantity"]
        send_whatsapp_message(from_phone, f"✅ Updated LPG Safety Kit quantity to {existing_item['quantity']}")
    else:
        # Add new safety kit
        safety_item = {
            "name": "LPG Safety Kit",
            "variant": "Standard",
            "price": 1200,
            "quantity": 1,
            "total": 1200
        }
        user_state["data"]["cart"].append(safety_item)
        send_whatsapp_message(from_phone, "✅ Added LPG Safety Kit to your cart!")
    
    user_states[from_phone] = user_state
    show_cart_and_ask_for_more(from_phone, user_state)

def add_burner_directly(from_phone, user_state):
    """Add burner directly to cart"""
    # Check if burner already exists
    existing_item_index = None
    for i, cart_item in enumerate(user_state["data"]["cart"]):
        if cart_item["name"] == "LPG Burner":
            existing_item_index = i
            break
    
    if existing_item_index is not None:
        # Update existing burner quantity
        existing_item = user_state["data"]["cart"][existing_item_index]
        existing_item["quantity"] += 1
        existing_item["total"] = existing_item["price"] * existing_item["quantity"]
        send_whatsapp_message(from_phone, f"✅ Updated LPG Burner quantity to {existing_item['quantity']}")
    else:
        # Add new burner
        burner_item = {
            "name": "LPG Burner",
            "variant": "Standard",
            "price": 1500,
            "quantity": 1,
            "total": 1500
        }
        user_state["data"]["cart"].append(burner_item)
        send_whatsapp_message(from_phone, "✅ Added LPG Burner to your cart!")
    
    user_states[from_phone] = user_state
    show_cart_and_ask_for_more(from_phone, user_state)

def add_stove_directly(from_phone, user_state):
    """Add stove directly to cart"""
    # Check if stove already exists
    existing_item_index = None
    for i, cart_item in enumerate(user_state["data"]["cart"]):
        if cart_item["name"] == "LPG Stove":
            existing_item_index = i
            break
    
    if existing_item_index is not None:
        # Update existing stove quantity
        existing_item = user_state["data"]["cart"][existing_item_index]
        existing_item["quantity"] += 1
        existing_item["total"] = existing_item["price"] * existing_item["quantity"]
        send_whatsapp_message(from_phone, f"✅ Updated LPG Stove quantity to {existing_item['quantity']}")
    else:
        # Add new stove
        stove_item = {
            "name": "LPG Stove",
            "variant": "Standard",
            "price": 2500,
            "quantity": 1,
            "total": 2500
        }
        user_state["data"]["cart"].append(stove_item)
        send_whatsapp_message(from_phone, "✅ Added LPG Stove to your cart!")
    
    user_states[from_phone] = user_state
    show_cart_and_ask_for_more(from_phone, user_state)

def handle_hose_selection(from_phone, message_text, user_state):
    """Handle hose length selection"""
    message_lower = message_text.lower().strip()
    
    if message_lower == "back":
        show_cart_and_ask_for_more(from_phone, user_state)
        return
    
    if message_text == "1":
        # Add/update 1.5m hose
        hose_name = "LPG Hose (1.5m)"
        hose_price = 300
        
        # Check if this hose already exists
        existing_item_index = None
        for i, cart_item in enumerate(user_state["data"]["cart"]):
            if cart_item["name"] == hose_name:
                existing_item_index = i
                break
        
        if existing_item_index is not None:
            # Update existing hose quantity
            existing_item = user_state["data"]["cart"][existing_item_index]
            existing_item["quantity"] += 1
            existing_item["total"] = existing_item["price"] * existing_item["quantity"]
            send_whatsapp_message(from_phone, f"✅ Updated {hose_name} quantity to {existing_item['quantity']}")
        else:
            # Add new hose
            hose_item = {
                "name": hose_name,
                "variant": "Standard",
                "price": hose_price,
                "quantity": 1,
                "total": hose_price
            }
            user_state["data"]["cart"].append(hose_item)
            send_whatsapp_message(from_phone, f"✅ Added {hose_name} to your cart!")
        
        user_states[from_phone] = user_state
        show_cart_and_ask_for_more(from_phone, user_state)
    elif message_text == "2":
        # Add/update 3m hose
        hose_name = "LPG Hose (3m)"
        hose_price = 500
        
        # Check if this hose already exists
        existing_item_index = None
        for i, cart_item in enumerate(user_state["data"]["cart"]):
            if cart_item["name"] == hose_name:
                existing_item_index = i
                break
        
        if existing_item_index is not None:
            # Update existing hose quantity
            existing_item = user_state["data"]["cart"][existing_item_index]
            existing_item["quantity"] += 1
            existing_item["total"] = existing_item["price"] * existing_item["quantity"]
            send_whatsapp_message(from_phone, f"✅ Updated {hose_name} quantity to {existing_item['quantity']}")
        else:
            # Add new hose
            hose_item = {
                "name": hose_name,
                "variant": "Standard",
                "price": hose_price,
                "quantity": 1,
                "total": hose_price
            }
            user_state["data"]["cart"].append(hose_item)
            send_whatsapp_message(from_phone, f"✅ Added {hose_name} to your cart!")
        
        user_states[from_phone] = user_state
        show_cart_and_ask_for_more(from_phone, user_state)
    else:
        send_whatsapp_message(from_phone, "Please select 1 for 1.5m hose, 2 for 3m hose, or 'back' to go back.")

def handle_address_input(from_phone, message_text, user_state):
    """Handle delivery address input"""
    if len(message_text.strip()) < 10:
        send_whatsapp_message(from_phone, "Please provide a complete delivery address with area and street details.")
        return
    
    user_state["data"]["delivery_address"] = message_text.strip()
    
    # Create the order with cart items
    create_complete_cart_order(from_phone, user_state)
    
    # Reset user state
    user_states[from_phone] = {"state": "idle", "data": {}}

def create_complete_cart_order(from_phone, user_state):
    """Create a complete order from cart items"""
    try:
        cart = user_state["data"]["cart"]
        delivery_address = user_state["data"]["delivery_address"]
        
        if not cart:
            send_whatsapp_message(from_phone, "Your cart is empty. Please add items first.")
            return
        
        # Calculate total
        total_amount = sum(item["total"] for item in cart)
        
        # Create order description
        order_items = []
        for item in cart:
            order_items.append(f"{item['name']} - {item['quantity']} × KES {item['price']}")
        
        order_description = " | ".join(order_items)
        
        # Create order in ERPNext
        order_id = create_erpnext_order(from_phone, order_description, 1, total_amount, total_amount, delivery_address)
        
        # Send confirmation
        confirmation_text = f"""
✅ *Order Confirmed!*

*Order Details:*
• Order ID: {order_id}
• Items: {order_description}
• Total: KES {total_amount}
• Delivery Address: {delivery_address}

*Payment Instructions:*
Pay KES {total_amount} on delivery to:
📱 *0742356449*

*Order Status:* Pending
We'll notify you when your order is being prepared!

*Commands:*
• Type *"My Orders"* to view all orders
• Type *"Status {order_id}"* to check this order
        """
        
        send_whatsapp_message(from_phone, confirmation_text)
        
    except Exception as e:
        print(f"Error creating complete cart order: {str(e)}")
        send_whatsapp_message(from_phone, "Sorry, there was an error creating your order. Please try again.")

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