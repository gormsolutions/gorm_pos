# optimized_cost_center_sql.py

import frappe

@frappe.whitelist()
def get_cost_centers(company=None, limit=1000, offset=0):
    """
    Fetch active Cost Centers efficiently using SQL, optionally filtered by company.
    
    Args:
        company (str, optional): The company name to filter Cost Centers. Defaults to None.
        limit (int, optional): Number of records to fetch. Defaults to 1000.
        offset (int, optional): For pagination. Defaults to 0.
    
    Returns:
        list: List of dictionaries with 'name', 'cost_center_name', and 'company'.
    """
    conditions = ["is_group = 0", "disabled = 0"]
    values = {}

    if company:
        conditions.append("company = %(company)s")
        values["company"] = company

    condition_sql = " AND ".join(conditions)

    query = f"""
        SELECT name, cost_center_name, company
        FROM `tabCost Center`
        WHERE {condition_sql}
        ORDER BY company ASC, cost_center_name ASC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    values["limit"] = limit
    values["offset"] = offset

    cost_centers = frappe.db.sql(query, values, as_dict=True)
    return cost_centers


# Example usage for testing
if __name__ == "__main__":
    centers = get_cost_centers(limit=20)  # fetch only first 20
    for center in centers:
        print(f"{center['company']} - {center['name']} - {center['cost_center_name']}")
