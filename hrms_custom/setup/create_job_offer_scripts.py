import frappe

def create_job_offer_scripts():
    print("\n--- Creating Job Offer Server Scripts ---")

    # Script 1 — Notify BH when sent for approval
    name1 = "Notify BH - Job Offer Pending Approval"
    if frappe.db.exists("Server Script", name1):
        frappe.delete_doc("Server Script", name1, ignore_permissions=True)

    script1_code = """
# Get BH users with Branch Head role
bh_users = frappe.get_all(
    "Has Role",
    filters={"role": "Branch Head", "parenttype": "User"},
    fields=["parent"]
)

bh_emails = []
for u in bh_users:
    email = frappe.db.get_value("User", u.parent, "email")
    if email:
        bh_emails.append(email)

if bh_emails:
    applicant_name = frappe.db.get_value(
        "Job Applicant", doc.job_applicant, "applicant_name"
    )
    form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)

    frappe.sendmail(
        recipients=bh_emails,
        subject="Job Offer Approval Required - " + (applicant_name or doc.job_applicant),
        message=(
            "<p>Dear Branch Head,</p>"
            "<p>A Job Offer requires your approval.</p>"
            "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
            "<tr><td><b>Candidate</b></td><td>" + (applicant_name or "") + "</td></tr>"
            "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
            "<tr><td><b>Proposed CTC</b></td><td>" + str(doc.custom_proposed_ctc or "") + "</td></tr>"
            "<tr><td><b>Joining Date</b></td><td>" + str(doc.custom_tentative_joining_date or "") + "</td></tr>"
            "<tr><td><b>Budget Code</b></td><td>" + (doc.custom_budget_code or "") + "</td></tr>"
            "</table>"
            "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>"
            "Review & Approve</a></p>"
            "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
        ),
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )
    frappe.msgprint(
        "Approval request sent to Branch Head!",
        indicator="green",
        title="Email Sent"
    )
"""

    ss1 = frappe.new_doc("Server Script")
    ss1.name = name1
    ss1.script_type = "DocType Event"
    ss1.reference_doctype = "Job Offer"
    ss1.doctype_event = "After Save"
    ss1.module = "HRMS Custom"
    ss1.script = script1_code
    ss1.disabled = 0
    ss1.insert(ignore_permissions=True)
    print("  Created: " + name1)

    # Script 2 — Notify HR when BH approves
    name2 = "Notify HR - Job Offer Approved by BH"
    if frappe.db.exists("Server Script", name2):
        frappe.delete_doc("Server Script", name2, ignore_permissions=True)

    script2_code = """
applicant_name = frappe.db.get_value(
    "Job Applicant", doc.job_applicant, "applicant_name"
)

hr_users = frappe.get_all(
    "Has Role",
    filters={"role": "HR User", "parenttype": "User"},
    fields=["parent"]
)

hr_emails = []
for u in hr_users:
    email = frappe.db.get_value("User", u.parent, "email")
    if email:
        hr_emails.append(email)

if hr_emails:
    form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
    frappe.sendmail(
        recipients=hr_emails,
        subject="Job Offer Approved - " + (applicant_name or doc.job_applicant),
        message=(
            "<p>Dear HR Team,</p>"
            "<p>The Job Offer for <b>" + (applicant_name or "") + "</b> has been <b>Approved</b> by the Branch Head.</p>"
            "<p>Please proceed with sending the offer letter to the candidate.</p>"
            "<p><a href='" + form_url + "'>View Job Offer</a></p>"
            "<p>Regards,<br><b>System</b></p>"
        ),
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )
"""

    ss2 = frappe.new_doc("Server Script")
    ss2.name = name2
    ss2.script_type = "DocType Event"
    ss2.reference_doctype = "Job Offer"
    ss2.doctype_event = "After Submit"
    ss2.module = "HRMS Custom"
    ss2.script = script2_code
    ss2.disabled = 0
    ss2.insert(ignore_permissions=True)
    print("  Created: " + name2)

    frappe.db.commit()
    print("\nAll Job Offer scripts created!")
