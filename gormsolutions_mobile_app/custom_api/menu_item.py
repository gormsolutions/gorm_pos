import frappe

@frappe.whitelist(allow_guest=True)
def fetch_menu_with_child_tables(limit, offset=0, search=None, category_name=None, child_stock_item=None):
    """
    Fetch Menu records along with child table data, filtering by category_name and stock_item,
    and excluding records where 'disable' is set to 1 on the parent Menu.

    Args:
        limit (int): Maximum number of records to fetch (default: 10).
        offset (int): Starting position for records (default: 0).
        search (str): Search term for parent Menu records.
        category_name (str): Filter Menu records by category_name.
        child_stock_item (str): Filter child table records by stock_item.

    Returns:
        dict: Total count and filtered Menu records with child table data.
    """
    # Validate and parse parameters
    limit = int(limit)
    offset = int(offset)

    # Build filters for the Menu doctype
    filters = {}
    if search:
        filters['name'] = ['like', f'%{search}%']
    if category_name:
        filters['category_name'] = ['like', f'%{category_name}%']
    
    # Exclude Menu records where 'disable' is set to 1
    filters['disable'] = 0  # Ensure that disable is not set to 1

    # Fetch limited Menu records based on filters
    menu_records = frappe.get_all(
        'Menu',
        fields=['category_name', 'description'],
        filters=filters,
        limit_start=offset,
        limit_page_length=limit
    )

    # Get the Meta information of the Menu doctype
    menu_meta = frappe.get_meta('Menu')

    # Identify all child table fields dynamically
    child_table_fields = [df.fieldname for df in menu_meta.fields if df.fieldtype == 'Table']

    # Create a list to hold the data with child table records
    menu_data = []

    for menu in menu_records:
        # Prepare a dictionary for each Menu with its child table data
        menu_entry = {'menu': menu}

        for child_field in child_table_fields:
            # Fetch child records for each child table dynamically
            child_table_doctype = frappe.get_meta(menu_meta.get_field(child_field).options).name

            # Apply child table filters
            filters_for_child = {'parent': menu.name}
            if child_stock_item:
                filters_for_child['stock_item'] = ['like', f'%{child_stock_item}%']

            # Fetch filtered child records
            child_records = frappe.get_all(
                child_table_doctype,
                filters=filters_for_child,
                fields=['stock_item', 'image', 'price', 'description', 'item_type', 'availability']
            )
            # Add child records under the fieldname in the dictionary
            menu_entry[child_field] = child_records

        # Append the menu entry with all its child table data
        menu_data.append(menu_entry)

    return {
        'total_count': frappe.db.count('Menu', filters=filters),
        'data': menu_data
    }
