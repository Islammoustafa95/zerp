import frappe
from frappe import _

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
        # Fetch subscription plans with only the required fields
        plans = frappe.get_all(
            "Subscription Plan",
            fields=["name", "plan_name", "plan_monthly_subscription", "plan_description"],
            order_by="plan_monthly_subscription asc"
        )
        return plans
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
        if not subdomain:
            frappe.throw(_("Subdomain is required"))
        
        # Check if subdomain already exists
        existing = frappe.db.exists("Subscription", {"sub_domain": subdomain})
        if existing:
            frappe.throw(_("This subdomain is already taken. Please choose another one."))

        # Validate plan exists
        if not plan_name:
            frappe.throw(_("Please select a subscription plan"))
        if not frappe.db.exists("Subscription Plan", plan_name):
            frappe.throw(_("Selected plan does not exist"))
        
        # Create subscription
        subscription = frappe.get_doc({
            "doctype": "Subscription",
            "user": frappe.session.user,
            "sub_domain": subdomain,
            "subscription_type": "Trial",
            "plan": plan_name,
            "start_date": frappe.utils.today(),
            "status": "Draft"
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