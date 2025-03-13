import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from .setup import custom_fields

def before_install():
    """Run before app installation"""
    pass

def after_install():
    """Run after app installation"""
    custom_fields.setup()