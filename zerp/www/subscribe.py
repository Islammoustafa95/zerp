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
    # Fetch all subscription plans
    plans = frappe.get_all(
        "Subscription Plan", 
        fields=["name", "plan_name", "plan_monthly_subscription", "plan_description"]
    )
    
    # Get apps for each plan
    plan_docs = []
    for plan in plans:
        # Fetch the full document to get child table
        plan_doc = frappe.get_doc("Subscription Plan", plan.name)
        
        # Prepare plan data
        plan_data = {
            "name": plan.name,
            "plan_name": plan.plan_name,
            "plan_monthly_subscription": plan.plan_monthly_subscription,
            "plan_description": plan.plan_description,
            "apps": []
        }
        
        # Add apps if they exist
        if hasattr(plan_doc, 'plan_apps'):
            plan_data['apps'] = [
                {"app_name": app.app_name} 
                for app in plan_doc.plan_apps
            ]
        
        plan_docs.append(plan_data)
        
    return plan_docs

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
            "start_date": frappe.utils.today(),
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