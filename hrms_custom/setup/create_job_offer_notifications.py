import frappe

def create_job_offer_notifications():

    scripts = [
        {
            "name": "Notify BH - Job Offer Pending Approval",
            "script_type": "DocType Event",
            "reference_doctype": "Job Offer",
            "doctype_event": "After Save",
            "module": "HRMS custom",
            "disabled": 0,
            "script": """if doc.workflow_state == "Pending BH Approval":
    bh_users = frappe.get_all(
        "Has Role",
        filters={"role": "Business Head", "parenttype": "User"},
        fields=["parent"]
    )
    bh_emails = []
    for u in bh_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email and email != "Administrator":
            bh_emails.append(email)

    if bh_emails:
        applicant_name = frappe.db.get_value(
            "Job Applicant", doc.job_applicant, "applicant_name"
        )
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        frappe.sendmail(
            recipients=bh_emails,
            subject="Job Offer Approval Required - " + (applicant_name or ""),
            message=(
                "<p>Dear Business Head,</p>"
                "<p>A Job Offer requires your approval.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Candidate</b></td><td>" + (applicant_name or "") + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "<tr><td><b>Proposed CTC</b></td><td>" + str(doc.custom_proposed_ctc or "") + "</td></tr>"
                "<tr><td><b>Joining Date</b></td><td>" + str(doc.custom_tentative_joining_date or "") + "</td></tr>"
                "</table>"
                "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Review and Approve</a></p>"
                "<p>Regards,<br><b>HR Team</b></p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
        frappe.msgprint("Approval request sent to Business Head!", indicator="green", title="Email Sent")
"""
        },
        {
            "name": "Notify HR - Job Offer Approved by BH",
            "script_type": "DocType Event",
            "reference_doctype": "Job Offer",
            "doctype_event": "After Submit",
            "module": "HRMS custom",
            "disabled": 0,
            "script": """if doc.workflow_state == "Approved by BH":
    frappe.db.set_value("Job Offer", doc.name, "docstatus", 1)
    frappe.db.commit()

    applicant_name = frappe.db.get_value(
        "Job Applicant", doc.job_applicant, "applicant_name"
    )
    hr_users = frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"]
    )
    hr_emails = []
    for u in hr_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email and email != "Administrator":
            hr_emails.append(email)

    if hr_emails:
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        frappe.sendmail(
            recipients=hr_emails,
            subject="Job Offer Approved - " + (applicant_name or ""),
            message=(
                "<p>Dear HR Manager,</p>"
                "<p>The Job Offer for <b>" + (applicant_name or "") + "</b> has been <b>Approved</b> by the Business Head.</p>"
                "<p>Please proceed with sending the offer letter to the candidate.</p>"
                "<p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>View Job Offer</a></p>"
                "<p>Regards,<br><b>System</b></p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
"""
        }
    ]

    for script in scripts:
        name = script["name"]
        if frappe.db.exists("Server Script", name):
            frappe.delete_doc("Server Script", name, force=True)
            print(f"  Deleted existing: {name}")

        doc = frappe.new_doc("Server Script")
        doc.update(script)
        doc.insert(ignore_permissions=True)
        print(f"  Created: {name}")

    frappe.db.commit()
    print("\nAll Job Offer notifications created successfully!")
