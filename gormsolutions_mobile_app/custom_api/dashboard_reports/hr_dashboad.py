import frappe
from frappe.utils import flt, nowdate, add_months

def compute_traffic_light(actual, target):
    ratio = flt(actual) / flt(target) if target else 0
    if ratio >= 0.9:
        return "Green"
    elif ratio >= 0.7:
        return "Amber"
    else:
        return "Red"

@frappe.whitelist()
def get_headcount(company, department=None, as_of_date=None, target_headcount=None):
    """
    Returns current headcount per department with optional RAG status
    """
    if not as_of_date:
        as_of_date = nowdate()

    filters = {"company": company, "as_of_date": as_of_date}
    dept_condition = f"AND department = %(department)s" if department else ""

    if department:
        filters["department"] = department

    data = frappe.db.sql(f"""
        SELECT 
            COALESCE(department, 'Unassigned') AS department,
            COUNT(name) AS headcount
        FROM `tabEmployee`
        WHERE company=%(company)s
          AND status='Active'
          {dept_condition}
        GROUP BY department
    """, filters, as_dict=True)

    for row in data:
        row['metric'] = "Headcount"
        row['actual'] = row.pop('headcount')
        row['target'] = target_headcount or 0
        row['status'] = compute_traffic_light(row['actual'], row['target'])

    return data



@frappe.whitelist()
def get_attrition_rate(company, from_date=None, to_date=None, department=None):
    """
    Calculates attrition rate = (Exits / Average Headcount) * 100
    """
    if not to_date:
        to_date = nowdate()
    if not from_date:
        from_date = add_months(to_date, -12)  # default last 12 months

    filters = {"company": company, "from_date": from_date, "to_date": to_date}
    dept_condition = f"AND department = %(department)s" if department else ""
    if department: filters["department"] = department

    # Exits
    exits = frappe.db.sql(f"""
        SELECT COUNT(name) AS exits
        FROM `tabEmployee`
        WHERE company=%(company)s
          AND relieving_date BETWEEN %(from_date)s AND %(to_date)s
          AND status='Left'
          {dept_condition}
    """, filters, as_dict=True)
    exits_count = flt(exits[0].exits) if exits else 0

    # Average Headcount
    headcount_start = frappe.db.sql(f"""
        SELECT COUNT(name) AS headcount
        FROM `tabEmployee`
        WHERE company=%(company)s
          AND date_of_joining <= %(from_date)s
          AND status='Active'
          {dept_condition}
    """, filters, as_dict=True)
    headcount_end = frappe.db.sql(f"""
        SELECT COUNT(name) AS headcount
        FROM `tabEmployee`
        WHERE company=%(company)s
          AND date_of_joining <= %(to_date)s
          AND status='Active'
          {dept_condition}
    """, filters, as_dict=True)

    avg_headcount = (flt(headcount_start[0].headcount) + flt(headcount_end[0].headcount)) / 2 if headcount_start and headcount_end else 1

    attrition_rate = round((exits_count / avg_headcount) * 100, 2)

    return {
        "metric": "Attrition Rate (%)",
        "department": department or "All",
        "actual": attrition_rate,
        "target": 10,  # typical HR benchmark
        "status": compute_traffic_light(10 - attrition_rate, 10)  # green if lower attrition
    }

import frappe

@frappe.whitelist()
def get_recruitment_pipeline(job_opening=None, from_date=None, to_date=None):

    conditions = []
    values = {}

    # Filter by job opening
    if job_opening:
        conditions.append("job_title = %(job_opening)s")
        values["job_opening"] = job_opening

    # Filter by start date
    if from_date:
        conditions.append("DATE(creation) >= %(from_date)s")
        values["from_date"] = from_date

    # Filter by end date
    if to_date:
        conditions.append("DATE(creation) <= %(to_date)s")
        values["to_date"] = to_date

    # Build WHERE clause
    condition_sql = ""
    if conditions:
        condition_sql = "WHERE " + " AND ".join(conditions)

    # Query recruitment pipeline
    data = frappe.db.sql(f"""
        SELECT
            COALESCE(status, 'Unknown') AS stage,
            COUNT(name) AS candidates
        FROM `tabJob Applicant`
        {condition_sql}
        GROUP BY status
        ORDER BY candidates DESC
    """, values, as_dict=True)

    total_candidates = sum(d["candidates"] for d in data)

    return {
        "pipeline": data,
        "total_candidates": total_candidates
    }

