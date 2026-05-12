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


@frappe.whitelist()
def send_offer_letter(job_offer):
    doc = frappe.get_doc("Job Offer", job_offer)

    # Get candidate email
    candidate_email = frappe.db.get_value(
        "Job Applicant", doc.job_applicant, "email_id"
    )
    candidate_name = frappe.db.get_value(
        "Job Applicant", doc.job_applicant, "applicant_name"
    )

    if not candidate_email:
        frappe.throw("No email found for this candidate!")

    # Generate accept/reject token
    import hashlib
    token = hashlib.md5(
        (doc.name + candidate_email + "aionion_secret_2026").encode()
    ).hexdigest()

    # Store token
    frappe.db.set_value("Job Offer", doc.name, {
        "custom_offer_token": token,
        "custom_offer_sent": 1,
        "custom_offer_sent_on": frappe.utils.now(),
        "custom_offer_sent_by": frappe.session.user,
        "custom_offer_response": "Awaiting Response"
    })
    frappe.db.commit()

    # Accept/Reject URLs
    base_url = frappe.utils.get_url()
    accept_url = base_url + "/api/method/hrms_custom.api.respond_to_offer?token=" + token + "&response=Accepted&offer=" + doc.name
    reject_url = base_url + "/api/method/hrms_custom.api.respond_to_offer?token=" + token + "&response=Rejected&offer=" + doc.name

    # Get appointment letter PDF if exists
    attachments = []
    appointment_letters = frappe.get_all(
        "Appointment Letter",
        filters={"job_applicant": doc.job_applicant},
        fields=["name"],
        limit=1
    )

    if appointment_letters:
        try:
            pdf_content = frappe.get_print(
                "Appointment Letter",
                appointment_letters[0].name,
                as_pdf=True
            )
            attachments = [{
                "fname": "Offer_Letter_" + (candidate_name or "Candidate").replace(" ", "_") + ".pdf",
                "fcontent": pdf_content
            }]
        except Exception:
            pass

    message = (
        "<div style='font-family:Arial,sans-serif;max-width:650px;margin:0 auto;'>"
        "<div style='background:#1B4F8A;padding:25px;text-align:center;'>"
        "<h2 style='color:white;margin:0;'>Offer Letter</h2>"
        "<p style='color:#cce0ff;margin:5px 0;'>Aionion Capital</p>"
        "</div>"
        "<div style='padding:30px;background:#f9f9f9;'>"
        "<p>Dear <b>" + (candidate_name or "Candidate") + "</b>,</p>"
        "<p>Congratulations! We are delighted to inform you that you have been selected for the position of "
        "<b>" + (doc.designation or "") + "</b> at <b>Aionion Capital</b>.</p>"
        "<p>Please find your offer letter attached to this email.</p>"
        "<p>Kindly respond within <b>48 hours</b> by clicking one of the buttons below:</p>"

        "<div style='text-align:center;margin:30px 0;'>"
        "<a href='" + accept_url + "' style='background:#0F6E56;color:white;"
        "padding:14px 30px;text-decoration:none;border-radius:4px;"
        "font-weight:bold;font-size:16px;margin-right:15px;'>✓ Accept Offer</a>"
        "&nbsp;&nbsp;&nbsp;"
        "<a href='" + reject_url + "' style='background:#A32D2D;color:white;"
        "padding:14px 30px;text-decoration:none;border-radius:4px;"
        "font-weight:bold;font-size:16px;'>✗ Decline Offer</a>"
        "</div>"

        "<p style='color:#666;font-size:13px;'>Please be advised that the offer will be deemed revoked "
        "if we do not receive your acceptance within 48 hours or if there are any inconsistencies "
        "between the information provided during the interview and the details in the offer letter.</p>"

        "<p>We look forward to welcoming you to our team!</p>"
        "<p>Warm Regards,<br><b>HR Department</b><br>Aionion Capital</p>"
        "</div>"
        "<div style='background:#1B4F8A;padding:10px;text-align:center;'>"
        "<p style='color:#cce0ff;margin:0;font-size:11px;'>"
        "CONFIDENTIAL: This email is intended solely for the named recipient.</p>"
        "</div>"
        "</div>"
    )

    frappe.sendmail(
        recipients=[candidate_email],
        subject="Offer Letter - " + (doc.designation or "") + " - Aionion Capital",
        message=message,
        attachments=attachments,
        reference_doctype="Job Offer",
        reference_name=doc.name,
    )

    return {
        "success": True,
        "message": "Offer Letter sent to " + (candidate_name or candidate_email)
    }


