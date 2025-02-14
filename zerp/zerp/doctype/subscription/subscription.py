# Copyright (c) 2024, Zerp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate
import re

class Subscription(Document):
    def validate(self):
        if not self.sub_domain:
            frappe.throw("Subdomain is required")
        
        # Basic subdomain validation
        if not re.match("^[a-z0-9][a-z0-9-]*[a-z0-9]$", self.sub_domain):
            frappe.throw("Invalid subdomain. Use only lowercase letters, numbers, and hyphens")
            
        # Check subdomain uniqueness
        existing = frappe.db.exists("Subscription", {
            "sub_domain": self.sub_domain,
            "name": ["!=", self.name]
        })
        if existing:
            frappe.throw(f"Subdomain {self.sub_domain} is already in use")
            
        # Set default dates if not provided
        if not self.start_date:
            self.start_date = nowdate()
            
        # Ensure we have a plan
        if not self.plan:
            frappe.throw("Subscription Plan is required")
            
    def on_update(self):
        """Trigger site creation after document is saved and committed"""
        if not self.is_site_created:
            # Commit any pending changes first
            frappe.db.commit()
            
            # Now queue the site creation
            frappe.enqueue(
                "zerp.zerp.server_scripts.site_creation.create_site",
                queue="long",
                timeout=1500,
                subscription_name=self.name,
                now=True  # Run immediately
            )