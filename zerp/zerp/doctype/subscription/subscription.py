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

    def after_insert(self):
        """After the document is saved and committed, queue the site creation"""
        # Ensure we're not re-triggering site creation
        if self.is_site_created:
            return

        # Commit the current transaction to ensure document is saved
        frappe.db.commit()

        # Now queue the site creation as a background job
        frappe.enqueue(
            "zerp.zerp.server_scripts.site_creation.create_site",
            queue="long",
            timeout=1500,
            subscription_name=self.name,
            at_front=True  # Put this job at the front of the queue
        )

        # Show a message to the user
        frappe.msgprint(
            msg='Subscription saved successfully. Site creation has been queued and will be processed in the background.',
            title='Site Creation Started',
            indicator='green'
        )