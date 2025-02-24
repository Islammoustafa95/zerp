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
                'command': ["bench", "setup", "add-domain", site_name, "--site", site_name]
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
                # Use Popen with more comprehensive error handling
                process = subprocess.Popen(
                    step['command'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,  # Add stdin to prevent potential blocking
                    universal_newlines=True,  # Use text mode for easier input/output handling
                    cwd=bench_path
                )
                
                # Attempt to read output without hanging
                try:
                    # Use communicate with timeout and input
                    stdout, stderr = process.communicate(input='\n', timeout=600)  # 10 minutes timeout
                except subprocess.TimeoutExpired:
                    # If timeout occurs, kill the process
                    process.kill()
                    stdout, stderr = process.communicate()
                    
                    # Log detailed timeout information
                    timeout_log = (
                        f"Command timed out: {step['command']}\n"
                        f"STDOUT: {stdout}\n"
                        f"STDERR: {stderr}"
                    )
                    frappe.log_error(message=timeout_log, title=f"Timeout in {step['name']}")
                    
                    # Check if process is still running and force kill
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                
                # Log command output
                step_log = (
                    f"{step['name']} Command: {' '.join(step['command'])}\n"
                    f"STDOUT: {stdout}\n"
                    f"STDERR: {stderr}\n"
                    f"Return Code: {process.returncode}"
                )
                log_messages.append(step_log)
                frappe.log_error(message=step_log, title=f"Site Creation Step: {step['name']}")
                
                # Check return code
                if process.returncode != 0:
                    # Detailed error logging
                    error_details = (
                        f"Command failed: {step['command']}\n"
                        f"Return Code: {process.returncode}\n"
                        f"STDOUT: {stdout}\n"
                        f"STDERR: {stderr}"
                    )
                    raise Exception(error_details)
            
            except Exception as step_error:
                # Comprehensive error handling
                error_log = (
                    f"Step {step['name']} failed: {str(step_error)}\n"
                    f"Command: {step['command']}"
                )
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
                
                # Log Cloudflare setup details
                log_messages.append(f"Cloudflare DNS setup result: {cloudflare_result}")
                
                # Add Cloudflare log messages to subscription comments
                for log_msg in cloudflare_result.get('log_messages', []):
                    subscription_doc.add_comment('Comment', log_msg)
            
            except Exception as cf_error:
                cf_error_log = f"Cloudflare DNS setup failed: {str(cf_error)}"
                log_messages.append(cf_error_log)
                frappe.log_error(message=cf_error_log, title="Cloudflare DNS Error")
                
                # Optionally, you can choose to continue or stop the process
                # Here, we'll continue but mark it in the logs
                subscription_doc.add_comment('Comment', cf_error_log)
        else:
            log_messages.append("Cloudflare integration is disabled or not fully configured")
        
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
    """Setup Cloudflare DNS record with extensive logging"""
    # Extensive logging setup
    log_messages = []
    
    try:
        # Validate input parameters
        if not all([subdomain, cf_settings.get('api_token'), cf_settings.get('zone_id')]):
            raise ValueError("Missing required Cloudflare configuration parameters")
        
        # Get server IP 
        settings = frappe.get_single("Zerp Settings")
        server_ip = settings.server_ip
        
        if not server_ip:
            raise ValueError("Server IP not configured in Zerp Settings")
        
        # Log initial parameters
        log_messages.append(f"Cloudflare DNS Setup Parameters:")
        log_messages.append(f"Subdomain: {subdomain}")
        log_messages.append(f"Base Domain: {cf_settings.get('base_domain')}")
        log_messages.append(f"Server IP: {server_ip}")
        
        # Prepare Cloudflare API request
        headers = {
            "Authorization": f"Bearer {cf_settings['api_token']}",
            "Content-Type": "application/json"
        }
        
        # Prepare DNS record data
        data = {
            "type": "A",
            "name": subdomain,
            "content": server_ip,
            "ttl": 1,
            "proxied": True
        }
        
        # Construct full domain for logging
        full_domain = f"{subdomain}.{cf_settings.get('base_domain')}"
        log_messages.append(f"Full Domain: {full_domain}")
        
        # Cloudflare API endpoint
        url = f"https://api.cloudflare.com/client/v4/zones/{cf_settings['zone_id']}/dns_records"
        log_messages.append(f"Cloudflare API Endpoint: {url}")
        
        # Perform API request with detailed logging
        try:
            import requests
            
            # Log request details
            log_messages.append("Sending Cloudflare DNS Record Creation Request")
            log_messages.append(f"Request Headers: {headers}")
            log_messages.append(f"Request Data: {data}")
            
            # Make the API request
            response = requests.post(url, headers=headers, json=data)
            
            # Log response details
            log_messages.append(f"Response Status Code: {response.status_code}")
            log_messages.append(f"Response Headers: {response.headers}")
            
            # Parse response
            response_data = response.json()
            log_messages.append(f"Response JSON: {response_data}")
            
            # Check for success
            if not response_data.get('success', False):
                # Log detailed error
                log_messages.append("Cloudflare API Error:")
                log_messages.append(f"Errors: {response_data.get('errors', 'No specific errors')}")
                log_messages.append(f"Messages: {response_data.get('messages', 'No messages')}")
                
                # Check for specific error conditions
                errors = response_data.get('errors', [])
                for error in errors:
                    # Check for duplicate record error
                    if error.get('code') == 81057:
                        log_messages.append("DNS record already exists. Skipping creation.")
                        return {
                            "success": True,
                            "message": "DNS record already exists",
                            "log_messages": log_messages
                        }
                
                # Raise exception for other errors
                raise Exception(f"Cloudflare DNS setup failed: {errors}")
            
            # Successful creation
            log_messages.append("Cloudflare DNS record created successfully")
            return {
                "success": True,
                "message": "DNS record created",
                "log_messages": log_messages
            }
        
        except requests.RequestException as req_error:
            # Network-level errors
            log_messages.append(f"Network Error: {str(req_error)}")
            raise
        
        except Exception as api_error:
            # Other unexpected errors
            log_messages.append(f"Unexpected Error: {str(api_error)}")
            raise
    
    except Exception as e:
        # Final catch-all error handling
        error_message = f"Cloudflare DNS Setup Failed: {str(e)}"
        log_messages.append(error_message)
        
        # Log the full error
        frappe.log_error(
            message="\n".join(log_messages),
            title="Cloudflare DNS Setup Error"
        )
        
        # Re-raise the exception
        raise Exception(error_message)

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