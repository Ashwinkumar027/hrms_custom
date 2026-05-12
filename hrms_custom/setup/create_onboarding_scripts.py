import frappe

def create_onboarding_scripts():
    print("\n--- Creating Onboarding Scripts ---")

    scripts = [
        {
            "name": "Notify Manager - Employee Onboarding Assigned",
            "doctype_event": "After Save",
            "script": """
if doc.workflow_state == "Pending Manager Input":
    mgr_users = frappe.get_all("Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"])
    recipients = []
    for u in mgr_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            recipients.append(email)
    if recipients:
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject="Action Required: Fill Onboarding Activities - " + (doc.employee_name or doc.name),
            message=(
                "<p>Dear Manager,</p>"
                "<p>Please fill the onboarding activities for new joiner <b>" + (doc.employee_name or "") + "</b>.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>Employee</b></td><td>" + (doc.employee_name or "") + "</td></tr>"
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                "<tr><td><b>Date of Joining</b></td><td>" + str(doc.date_of_joining or "") + "</td></tr>"
                "</table>"
                "<p>Please add activities like Laptop, SIM, Email ID, Seating etc. with the responsible user for each.</p>"
                "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Fill Activities</a></p>"
                "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
            ),
        )
"""
        },
        {
            "name": "Notify HR - Onboarding Activities Submitted",
            "doctype_event": "After Save",
            "script": """
if doc.workflow_state == "Pending HR Review":
    hr_users = frappe.get_all("Has Role",
        filters={"role": "HR User", "parenttype": "User"},
        fields=["parent"])
    recipients = []
    for u in hr_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            recipients.append(email)
    if recipients:
        form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        activity_rows = ""
        for a in doc.activities:
            activity_rows += "<tr><td>" + (a.activity_name or "") + "</td><td>" + (a.user or "") + "</td></tr>"
        frappe.sendmail(
            recipients=list(set(recipients)),
            subject="Review Onboarding Activities - " + (doc.employee_name or doc.name),
            message=(
                "<p>Dear HR Team,</p>"
                "<p>Manager has submitted onboarding activities for <b>" + (doc.employee_name or "") + "</b>. Please review and approve.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><th>Activity</th><th>Assigned To</th></tr>"
                + activity_rows +
                "</table>"
                "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Review & Approve</a></p>"
                "<p>Regards,<br><b>System</b></p>"
            ),
        )
"""
        },
        {
            "name": "Create Helpdesk Tickets - Employee Onboarding",
            "doctype_event": "After Submit",
            "script": """
if doc.workflow_state == "Onboarding In Progress":
    for activity in doc.activities:
        if not activity.user:
            continue

        user_email = frappe.db.get_value("User", activity.user, "email")
        if not user_email:
            continue

        # Create Helpdesk ticket for each activity
        ticket = frappe.new_doc("HD Ticket")
        ticket.subject = activity.activity_name + " - " + (doc.employee_name or doc.name)
        ticket.description = (
            "<p>Onboarding Activity for New Joiner:</p>"
            "<ul>"
            "<li><b>Employee:</b> " + (doc.employee_name or "") + "</li>"
            "<li><b>Department:</b> " + (doc.department or "") + "</li>"
            "<li><b>Designation:</b> " + (doc.designation or "") + "</li>"
            "<li><b>Date of Joining:</b> " + str(doc.date_of_joining or "") + "</li>"
            "<li><b>Activity:</b> " + (activity.activity_name or "") + "</li>"
            "<li><b>Assigned To:</b> " + (activity.user or "") + "</li>"
            "</ul>"
        )
        ticket.raised_by = frappe.session.user
        ticket.contact = activity.user
        ticket.insert(ignore_permissions=True)

        # Notify the assignee
        frappe.sendmail(
            recipients=[user_email],
            subject="New Onboarding Task: " + (activity.activity_name or "") + " - " + (doc.employee_name or ""),
            message=(
                "<p>Dear Team,</p>"
                "<p>A new onboarding task has been assigned to you.</p>"
                "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                "<tr><td><b>New Joiner</b></td><td>" + (doc.employee_name or "") + "</td></tr>"
                "<tr><td><b>Task</b></td><td>" + (activity.activity_name or "") + "</td></tr>"
                "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                "<tr><td><b>Date of Joining</b></td><td>" + str(doc.date_of_joining or "") + "</td></tr>"
                "</table>"
                "<p>Please complete this task before the joining date.</p>"
                "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
            ),
        )

    frappe.db.commit()
    frappe.msgprint(
        "Helpdesk tickets created for all onboarding activities!",
        indicator="green",
        title="Tickets Created"
    )
"""
        },
    ]

    for s in scripts:
        if frappe.db.exists("Server Script", s["name"]):
            frappe.delete_doc("Server Script", s["name"], ignore_permissions=True)
        ss = frappe.new_doc("Server Script")
        ss.name = s["name"]
        ss.script_type = "DocType Event"
        ss.reference_doctype = "Employee Onboarding"
        ss.doctype_event = s["doctype_event"]
        ss.module = "HRMS Custom"
        ss.script = s["script"]
        ss.disabled = 0
        ss.insert(ignore_permissions=True)
        print("  Created: " + s["name"])

    frappe.db.commit()
    print("All scripts created!")
