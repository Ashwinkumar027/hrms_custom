import frappe

def create_job_requisition_field():
    print("\n--- Adding Job Requisition field to Job Offer ---")

    field_name = "Job Offer-custom_job_requisition"

    if not frappe.db.exists("Custom Field", field_name):
        cf = frappe.new_doc("Custom Field")
        cf.dt = "Job Offer"
        cf.fieldname = "custom_job_requisition"
        cf.fieldtype = "Link"
        cf.label = "Job Requisition"
        cf.options = "Job Requisition"
        cf.insert_after = "job_applicant"
        cf.module = "HRMS Custom"
        cf.insert(ignore_permissions=True)
        frappe.db.commit()
        print("  Created: Job Requisition field")
    else:
        print("  Already exists: Job Requisition field")

    print("Done!")
