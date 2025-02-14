import frappe
import os
import subprocess
import json
import requests
from frappe.utils import get_url, now, get_datetime
from frappe.utils.password import get_decrypted_password
from frappe import _
import re

class SiteCreationError(Exception):
    pass

def validate_subdomain(subdomain):
    """Validate subdomain format"""
    if not re.match("^[a-z0-9][a-z0-9-]*[a-z0-9]$", subdomain):
        raise SiteCreationError("Invalid subdomain format. Use only lowercase letters, numbers, and hyphens.")
    if len(subdomain) < 3 or len(subdomain) > 63:
        raise SiteCreationError("Subdomain length must be between 3 and 63 characters.")

def get_cloudflare_settings():
    """Get Cloudflare settings from DocType"""
    try:
        settings = frappe.get_doc("Zerp Settings")
        return {
            "api_token": get_decrypted_password("Zerp Settings", "Zerp Settings", "cloudflare_api_token"),
            "zone_id": settings.cloudflare_zone_id,
            "base_domain": settings.base_domain
        }
    except Exception as e:
        frappe.log_error(f"Failed to get Cloudflare settings: {str(e)}", "Site Creation Error")
        raise SiteCreationError("Failed to get Cloudflare settings")

def get_mysql_password():
    """Get MySQL root password from configuration"""
    try:
        return get_decrypted_password("Zerp Settings", "Zerp Settings", "mysql_root_password")
    except Exception as e:
        frappe.log_error(f"Failed to get MySQL password: {str(e)}", "Site Creation Error")
        raise SiteCreationError("Failed to get MySQL root password")

def setup_cloudflare_dns(subdomain, cf_settings):
    """Setup Cloudflare DNS record"""
    headers = {
        "Authorization": f"Bearer {cf_settings['api_token']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "type": "A",
        "name": subdomain,
        "content": frappe.local.conf.get("server_ip"),
        "ttl": 1,
        "proxied": True
    }
    
    url = f"https://api.cloudflare.com/client/v4/zones/{cf_settings['zone_id']}/dns_records"
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Cloudflare API Error: {str(e)}", "Site Creation Error")
        raise SiteCreationError(f"Failed to setup DNS: {str(e)}")

def create_new_site(subscription):
    """Main function to create new site"""
    try:
        # Validate subdomain
        validate_subdomain(subscription.sub_domain)
        
        # Get required settings
        mysql_password = get_mysql_password()
        cf_settings = get_cloudflare_settings()
        
        # Get apps to install from subscription plan
        plan_apps = frappe.get_doc("Subscription Plan", subscription.plan)
        apps_to_install = [app.app_name for app in plan_apps.plan_apps]
        
        # Create site directory if it doesn't exist
        sites_dir = os.path.join(frappe.utils.get_bench_path(), "sites")
        if not os.path.exists(sites_dir):
            os.makedirs(sites_dir)
        
        # Prepare site creation command
        site_name = f"{subscription.sub_domain}.{cf_settings['base_domain']}"
        cmd = [
            "bench",
            "new-site",
            site_name,
            "--admin-password", "admin",
            "--mariadb-root-password", mysql_password,
            "--install-app", "zerp"
        ]
        
        # Add additional apps from plan
        for app in apps_to_install:
            cmd.extend(["--install-app", app])
        
        # Execute site creation
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=frappe.utils.get_bench_path()
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise SiteCreationError(f"Site creation failed: {stderr.decode()}")
        
        # Setup Cloudflare DNS
        setup_cloudflare_dns(subscription.sub_domain, cf_settings)
        
        # Update subscription status
        subscription.is_site_created = 1
        subscription.save()
        
        # Send email notification
        send_site_creation_email(subscription, site_name)
        
        frappe.log_error(
            message=f"Site created successfully: {site_name}",
            title="Site Creation Success"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Site creation failed for {subscription.name}: {str(e)}",
            title="Site Creation Error"
        )
        raise

def send_site_creation_email(subscription, site_name):
    """Send email notification about site creation"""
    try:
        subject = "Your Frappe Site has been created!"
        message = frappe.render_template(
            "templates/emails/site_creation.html",
            {
                "site_url": f"https://{site_name}",
                "username": "Administrator",
                "password": "admin",
                "subscription": subscription
            }
        )
        
        frappe.sendmail(
            recipients=[subscription.user],
            subject=subject,
            message=message
        )
    except Exception as e:
        frappe.log_error(f"Failed to send email notification: {str(e)}", "Email Notification Error")

@frappe.whitelist()
def enqueue_site_creation(subscription_name):
    """Enqueue site creation job"""
    if not frappe.has_permission("Subscription", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    
    subscription = frappe.get_doc("Subscription", subscription_name)
    
    if subscription.is_site_created:
        frappe.throw(_("Site already created for this subscription"))
    
    frappe.enqueue(
        "zerp.zerp.server_scripts.site_creation.create_new_site",
        queue="long",
        timeout=1500,
        subscription=subscription
    )