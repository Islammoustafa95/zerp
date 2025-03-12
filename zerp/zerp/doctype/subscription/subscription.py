import frappe
from frappe import _
from frappe.model.document import Document
import subprocess
from frappe.utils import get_bench_path
import os

class Subscription(Document):
    @frappe.whitelist()
    def cancel_subscription(self):
        """Cancel subscription and drop the associated site"""
        try:
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