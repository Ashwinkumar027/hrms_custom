import frappe
from frappe.utils import getdate, add_days

def generate_token(doc, method):
    if not doc.custom_guest_token:
        doc.custom_guest_token = frappe.generate_hash(length=20)

@frappe.whitelist(allow_guest=True)
def submit_candidate_response(token, action, reason=None, new_date=None, new_time=None):
    if not token:
        frappe.throw("Invalid or missing token")
        
    interview = frappe.get_all(
        "Interview",
        filters={"custom_guest_token": token, "status": "Pending"},
        fields=["name", "custom_candidate_response"],
        limit=1
    )
    
    if not interview:
        frappe.throw("Interview not found or invalid token.")
        
    if interview[0].custom_candidate_response and interview[0].custom_candidate_response != "Pending":
        frappe.throw("You have already submitted a response for this interview.")
        
    interview_name = interview[0].name
    doc = frappe.get_doc("Interview", interview_name)
    
    if action == "accept":
        doc.custom_candidate_response = "Accepted"
    elif action == "reject":
        if not reason:
            frappe.throw("Reason is mandatory when rejecting.")
        doc.custom_candidate_response = "Rejected"
        doc.custom_candidate_reason = reason
    elif action == "reschedule":
        if not reason or not new_date or not new_time:
            frappe.throw("Reason, new date, and new time are mandatory when rescheduling.")
            
        proposed_date = getdate(new_date)
        original_date = getdate(doc.scheduled_on)
        max_allowed_date = add_days(original_date, 2)
        
        if proposed_date < getdate():
            frappe.throw("Reschedule date cannot be in the past.")
            
        if proposed_date > max_allowed_date:
            frappe.throw(f"Reschedule date cannot be more than 2 days after original schedule ({max_allowed_date}).")
            
        doc.custom_candidate_response = "Reschedule Requested"
        doc.custom_candidate_reason = reason
        doc.custom_proposed_reschedule_date = new_date
        doc.custom_proposed_reschedule_time = new_time
    else:
        frappe.throw("Invalid action")
        
    doc.save(ignore_permissions=True)
    
    # Notify HR and Interviewer
    send_response_notification(doc)
    
    frappe.db.commit()
    return "Success"

def send_response_notification(doc):
    # Collect recipients: HR usually has a role, or we can send to a default hr email
    # The user mentioned HR and Interviewer. Let's get the interviewers list.
    recipients = []
    
    # Find all interviewers
    for i in doc.interview_details:
        if i.interviewer:
            recipients.append(i.interviewer)
            
    # Find all users with HR Manager role
    hr_manager_users = frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"]
    )
    for u in hr_manager_users:
        email = frappe.db.get_value("User", u.parent, "email")
        if email:
            recipients.append(email)
            
    # Add HR email from Settings as fallback/additional
    hr_sender = frappe.db.get_single_value("HR Settings", "sender_email")
    if hr_sender:
        recipients.append(hr_sender)
        
    recipients = list(set(recipients))
    
    subject = f"Candidate Response: {doc.custom_candidate_response} for {doc.name}"
    
    applicant_name = frappe.db.get_value("Job Applicant", doc.job_applicant, "applicant_name") or doc.job_applicant
    
    message = f"""
    <p>Hello,</p>
    <p>The candidate <b>{applicant_name}</b> (for Job Applicant {doc.job_applicant}) has responded to the interview schedule.</p>
    <p><b>Response:</b> {doc.custom_candidate_response}</p>
    """
    
    if doc.custom_candidate_response in ["Rejected", "Reschedule Requested"]:
        message += f"<p><b>Reason provided:</b> {doc.custom_candidate_reason}</p>"
        
    if doc.custom_candidate_response == "Reschedule Requested":
        message += f"<p><b>Proposed Date:</b> {doc.custom_proposed_reschedule_date}</p>"
        message += f"<p><b>Proposed Time:</b> {doc.custom_proposed_reschedule_time}</p>"
        
    message += f"<p><a href='/app/interview/{doc.name}'>Click here to view the Interview</a></p>"
    
    frappe.sendmail(
        recipients=recipients,
        sender=hr_sender or None,
        subject=subject,
        message=message
    )
