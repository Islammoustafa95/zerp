frappe.ui.form.on('Subscription', {
    refresh: function(frm) {
        // Add delete site button if site exists
        if (frm.doc.__onload && frm.doc.__onload.show_delete_site_button) {
            frm.add_custom_button(__('Delete Site'), function() {
                frappe.confirm(
                    'Are you sure you want to delete this site? This action cannot be undone.',
                    function() {
                        frappe.call({
                            method: 'delete_site',
                            doc: frm.doc,
                            freeze: true,
                            freeze_message: __('Deleting site...'),
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.msgprint({
                                        title: __('Success'),
                                        message: r.message.message,
                                        indicator: 'green'
                                    });
                                    frm.reload_doc();
                                } else {
                                    frappe.msgprint({
                                        title: __('Error'),
                                        message: r.message.message || 'Site deletion failed',
                                        indicator: 'red'
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