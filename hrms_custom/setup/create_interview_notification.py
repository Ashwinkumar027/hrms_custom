import frappe

def create_interview_notification():
    print("\n--- Fixing Interview Notification Script ---")

    name = "Notify Candidate - Interview Scheduled"

    if frappe.db.exists("Server Script", name):
        frappe.delete_doc("Server Script", name, ignore_permissions=True)
        print("  Deleted existing script")

    script_code = """
candidate_email = frappe.db.get_value(
    "Job Applicant", doc.job_applicant, "email_id"
)
candidate_name = frappe.db.get_value(
    "Job Applicant", doc.job_applicant, "applicant_name"
)

if candidate_email and not doc.custom_notification_sent:

    # Format date without import
    interview_date = frappe.utils.formatdate(doc.scheduled_on) if doc.scheduled_on else ""
    from_time = str(doc.from_time)[:5] if doc.from_time else ""
    to_time = str(doc.to_time)[:5] if doc.to_time else ""

    mode = doc.custom_interview_mode or "Face to Face"
    location = doc.custom_interview_location or "Will be informed shortly"
    instructions = doc.custom_interview_instructions or ""

    interviewers = []
    for i in doc.interviewers:
        interviewers.append(i.interviewer)
    interviewer_str = ", ".join(interviewers) if interviewers else "Will be informed shortly"

    subject = "Interview Scheduled - " + (doc.designation or "Position") + " - Aionion Capital"

    message = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
        "<div style='background:#1B4F8A;padding:20px;text-align:center;'>"
        "<h2 style='color:white;margin:0;'>Interview Invitation</h2>"
        "<p style='color:#cce0ff;margin:5px 0;'>Aionion Capital</p>"
        "</div>"
        "<div style='padding:30px;background:#f9f9f9;'>"
        "<p>Dear <b>" + (candidate_name or "Candidate") + "</b>,</p>"
        "<p>Congratulations! Your resume has been shortlisted. You are invited for an interview.</p>"
        "<div style='background:white;border-left:4px solid #1B4F8A;padding:20px;margin:20px 0;border-radius:4px;'>"
        "<h3 style='color:#1B4F8A;margin-top:0;'>Interview Details</h3>"
        "<table style='width:100%;border-collapse:collapse;'>"
        "<tr style='border-bottom:1px solid #eee;'>"
        "<td style='padding:8px 0;color:#666;width:40%;'><b>Interview Round</b></td>"
        "<td style='padding:8px 0;'>" + (doc.interview_round or "") + "</td>"
        "</tr>"
        "<tr style='border-bottom:1px solid #eee;'>"
        "<td style='padding:8px 0;color:#666;'><b>Date</b></td>"
        "<td style='padding:8px 0;color:#1B4F8A;'><b>" + interview_date + "</b></td>"
        "</tr>"
        "<tr style='border-bottom:1px solid #eee;'>"
        "<td style='padding:8px 0;color:#666;'><b>Time</b></td>"
        "<td style='padding:8px 0;color:#1B4F8A;'><b>" + from_time + " - " + to_time + "</b></td>"
        "</tr>"
        "<tr style='border-bottom:1px solid #eee;'>"
        "<td style='padding:8px 0;color:#666;'><b>Mode</b></td>"
        "<td style='padding:8px 0;'>" + mode + "</td>"
        "</tr>"
        "<tr style='border-bottom:1px solid #eee;'>"
        "<td style='padding:8px 0;color:#666;'><b>Location / Link</b></td>"
        "<td style='padding:8px 0;'>" + location + "</td>"
        "</tr>"
        "<tr style='border-bottom:1px solid #eee;'>"
        "<td style='padding:8px 0;color:#666;'><b>Interviewer</b></td>"
        "<td style='padding:8px 0;'>" + interviewer_str + "</td>"
        "</tr>"
        "</table>"
        "</div>"
        + (
            "<div style='background:#fff8e1;padding:15px;border-radius:4px;margin:15px 0;'>"
            "<b>Special Instructions:</b><br>" + instructions + "</div>"
            if instructions else ""
        ) +
        "<div style='background:#e8f5e9;padding:15px;border-radius:4px;margin:15px 0;'>"
        "<b>Please bring the following documents:</b>"
        "<ul style='margin:10px 0;'>"
        "<li>Updated Resume (2 copies)</li>"
        "<li>Original ID Proof (Aadhar/PAN)</li>"
        "<li>Educational Certificates</li>"
        "<li>Experience Certificate (if applicable)</li>"
        "<li>Last 3 months salary slips (if applicable)</li>"
        "</ul>"
        "</div>"
        "<p>Please confirm attendance by replying to this email or contact HR at "
        "<a href='mailto:hr@aionioncapital.com'>hr@aionioncapital.com</a></p>"
        "<p>We look forward to meeting you!</p>"
        "<p>Warm Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
        "</div>"
        "<div style='background:#1B4F8A;padding:10px;text-align:center;'>"
        "<p style='color:#cce0ff;margin:0;font-size:12px;'>Aionion Capital HRMS</p>"
        "</div>"
        "</div>"
    )

    frappe.sendmail(
        recipients=[candidate_email],
        subject=subject,
        message=message,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )

    frappe.db.set_value("Interview", doc.name, "custom_notification_sent", 1)

    frappe.msgprint(
        "Interview notification sent to " + (candidate_name or candidate_email),
        indicator="green",
        title="Email Sent!"
    )
"""

    ss = frappe.new_doc("Server Script")
    ss.name = name
    ss.script_type = "DocType Event"
    ss.reference_doctype = "Interview"
    ss.doctype_event = "After Save"
    ss.module = "HRMS Custom"
    ss.script = script_code
    ss.disabled = 0
    ss.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  Created: " + name)
    print("Interview notification script fixed!")
