frappe.ready(function() {
    $('#subscription-form').on('submit', function(e) {
        e.preventDefault();
        
        // Get form values
        var plan = $('#plan').val();
        var subdomain = $('#subdomain').val();
        
        // Basic client-side validation
        if (!subdomain) {
            frappe.msgprint('Please enter a subdomain');
            return;
        }
        
        // Validate subdomain format
        var subdomainRegex = /^[a-z0-9][a-z0-9-]*[a-z0-9]$/;
        if (!subdomainRegex.test(subdomain)) {
            frappe.msgprint('Invalid subdomain. Use only lowercase letters, numbers, and hyphens.');
            return;
        }
        
        // Disable submit button to prevent multiple submissions
        var submitBtn = $(this).find('button[type="submit"]');
        submitBtn.prop('disabled', true).html('Creating...');
        
        // Call server method
        frappe.call({
            method: 'zerp.zerp.www.subscribe.subscribe.create_subscription',
            args: {
                plan: plan,
                subdomain: subdomain
            },
            callback: function(response) {
                submitBtn.prop('disabled', false).html('Create Subscription');
                
                if (response.message.status === 'success') {
                    frappe.msgprint({
                        title: 'Success',
                        message: 'Your subscription has been created. Site creation is in progress.',
                        indicator: 'green'
                    });
                    
                    // Optional: Redirect or clear form
                    $('#subdomain').val('');
                } else {
                    frappe.msgprint({
                        title: 'Error',
                        message: response.message.message,
                        indicator: 'red'
                    });
                }
            }
        });
    });
});