import frappe
from frappe import throw, msgprint, _

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key": 0,
            "message": "Authentication Failed"
        }
        return

    user = frappe.get_doc('User', frappe.session.user)

    # Generate a new API secret key for the user
    new_api_secret = user.custom_secret

    # Clear out the default `home_page` if present
    frappe.local.response["message"] = {
        "sid": frappe.session.sid,
        "user": user.name,
        "api_key": user.api_key,
        "api_secret": new_api_secret,
        "full_name": user.full_name  # Add full_name explicitly if you need it
    }
    
    # Ensure `home_page` is not returned (clear it if it is added automatically)
    if 'home_page' in frappe.local.response:
        del frappe.local.response['home_page']
        
    return


# signup.py
import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def sign_up(first_name, email, password):
    # Check if the email is already registered
    if frappe.db.exists("User", email):
        frappe.throw(_("Email already exists."))

    # Create a new user
    user = frappe.new_doc("User")
    user.first_name = first_name
    user.email = email
    user.username = email  # Use email as the username
    user.new_password = password  # Set the user's password
    user.role_profile_name = "portal"  # Set the user's role_profile_name
    user.enabled = 1  # Enable the user

    try:
        # Insert the new user, ignoring permissions
        user.insert(ignore_permissions=True)
        
        # Set the full name for the customer creation
        full_name = f"{first_name} {user.last_name or ''}".strip()
        
        # Check if a Customer linked to this user email already exists
        if not frappe.db.exists("Customer", {"custom_link_user_email": email}):
            # Create a new Customer document
            new_customer = frappe.get_doc({
                'doctype': 'Customer',
                'customer_name': full_name,  # Set the full name as customer name
                'customer_group': 'All Customer Groups',  # Specify a valid customer group
                'territory': 'All Territories',  # Specify a valid territory
                'custom_link_user_email': email  # Link the customer to the user email
            })
            
            new_customer.insert(ignore_permissions=True)  # Insert the customer document

        # Commit changes to the database
        frappe.db.commit()
        
    except frappe.PermissionError:
        frappe.throw(_("Insufficient permissions to create user."))

    # Optionally, send a welcome email to the user
    frappe.sendmail(
        recipients=[email],
        subject=_("Welcome to ERPNext!"),
        message=_("Thank you for signing up, {}! You can now log in using your email and password.").format(first_name)
    )

    return {
        "message": _("User created successfully.")
    }
