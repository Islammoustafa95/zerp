import frappe
import os
import subprocess
import requests
from frappe.utils import get_bench_path

def create_site(subscription_name):
    """Create a new site for the subscription"""
    log_messages = []
    subscription_doc = None

    try:
        # Ensure clean state
        frappe.db.rollback()
        
        # Log the start
        start_log = f"Starting site creation process for {subscription_name}"
        log_messages.append(start_log)
        frappe.log_error(message=start_log, title="Site Creation Start")
        
        # Get subscription document
        subscription_doc = frappe.get_doc("Subscription", subscription_name)
        
        # Get settings
        settings = frappe.get_single("Zerp Settings")
        if not settings:
            raise Exception("Zerp Settings not found")
        
        # Validate required settings
        required_settings = [
            'mysql_root_password', 
            'base_domain', 
            'server_ip'
        ]
        
        for setting in required_settings:
            if not getattr(settings, setting, None):
                raise Exception(f"{setting.replace('_', ' ').title()} not configured in Zerp Settings")
        
        # Prepare site URL
        site_name = f"{subscription_doc.sub_domain}.{settings.base_domain}"
        log_messages.append(f"Site URL prepared: {site_name}")
        
        # Get apps to install from subscription plan
        plan_apps = frappe.get_doc("Subscription Plan", subscription_doc.plan)
        apps_to_install = [app.app_name for app in plan_apps.plan_apps]
        log_messages.append(f"Apps to install: {apps_to_install}")
        
        # Get bench path
        bench_path = get_bench_path()
        
        # Site creation steps
        steps = [
            {
                'name': 'New Site Creation',
                'command': [
                    "bench", "new-site", site_name,
                    "--admin-password", "admin",
                    "--mariadb-root-password", settings.mysql_root_password
                ]
            }
        ]
        
        # Add app installation steps
        for app in apps_to_install:
            steps.append({
                'name': f'Install App: {app}',
                'command': ["bench", "--site", site_name, "install-app", app]
            })
        
        # Add domain and nginx steps
        steps.extend([
            {
                'name': 'Add Domain',
                'command': ["bench", "setup", "add-domain", site_name]
            },
            {
                'name': 'Nginx Setup',
                'command': ["bench", "setup", "nginx", "--yes"]
            },
            {
                'name': 'Reload Nginx',
                'command': ["sudo", "service", "nginx", "reload"]
            }
        ])
        
        # Execute steps
        for step in steps:
            try:
                process = subprocess.Popen(
                    step['command'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=bench_path
                )
                
                # Add timeout to prevent hanging
                try:
                    stdout, stderr = process.communicate(timeout=300)  # 5 minutes timeout per step
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    raise Exception(f"Command timed out after 300 seconds")
                
                # Log step output
                step_log = f"{step['name']} Output:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
                log_messages.append(step_log)
                frappe.log_error(message=step_log, title=f"Site Creation Step: {step['name']}")
                
                if process.returncode != 0:
                    raise Exception(f"{step['name']} failed with return code {process.returncode}: {stderr.decode()}")
            
            except Exception as step_error:
                error_log = f"Step {step['name']} failed: {str(step_error)}"
                log_messages.append(error_log)
                frappe.log_error(message=error_log, title=f"Site Creation Step Error: {step['name']}")
                raise
        
        # Cloudflare DNS setup if enabled
        if getattr(settings, 'use_cloudflare', 0) and settings.cloudflare_api_token and settings.cloudflare_zone_id:
            try:
                cloudflare_result = setup_cloudflare_dns(
                    subdomain=subscription_doc.sub_domain, 
                    cf_settings={
                        'api_token': settings.cloudflare_api_token,
                        'zone_id': settings.cloudflare_zone_id,
                        'base_domain': settings.base_domain
                    }
                )
                log_messages.append(f"Cloudflare DNS setup successful: {cloudflare_result}")
            except Exception as cf_error:
                cf_error_log = f"Cloudflare DNS setup failed: {str(cf_error)}"
                log_messages.append(cf_error_log)
                frappe.log_error(message=cf_error_log, title="Cloudflare DNS Error")
                # Don't raise exception here, continue with site creation
        
        # Update subscription status
        subscription_doc.db_set('is_site_created', 1)
        subscription_doc.db_set('site_url', f"https://{site_name}")
        subscription_doc.db_set('status', 'Active')
        frappe.db.commit()
        
        # Add comments with logs
        for log_message in log_messages:
            subscription_doc.add_comment('Comment', log_message)
        
        # Send email notification
        send_success_email(subscription_doc, site_name)
        
        # Final success log
        success_log = f"Site created successfully: {site_name}"
        log_messages.append(success_log)
        frappe.log_error(message=success_log, title="Site Creation Success")
        
        return True
    
    except Exception as e:
        error_log = f"Site creation failed for {subscription_name}: {str(e)}\n{frappe.get_traceback()}"
        frappe.log_error(message=error_log, title="Site Creation Error")
        
        # Update subscription status to reflect failure
        if subscription_doc:
            subscription_doc.db_set('status', 'Draft')
            subscription_doc.add_comment('Comment', error_log)
            frappe.db.commit()
        
        raise

def setup_cloudflare_dns(subdomain, cf_settings):
    """Setup Cloudflare DNS record"""
    headers = {
        "Authorization": f"Bearer {cf_settings['api_token']}",
        "Content-Type": "application/json"
    }
    
    # Get server IP 
    settings = frappe.get_single("Zerp Settings")
    server_ip = settings.server_ip
    
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
        
        if not response_data.get('success'):
            raise Exception(f"Cloudflare DNS setup failed: {response_data.get('errors')}")
        
        return response_data
    except Exception as e:
        frappe.log_error(
            message=f"Cloudflare API Error: {str(e)}",
            title="Cloudflare DNS Setup Error"
        )
        raise

def send_success_email(subscription_doc, site_name):
    """Send success email to user"""
    try:
        frappe.sendmail(
            recipients=[subscription_doc.user],
            subject="Your Site is Ready!",
            template="new_site_created",
            args={
                "site_url": f"https://{site_name}",
                "username": "Administrator",
                "password": "admin",
                "user": subscription_doc.user
            }
        )
    except Exception as e:
        frappe.log_error(
            message=f"Failed to send email for {subscription_doc.name}: {str(e)}",
            title="Email Sending Error"
        )