import frappe
from frappe import _

def get_context(context):
    context.subscription_plans = get_subscription_plans()
    context.no_cache = 1

def get_subscription_plans():
    # Fetch all subscription plans
    plans = frappe.get_all(
        "Subscription Plan", 
        fields=["name", "plan_name", "plan_monthly_subscription", "plan_description"],
        filters={"enabled": 1} if frappe.db.has_column("Subscription Plan", "enabled") else {}
    )
    
    # Enrich plan data with apps
    enriched_plans = []
    for plan in plans:
        # Fetch full document to get child table
        try:
            plan_doc = frappe.get_doc("Subscription Plan", plan.name)
            
            # Prepare plan data
            plan_data = {
                "name": plan.name,
                "plan_name": plan.plan_name,
                "plan_monthly_subscription": plan.plan_monthly_subscription,
                "plan_description": plan.plan_description,
                "apps": []
            }
            
            # Add apps if child table exists
            if hasattr(plan_doc, 'plan_apps'):
                plan_data['apps'] = [
                    {"app_name": app.app_name} 
                    for app in plan_doc.plan_apps 
                    if hasattr(app, 'app_name')
                ]
            
            enriched_plans.append(plan_data)
        
        except Exception as e:
            # Log any errors but continue processing other plans
            frappe.log_error(f"Error processing plan {plan.name}: {str(e)}")
    
    return enriched_plans