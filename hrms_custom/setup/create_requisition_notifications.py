import frappe

def create_requisition_notifications():
    print("\n--- Creating Job Requisition Notification Scripts ---")

    scripts = [
        # Script 1 — After HR Approves
        # New Position → go to Final Approval
        # Replacement → auto approve + notify Final Approver & Director
        {
            "name": "Job Requisition - HR Approved Handler",
            "doctype_event": "After Save",
            "script": """
type_of_req = doc.custom_type_of_requirement or ""

# ── NEW POSITION → Notify HR Manager for approval ──────────
if type_of_req == "New Position" and doc.workflow_state == "Pending HR Approval":
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
            subject="[New Position] Job Requisition Pending Your Approval - " + (doc.designation or doc.name),
            message=(
                "<p>Dear HR Manager,</p>"
                "<p>A <b>New Position</b> Job Requisition has been submitted and requires your approval.</p>"
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

# ── REPLACEMENT → HR approves → notify Final Approver & Director ──
if type_of_req == "Replacement" and doc.workflow_state == "Pending HR Approval":
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
            subject="[Replacement] Job Requisition Pending Your Approval - " + (doc.designation or doc.name),
            message=(
                "<p>Dear HR Manager,</p>"
                "<p>A <b>Replacement</b> Job Requisition has been submitted and requires your approval.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                "</table>"
                "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Review & Approve</a></p>"
                "<p>Regards,<br><b>System</b><br>Aionion Capital</p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
"""
        },

        # Script 2 — Pending Final Approval
        # New Position → notify Final Approver for approval
        # Replacement → auto move to Approved + notify Final Approver & Director FYI
        {
            "name": "Job Requisition - Pending Final Approval Handler",
            "doctype_event": "After Save",
            "script": """
type_of_req = doc.custom_type_of_requirement or ""

# ── NEW POSITION → Notify Final Approver to approve ────────
if type_of_req == "New Position" and doc.workflow_state == "Pending Final Approval":
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
            subject="[New Position] Final Approval Required - " + (doc.designation or doc.name),
            message=(
                "<p>Dear Team,</p>"
                "<p>A <b>New Position</b> Requisition requires your <b>Final Approval</b>.</p>"
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

# ── REPLACEMENT → Skip Final Approval → Auto Approve ───────
if type_of_req == "Replacement" and doc.workflow_state == "Pending Final Approval":
    # Auto move to Approved
    frappe.db.set_value("Job Requisition", doc.name, "workflow_state", "Approved")

    # Notify Final Approver & Director (FYI only)
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
            subject="[FYI] Replacement Position Approved - " + (doc.designation or doc.name),
            message=(
                "<p>Dear Team,</p>"
                "<p>This is to inform you that a <b>Replacement</b> position has been approved by HR Manager.</p>"
                "<p>No action required from your end.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                "<tr><td><b>Type</b></td><td><b>Replacement</b></td></tr>"
                "</table>"
                "<br><p><a href='" + form_url + "' style='background:#0F6E56;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>View Requisition</a></p>"
                "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
            ),
            reference_doctype=doc.doctype,
            reference_name=doc.name,
        )
"""
        },

        # Script 3 — Fully Approved → Notify HR Manager + Director
        {
            "name": "Notify HR Manager - Job Requisition Fully Approved",
            "doctype_event": "After Save",
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
        type_of_req = doc.custom_type_of_requirement or ""
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject="Job Requisition APPROVED - Start Recruitment - " + (doc.designation or doc.name),
            message=(
                "<p>Dear HR Team,</p>"
                "<p>The Job Requisition is <b style='color:green'>Approved</b>. Please start recruitment.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                "<tr><td><b>Type</b></td><td>" + type_of_req + "</td></tr>"
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

        # Script 4 — Rejected → Notify Hiring Manager
        {
            "name": "Notify Hiring Manager - Job Requisition Rejected",
            "doctype_event": "After Save",
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
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
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
        "Notify HR Manager - Job Requisition Submitted",
        "Job Requisition - Submit Handler",
        "Notify Final Approver - Job Requisition HR Approved",
        "Notify HR Manager - Job Requisition Fully Approved",
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
        ss.doctype_event = s["doctype_event"]
        ss.module = "HRMS Custom"
        ss.script = s["script"]
        ss.disabled = 0
        ss.insert(ignore_permissions=True)
        print("  Created: " + s["name"])

    frappe.db.commit()
    print("\nAll scripts updated!")