@frappe.whitelist(allow_guest=True)
def respond_to_offer(token, response, offer):
    # Validate token
    job_offer = frappe.get_doc("Job Offer", offer)
    candidate_email = frappe.db.get_value(
        "Job Applicant", job_offer.job_applicant, "email_id"
    )

    import hashlib
    expected_token = hashlib.md5(
        (offer + candidate_email + "aionion_secret_2026").encode()
    ).hexdigest()

    if token != expected_token:
        return "<h2 style='color:red;text-align:center;'>Invalid or expired link!</h2>"

    if job_offer.custom_offer_response in ["Accepted", "Rejected"]:
        return (
            "<div style='font-family:Arial;text-align:center;padding:50px;'>"
            "<h2>You have already responded to this offer.</h2>"
            "<p>Response: <b>" + job_offer.custom_offer_response + "</b></p>"
            "</div>"
        )

    # Update response
    frappe.db.set_value("Job Offer", offer, {
        "custom_offer_response": response,
        "custom_offer_responded_on": frappe.utils.now(),
        "status": response
    })
    frappe.db.commit()

    # Notify HR
    hr_users = frappe.get_all("Has Role",
        filters={"role": "HR User", "parenttype": "User"},
        fields=["parent"])
    hr_emails = []
    for u in hr_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            hr_emails.append(email)

    candidate_name = frappe.db.get_value(
        "Job Applicant", job_offer.job_applicant, "applicant_name"
    )

    if hr_emails:
        color = "#0F6E56" if response == "Accepted" else "#A32D2D"
        frappe.sendmail(
            recipients=hr_emails,
            subject="Offer " + response + " - " + (candidate_name or offer),
            message=(
                "<div style='font-family:Arial;padding:20px;'>"
                "<h2 style='color:" + color + ";'>Offer " + response + "!</h2>"
                "<p>Candidate <b>" + (candidate_name or "") + "</b> has "
                "<b style='color:" + color + ";'>" + response + "</b> the offer.</p>"
                "<p><b>Position:</b> " + (job_offer.designation or "") + "</p>"
                "<p><b>Response Time:</b> " + frappe.utils.now() + "</p>"
                "</div>"
            ),
        )

    # Return response page
    if response == "Accepted":
        return (
            "<div style='font-family:Arial,sans-serif;text-align:center;padding:50px;"
            "max-width:500px;margin:0 auto;'>"
            "<div style='color:#0F6E56;font-size:60px;'>✓</div>"
            "<h2 style='color:#0F6E56;'>Offer Accepted!</h2>"
            "<p>Thank you for accepting our offer, <b>" + (candidate_name or "") + "</b>!</p>"
            "<p>Our HR team will contact you shortly with further details.</p>"
            "<p>We look forward to welcoming you to <b>Aionion Capital</b>!</p>"
            "</div>"
        )
    else:
        return (
            "<div style='font-family:Arial,sans-serif;text-align:center;padding:50px;"
            "max-width:500px;margin:0 auto;'>"
            "<div style='color:#A32D2D;font-size:60px;'>✗</div>"
            "<h2 style='color:#A32D2D;'>Offer Declined</h2>"
            "<p>Thank you for letting us know, <b>" + (candidate_name or "") + "</b>.</p>"
            "<p>We appreciate your time and wish you all the best.</p>"
            "</div>"
        )
