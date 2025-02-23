import frappe
import os
import subprocess
import requests
from frappe.utils import get_bench_path

def create_site(subscription_name):
    """Create a new site for the subscription"""
    try:
        frappe.db.commit()  # Commit any pending transactions
        
        # Log the start
        frappe.log_error(
            message=f"Starting site creation process for {subscription_name}",
            title="Site Creation Started"
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
        
        # Get settings
        settings = frappe.get_single("Zerp Settings")
        if not settings:
            raise Exception("Zerp Settings not found")
            
        # Basic validation
        if not settings.mysql_root_password:
            raise Exception("MySQL root password not configured in Zerp Settings")
            
        if not settings.base_domain:
            raise Exception("Base domain not configured in Zerp Settings")
        
        # Validate Cloudflare settings if Cloudflare is to be used
        use_cloudflare = getattr(settings, 'use_cloudflare', 0)
        if use_cloudflare:
            if not (getattr(settings, 'cloudflare_api_token', '') and 
                    getattr(settings, 'cloudflare_zone_id', '')):
                frappe.log_error(
                    message="Cloudflare settings incomplete",
                    title="Cloudflare Configuration Error"
                )
                use_cloudflare = 0
        
        # Prepare site URL
        site_name = f"{subscription.sub_domain}.{settings.base_domain}"
        
        # Get apps to install from subscription plan
        plan_apps = frappe.get_doc("Subscription Plan", subscription.plan)
        apps_to_install = []  # Only apps from the plan
        for app in plan_apps.plan_apps:
            apps_to_install.append(app.app_name)
                
        # Log apps to be installed
        frappe.log_error(
            message=f"Will install these apps: {apps_to_install}",
            title="Site Creation Apps"
        )
        
        # Prepare site creation command (without apps)
        bench_path = get_bench_path()
        create_site_cmd = [
            "bench",
            "new-site",
            site_name,
            "--admin-password", "admin",
            "--mariadb-root-password", settings.mysql_root_password
        ]
            
        # Log the command (excluding sensitive info)
        safe_command = create_site_cmd.copy()
        safe_command[safe_command.index(settings.mysql_root_password)] = "****"
        frappe.log_error(
            message=f"Will execute: {' '.join(safe_command)}",
            title="Site Creation Command"
        )
        
        # Execute site creation
        process = subprocess.Popen(
            create_site_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=bench_path
        )
        
        stdout, stderr = process.communicate()
        
        # Log the output
        frappe.log_error(
            message=f"Site creation output:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}",
            title="Site Creation Output"
        )
        
        if process.returncode != 0:
            raise Exception(f"Site creation failed: {stderr.decode()}")
            
        # Install apps one by one
        for app in apps_to_install:
            install_app_cmd = f"bench --site {site_name} install-app {app}"
            
            frappe.log_error(
                message=f"Installing app: {install_app_cmd}",
                title="App Installation"
            )
            
            process = subprocess.Popen(
                install_app_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=bench_path
            )
            
            stdout, stderr = process.communicate()
            
            # Log the output
            frappe.log_error(
                message=f"App {app} installation output:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}",
                title=f"App Installation: {app}"
            )
            
            if process.returncode != 0:
                raise Exception(f"Failed to install app {app}: {stderr.decode()}")
        
        # Setup Cloudflare DNS if enabled
        if use_cloudflare:
            try:
                cloudflare_response = setup_cloudflare_dns(
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
        
        # Add domain to site
        add_domain_cmd = f"bench setup add-domain {site_name}"
        process = subprocess.Popen(
            add_domain_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=bench_path
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            frappe.log_error(
                message=f"Domain addition failed: {stderr.decode()}",
                title="Domain Addition Error"
            )
        
        # Setup Nginx
        nginx_setup_cmds = [
            "bench setup nginx --yes",
            "sudo -n service nginx reload"  # Added -n flag for non-interactive
        ]
        
        for cmd in nginx_setup_cmds:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=bench_path
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                frappe.log_error(
                    message=f"Nginx setup failed for command {cmd}: {stderr.decode()}",
                    title="Nginx Setup Error"
                )
        
        # Update subscription status using frappe ORM
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
        
    except Exception as e:
        frappe.log_error(
            message=f"Site creation failed for {subscription_name}: {str(e)}",
            title="Site Creation Error"
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