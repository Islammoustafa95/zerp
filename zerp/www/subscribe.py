import frappe

def get_context(context):
    context.subscription_plans = get_subscription_plans()
    context.no_cache = 1

def get_subscription_plans():
    # You can customize this function to fetch plans from your database
    return [
        {
            "name": "Basic",
            "price": "$9.99/month",
            "features": [
                "Feature 1",
                "Feature 2",
                "Feature 3"
            ]
        },
        {
            "name": "Professional",
            "price": "$29.99/month",
            "features": [
                "All Basic features",
                "Pro Feature 1",
                "Pro Feature 2",
                "Pro Feature 3"
            ]
        },
        {
            "name": "Enterprise",
            "price": "$99.99/month",
            "features": [
                "All Professional features",
                "Enterprise Feature 1",
                "Enterprise Feature 2",
                "Enterprise Feature 3"
            ]
        }
    ]