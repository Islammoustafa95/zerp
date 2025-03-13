# Copyright (c) 2024, Zerp and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import subprocess
from frappe.utils import get_bench_path, nowdate, getdate
import os
import re

class Subscription(Document):
    def validate(self):
        if not self.sub_domain:
            frappe.throw("Subdomain is required")
        
        # Basic subdomain validation
        if not re.match("^[a-z0-9][a-z0-9-]*[a-z0-9]$", self.sub_domain):
            frappe.throw("Invalid subdomain. Use only lowercase letters, numbers, and hyphens")
            
        # Check subdomain uniqueness
        existing = frappe.db.exists("Subscription", {
            "sub_domain": self.sub_domain,
            "name": ["!=", self.name]
        })
        if existing:
            frappe.throw(f"Subdomain {self.sub_domain} is already in use")
            
        # Set default dates if not provided
        if not self.start_date:
            self.start_date = nowdate()
            
        # Ensure we have a plan
        if not self.plan:
            frappe.throw("Subscription Plan is required")

    def after_insert(self):
        """After the document is saved and committed, queue the site creation"""
        # Ensure we're not re-triggering site creation
        if self.is_site_created:
            return

        # Commit the current transaction to ensure document is saved
        frappe.db.commit()

        # Now queue the site creation as a background job
        frappe.enqueue(
            "zerp.zerp.server_scripts.site_creation.create_site",
            queue="long",
            timeout=1500,
            subscription_name=self.name,
            at_front=True  # Put this job at the front of the queue
        )

        # Show a message to the user
        frappe.msgprint(
            msg='Subscription saved successfully. Site creation has been queued and will be processed in the background.',
            title='Site Creation Started',
            indicator='green'
        )

    def onload(self):
        # Add custom button for site deletion
        if self.is_site_created and self.site_url:
            self.set_onload('show_delete_site_button', True)

    @frappe.whitelist()
    def delete_site(self):
        """Delete the site associated with this subscription"""
        try:
            frappe.flags.ignore_permissions = True
            
            if not self.is_site_created or not self.site_url:
                return {
                    "success": False,
                    "message": "No active site found"
                }

            # Get settings for MySQL and Cloudflare
            settings = frappe.get_single("Zerp Settings")
            mysql_password = settings.mysql_root_password
            cloudflare_token = settings.cloudflare_token
            zone_id = settings.cloudflare_zone_id

            # Extract site name from URL
            site_name = self.site_url.replace("https://", "").replace("http://", "")

            # Delete Cloudflare DNS record
            try:
                import requests
                headers = {
                    "Authorization": f"Bearer {cloudflare_token}",
                    "Content-Type": "application/json"
                }

                # First, get the DNS record ID
                list_records_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
                params = {"name": site_name}
                response = requests.get(list_records_url, headers=headers, params=params)
                response_data = response.json()

                if response_data["success"] and response_data["result"]:
                    # Delete each matching DNS record
                    for record in response_data["result"]:
                        record_id = record["id"]
                        delete_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
                        delete_response = requests.delete(delete_url, headers=headers)
                        
                        if not delete_response.json()["success"]:
                            frappe.log_error(
                                message=f"Failed to delete Cloudflare DNS record: {delete_response.text}",
                                title="Cloudflare DNS Deletion Error"
                            )
                            
                frappe.log_error(
                    message=f"Cloudflare DNS records deletion attempt completed for {site_name}",
                    title="Cloudflare DNS Deletion"
                )
                
            except Exception as cf_error:
                frappe.log_error(
                    message=f"Error deleting Cloudflare DNS record: {str(cf_error)}",
                    title="Cloudflare DNS Deletion Error"
                )
            
            # Get bench path and execute drop-site command
            bench_path = get_bench_path()
            process = subprocess.Popen(
                [
                    "bench", "drop-site",
                    site_name,
                    "--force",
                    "--mariadb-root-password", mysql_password
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=bench_path
            )
            
            stdout, stderr = process.communicate(timeout=300)
            
            if process.returncode == 0:
                # Update subscription status
                self.status = "Cancelled"
                self.add_comment("Comment", f"Site {site_name} and its DNS records were deleted")
                self.save(ignore_permissions=True)
                frappe.db.commit()
                
                return {
                    "success": True,
                    "message": "Site and DNS records deleted successfully"
                }
            else:
                raise Exception(f"Site deletion failed: {stderr.decode()}")
                
        except Exception as e:
            frappe.log_error(
                message=f"Site deletion failed: {str(e)}",
                title="Site Deletion Error"
            )
            return {
                "success": False,
                "message": str(e)
            }

    @frappe.whitelist()
    def cancel_subscription(self):
        """Cancel subscription and drop the associated site"""
        frappe.flags.ignore_permissions = True
        try:
            # Ensure we're running with full permissions
            if not hasattr(frappe.local, 'no_permission_check'):
                frappe.local.no_permission_check = True
            
            # Check if site is created
            if not self.is_site_created or not self.site_url:
                return {
                    "success": False,
                    "message": "No active site found for this subscription"
                }
            
            # Get settings for MySQL password
            settings = frappe.get_single("Zerp Settings")
            if not settings or not settings.mysql_root_password:
                return {
                    "success": False,
                    "message": "System configuration error: MySQL root password not found"
                }
            
            # Extract site name from URL
            site_name = self.site_url.replace("https://", "").replace("http://", "")
            
            # Log the cancellation attempt
            frappe.log_error(
                message=f"Starting site deletion for subscription {self.name}",
                title="Site Deletion Start"
            )
            
            try:
                # Get bench path
                bench_path = get_bench_path()
                
                # Execute bench drop-site command
                process = subprocess.Popen(
                    [
                        "bench", "drop-site",
                        site_name,
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
                    
                    # Log the output
                    log_message = f"""Site Deletion Output:
                    STDOUT: {stdout.decode()}
                    STDERR: {stderr.decode()}
                    Return Code: {process.returncode}
                    """
                    frappe.log_error(message=log_message, title="Site Deletion Output")
                    
                    if process.returncode != 0:
                        raise Exception(f"Site deletion failed: {stderr.decode()}")
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                    raise Exception("Site deletion timed out after 300 seconds")
                
            except Exception as e:
                frappe.log_error(
                    message=f"Error during site deletion: {str(e)}",
                    title="Site Deletion Error"
                )
                raise
            
            # Update subscription status
            self.status = "Cancelled"
            self.add_comment(
                "Comment",
                f"Subscription cancelled and site {site_name} was deleted"
            )
            self.save(ignore_permissions=True)
            
            # Commit the transaction
            frappe.db.commit()
            
            return {
                "success": True,
                "message": "Subscription cancelled successfully"
            }
            
        except Exception as e:
            frappe.log_error(
                message=f"Subscription cancellation failed: {str(e)}\n{frappe.get_traceback()}",
                title="Subscription Cancellation Error"
            )
            return {
                "success": False,
                "message": str(e)
            }