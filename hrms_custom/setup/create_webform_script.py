import frappe

def create_preoffer_client_script():
    print("\n--- Updating Pre-Offer Web Form Client Script ---")

    wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
    wf.client_script = """
// Pre-fill fields from URL parameter
frappe.ready(function() {
    var name = frappe.utils.get_url_arg('name');
    if (name) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Job Applicant',
                name: name
            },
            callback: function(r) {
                if (r.message) {
                    var doc = r.message;
                    frappe.web_form.set_value('applicant_name', doc.applicant_name);
                    frappe.web_form.set_value('email_id', doc.email_id);
                    frappe.web_form.set_value('phone_number', doc.phone_number);
                }
            }
        });
    }
});
"""
    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print("Client script added to Pre-Offer Web Form!")
