import frappe
from frappe.utils import nowdate

def get_context(context):
    # Ensure user is logged in
    if not frappe.session.user or frappe.session.user == 'Guest':
        frappe.throw("Please log in to create a subscription")
    
    # Get base domain from Zerp Settings
    settings = frappe.get_single("Zerp Settings")
    context.base_domain = settings.base_domain or 'zaynerp.com'
    
    # Get available subscription plans
    context.plans = frappe.get_list(
        "Subscription Plan", 
        fields=["name", "plan_name", "plan_description", "plan_monthly_subscription"]
    )
    
    return context

@frappe.whitelist()
def create_subscription(plan, subdomain):
    try:
        # Validate input
        if not subdomain or not plan:
            return {"status": "error", "message": "Subdomain and Plan are required"}
        
        # Check subdomain uniqueness
        existing = frappe.db.exists("Subscription", {"sub_domain": subdomain})
        if existing:
            return {"status": "error", "message": "Subdomain already in use"}
        
        # Create subscription
        subscription = frappe.get_doc({
            "doctype": "Subscription",
            "plan": plan,
            "sub_domain": subdomain,
            "user": frappe.session.user,
            "start_date": nowdate(),
            "subscription_type": "Trial",
            "status": "Draft"
        })
        
        subscription.insert(ignore_permissions=True)
        
        return {
            "status": "success", 
            "message": "Subscription created successfully",
            "name": subscription.name
        }
    
    except Exception as e:
        frappe.log_error(f"Subscription creation error: {str(e)}")
        return {"status": "error", "message": str(e)}