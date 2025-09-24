// Copyright (c) 2024, TCL and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Order', {
	refresh: function(frm) {
		// Add custom buttons or actions when form loads
		if (frm.doc.order_status === 'Pending') {
			frm.add_custom_button(__('Confirm Order'), function() {
				frm.set_value('order_status', 'Confirmed');
				frm.save();
			});
		}
		
		if (frm.doc.order_status === 'Confirmed') {
			frm.add_custom_button(__('Start Preparing'), function() {
				frm.set_value('order_status', 'Preparing');
				frm.save();
			});
		}
		
		if (frm.doc.order_status === 'Preparing') {
			frm.add_custom_button(__('Out for Delivery'), function() {
				frm.set_value('order_status', 'Out for Delivery');
				frm.save();
			});
		}
		
		if (frm.doc.order_status === 'Out for Delivery') {
			frm.add_custom_button(__('Mark as Delivered'), function() {
				frm.set_value('order_status', 'Delivered');
				frm.save();
			});
		}
	},
	
	phone_number: function(frm) {
		// Format phone number as user types
		if (frm.doc.phone_number) {
			// Basic phone number formatting
			let phone = frm.doc.phone_number.replace(/\D/g, '');
			if (phone.length > 0) {
				// Format as international number if it starts with country code
				if (phone.startsWith('254')) {
					// Kenyan number format
					phone = phone.substring(0, 3) + ' ' + phone.substring(3, 6) + ' ' + phone.substring(6);
				}
				frm.set_value('phone_number', phone);
			}
		}
	},
	
	quantity: function(frm) {
		// Validate quantity
		if (frm.doc.quantity && frm.doc.quantity <= 0) {
			frappe.msgprint(__('Quantity must be greater than 0'));
			frm.set_value('quantity', 1);
		}
	}
});