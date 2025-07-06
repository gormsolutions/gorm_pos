import frappe
from frappe import _
from frappe.core.doctype.sms_settings.sms_settings import send_sms  # Import SMS utility

@frappe.whitelist(allow_guest=True)
def create_otp_code(reason,tel=None):
    try:
        # Create OTP Code doc
        otp_code_doc = frappe.new_doc('OTP Code')
        otp_code_doc.tel = tel
        otp_code_doc.date = frappe.utils.nowdate()  # Set the current date
        otp_code_doc.active = 1  # Set the OTP code as active
        otp_code_doc.reason = reason
        otp_code_doc.senders_email = frappe.session.user  # Set the sender's email to the current user
        otp_code_doc.senders_full_name = frappe.get_value('User', frappe.session.user, 'full_name')  # Get the full name of the user
        otp_code_doc.insert(ignore_permissions=True)
        otp_code_doc.submit()

        # Send the OTP document name via SMS
        # message = f"Your OTP code is: {otp_code_doc.name}"
        # send_sms(receiver_list=[tel], msg=message)

        return {
            "status": "success",
            "message": "OTP Code created and sent via SMS!",
            "otp_code": otp_code_doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "OTP Creation Failed")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_all_otp_codes():
    """
    Fetch and return all active OTP Code documents created today.
    """
    try:
        today = frappe.utils.nowdate()
        otp_list = frappe.get_all(
            'OTP Code',
            filters={
                'date': today,
                'active': 1
            },
            fields=['name', 'tel', 'date', 'active', 'reason', 'senders_email', 'senders_full_name'],
            order_by='creation desc'
        )
        return {
            "status": "success",
            "data": otp_list
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Fetch OTP Codes Failed")
        return {
            "status": "error",
            "message": str(e)
        }
    
import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def verify_otp_code(name, user_email, date):
    """
    Verifies if an OTP Code with matching name, user_email and date exists and is active.
    Args:
        name (str): Name of the OTP Code document.
        user_email (str): Email associated with the OTP.
        date (str): Date (YYYY-MM-DD) the OTP was issued.
    Returns:
        dict: Result status and message.
    """
    try:
        if not frappe.db.exists("OTP Code", name):
            return {
                "status": "error",
                "message": f"OTP Code '{name}' not found."
            }

        otp_doc = frappe.get_doc("OTP Code", name)

        # Validate the email, date and active status
        if (
            otp_doc.senders_email == user_email and
            str(otp_doc.date) == str(date) and
            int(otp_doc.active) == 1
        ):
            return {
                "status": "success",
                "message": "OTP Code is valid."
            }
        else:
            return {
                "status": "failed",
                "message": "OTP Code is invalid or expired."
            }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "OTP Verification Failed")
        return {
            "status": "error",
            "message": _("An unexpected error occurred during OTP verification.")
        }

import frappe
from frappe.utils import add_days, now_datetime

def deactivate_expired_otps():
    """Disable OTPs older than 24 hours (1 day)"""
    threshold_time = add_days(now_datetime(), -1)  # 24 hours ago

    expired_otps = frappe.get_all(
        "OTP Code",
        filters={
            "active": 1,
            "creation": ("<", threshold_time)
        },
        fields=["name"]
    )

    for otp in expired_otps:
        try:
            doc = frappe.get_doc("OTP Code", otp.name)
            doc.active = 0
            doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"OTP Expiry Failed for {otp.name}")
