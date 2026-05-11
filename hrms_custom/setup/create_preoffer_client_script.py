import frappe

def create_preoffer_client_script():
    print("\n--- Creating Pre-Offer Button Client Script ---")

    name = "Job Applicant - Send Pre-Offer Form Button"

    if frappe.db.exists("Client Script", name):
        frappe.delete_doc("Client Script", name, ignore_permissions=True)
        print("  Deleted existing script")

    cs = frappe.new_doc("Client Script")
    cs.name = name
    cs.dt = "Job Applicant"
    cs.module = "HRMS Custom"
    cs.enabled = 1
    cs.script = """
frappe.ui.form.on('Job Applicant', {
    refresh(frm) {
        // Show Send Pre-Offer Form button
        if (!frm.is_new()) {

            if (frm.doc.custom_preoffer_form_sent) {
                // Already sent — show resend button
                frm.add_custom_button(__('Resend Pre-Offer Form'), function() {
                    send_preoffer_form(frm);
                }, __('Pre-Offer')).addClass('btn-warning');

                // Show sent info
                frm.set_intro(
                    __('Pre-Offer Form sent on {0} by {1}',
                    [
                        frappe.datetime.str_to_user(frm.doc.custom_preoffer_sent_on),
                        frm.doc.custom_preoffer_sent_by
                    ]),
                    'green'
                );
            } else {
                // Not sent yet — show send button
                frm.add_custom_button(__('Send Pre-Offer Form'), function() {
                    send_preoffer_form(frm);
                }, __('Pre-Offer')).addClass('btn-primary');
            }
        }
    }
});

function send_preoffer_form(frm) {
    // Confirm before sending
    frappe.confirm(
        __('Send Pre-Offer Form to <b>{0}</b> ({1})?',
        [frm.doc.applicant_name, frm.doc.email_id]),
        function() {
            frappe.call({
                method: 'hrms_custom.api.send_preoffer_form',
                args: {
                    job_applicant: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Sending Pre-Offer Form...'),
                callback: function(r) {
                    if (!r.exc) {
                        frappe.show_alert({
                            message: __('Pre-Offer Form sent to {0}!',
                                [frm.doc.applicant_name]),
                            indicator: 'green'
                        }, 5);
                        frm.reload_doc();
                    }
                }
            });
        }
    );
}
"""

    cs.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  Created: " + name)
    print("Client Script created!")
