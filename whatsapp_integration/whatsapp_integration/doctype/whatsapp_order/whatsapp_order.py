# Copyright (c) 2024, TCL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime

class WhatsAppOrder(Document):
    def before_save(self):
        # Set created_at timestamp if not set
        if not self.created_at:
            self.created_at = datetime.now()

        # Always update the updated_at timestamp
        self.updated_at = datetime.now()

        # Calculate total_price if unit_price and quantity are available
        if self.unit_price and self.quantity:
            self.total_price = self.unit_price * self.quantity
        else:
            self.total_price = 0

    def on_update(self):
        # You can add any logic here that should run after the document is updated
        # e.g., update stock if order status changes to 'Cancelled'
        pass

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