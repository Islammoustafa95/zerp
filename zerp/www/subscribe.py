import frappe
from frappe import _

def get_context(context):
    context.subscription_plans = get_subscription_plans()
    context.no_cache = 1
    context.base_domain = "zaynerp.com"
    if frappe.form_dict:
        context.subdomain = frappe.form_dict.get('subdomain', '')
        context.selected_plan = frappe.form_dict.get('plan', '')

def get_subscription_plans():
    # Fetch all subscription plans using only confirmed fields
    plans = frappe.get_all(
        "Subscription Plan", 
        fields=["name", "plan_name", "plan_monthly_subscription", "plan_description"]
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
                filters={"parent": plan.name, "parenttype": "Subscription Plan", "parentfield": "plan_apps"},
                fields=["app_name"]
            )
            plan_data['apps'] = [{"app_name": app.app_name} for app in plan_apps]
        except Exception as e:
            frappe.log_error(f"Error fetching apps for plan {plan.name}: {str(e)}")
        
        enriched_plans.append(plan_data)
    
    return enriched_plans

@frappe.whitelist()
def create_subscription():
    try:
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

        # Get current user
        user = frappe.session.user
        if user == 'Guest':
            frappe.throw(_("Please login to create a subscription"))
        
        # Validate plan exists
        if not frappe.db.exists("Subscription Plan", plan_name):
            frappe.throw(_("Selected plan does not exist"))
            
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