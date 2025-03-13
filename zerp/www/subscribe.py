import frappe
from frappe import _
import stripe
import json

no_cache = 1

def get_context(context):
    # Get Stripe settings
    settings = frappe.get_single("Zerp Settings")
    context.stripe_publishable_key = settings.stripe_publishable_key
    stripe.api_key = settings.stripe_secret_key
    
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
def create_subscription(plan, subdomain, payment_method_id):
    """Create a subscription with trial period"""
    try:
        # Get Stripe settings
        settings = frappe.get_single("Zerp Settings")
        stripe.api_key = settings.stripe_secret_key

        # Validate inputs
        if not plan:
            return {"success": False, "message": "Plan is required"}
        if not subdomain:
            return {"success": False, "message": "Subdomain is required"}
        if not payment_method_id:
            return {"success": False, "message": "Payment method is required"}
        
        # Check if subdomain already exists
        existing = frappe.db.exists("Subscription", {"sub_domain": subdomain})
        if existing:
            return {"success": False, "message": "This subdomain is already taken. Please choose another one."}
        
        # Get plan details
        plan_doc = frappe.get_doc("Subscription Plan", plan)
        if not plan_doc:
            return {"success": False, "message": "Invalid plan selected"}
            
        if not plan_doc.stripe_price_id:
            return {"success": False, "message": "Plan not properly configured"}
        
        try:
            # Create or get customer from existing subscriptions
            customer_id = frappe.db.get_value(
                "Subscription",
                {
                    "user": frappe.session.user,
                    "stripe_customer_id": ("!=", "")
                },
                "stripe_customer_id"
            )
            
            if not customer_id:
                # Create new customer
                customer = stripe.Customer.create(
                    email=frappe.session.user,
                    payment_method=payment_method_id,
                    invoice_settings={
                        'default_payment_method': payment_method_id
                    }
                )
                customer_id = customer.id
                
                # Save customer ID to user
                frappe.db.set_value("User", frappe.session.user, "stripe_customer_id", customer_id)
                frappe.db.commit()

            # Attach payment method to customer if not already attached
            try:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer_id,
                )
            except stripe.error.InvalidRequestError as e:
                if "already been attached" not in str(e):
                    raise

            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': plan_doc.stripe_price_id}],
                trial_period_days=14,  # 14 days trial
                payment_behavior='default_incomplete',
                payment_settings={'payment_method_types': ['card']},
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'subdomain': subdomain,
                    'plan': plan,
                    'user': frappe.session.user
                }
            )
            
            # Create subscription record
            doc = frappe.get_doc({
                "doctype": "Subscription",
                "user": frappe.session.user,
                "sub_domain": subdomain,
                "subscription_type": "Trial",
                "plan": plan,
                "start_date": frappe.utils.today(),
                "status": "Active",
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription.id,
                "trial_end_date": frappe.utils.add_days(None, 14),  # 14 days from now
                "next_billing_date": frappe.utils.add_days(None, 14)  # Same as trial end
            })
            
            doc.insert(ignore_permissions=True)
            
            # Trigger site creation
            frappe.enqueue(
                "zerp.zerp.site_creation.create_new_site",
                subscription=doc.name,
                now=True
            )
            
            return {
                "success": True,
                "message": _("Subscription created successfully! Your site is being created."),
                "subscription": doc.name,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None
            }
            
        except stripe.error.StripeError as e:
            frappe.log_error(message=f"Stripe error: {str(e)}", title="Stripe Subscription Error")
            return {"success": False, "message": str(e)}
            
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Subscription Creation Failed"))
        return {
            "success": False,
            "message": str(e)
        }