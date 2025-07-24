import requests
import frappe

@frappe.whitelist()
def send_whatsapp_template(to):
    # Replace these values with your actual WhatsApp Cloud API details
    phone_number_id = "569673982891415"  # Replace with your Phone Number ID
    access_token = "EAAd8L5yb9MABO8FimqxcMmXIGuATKYjwPQeVfUd82FeHVTTwxOENt3MDd3LAje8g2ZC6gE457G6sgNiYpuZCwXmZBvNMt2WMpaZCziJcey20DYsxZAp2m3xCv0RkmTYpO2zYQx0nmZA968QlumY9yhL9yhQM1HEBJsBZCUz93F6K2QhWCvYT1hZBk6pZCYOqJL9upYwZDZD"  # Replace with your Access Token
    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"

    # Headers and payload for the API request
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,  # Recipient's phone number in international format (e.g., +256773091141)
        "type": "template",
        "template": {
            "name": "hello_world",  # Replace with your template name
            "language": {
                "code": "en_US"  # Language code of the template
            }
        }
    }

    # Make the API request
    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            return {"status": "success", "message": "Template message sent successfully!"}
        else:
            frappe.throw(f"Failed to send message: {response_data.get('error', {}).get('message', 'Unknown error')}")
    except Exception as e:
        frappe.throw(f"Error sending WhatsApp message: {str(e)}")
