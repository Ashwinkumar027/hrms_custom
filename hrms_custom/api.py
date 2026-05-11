import frappe
from frappe.utils import now, get_url
import urllib.parse

@frappe.whitelist()
def send_preoffer_form(job_applicant):
    doc = frappe.get_doc("Job Applicant", job_applicant)

    if not doc.email_id:
        frappe.throw("No email address found for this applicant!")

    # Build pre-filled form URL
    params = urllib.parse.urlencode({
        "applicant_name": doc.applicant_name or "",
        "email": doc.email_id or "",
        "phone": doc.phone_number or "",
        "job_applicant": doc.name
    })

    form_url = get_url("/candidate-pre-offer/new?" + params)

    subject = "Action Required: Pre-Offer Form - Aionion Capital"

    message = (
        "<div style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;'>"
        "<div style='background:#1B4F8A;padding:20px;text-align:center;'>"
        "<h2 style='color:white;margin:0;'>Pre-Offer Form</h2>"
        "<p style='color:#cce0ff;margin:5px 0;'>Aionion Capital</p>"
        "</div>"
        "<div style='padding:30px;background:#f9f9f9;'>"
        "<p>Dear <b>" + (doc.applicant_name or "Candidate") + "</b>,</p>"
        "<p>Congratulations! You have successfully cleared the interview process at "
        "<b>Aionion Capital</b>.</p>"
        "<p>As the next step towards your offer letter, please fill in the "
        "<b>Pre-Offer Form</b> with your personal details, KYC information, "
        "CTC expectations, and upload all required documents.</p>"
        "<p style='margin:25px 0;text-align:center;'>"
        "<a href='" + form_url + "' style='background:#1B4F8A;color:white;"
        "padding:14px 28px;text-decoration:none;border-radius:4px;"
        "font-weight:bold;font-size:16px;'>Fill Pre-Offer Form</a>"
        "</p>"
        "<p><b>Documents Required:</b></p>"
        "<ul>"
        "<li>Aadhar Card</li>"
        "<li>PAN Card</li>"
        "<li>Bank Passbook / Cancelled Cheque</li>"
        "<li>10th &amp; 12th Marksheet</li>"
        "<li>Degree Certificate</li>"
        "<li>Experience Certificate (if applicable)</li>"
        "<li>Last Salary Slip (if applicable)</li>"
        "<li>Resume / CV</li>"
        "</ul>"
        "<p>Please complete the form at the earliest to proceed with your offer letter.</p>"
        "<p>For any queries contact: "
        "<a href='mailto:hr@aionioncapital.com'>hr@aionioncapital.com</a></p>"
        "<p>Warm Regards,<br><b>HR Team</b><br>Aionion Capital</p>"
        "</div>"
        "<div style='background:#1B4F8A;padding:10px;text-align:center;'>"
        "<p style='color:#cce0ff;margin:0;font-size:12px;'>"
        "Aionion Capital HRMS</p>"
        "</div>"
        "</div>"
    )

    frappe.sendmail(
        recipients=[doc.email_id],
        subject=subject,
        message=message,
        reference_doctype="Job Applicant",
        reference_name=doc.name,
    )

    # Update sent status
    frappe.db.set_value("Job Applicant", doc.name, {
        "custom_preoffer_form_sent": 1,
        "custom_preoffer_sent_on": now(),
        "custom_preoffer_sent_by": frappe.session.user
    })

    frappe.db.commit()
    return {"success": True, "message": "Pre-Offer Form sent successfully!"}
