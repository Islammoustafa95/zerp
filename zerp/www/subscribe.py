import frappe
from frappe import _
import json

no_cache = 1

def get_context(context):
    context.subscription_plans = get_subscription_plans()
    context.no_cache = 1
    context.base_domain = "zaynerp.com"
    context.is_user_logged_in = frappe.session.user != 'Guest'
    
    if frappe.form_dict:
        context.subdomain = frappe.form_dict.get('subdomain', '')
        context.selected_plan = frappe.form_dict.get('plan', '')

def get_subscription_plans():
    try:
        # Fetch all subscription plans using only confirmed fields
        plans = frappe.get_all(
            "Subscription Plan", 
            fields=["name", "plan_name", "plan_monthly_subscription", "plan_description"],
            order_by="plan_monthly_subscription asc"
        )
        
        # Enrich plan data with apps
        enriched_plans = []
        for plan in plans:
            # Prepare plan data
            plan_data = {
                "name": plan.name,
                "plan_name": plan.plan_name,
                "plan_monthly_subscription": plan.plan_monthly_subscription,
                "plan_description": plan.plan_description,
                "apps": []
            }
            
            # Fetch apps separately to avoid column issues
            try:
                plan_apps = frappe.get_all(
                    "Subscription Plan App", 
                    filters={"parent": plan.name, "parenttype": "Subscription Plan"},
                    fields=["app_name"]
                )
                plan_data['apps'] = [{"app_name": app.app_name} for app in plan_apps]
            except Exception as e:
                frappe.log_error(f"Error fetching apps for plan {plan.name}: {str(e)}")
            
            enriched_plans.append(plan_data)
        
        return enriched_plans
    except Exception as e:
        frappe.log_error(f"Error in get_subscription_plans: {str(e)}")
        return []

@frappe.whitelist(allow_guest=True)
def create_subscription():
    try:
        # Check if user is logged in
        if frappe.session.user == 'Guest':
            return {
                "success": False,
                "message": _("Please login to create a subscription"),
                "requires_login": True,
                "login_url": "/login",
                "signup_url": "/login#signup"
            }
            
        # Get form data
        data = frappe.form_dict
        subdomain = data.get('subdomain', '').strip()
        plan_name = data.get('plan', '')
        
        # Validate subdomain
        subdomain = frappe.form_dict.get('subdomain', '').strip()
        if not subdomain:
            frappe.throw(_("Subdomain is required"))
        
        # Check if subdomain already exists
        existing = frappe.db.exists("Subscription", {"sub_domain": subdomain})
        if existing:
            frappe.throw(_("This subdomain is already taken. Please choose another one."))

        # Get plan details
        plan_name = frappe.form_dict.get('plan', '')
        if not plan_name:
            frappe.throw(_("Please select a subscription plan"))
        
        # Validate plan exists
        if not frappe.db.exists("Subscription Plan", plan_name):
            frappe.throw(_("Selected plan does not exist"))
        
        # Get current user
        user = frappe.session.user
        
        # Create subscription
        subscription = frappe.get_doc({
            "doctype": "Subscription",
            "user": user,
            "sub_domain": subdomain,
            "subscription_type": "Trial",
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