import frappe

def execute():
    if not frappe.db.has_column("Employee", "custom_probation_status"):
        return

    # Option B:
    # 1. Employees with final_confirmation_date -> 'Confirmed'
    frappe.db.sql("""
        UPDATE `tabEmployee`
        SET `custom_probation_status` = 'Confirmed'
        WHERE `final_confirmation_date` IS NOT NULL
    """)

    # 2. All remaining employees without status -> 'Not Confirmed'
    frappe.db.sql("""
        UPDATE `tabEmployee`
        SET `custom_probation_status` = 'Not Confirmed'
        WHERE `custom_probation_status` IS NULL OR `custom_probation_status` = ''
    """)

    frappe.db.commit()
