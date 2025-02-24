# Copyright (c) 2024, Zerp and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SubscriptionComment(Document):
    def before_save(self):
        if not self.comment_by:
            self.comment_by = frappe.session.user
        if not self.comment_date:
            self.comment_date = frappe.utils.now()