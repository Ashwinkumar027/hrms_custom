import frappe

def create_interview_cleared_script():
    print("\n--- Creating Interview Cleared Server Script ---")

    name = "Send Pre-Offer Form - Interview Cleared"

    if frappe.db.exists("Server Script", name):
        frappe.delete_doc("Server Script", name, ignore_permissions=True)
        print("  Deleted existing script")

    script_code = """
job_applicant_data = frappe.db.get_value(
    "Job Applicant",
    doc.job_applicant,
    ["applicant_name", "email_id", "phone_number"],
    as_dict=True
)

if doc.status == "Cleared" and job_applicant_data and job_applicant_data.email_id:
    from frappe.utils import get_url
    import urllib.parse

    # Build URL with pre-filled data
    params = urllib.parse.urlencode({
        "applicant_name": job_applicant_data.applicant_name or "",
        "email": job_applicant_data.email_id or "",
        "phone": job_applicant_data.phone_number or "",
        "job_applicant": doc.job_applicant
    })

    form_url = get_url("/candidate-pre-offer/new?" + params)

    subject = "Congratulations! Please Fill Your Pre-Offer Form - Aionion Capital"

    message = (
        "<p>Dear " + (job_applicant_data.applicant_name or "Candidate") + ",</p>"
        "<p>Congratulations! You have successfully cleared the interview at <b>Aionion Capital</b>.</p>"
        "<p>Please fill in the Pre-Offer Form with your details and upload all required documents.</p>"
        "<p style='margin:20px 0;'>"
        "<a href='" + form_url + "' style='background:#1B4F8A;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:bold;'>"
        "Click Here to Fill Pre-Offer Form</a></p>"
        "<p><b>Documents Required:</b></p>"
        "<ul>"
        "<li>Aadhar Card</li>"
        "<li>PAN Card</li>"
        "<li>Bank Passbook / Cancelled Cheque</li>"
        "<li>10th Marksheet</li>"
        "<li>12th Marksheet</li>"
        "<li>Semester Marksheet</li>"
        "<li>Degree Certificate</li>"
        "<li>Experience Certificate (if applicable)</li>"
        "<li>Last Salary Slip (if applicable)</li>"
        "<li>Resume / CV</li>"
        "</ul>"
        "<p>Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
    )

    frappe.sendmail(
        recipients=[job_applicant_data.email_id],
        subject=subject,
        message=message,
        reference_doctype=doc.doctype,
        reference_name=doc.name,
    )

    frappe.msgprint(
        "Pre-Offer Form link sent to " + (job_applicant_data.applicant_name or ""),
        indicator="green",
        title="Email Sent!"
    )
"""

    ss = frappe.new_doc("Server Script")
    ss.name = name
    ss.script_type = "DocType Event"
    ss.reference_doctype = "Interview"
    ss.doctype_event = "After Submit"
    ss.module = "HRMS Custom"
    ss.script = script_code
    ss.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Server Script created: " + name)
