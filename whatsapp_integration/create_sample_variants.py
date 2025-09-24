#!/usr/bin/env python3
"""
Script to create sample WhatsApp Product Variants for testing
"""

import frappe

def create_variant(product_name, variant_name, variant_type, unit_price, currency, stock_quantity, is_available=1, description=""):
    """Create a product variant"""
    try:
        # Check if variant already exists
        if frappe.db.exists("WhatsApp Product Variant", variant_name):
            print(f"Variant '{variant_name}' already exists. Skipping creation.")
            return

        doc = frappe.get_doc({
            "doctype": "WhatsApp Product Variant",
            "product_name": product_name,
            "variant_name": variant_name,
            "variant_type": variant_type,
            "unit_price": unit_price,
            "currency": currency,
            "stock_quantity": stock_quantity,
            "is_available": is_available,
            "description": description
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Created variant: {variant_name} ({product_name})")
    except Exception as e:
        frappe.db.rollback()
        print(f"Error creating variant {variant_name}: {e}")

def create_sample_variants():
    """Create sample product variants"""
    frappe.set_user("Administrator")  # Ensure admin permissions
    
    print("Creating sample WhatsApp Product Variants...")
    
    # Pizza Variants
    create_variant("Pizza Margherita", "Pizza Margherita - Small", "Size", 800, "KES", 50, description="Classic Margherita, small size")
    create_variant("Pizza Margherita", "Pizza Margherita - Medium", "Size", 1200, "KES", 75, description="Classic Margherita, medium size")
    create_variant("Pizza Margherita", "Pizza Margherita - Large", "Size", 1600, "KES", 100, description="Classic Margherita, large size")
    
    create_variant("Pizza Pepperoni", "Pizza Pepperoni - Small", "Size", 900, "KES", 40, description="Spicy Pepperoni, small size")
    create_variant("Pizza Pepperoni", "Pizza Pepperoni - Medium", "Size", 1350, "KES", 60, description="Spicy Pepperoni, medium size")
    create_variant("Pizza Pepperoni", "Pizza Pepperoni - Large", "Size", 1800, "KES", 80, description="Spicy Pepperoni, large size")
    
    # Burger Variants
    create_variant("Chicken Burger", "Chicken Burger - Single", "Size", 450, "KES", 120, description="Single patty chicken burger")
    create_variant("Chicken Burger", "Chicken Burger - Double", "Size", 650, "KES", 80, description="Double patty chicken burger")
    
    create_variant("Beef Burger", "Beef Burger - Single", "Size", 500, "KES", 100, description="Single patty beef burger")
    create_variant("Beef Burger", "Beef Burger - Double", "Size", 750, "KES", 70, description="Double patty beef burger")
    
    # Drinks Variants
    create_variant("Coca Cola", "Coca Cola - Small", "Size", 80, "KES", 200, description="Refreshing Coca Cola, small")
    create_variant("Coca Cola", "Coca Cola - Medium", "Size", 120, "KES", 150, description="Refreshing Coca Cola, medium")
    create_variant("Coca Cola", "Coca Cola - Large", "Size", 150, "KES", 100, description="Refreshing Coca Cola, large")
    
    create_variant("Orange Juice", "Orange Juice - Small", "Size", 100, "KES", 90, description="Fresh orange juice, small")
    create_variant("Orange Juice", "Orange Juice - Large", "Size", 180, "KES", 60, description="Fresh orange juice, large")
    
    print("\nSample WhatsApp Product Variants creation complete.")

if __name__ == "__main__":
    # This script should be run within a Frappe bench context
    # e.g., `bench --site your_site_name console -c` then `exec(open('create_sample_variants.py').read())`
    try:
        # Assuming frappe is already initialized and connected if run via bench execute
        create_sample_variants()
    except Exception as e:
        print(f"Failed to run script: {e}")