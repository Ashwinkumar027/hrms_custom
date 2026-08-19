import frappe

@frappe.whitelist(allow_guest=True)
def get_job_opening_designation(job_opening):
    return frappe.db.get_value("Job Opening", job_opening, "designation")