import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_employee_performance(company, department=None):
    """
    Returns average performance score per department
    using total_score from Employee Performance Feedback
    """

    filters = {"company": company}
    dept_condition = f"AND department = %(department)s" if department else ""
    if department:
        filters["department"] = department

    perf = frappe.db.sql(f"""
        SELECT
            COALESCE(department,'Unassigned') AS department,
            AVG(total_score) AS avg_score
        FROM `tabEmployee Performance Feedback`
        WHERE company=%(company)s
        {dept_condition}
        GROUP BY department
    """, filters, as_dict=True)

    for row in perf:
        row["metric"] = "Performance Score"
        row["actual"] = round(flt(row.pop("avg_score")), 2)
        row["target"] = 5  # assuming max 5 scale
        row["status"] = compute_traffic_light(row["actual"], row["target"])

    return perf


import frappe
from frappe.utils import flt, nowdate, add_months

@frappe.whitelist()
def get_payroll_budget_vs_actual(company, from_date=None, to_date=None, department=None, cost_center=None):
    """
    Returns payroll actual vs budget per cost center
    """

    if not to_date:
        to_date = nowdate()
    if not from_date:
        from_date = add_months(to_date, -1)

    filters = {
        "company": company,
        "from_date": from_date,
        "to_date": to_date
    }

    # Optional filters
    dept_condition = f"AND department=%(department)s" if department else ""
    cost_center_condition = f"AND cost_center=%(cost_center)s" if cost_center else ""

    if department:
        filters["department"] = department
    if cost_center:
        filters["cost_center"] = cost_center

    # --- Actual Payroll from Salary Slips ---
    actual = frappe.db.sql(f"""
        SELECT cost_center,
               SUM(total) AS actual
        FROM `tabSalary Slip`
        WHERE company=%(company)s
          AND start_date BETWEEN %(from_date)s AND %(to_date)s
          {dept_condition}
          {cost_center_condition}
          AND docstatus=1
        GROUP BY cost_center
        ORDER BY cost_center
    """, filters, as_dict=True)

    # --- Budgeted Payroll from GL Entries (Salary Accounts) ---
    budget = frappe.db.sql(f"""
        SELECT gle.cost_center,
               SUM(gle.debit - gle.credit) AS budget
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.company=%(company)s
          AND acc.root_type='Expense'
          AND acc.account_type='Expense'
          AND acc.account_name LIKE 'Salary%'
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          {dept_condition}
          {cost_center_condition}
          AND gle.is_cancelled=0
        GROUP BY gle.cost_center
        ORDER BY gle.cost_center
    """, filters, as_dict=True)

    # Merge actual and budget per cost center
    result = {}
    for row in actual:
        key = row["cost_center"] or "Unassigned"
        result[key] = {"cost_center": key, "actual": flt(row["actual"]), "target": 0}

    for row in budget:
        key = row["cost_center"] or "Unassigned"
        if key in result:
            result[key]["target"] = flt(row["budget"])
        else:
            result[key] = {"cost_center": key, "actual": 0, "target": flt(row["budget"])}

    # Add traffic light status
    for row in result.values():
        row["metric"] = "Payroll"
        row["status"] = compute_traffic_light(row["actual"], row["target"])

    # Return as list
    return list(result.values())

@frappe.whitelist()
def get_newhire_exit_trend(company, from_date=None, to_date=None):
    if not to_date: to_date = nowdate()
    if not from_date: from_date = add_months(to_date, -12)

    filters = {"company": company, "from_date": from_date, "to_date": to_date}

    hires = frappe.db.sql(f"""
        SELECT DATE_FORMAT(date_of_joining,'%%Y-%%m') AS month, COUNT(name) AS hires
        FROM `tabEmployee`
        WHERE company=%(company)s
          AND date_of_joining BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY month
        ORDER BY month ASC
    """, filters, as_dict=True)

    exits = frappe.db.sql(f"""
        SELECT DATE_FORMAT(relieving_date,'%%Y-%%m') AS month, COUNT(name) AS exits
        FROM `tabEmployee`
        WHERE company=%(company)s
          AND relieving_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY month
        ORDER BY month ASC
    """, filters, as_dict=True)

    return {"hires": hires, "exits": exits}