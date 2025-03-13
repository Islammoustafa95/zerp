import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_custom_fields():
    """Setup custom fields needed by the app"""
    custom_fields = {
        "User": [
            {
                "fieldname": "stripe_customer_id",
                "label": "Stripe Customer ID",
                "fieldtype": "Data",
                "insert_after": "last_name",
                "read_only": 1,
                "translatable": 0,
                "unique": 0,
                "hidden": 1
            }
        ]
    }
    
    create_custom_fields(custom_fields)