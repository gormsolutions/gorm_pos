import shutil
import frappe

@frappe.whitelist()
def get_disk_usage():
    # Overall server disk usage (where this code runs)
    total, used, free = shutil.disk_usage("/")
    total_gb = round(total / (1024**3), 2)
    used_gb = round(used / (1024**3), 2)
    free_gb = round(free / (1024**3), 2)
    percent_used = round((used / total) * 100, 2)

    # MariaDB size per database via SQL (remote DB info)
    db_sizes = frappe.db.sql("""
        SELECT table_schema AS `database_name`,
               ROUND(SUM(data_length) / 1024 / 1024, 2) AS data_size_mb,
               ROUND(SUM(index_length) / 1024 / 1024, 2) AS index_size_mb,
               ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS total_size_mb
        FROM information_schema.tables
        GROUP BY table_schema
        ORDER BY total_size_mb DESC
    """, as_dict=True)

    return {
        "disk": {
            "total": total_gb,
            "used": used_gb,
            "free": free_gb,
            "percent_used": percent_used
        },
        "mariadb": db_sizes
    }
