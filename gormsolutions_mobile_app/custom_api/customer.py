import frappe

@frappe.whitelist(allow_guest=True)
def get_customer_details(limit,offset,search=None):
    if search:
        filters=[
        ['disabled','=','No'] ,
        ['customer_name','like','%'+search+'%']]
    else:
        filters=[
        ['disabled','=','No']]

    customer_details = frappe.db.get_list('Customer',
    filters = filters,
    fields=['name','customer_name', 'mobile_no','email_id'],
    
    start=offset,
    page_length=limit
    )

    return customer_details

# @frappe.whitelist(allow_guest=True)
# def create_customer(customer_name,mobile_no,email_id=None):

#     doc = frappe.new_doc('Customer')
#     doc.customer_name = customer_name
#     doc.mobile_no = mobile_no
#     doc.custom_customer_section = 'Gas Customer'
#     if email_id:
#         doc.email_id = email_id
#     doc.insert()

#     return doc.name

@frappe.whitelist(allow_guest=True)
def create_customer(customer_name, mobile_no, email_id=None):
    # Check if a customer with the same mobile number already exists
    existing_customer = frappe.db.exists("Customer", {"mobile_no": mobile_no})
    if existing_customer:
        frappe.throw(f"A customer with mobile number {mobile_no} already exists: {existing_customer}")

    # Create new customer
    doc = frappe.new_doc("Customer")
    doc.customer_name = customer_name
    doc.mobile_no = mobile_no
    doc.custom_customer_section = "Gas Customer"
    if email_id:
        doc.email_id = email_id

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return doc.name

@frappe.whitelist(allow_guest=True)
def get_customers_and_pricing_rules():
    # Fetch all customers
    customers = frappe.get_all('Customer', fields=['name', 'customer_group','customer_name', 'mobile_no','email_id'])

    # Prepare result
    result = []

    for customer in customers:
        # Fetch the pricing rules associated with this customer (if any)
        pricing_rules = frappe.get_all('Pricing Rule', filters={'customer': customer['name']}, fields=['name', 'rate'])

        # Initialize the customer data
        customer_info = {
            'customer': customer['name'],
            'mobile_no': customer['mobile_no'],
            'email_id': customer['email_id'],
            'customer_group': customer['customer_group'],
            'pricing_rules': []
        }

        for pricing_rule in pricing_rules:
            # Fetch the items related to this pricing rule from the Pricing Rule Item Code child table
            pricing_rule_items = frappe.get_all('Pricing Rule Item Code', filters={'parent': pricing_rule['name']}, fields=['item_code'])

            pricing_rule_info = {
                'rate': pricing_rule['rate'],  # Rate from the Pricing Rule
                'items': []
            }

            # Add items to the pricing rule info
            for item in pricing_rule_items:
                pricing_rule_info['items'].append({
                    'item_code': item['item_code']
                })

            # Add pricing rule info to customer data
            customer_info['pricing_rules'].append(pricing_rule_info)

        # Add the customer info to the result
        result.append(customer_info)

    return result

# Fetch customers and their pricing rules with items
customers_pricing_rules = get_customers_and_pricing_rules()

# Print the result
for customer_info in customers_pricing_rules:
    print(f"Customer: {customer_info['customer']}")
    print(f"Customer Group: {customer_info['customer_group']}")
    
    for pricing_rule in customer_info['pricing_rules']:
        print(f"  Pricing Rule Rate: {pricing_rule['rate']}")
