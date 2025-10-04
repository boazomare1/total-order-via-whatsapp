# Copyright (c) 2024, TCL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime

class WhatsAppOrder(Document):
    def before_save(self):
        # Store the old status for comparison
        if self.name:  # If document exists (not new)
            try:
                old_doc = frappe.get_doc("WhatsApp Order", self.name)
                self._doc_before_save = {"order_status": old_doc.order_status}
            except:
                self._doc_before_save = None
        else:
            self._doc_before_save = None

        # Calculate total_price if unit_price and quantity are available
        if self.unit_price and self.quantity:
            self.total_price = self.unit_price * self.quantity
        else:
            self.total_price = 0

    def on_update(self):
        # Check if order status has changed and send WhatsApp notification
        if hasattr(self, '_doc_before_save') and self._doc_before_save:
            old_status = self._doc_before_save.get('order_status')
            new_status = self.order_status
            
            if old_status != new_status:
                self.send_status_notification(old_status, new_status)
    
    def send_status_notification(self, old_status, new_status):
        """Send WhatsApp notification when order status changes"""
        try:
            import requests
            
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

Order ID: {self.name}
Item: {self.item}
Quantity: {self.quantity}
Total: KES {self.total_price}

Status: {old_status} → {new_status}

{message}

*Payment:* Pay on delivery to *0742356449*
            """
            
            # Send WhatsApp message
            phone_id = frappe.conf.get("whatsapp_phone_id")
            access_token = frappe.conf.get("whatsapp_token")
            
            if phone_id and access_token and self.phone_number:
                url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "messaging_product": "whatsapp",
                    "to": self.phone_number,
                    "type": "text",
                    "text": {"body": notification_text}
                }
                
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 200:
                    frappe.logger().info(f"Status notification sent to {self.phone_number} for order {self.name}")
                else:
                    frappe.logger().error(f"Failed to send status notification: {response.text}")
            else:
                frappe.logger().error("WhatsApp credentials not configured or phone number missing")
                
        except Exception as e:
            frappe.logger().error(f"Error sending status notification: {str(e)}")

    def validate(self):
        # Validate phone number format (basic validation)
        if self.phone_number:
            # Remove any non-digit characters for validation
            phone_digits = ''.join(filter(str.isdigit, self.phone_number))
            if len(phone_digits) < 10:
                frappe.throw("Please enter a valid phone number")

        # Validate quantity
        if self.quantity and self.quantity <= 0:
            frappe.throw("Quantity must be greater than 0")

        # Validate variant_id if item_code is provided
        if self.item_code and not self.variant_id:
            frappe.throw("Please select a variant for the chosen item.")

        # Ensure unit_price is set if variant is chosen
        if self.variant_id and not self.unit_price:
            frappe.throw("Unit price must be set for the selected variant.")

    def before_insert(self):
        # Set initial order status if not provided
        if not self.order_status:
            self.order_status = "Pending"