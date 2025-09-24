# Copyright (c) 2024, TCL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WhatsAppProductVariant(Document):
    def validate(self):
        if not self.product_name:
            frappe.throw("Product Name is required.")
        if not self.variant_name:
            frappe.throw("Variant Name is required.")
        if self.unit_price is None or self.unit_price < 0:
            frappe.throw("Unit Price must be a non-negative number.")
        if self.stock_quantity is None or self.stock_quantity < 0:
            frappe.throw("Stock Quantity must be a non-negative number.")