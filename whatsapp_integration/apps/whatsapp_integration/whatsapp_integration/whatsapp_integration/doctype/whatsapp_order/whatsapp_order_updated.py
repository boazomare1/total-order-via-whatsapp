# Copyright (c) 2025, TCL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime

class WhatsAppOrder(Document):
    def before_save(self):
        """Set timestamps before saving"""
        now = datetime.now()
        
        if not self.created_at:
            self.created_at = now
        
        self.updated_at = now
        
        # Calculate pricing if product variant is selected
        if self.product_variant:
            self.update_pricing_from_variant()
    
    def update_pricing_from_variant(self):
        """Update pricing fields from selected product variant"""
        try:
            variant_doc = frappe.get_doc("WhatsApp Product Variant", self.product_variant)
            
            # Update product details
            self.item = variant_doc.product_name
            self.variant_name = variant_doc.variant_name
            self.unit_price = variant_doc.price
            self.currency = variant_doc.currency
            
            # Calculate total price
            if self.quantity and self.unit_price:
                self.total_price = self.quantity * self.unit_price
            else:
                self.total_price = 0
                
        except frappe.DoesNotExistError:
            frappe.throw(f"Product variant '{self.product_variant}' not found")
    
    def on_update(self):
        """Called after document is updated"""
        # Update stock if order status changes
        if self.has_value_changed("order_status"):
            self.update_stock_on_status_change()
    
    def update_stock_on_status_change(self):
        """Update stock based on order status changes"""
        try:
            variant_doc = frappe.get_doc("WhatsApp Product Variant", self.product_variant)
            
            # Reduce stock when order is confirmed
            if self.order_status == "Confirmed":
                if variant_doc.stock_quantity >= self.quantity:
                    variant_doc.update_stock(-self.quantity)
                else:
                    frappe.throw(f"Insufficient stock. Available: {variant_doc.stock_quantity}")
            
            # Restore stock if order is cancelled
            elif self.order_status == "Cancelled":
                variant_doc.update_stock(self.quantity)
                
        except frappe.DoesNotExistError:
            frappe.logger().error(f"Product variant '{self.product_variant}' not found for stock update")
    
    def validate(self):
        """Validate the document"""
        # Validate phone number format (basic validation)
        if self.phone_number:
            phone_digits = ''.join(filter(str.isdigit, self.phone_number))
            if len(phone_digits) < 10:
                frappe.throw("Please enter a valid phone number")
        
        # Validate quantity
        if self.quantity and self.quantity <= 0:
            frappe.throw("Quantity must be greater than 0")
        
        # Validate product variant
        if self.product_variant:
            try:
                variant_doc = frappe.get_doc("WhatsApp Product Variant", self.product_variant)
                
                # Check if variant is available
                if not variant_doc.is_available:
                    frappe.throw(f"Product variant '{variant_doc.variant_name}' is not available")
                
                # Check stock availability
                if variant_doc.stock_quantity < self.quantity:
                    frappe.throw(f"Insufficient stock. Available: {variant_doc.stock_quantity}, Required: {self.quantity}")
                    
            except frappe.DoesNotExistError:
                frappe.throw(f"Product variant '{self.product_variant}' not found")
    
    def before_insert(self):
        """Set initial values before inserting"""
        if not self.order_status:
            self.order_status = "Pending"
        
        # Set pricing from variant if available
        if self.product_variant:
            self.update_pricing_from_variant()
    
    def get_display_name(self):
        """Get display name for the order"""
        return f"{self.item} - {self.variant_name} x {self.quantity}"
    
    def get_total_amount(self):
        """Get total amount for the order"""
        return self.total_price or 0