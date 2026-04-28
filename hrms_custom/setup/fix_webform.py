import frappe

def fix_pre_offer_webform():
    wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
    wf.allow_multiple = 0
    wf.allow_edit = 1
    wf.login_required = 0

    # Make fields editable
    for field in wf.web_form_fields:
        if field.fieldname in ["applicant_name", "email_id", "phone_number"]:
            field.read_only = 0

    wf.client_script = """
frappe.ready(function() {
    var params = new URLSearchParams(window.location.search);
    var applicant_name = params.get('applicant_name');
    var email = params.get('email');
    var phone = params.get('phone');
    var job_applicant = params.get('job_applicant');

    // Set the name field to link to existing Job Applicant
    if (job_applicant) {
        frappe.web_form.doc.name = decodeURIComponent(job_applicant);
    }

    function fill_fields() {
        if (applicant_name) {
            frappe.web_form.set_value('applicant_name', decodeURIComponent(applicant_name));
        }
        if (email) {
            frappe.web_form.set_value('email_id', decodeURIComponent(email));
        }
        if (phone) {
            frappe.web_form.set_value('phone_number', decodeURIComponent(phone));
        }
    }

    setTimeout(fill_fields, 500);
    setTimeout(fill_fields, 1500);
});
"""
    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print("Web Form updated!")
