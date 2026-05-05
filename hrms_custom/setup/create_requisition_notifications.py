import frappe

def create_requisition_notifications():
    print("\n--- Creating Job Requisition Notification Scripts ---")

    scripts = [
        # Script 1 — Notify HR Manager when Hiring Manager submits
        {
            "name": "Notify HR Manager - Job Requisition Submitted",
            "script": """
if doc.workflow_state == "Pending HR Approval":
    hr_users = frappe.get_all("Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"])

    recipients = []
    for u in hr_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            recipients.append(email)

    if recipients:
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject="Job Requisition Pending Your Approval - " + (doc.designation or doc.name),
            message=(
                "<p>Dear HR Manager,</p>"
                "<p>A new Job Requisition has been submitted by Hiring Manager and requires your review.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                "<tr><td><b>Urgency Level</b></td><td>" + (doc.custom_urgency_level or "") + "</td></tr>"
                "<tr><td><b>Proposed Salary</b></td><td>" + (doc.custom_proposed_salary or "") + "</td></tr>"
                "</table>"
                "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Review & Approve</a></p>"
                "<p>Regards,<br><b>System</b><br>Aionion Capital</p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
"""
        },
        # Script 2 — Notify Final Approver when HR approves
        {
            "name": "Notify Final Approver - Job Requisition HR Approved",
            "script": """
if doc.workflow_state == "Pending Final Approval":
    fa_users = frappe.get_all("Has Role",
        filters={"role": "Final Approver", "parenttype": "User"},
        fields=["parent"])
    director_users = frappe.get_all("Has Role",
        filters={"role": "Director", "parenttype": "User"},
        fields=["parent"])

    recipients = []
    for u in fa_users + director_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            recipients.append(email)

    if recipients:
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject="Job Requisition - HR Approved - Final Approval Required - " + (doc.designation or doc.name),
            message=(
                "<p>Dear Team,</p>"
                "<p>A Job Requisition has been approved by HR Manager and requires <b>Final Approval</b>.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                "<tr><td><b>Urgency Level</b></td><td>" + (doc.custom_urgency_level or "") + "</td></tr>"
                "<tr><td><b>Proposed Salary</b></td><td>" + (doc.custom_proposed_salary or "") + "</td></tr>"
                "</table>"
                "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Final Approve</a></p>"
                "<p>Regards,<br><b>System</b><br>Aionion Capital</p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
"""
        },
        # Script 3 — Notify HR Manager when fully approved
        {
            "name": "Notify HR Manager - Job Requisition Fully Approved",
            "script": """
if doc.workflow_state == "Approved":
    hr_users = frappe.get_all("Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"])
    director_users = frappe.get_all("Has Role",
        filters={"role": "Director", "parenttype": "User"},
        fields=["parent"])

    recipients = []
    for u in hr_users + director_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            recipients.append(email)

    if recipients:
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject="Job Requisition APPROVED - Start Recruitment - " + (doc.designation or doc.name),
            message=(
                "<p>Dear HR Team,</p>"
                "<p>The Job Requisition has been <b style='color:green'>Fully Approved</b>. Please start recruitment.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                "<tr><td><b>Urgency Level</b></td><td>" + (doc.custom_urgency_level or "") + "</td></tr>"
                "</table>"
                "<br><p><a href='" + form_url + "' style='background:#0F6E56;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>View Requisition</a></p>"
                "<p>Regards,<br><b>System</b><br>Aionion Capital</p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
"""
        },
        # Script 4 — Notify Hiring Manager when rejected
        {
            "name": "Notify Hiring Manager - Job Requisition Rejected",
            "script": """
if doc.workflow_state == "Rejected":
    hm_users = frappe.get_all("Has Role",
        filters={"role": "Hiring Manager", "parenttype": "User"},
        fields=["parent"])

    recipients = []
    for u in hm_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            recipients.append(email)

    if recipients:
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject="Job Requisition REJECTED - " + (doc.designation or doc.name),
            message=(
                "<p>Dear Hiring Manager,</p>"
                "<p>Your Job Requisition has been <b style='color:red'>Rejected</b>.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "</table>"
                "<br><p><a href='" + form_url + "'>View Requisition</a></p>"
                "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
"""
        },
    ]

    # Delete old scripts
    old_scripts = [
        "Notify BH and HR - Job Requisition Submitted",
        "Notify Final Approver - Job Requisition BH Approved",
        "Notify HR Manager - Job Requisition Approved",
        "Notify Hiring Manager - Job Requisition Rejected",
    ]
    for old in old_scripts:
        if frappe.db.exists("Server Script", old):
            frappe.delete_doc("Server Script", old, ignore_permissions=True)
            print("  Deleted: " + old)

    for s in scripts:
        if frappe.db.exists("Server Script", s["name"]):
            frappe.delete_doc("Server Script", s["name"], ignore_permissions=True)

        ss = frappe.new_doc("Server Script")
        ss.name = s["name"]
        ss.script_type = "DocType Event"
        ss.reference_doctype = "Job Requisition"
        ss.doctype_event = "After Save"
        ss.module = "HRMS Custom"
        ss.script = s["script"]
        ss.disabled = 0
        ss.insert(ignore_permissions=True)
        print("  Created: " + s["name"])

    frappe.db.commit()
    print("\nAll notification scripts updated!")
