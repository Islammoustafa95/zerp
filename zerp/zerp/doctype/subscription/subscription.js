frappe.ui.form.on('Subscription', {
    refresh: function(frm) {
        // Add cancel button only if subscription is Active and site is created
        if (frm.doc.status === 'Active' && frm.doc.is_site_created) {
            frm.add_custom_button(__('Cancel Subscription'), function() {
                // Show confirmation dialog with warning
                frappe.confirm(
                    `<div class="text-center">
                        <div class="mb-3">
                            <i class="fa fa-exclamation-triangle fa-3x text-warning"></i>
                        </div>
                        <h4>Cancel Subscription</h4>
                        <p class="text-danger"><strong>WARNING: This action cannot be undone!</strong></p>
                        <p>This will permanently delete your site and all its data.</p>
                        <p>Are you absolutely sure you want to cancel this subscription?</p>
                        <p><strong>${frm.doc.site_url}</strong></p>
                    </div>`,
                    () => {
                        // User confirmed, proceed with cancellation
                        frappe.call({
                            method: 'zerp.www.my_subscriptions.cancel_subscription',
                            args: {
                                subscription: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Cancelling subscription and dropping site...'),
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Success'),
                                        indicator: 'green',
                                        message: __('Subscription cancelled successfully')
                                    });
                                    frm.reload_doc();
                                } else {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        indicator: 'red',
                                        message: r.message.message || __('Failed to cancel subscription')
                                    });
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));
        }
    }
});