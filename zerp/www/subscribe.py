import frappe
from frappe import _
import stripe
import json

no_cache = 1

# Initialize Stripe with the secret key
stripe.api_key = "#"

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
        return frappe.get_all(
            "Subscription Plan",
            fields=[
                "name",
                "plan_name",
                "plan_monthly_subscription",
                "plan_description"
            ],
            order_by="plan_monthly_subscription asc"
        )
    except Exception as e:
        frappe.log_error(f"Error in get_subscription_plans: {str(e)}")
        return []

@frappe.whitelist(allow_guest=True)
def check_user_login():
    """Check if the user is logged in"""
    is_logged_in = frappe.session.user != 'Guest'
    return {
        "is_logged_in": is_logged_in
    }

@frappe.whitelist()
def create_payment_intent(plan, subdomain):
    """Create a payment intent for the subscription"""
    try:
        # Validate inputs
        if not plan:
            return {"success": False, "message": "Plan is required"}
        if not subdomain:
            return {"success": False, "message": "Subdomain is required"}
        
        # Check if subdomain already exists
        existing = frappe.db.exists("Subscription", {"sub_domain": subdomain})
        if existing:
            return {"success": False, "message": "This subdomain is already taken. Please choose another one."}
        
        # Get plan details
        plan_doc = frappe.get_doc("Subscription Plan", plan)
        if not plan_doc:
            return {"success": False, "message": "Invalid plan selected"}
        
        # Calculate amount in cents (Stripe requires amount in smallest currency unit)
        amount = int(float(plan_doc.plan_monthly_subscription) * 100)
        
        # Create payment intent
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency="usd",
                payment_method_types=["card"],
                description=f"Subscription for {plan_doc.plan_name} - {subdomain}",
                metadata={
                    "plan": plan,
                    "subdomain": subdomain,
                    "user": frappe.session.user
                }
            )
            
            return {
                "success": True,
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id
            }
            
        except stripe.error.StripeError as e:
            frappe.log_error(message=f"Stripe error: {str(e)}", title="Stripe Payment Intent Error")
            return {"success": False, "message": str(e)}
            
    except Exception as e:
        frappe.log_error(message=f"Error creating payment intent: {str(e)}", title="Payment Intent Error")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def create_subscription(plan, subdomain, payment_intent_id):
    """Create a subscription after successful payment"""
    try:
        # Validate inputs
        if not plan:
            return {"success": False, "message": "Plan is required"}
        if not subdomain:
            return {"success": False, "message": "Subdomain is required"}
        if not payment_intent_id:
            return {"success": False, "message": "Payment information is required"}
        
        # Verify the payment intent
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Check payment status
            if payment_intent.status != "succeeded":
                return {"success": False, "message": f"Payment not completed. Status: {payment_intent.status}"}
            
            # Verify payment amount matches plan amount
            plan_doc = frappe.get_doc("Subscription Plan", plan)
            expected_amount = int(float(plan_doc.plan_monthly_subscription) * 100)
            
            if payment_intent.amount != expected_amount:
                frappe.log_error(
                    message=f"Payment amount mismatch: expected {expected_amount}, got {payment_intent.amount}",
                    title="Payment Amount Error"
                )
                return {"success": False, "message": "Payment amount doesn't match plan price"}
                
        except stripe.error.StripeError as e:
            frappe.log_error(message=f"Stripe error: {str(e)}", title="Stripe Payment Verification Error")
            return {"success": False, "message": f"Payment verification failed: {str(e)}"}
        
        # Check if subdomain already exists
        existing = frappe.db.exists("Subscription", {"sub_domain": subdomain})
        if existing:
            return {"success": False, "message": "This subdomain is already taken. Please choose another one."}
        
        # Get plan details
        if not frappe.db.exists("Subscription Plan", plan):
            return {"success": False, "message": "Invalid plan selected"}
        
        # Create subscription
        subscription = frappe.get_doc({
            "doctype": "Subscription",
            "user": frappe.session.user,
            "sub_domain": subdomain,
            "subscription_type": "Paid",  # Changed from Trial to Paid
            "plan": plan,
            "start_date": frappe.utils.today(),
            "status": "Draft"
        })
        
        # Add payment info as custom fields
        subscription.payment_id = payment_intent_id
        subscription.payment_status = "Paid"
        subscription.payment_amount = plan_doc.plan_monthly_subscription
        subscription.payment_date = frappe.utils.now()
        
        subscription.insert(ignore_permissions=True)
        
        # Add payment details as a comment
        payment_details = f"""
Payment processed successfully:
- Payment ID: {payment_intent_id}
- Amount: ${plan_doc.plan_monthly_subscription}
- Date: {frappe.utils.now()}
- Status: Paid
"""
        subscription.add_comment("Comment", payment_details)
        
        # Log success
        frappe.log_error(
            message=f"Subscription created successfully: {subscription.name} with payment {payment_intent_id}",
            title="Subscription Created"
        )
        
        return {
            "success": True,
            "message": _("Subscription created successfully! Your site is being created."),
            "subscription": subscription.name
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Subscription Creation Failed"))
        return {
            "success": False,
            "message": str(e)
        }