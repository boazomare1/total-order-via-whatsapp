# Copyright (c) 2024, TCL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime


class WhatsAppSession(Document):
	def before_save(self):
		# Set created_at timestamp if not set
		if not self.created_at:
			self.created_at = datetime.now()
		
		# Always update the updated_at timestamp
		self.updated_at = datetime.now()
	
	def validate(self):
		# Validate phone number format
		if self.phone_number:
			# Remove any non-digit characters for validation
			phone_digits = ''.join(filter(str.isdigit, self.phone_number))
			if len(phone_digits) < 10:
				frappe.throw("Please enter a valid phone number")
		
		# Validate quantity if set
		if self.quantity and self.quantity <= 0:
			frappe.throw("Quantity must be greater than 0")