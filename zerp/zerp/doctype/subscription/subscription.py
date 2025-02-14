# Copyright (c) 2024, Zerp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, nowdate, getdate
from zerp.zerp.server_scripts.site_creation import enqueue_site_creation

class Subscription(Document):
    def validate(self):
        self.set_dates()
        self.validate_dates()
        self.set_system_fields()
        self.validate_subdomain()
    
    def set_dates(self):
        if not self.start_date:
            self.start_date = nowdate()
        
        # Set end date based on subscription type
        if self.subscription_type == "Trial":
            self.end_date = add_days(self.start_date, 14)
        elif self.subscription_type == "Paid":
            self.end_date = add_days(self.start_date, 30)
        
        # Set renewal dates
        self.next_renewal_date = self.end_date
        if not self.last_renewal_date:
            self.last_renewal_date = self.start_date
            
        # Calculate total active days
        self.total_active_days = (getdate(self.end_date) - getdate(self.start_date)).days

    def validate_dates(self):
        if getdate(self.start_date) > getdate(self.end_date):
            frappe.throw("Start Date cannot be greater than End Date")
    
    def set_system_fields(self):
        if not self.created_by:
            self.created_by = frappe.session.user
            self.creation_date = frappe.utils.now()
        self.modified_by = frappe.session.user
        self.modified_date = frappe.utils.now()
    
    def validate_subdomain(self):
        if not self.sub_domain:
            return
            
        # Convert to lowercase and remove spaces
        self.sub_domain = self.sub_domain.lower().replace(" ", "")
        
        # Check if subdomain already exists in another active subscription
        existing = frappe.db.exists("Subscription", {
            "sub_domain": self.sub_domain,
            "name": ["!=", self.name],
            "status": ["in", ["Active", "Draft"]]
        })
        
        if existing:
            frappe.throw(f"Subdomain {self.sub_domain} is already in use")
            
    def after_insert(self):
        # Set status to Active for new subscriptions
        self.status = "Active"
        self.db_set('status', 'Active', update_modified=False)
        
        # Trigger site creation for new subscription
        if not self.is_site_created:
            enqueue_site_creation(self.name)
    
    def on_update(self):
        self.check_expiry()
    
    def check_expiry(self):
        if getdate(self.end_date) < getdate(nowdate()) and self.status == "Active":
            self.status = "Expired"
            self.save()