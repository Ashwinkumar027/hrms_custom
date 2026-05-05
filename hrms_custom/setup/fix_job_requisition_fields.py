import frappe

def fix_job_requisition_fields():
    print("\n--- Fixing Job Requisition Custom Fields ---")

    # Fields to DELETE (duplicates of original)
    fields_to_delete = [
        "Job Requisition-custom_company",
        "Job Requisition-custom_requested_by",
        "Job Requisition-custom_col_break_top",
    ]

    for field in fields_to_delete:
        if frappe.db.exists("Custom Field", field):
            frappe.delete_doc("Custom Field", field, ignore_permissions=True)
            print("  Deleted: " + field)
        else:
            print("  Not found: " + field)

    frappe.db.commit()
    print("\nDone! Duplicate fields removed.")
