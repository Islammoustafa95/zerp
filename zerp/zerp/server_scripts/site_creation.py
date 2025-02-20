import frappe
import os
import subprocess
import requests
from frappe.utils import get_bench_path

def create_site(subscription_name):
    """Create a new site for the subscription"""
    try:
        # Ensure clean state
        frappe.db.rollback()
        frappe.db.commit()
        
        # Log the start with more context
        frappe.log_error(
            message=f"Starting comprehensive site creation process for {subscription_name}",
            title="Site Creation Comprehensive Start"
        )
        
        # Get subscription document with direct SQL to avoid transaction issues
        subscription_doc = frappe.db.sql("""
            SELECT name, sub_domain, plan, user
            FROM `tabSubscription`
            WHERE name = %s
        """, subscription_name, as_dict=1)
        
        if not subscription_doc:
            raise Exception(f"Subscription {subscription_name} not found in database")
            
        subscription = subscription_doc[0]
        
        # Get settings with more comprehensive checks
        settings = frappe.get_single("Zerp Settings")
        if not settings:
            raise Exception("Zerp Settings not found")
            
        # Comprehensive validation
        required_settings = [
            'mysql_root_password', 
            'base_domain', 
            'server_ip',
            'cloudflare_api_token',
            'cloudflare_zone_id'
        ]
        
        for setting in required_settings:
            if not getattr(settings, setting, None):
                raise Exception(f"{setting.replace('_', ' ').title()} not configured in Zerp Settings")
        
        # Prepare site URL
        site_name = f"{subscription.sub_domain}.{settings.base_domain}"
        
        # Get apps to install from subscription plan
        plan_apps = frappe.get_doc("Subscription Plan", subscription.plan)
        apps_to_install = [app.app_name for app in plan_apps.plan_apps]
        
        # Comprehensive site creation process
        bench_path = get_bench_path()
        
        # Detailed site creation steps
        steps = [
            {
                'name': 'New Site Creation',
                'command': [
                    "bench", "new-site", site_name,
                    "--admin-password", "admin",
                    "--mariadb-root-password", settings.mysql_root_password
                ]
            },
            *[{
                'name': f'Install App: {app}',
                'command': f"bench --site {site_name} install-app {app}"
            } for app in apps_to_install],
            {
                'name': 'Add Domain',
                'command': f"bench setup add-domain {site_name}"
            },
            {
                'name': 'Nginx Setup',
                'command': "bench setup nginx --yes"
            },
            {
                'name': 'Reload Nginx',
                'command': "sudo -n service nginx reload"
            }
        ]
        
        # Execute steps with comprehensive error tracking
        for step in steps:
            try:
                if isinstance(step['command'], list):
                    process = subprocess.Popen(
                        step['command'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=bench_path
                    )
                    stdout, stderr = process.communicate()
                else:
                    process = subprocess.Popen(
                        step['command'],
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=bench_path
                    )
                    stdout, stderr = process.communicate()
                
                # Log detailed output
                frappe.log_error(
                    message=f"{step['name']} Output:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}",
                    title=f"Site Creation Step: {step['name']}"
                )
                
                if process.returncode != 0:
                    raise Exception(f"{step['name']} failed: {stderr.decode()}")
            
            except Exception as step_error:
                frappe.log_error(
                    message=f"Step {step['name']} failed: {str(step_error)}",
                    title=f"Site Creation Step Error: {step['name']}"
                )
                raise
        
        # Cloudflare DNS setup
        try:
            setup_cloudflare_dns(
                subdomain=subscription.sub_domain, 
                cf_settings={
                    'api_token': settings.cloudflare_api_token,
                    'zone_id': settings.cloudflare_zone_id,
                    'base_domain': settings.base_domain
                }
            )
        except Exception as cf_error:
            frappe.log_error(
                message=f"Cloudflare DNS setup failed: {str(cf_error)}",
                title="Cloudflare DNS Error"
            )
        
        # Update subscription status
        subscription_doc = frappe.get_doc("Subscription", subscription_name)
        subscription_doc.is_site_created = 1
        subscription_doc.site_url = f"https://{site_name}"
        subscription_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Send email notification
        send_success_email(subscription, site_name)
        
        frappe.log_error(
            message=f"Site created successfully: {site_name}",
            title="Site Creation Success"
        )
        
        return True
    
    except Exception as e:
        # Comprehensive error logging
        frappe.log_error(
            message=f"Comprehensive site creation failed for {subscription_name}: {str(e)}\n{frappe.get_traceback()}",
            title="Comprehensive Site Creation Error"
        )
        
        # Update subscription status to reflect failure
        try:
            subscription_doc = frappe.get_doc("Subscription", subscription_name)
            subscription_doc.status = "Draft"  # Or another appropriate status
            subscription_doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as update_error:
            frappe.log_error(
                message=f"Failed to update subscription status: {str(update_error)}",
                title="Subscription Status Update Error"
            )
        
        raise

def setup_cloudflare_dns(subdomain, cf_settings):
    """Setup Cloudflare DNS record"""
    headers = {
        "Authorization": f"Bearer {cf_settings['api_token']}",
        "Content-Type": "application/json"
    }
    
    # Get server IP 
    server_ip = getattr(frappe.get_single("Zerp Settings"), 'server_ip', None)
    if not server_ip:
        raise Exception("Server IP not configured in Zerp Settings")
    
    data = {
        "type": "A",
        "name": subdomain,
        "content": server_ip,
        "ttl": 1,
        "proxied": True
    }
    
    url = f"https://api.cloudflare.com/client/v4/zones/{cf_settings['zone_id']}/dns_records"
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        
        if not response_data['success']:
            raise Exception(f"Cloudflare DNS setup failed: {response_data['errors']}")
        
        return response_data
    except Exception as e:
        frappe.log_error(
            message=f"Cloudflare API Error: {str(e)}",
            title="Cloudflare DNS Setup Error"
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