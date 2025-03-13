import frappe
from frappe import _
import stripe
import json
from frappe.utils import now_datetime, add_days, get_url

def handle_webhook(request):
    """Handle Stripe webhook events"""
    try:
        event = stripe.Event.construct_from(
            json.loads(request.data), stripe.api_key
        )
        
        # Handle different event types
        if event.type == 'customer.subscription.created':
            handle_subscription_created(event.data.object)
        elif event.type == 'customer.subscription.updated':
            handle_subscription_updated(event.data.object)
        elif event.type == 'customer.subscription.deleted':
            handle_subscription_deleted(event.data.object)
        elif event.type == 'invoice.paid':
            handle_invoice_paid(event.data.object)
        elif event.type == 'invoice.payment_failed':
            handle_payment_failed(event.data.object)
            
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(
            message=f"Webhook handling failed: {str(e)}\n{frappe.get_traceback()}",
            title="Stripe Webhook Error"
        )
        return {"success": False, "message": str(e)}

def handle_subscription_created(subscription):
    """Handle new subscription creation"""
    try:
        # Get subscription doc
        sub_name = frappe.get_value(
            "Subscription",
            {"stripe_subscription_id": subscription.id},
            "name"
        )
        
        if not sub_name:
            return
            
        sub_doc = frappe.get_doc("Subscription", sub_name)
        
        # Update subscription details
        sub_doc.trial_end_date = add_days(now_datetime(), subscription.trial_end) if subscription.trial_end else None
        sub_doc.next_billing_date = add_days(now_datetime(), subscription.current_period_end)
        sub_doc.status = "Active"
        
        sub_doc.save()
        
        # Trigger site creation if not already created
        if not sub_doc.is_site_created:
            frappe.enqueue(
                "zerp.zerp.site_creation.create_new_site",
                subscription=sub_doc.name,
                now=True
            )
            
    except Exception as e:
        frappe.log_error(
            message=f"Error handling subscription created: {str(e)}",
            title="Subscription Creation Error"
        )

def handle_subscription_updated(subscription):
    """Handle subscription updates"""
    try:
        sub_name = frappe.get_value(
            "Subscription",
            {"stripe_subscription_id": subscription.id},
            "name"
        )
        
        if not sub_name:
            return
            
        sub_doc = frappe.get_doc("Subscription", sub_name)
        
        # Update subscription status
        status_map = {
            'trialing': 'Active',
            'active': 'Active',
            'past_due': 'Past Due',
            'canceled': 'Cancelled',
            'unpaid': 'Past Due'
        }
        
        sub_doc.status = status_map.get(subscription.status, sub_doc.status)
        sub_doc.next_billing_date = add_days(now_datetime(), subscription.current_period_end)
        
        if subscription.trial_end:
            sub_doc.trial_end_date = add_days(now_datetime(), subscription.trial_end)
            
        sub_doc.save()
        
    except Exception as e:
        frappe.log_error(
            message=f"Error handling subscription update: {str(e)}",
            title="Subscription Update Error"
        )

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    try:
        sub_name = frappe.get_value(
            "Subscription",
            {"stripe_subscription_id": subscription.id},
            "name"
        )
        
        if not sub_name:
            return
            
        sub_doc = frappe.get_doc("Subscription", sub_name)
        sub_doc.status = "Cancelled"
        sub_doc.save()
        
    except Exception as e:
        frappe.log_error(
            message=f"Error handling subscription deletion: {str(e)}",
            title="Subscription Deletion Error"
        )

def handle_invoice_paid(invoice):
    """Handle successful payment"""
    try:
        if not invoice.subscription:
            return
            
        sub_name = frappe.get_value(
            "Subscription",
            {"stripe_subscription_id": invoice.subscription},
            "name"
        )
        
        if not sub_name:
            return
            
        sub_doc = frappe.get_doc("Subscription", sub_name)
        
        # Add payment record
        sub_doc.add_comment(
            "Comment",
            f"Payment received: ${invoice.amount_paid/100:.2f} - Invoice ID: {invoice.id}"
        )
        
        sub_doc.payment_status = "Paid"
        sub_doc.last_payment_date = now_datetime()
        sub_doc.save()
        
    except Exception as e:
        frappe.log_error(
            message=f"Error handling invoice payment: {str(e)}",
            title="Invoice Payment Error"
        )

def handle_payment_failed(invoice):
    """Handle failed payment"""
    try:
        if not invoice.subscription:
            return
            
        sub_name = frappe.get_value(
            "Subscription",
            {"stripe_subscription_id": invoice.subscription},
            "name"
        )
        
        if not sub_name:
            return
            
        sub_doc = frappe.get_doc("Subscription", sub_name)
        
        # Add payment failure record
        sub_doc.add_comment(
            "Comment",
            f"Payment failed for amount ${invoice.amount_due/100:.2f} - Invoice ID: {invoice.id}"
        )
        
        sub_doc.payment_status = "Failed"
        sub_doc.save()
        
        # Notify user
        frappe.sendmail(
            recipients=[sub_doc.user],
            subject="Payment Failed for Your Subscription",
            message=f"""
Dear User,

The payment for your subscription has failed. Please update your payment information to avoid service interruption.

Subscription: {sub_doc.name}
Amount Due: ${invoice.amount_due/100:.2f}
Due Date: {invoice.due_date}

You can update your payment information here: {get_url()}/my_subscriptions

Best regards,
Your Service Team
"""
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Error handling payment failure: {str(e)}",
            title="Payment Failure Error"
        )