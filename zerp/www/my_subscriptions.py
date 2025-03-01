import frappe
from frappe import _

def get_context(context):
    if frappe.session.user == 'Guest':
        frappe.throw(_("Please login to view subscriptions"), frappe.PermissionError)
    
    context.no_cache = 1
    context.base_domain = "zaynerp.com"
    context.subscriptions = get_user_subscriptions()

def get_user_subscriptions():
    # Fetch all subscriptions for the current user
    subscriptions = frappe.get_all(
        "Subscription",
        filters={
            "user": frappe.session.user
        },
        fields=[
            "name", "sub_domain", "plan", "plan_name", 
            "plan_monthly_subscription", "start_date", 
            "end_date", "status", "is_site_created", 
            "site_url"
        ],
        order_by="creation desc"
    )
    return subscriptions

@frappe.whitelist()
def cancel_subscription(subscription):
    try:
        if not subscription:
            frappe.throw(_("Subscription ID is required"))
            
        # Get the subscription document
        sub_doc = frappe.get_doc("Subscription", subscription)
        
        # Check if user owns this subscription
        if sub_doc.user != frappe.session.user:
            frappe.throw(_("You don't have permission to cancel this subscription"))
        
        # Check if site is created
        if sub_doc.is_site_created and sub_doc.status == "Active":
            # Get MySQL root password from Zerp Settings
            settings = frappe.get_single("Zerp Settings")
            if not settings or not settings.mysql_root_password:
                frappe.throw(_("System configuration error: MySQL root password not found"))
            
            # Get base domain
            base_domain = getattr(settings, 'base_domain', "ventotech.co")
            
            # Prepare site name
            site_name = f"{sub_doc.sub_domain}.{base_domain}"
            
            # Log site deletion attempt
            frappe.log_error(message=f"Site deletion started for {site_name}", title="Site Deletion")
            
            try:
                # Import needed modules
                import subprocess
                import os
                from frappe.utils import get_bench_path
                
                # Get bench path
                bench_path = get_bench_path()
                
                # Execute bench drop-site command
                process = subprocess.Popen(
                    [
                        "bench", "drop-site", site_name,
                        "--force",
                        "--mariadb-root-password", settings.mysql_root_password
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=bench_path
                )
                
                # Wait for process to complete with timeout
                try:
                    stdout, stderr = process.communicate(timeout=300)  # 5 minutes timeout
                    
                    # Log output
                    log_output = f"Site Deletion Output for {site_name}:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
                    frappe.log_error(message=log_output, title="Site Deletion Output")
                    
                    # Check if successful
                    if process.returncode != 0:
                        error_msg = f"Site deletion failed with code {process.returncode}: {stderr.decode()}"
                        frappe.log_error(message=error_msg, title="Site Deletion Error")
                        frappe.throw(error_msg)
                    
                except subprocess.TimeoutExpired:
                    # Kill the process if it times out
                    process.kill()
                    stdout, stderr = process.communicate()
                    error_msg = f"Site deletion timed out: {stderr.decode()}"
                    frappe.log_error(message=error_msg, title="Site Deletion Timeout")
                    frappe.throw(error_msg)
                
                # Add comment about site deletion
                sub_doc.add_comment("Comment", f"Site {site_name} was deleted")
                
            except Exception as site_error:
                # Log detailed error
                frappe.log_error(
                    message=f"Error deleting site {site_name}: {str(site_error)}\n{frappe.get_traceback()}",
                    title="Site Deletion Error"
                )
                frappe.throw(f"Error deleting site: {str(site_error)}")
        
        # Update subscription status
        sub_doc.status = "Cancelled"
        sub_doc.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": _("Subscription cancelled successfully")
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Subscription Cancellation Failed"))
        return {
            "success": False,
            "message": str(e)
        }