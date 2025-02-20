import frappe
from frappe import _
from datetime import date, timedelta

def get_context(context):
    context.subscription_plans = get_subscription_plans()
    context.no_cache = 1
    context.base_domain = "zaynerp.com"
    if frappe.form_dict:
        context.subdomain = frappe.form_dict.subdomain
        context.selected_plan = frappe.form_dict.plan

def get_subscription_plans():
    # Fetch actual subscription plans from the DocType
    plans = frappe.get_all(
        "Subscription Plan",
        fields=["name", "plan_name", "plan_monthly_subscription", "plan_description", "plan_apps"],
        order_by="plan_monthly_subscription"
    )
    
    # Get apps for each plan
    for plan in plans:
        plan_doc = frappe.get_doc("Subscription Plan", plan.name)
        plan.apps = plan_doc.plan_apps
        
    return plans

@frappe.whitelist()
def create_subscription():
    try:
        # Validate subdomain
        subdomain = frappe.form_dict.subdomain
        if not subdomain:
            frappe.throw(_("Subdomain is required"))
        
        # Check if subdomain already exists
        existing = frappe.db.exists("Subscription", {"sub_domain": subdomain})
        if existing:
            frappe.throw(_("This subdomain is already taken. Please choose another one."))

        # Get plan details
        plan_name = frappe.form_dict.plan
        if not plan_name:
            frappe.throw(_("Please select a subscription plan"))

        # Get current user
        user = frappe.session.user
        if user == 'Guest':
            frappe.throw(_("Please login to create a subscription"))
            
        # Create subscription
        subscription = frappe.get_doc({
            "doctype": "Subscription",
            "user": user,
            "sub_domain": subdomain,
            "subscription_type": "Trial",  # You can modify this based on your requirements
            "plan": plan_name,
            "start_date": date.today(),
            "status": "Draft",
            "created_by": user,
            "creation_date": frappe.utils.now(),
            "modified_by": user,
            "modified_date": frappe.utils.now()
        })
        
        subscription.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "message": _("Subscription created successfully"),
            "subscription": subscription.name
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Subscription Creation Failed"))
        return {
            "success": False,
            "message": str(e)
        }