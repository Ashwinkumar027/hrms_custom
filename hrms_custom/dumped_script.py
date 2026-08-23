if doc.has_value_changed('workflow_state') or getattr(frappe.flags, 'in_test', False):

    sender_email = frappe.db.get_value("HR Settings", "HR Settings", "sender_email") or None

    type_of_req = doc.custom_type_of_requirement or ""
    company = doc.company or ""
    team = doc.custom_team or ""
    req_exp = str(doc.custom_required_experience or "")

    # Generate dynamic rows directly
    extra_rows = f"<tr><td><b>Company</b></td><td>{company}</td></tr>"
    extra_rows += f"<tr><td><b>Team</b></td><td>{team}</td></tr>"
    extra_rows += f"<tr><td><b>Type of Requirement</b></td><td>{type_of_req}</td></tr>"
    extra_rows += f"<tr><td><b>Urgency Level</b></td><td>{doc.custom_urgency_level or ''}</td></tr>"
    extra_rows += f"<tr><td><b>Proposed Salary</b></td><td>{str(doc.custom_proposed_salarybudget or '')}</td></tr>"
    extra_rows += f"<tr><td><b>Required Experience</b></td><td>{req_exp} Years</td></tr>"
    if type_of_req == "Replacement":
        extra_rows += f"<tr><td><b>Employee Being Replaced</b></td><td>{doc.custom_name_of_employee_being_replaced or ''}</td></tr>"
        extra_rows += f"<tr><td><b>Replacement Employee CTC</b></td><td>{str(doc.custom_replacement_employee_ctc or '')}</td></tr>"
        extra_rows += f"<tr><td><b>Replacement Details</b></td><td>{doc.custom_replacement_details or ''}</td></tr>"


    # ── REJECTED ──────────────────────────────────────────
    if doc.workflow_state == "Rejected":
        recipient_email = None
        if doc.requested_by:
            user_id = frappe.db.get_value("Employee", doc.requested_by, "user_id")
            if user_id:
                recipient_email = frappe.db.get_value("User", user_id, "email")

        if recipient_email:
            form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
            frappe.sendmail(
                recipients=[recipient_email],
                subject="Job Requisition REJECTED - " + (doc.designation or doc.name),
                sender=sender_email,
                message=(
                    "<p>Dear " + (doc.requested_by_name or "Hiring Manager") + ",</p>"
                    "<p>Your Job Requisition has been <b style='color:red'>Rejected</b>.</p>"
                    "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                    "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                    "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                    "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                    "<tr><td><b>Rejection Reason</b></td><td><span style='color:red'>" + (doc.custom_rejection_reason or "No reason provided") + "</span></td></tr>"
                    + extra_rows +
                    "</table>"
                    "<br><p><a href='" + form_url + "'>View Requisition</a></p>"
                    f"<p>Regards,<br><b>HR Team</b><br>{company}</p>"
                ),
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )

    # ── FULLY APPROVED ────────────────────────────────────
    elif doc.workflow_state == "Approved":
        hr_users = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"}, fields=["parent"])
        recipients = []
        for u in hr_users:
            email = frappe.db.get_value("User", u.parent, "email")
            if email: recipients.append(email)

        if doc.requested_by:
            user_id = frappe.db.get_value("Employee", doc.requested_by, "user_id")
            if user_id:
                requesting_email = frappe.db.get_value("User", user_id, "email")
                if requesting_email: recipients.append(requesting_email)

        if recipients:
            form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
            frappe.sendmail(
                recipients=list(set(recipients)),
                subject="Job Requisition APPROVED - Start Recruitment - " + (doc.designation or doc.name),
                sender=sender_email,
                message=(
                    "<p>Dear HR Team,</p>"
                    "<p>The Job Requisition is <b style='color:green'>Approved</b>. Please start recruitment.</p>"
                    "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                    "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                    "<tr><td><b>Requested By</b></td><td>" + (doc.requested_by_name or doc.requested_by or "") + "</td></tr>"
                    "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                    "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                    "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                                    + extra_rows +
                    "</table>"
                    "<br><p><a href='" + form_url + "' style='background:#0F6E56;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>View Requisition</a></p>"
                    f"<p>Regards,<br><b>System</b><br>{company}</p>"
                ),
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )

    # ── PENDING FINAL APPROVAL ────────────────────────────
    elif doc.workflow_state == "Pending Final Approval":

        # NEW: Check if Position Approval Status is "Yes" (meaning it has offline approval)
        if doc.custom_position_approval_status == "Yes":
            # Auto-Approve it
            frappe.db.set_value("Job Requisition", doc.name, "workflow_state", "Approved")
        
            # Send FYI to Final Approvers and Directors
            fa_users = frappe.get_all("Has Role", filters={"role": "Final Approver", "parenttype": "User"}, fields=["parent"])
            director_users = frappe.get_all("Has Role", filters={"role": "Dileep Director", "parenttype": "User"}, fields=["parent"])
            recipients = []
            for u in fa_users + director_users:
                email = frappe.db.get_value("User", u.parent, "email")
                if email: recipients.append(email)

            if recipients:
                form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
                frappe.sendmail(
                    recipients=list(set(recipients)),
                    subject="[FYI] Final Approval Received Offline - " + (doc.designation or doc.name),
                    sender=sender_email,
                    message=(
                        "<p>Dear Team,</p>"
                        "<p>This Job Requisition has been automatically approved because you already provided approval offline via email attachment.</p>"
                        "<p><b>No further action is required from your end.</b></p>"
                        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                        "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                        "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                        "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                        "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                                                                + extra_rows +
                        "</table>"
                        "<br><p><a href='" + form_url + "' style='background:#0F6E56;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>View Requisition</a></p>"
                        f"<p>Regards,<br><b>System</b><br>{company}</p>"
                    ),
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )
            
        # Proceed with NORMAL flow if no offline approval
        elif type_of_req == "New Position":
            form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
        
            # 1. Actionable Email to Final Approvers
            fa_users = frappe.get_all("Has Role", filters={"role": "Final Approver", "parenttype": "User"}, fields=["parent"])
            fa_recipients = []
            for u in fa_users:
                email = frappe.db.get_value("User", u.parent, "email")
                if email: fa_recipients.append(email)

            if fa_recipients:
                frappe.sendmail(
                    recipients=list(set(fa_recipients)),
                    subject="[New Position] Final Approval Required - " + (doc.designation or doc.name),
                    sender=sender_email,
                    message=(
                        "<p>Dear Team,</p>"
                        "<p>A <b>New Position</b> Requisition requires your <b>Final Approval</b>.</p>"
                        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                        "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                        "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                        "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                        "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                                                                + extra_rows +
                        "</table>"
                        "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Final Approve</a></p>"
                        f"<p>Regards,<br><b>System</b><br>{company}</p>"
                    ),
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )
            
            # 2. FYI Email to Directors
            director_users = frappe.get_all("Has Role", filters={"role": "Dileep Director", "parenttype": "User"}, fields=["parent"])
            director_recipients = []
            for u in director_users:
                email = frappe.db.get_value("User", u.parent, "email")
                if email: director_recipients.append(email)

            if director_recipients:
                frappe.sendmail(
                    recipients=list(set(director_recipients)),
                    subject="[FYI] New Position Pending Final Approval - " + (doc.designation or doc.name),
                    sender=sender_email,
                    message=(
                        "<p>Dear Director,</p>"
                        "<p>A <b>New Position</b> Requisition is currently pending Final Approval from the assigned approvers.</p>"
                        "<p><b>No action is required from your end. This is for your information.</b></p>"
                        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                        "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                        "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                        "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                        "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                                                                + extra_rows +
                        "</table>"
                        "<br><p><a href='" + form_url + "' style='background:#0F6E56;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>View Requisition</a></p>"
                        f"<p>Regards,<br><b>System</b><br>{company}</p>"
                    ),
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )
            
        elif type_of_req == "Replacement":
            frappe.db.set_value("Job Requisition", doc.name, "workflow_state", "Approved")
            fa_users = frappe.get_all("Has Role", filters={"role": "Final Approver", "parenttype": "User"}, fields=["parent"])
            director_users = frappe.get_all("Has Role", filters={"role": "Dileep Director", "parenttype": "User"}, fields=["parent"])
            recipients = []
            for u in fa_users + director_users:
                email = frappe.db.get_value("User", u.parent, "email")
                if email: recipients.append(email)

            if recipients:
                form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
                frappe.sendmail(
                    recipients=list(set(recipients)),
                    subject="[FYI] Replacement Position Approved - " + (doc.designation or doc.name),
                    sender=sender_email,
                    message=(
                        "<p>Dear Team,</p>"
                        "<p>This is to inform you that a <b>Replacement</b> position has been approved by HR Manager.</p>"
                        "<p>No action required from your end.</p>"
                        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                        "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                        "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                        "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                        "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                        + extra_rows +
                        "</table>"
                        "<br><p><a href='" + form_url + "' style='background:#0F6E56;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>View Requisition</a></p>"
                        f"<p>Regards,<br><b>HR Team</b><br>{company}</p>"
                    ),
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

    # ── PENDING HR APPROVAL ───────────────────────────────
    elif doc.workflow_state == "Pending Hr Approval":
        hr_users = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"}, fields=["parent"])
        recipients = []
        for u in hr_users:
            email = frappe.db.get_value("User", u.parent, "email")
            if email: recipients.append(email)

        if recipients:
            form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
            subject_prefix = "[New Position]" if type_of_req == "New Position" else "[Replacement]"
            message_prefix = "A <b>New Position</b>" if type_of_req == "New Position" else "A <b>Replacement</b>"
        
            frappe.sendmail(
                recipients=list(set(recipients)),
                subject=f"{subject_prefix} Job Requisition Pending Your Approval - " + (doc.designation or doc.name),
                sender=sender_email,
                message=(
                    f"<p>Dear HR Manager,</p>"
                    f"<p>{message_prefix} Job Requisition has been submitted and requires your approval.</p>"
                    "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
                    "<tr><td><b>Requisition</b></td><td>" + doc.name + "</td></tr>"
                    "<tr><td><b>Designation</b></td><td>" + (doc.designation or "") + "</td></tr>"
                    "<tr><td><b>Department</b></td><td>" + (doc.department or "") + "</td></tr>"
                    "<tr><td><b>No of Positions</b></td><td>" + str(doc.no_of_positions or "") + "</td></tr>"
                    + extra_rows +
                    "</table>"
                    "<br><p><a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:10px 20px;text-decoration:none;border-radius:4px;'>Review & Approve</a></p>"
                    f"<p>Regards,<br><b>System</b><br>{company}</p>"
                ),
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )
