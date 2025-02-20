import frappe
from frappe import _

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
        fields=["name", "plan_name", "price", "billing_interval", "features", "maximum_users", "maximum_space"],
        filters={"enabled": 1},
        order_by="price"
    )
    return plans

@frappe.whitelist()
def create_subscription():
    try:
        # Validate subdomain
        subdomain = frappe.form_dict.subdomain
        if not subdomain:
            frappe.throw(_("Subdomain is required"))
        
        # Check if subdomain already exists
        existing = frappe.db.exists("Subscription", {"subdomain": subdomain})
        if existing:
            frappe.throw(_("This subdomain is already taken. Please choose another one."))

        # Get plan details
        plan_name = frappe.form_dict.plan
        plan = frappe.get_doc("Subscription Plan", plan_name)
        
        # Create subscription
        subscription = frappe.get_doc({
            "doctype": "Subscription",
            "subdomain": subdomain,
            "subscription_plan": plan_name,
            "status": "Pending",
            # Add other fields as needed
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