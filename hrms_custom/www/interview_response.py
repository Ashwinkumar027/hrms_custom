import frappe

def get_context(context):
    token = frappe.form_dict.get("token")
    action = frappe.form_dict.get("action")
    
    if not token or not action:
        context.error_message = "Invalid or missing token and action."
        return context
        
    interview = frappe.get_all(
        "Interview",
        filters={"custom_guest_token": token, "status": "Pending"},
        fields=["name", "job_applicant", "interview_type", "scheduled_on", "from_time", "to_time", "custom_candidate_response"],
        limit=1
    )
    
    if not interview:
        context.error_message = "Interview not found or invalid token."
        return context
        
    if interview[0].custom_candidate_response and interview[0].custom_candidate_response != "Pending":
        context.error_message = "You have already submitted a response for this interview."
        return context
        
    context.interview = interview[0]
    context.action = action
    context.token = token
    return context
