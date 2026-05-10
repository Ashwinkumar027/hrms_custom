import frappe

def fix_position_reporting_to():
    print("\n--- Fixing Position Reporting To field ---")

    # Delete existing field
    if frappe.db.exists("Custom Field", "Job Requisition-custom_position_reporting_to"):
        frappe.delete_doc("Custom Field",
            "Job Requisition-custom_position_reporting_to",
            ignore_permissions=True)
        frappe.db.commit()
        print("  Deleted old field")

    # Recreate as Link to Employee
    cf = frappe.new_doc("Custom Field")
    cf.dt = "Job Requisition"
    cf.fieldname = "custom_position_reporting_to"
    cf.fieldtype = "Link"
    cf.label = "Position Reporting To"
    cf.options = "Employee"
    cf.insert_after = "custom_section_reporting"
    cf.reqd = 1
    cf.module = "HRMS Custom"
    cf.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  Created: Position Reporting To (Link → Employee)")
    print("Done!")
