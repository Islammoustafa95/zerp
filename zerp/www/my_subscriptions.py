import frappe
from frappe import _

def get_context(context):
    if frappe.session.user == 'Guest':
        frappe.throw(_("Please login to view subscriptions"), frappe.PermissionError)
    
    context.no_cache = 1
    context.base_domain = "zaynerp.com"
    context.subscriptions = get_user_subscriptions()

def get_user_subscriptions():
    # Fetch all subscriptions for the current user
    subscriptions = frappe.get_all(
        "Subscription",
        filters={
            "user": frappe.session.user
        },
        fields=[
            "name", "sub_domain", "plan", "plan_name", 
            "plan_monthly_subscription", "start_date", 
            "end_date", "status", "is_site_created", 
            "site_url"
        ],
        order_by="creation desc"
    )
    return subscriptions

@frappe.whitelist()
def cancel_subscription(subscription):
    try:
        if not subscription:
            frappe.throw(_("Subscription ID is required"))
            
        # Get the subscription document
        sub_doc = frappe.get_doc("Subscription", subscription)
        
        # Check if user owns this subscription
        if sub_doc.user != frappe.session.user:
            frappe.throw(_("You don't have permission to cancel this subscription"))
            
        # Update status to Cancelled
        sub_doc.status = "Cancelled"
        sub_doc.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": _("Subscription cancelled successfully")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Subscription Cancellation Failed"))
        return {
            "success": False,
            "message": str(e)
        }