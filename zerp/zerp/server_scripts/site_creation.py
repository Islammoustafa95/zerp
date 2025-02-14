import frappe
import os
import subprocess
from frappe.utils import get_bench_path

def create_site(subscription_name):
    """Create a new site for the subscription"""
    try:
        # Get subscription document
        subscription = frappe.get_doc("Subscription", subscription_name)
        
        # Get settings
        settings = frappe.get_single("Zerp Settings")
        if not settings:
            raise Exception("Zerp Settings not found")
            
        # Log the process
        frappe.log_error(
            message=f"Processing site creation for {subscription_name}",
            title="Site Creation Process"
        )
        
        # Basic validation
        if not settings.mysql_root_password:
            raise Exception("MySQL root password not configured in Zerp Settings")
            
        if not settings.base_domain:
            raise Exception("Base domain not configured in Zerp Settings")
            
        # Prepare site URL
        site_name = f"{subscription.sub_domain}.{settings.base_domain}"
        
        # Get apps to install from subscription plan
        plan = frappe.get_doc("Subscription Plan", subscription.plan)
        apps_to_install = ["zerp"]  # Always install zerp
        for app in plan.plan_apps:
            if app.app_name not in apps_to_install:
                apps_to_install.append(app.app_name)
                
        # Log apps to be installed
        frappe.log_error(
            message=f"Apps to install: {apps_to_install}",
            title="Site Creation Apps"
        )
        
        # Prepare bench command
        bench_path = get_bench_path()
        command = [
            "bench",
            "new-site",
            site_name,
            "--admin-password", "admin",
            "--mariadb-root-password", settings.mysql_root_password
        ]
        
        # Add apps to install
        for app in apps_to_install:
            command.extend(["--install-app", app])
            
        # Log the command (excluding sensitive info)
        safe_command = command.copy()
        safe_command[safe_command.index(settings.mysql_root_password)] = "****"
        frappe.log_error(
            message=f"Executing command: {' '.join(safe_command)}",
            title="Site Creation Command"
        )
        
        # Execute site creation
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=bench_path
        )
        
        stdout, stderr = process.communicate()
        
        # Log the output
        frappe.log_error(
            message=f"Command output:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}",
            title="Site Creation Output"
        )
        
        if process.returncode != 0:
            raise Exception(f"Site creation failed: {stderr.decode()}")
            
        # Update subscription status
        subscription.db_set('is_site_created', 1, update_modified=False)
        subscription.db_set('site_url', f"https://{site_name}", update_modified=False)
        
        # Send email notification
        send_success_email(subscription, site_name)
        
        frappe.log_error(
            message=f"Site created successfully: {site_name}",
            title="Site Creation Success"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Site creation failed for {subscription_name}: {str(e)}",
            title="Site Creation Error"
        )
        raise

def send_success_email(subscription, site_name):
    """Send success email to user"""
    try:
        frappe.sendmail(
            recipients=[subscription.user],
            subject="Your Site is Ready!",
            template="new_site_created",
            args={
                "site_url": f"https://{site_name}",
                "username": "Administrator",
                "password": "admin",
                "user": subscription.user
            }
        )
    except Exception as e:
        frappe.log_error(
            message=f"Failed to send email for {subscription.name}: {str(e)}",
            title="Email Sending Error"
        )