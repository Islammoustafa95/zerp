import frappe
from frappe import _
import stripe
from .stripe_webhooks import handle_webhook

@frappe.whitelist(allow_guest=True)
def stripe_webhook():
    """Handle Stripe webhook events"""
    if frappe.request.method != "POST":
        frappe.throw(_("Invalid request method"))
        
    # Get Stripe webhook secret from settings
    settings = frappe.get_single("Zerp Settings")
    if not settings.stripe_webhook_secret:
        frappe.throw(_("Stripe webhook secret not configured"))
        
    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            frappe.request.data,
            frappe.request.headers.get('Stripe-Signature'),
            settings.stripe_webhook_secret
        )
    except ValueError as e:
        frappe.throw(_("Invalid payload"))
    except stripe.error.SignatureVerificationError as e:
        frappe.throw(_("Invalid signature"))
        
    return handle_webhook(frappe.request)