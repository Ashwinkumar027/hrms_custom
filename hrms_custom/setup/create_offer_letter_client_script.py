import frappe

def create_offer_letter_client_script():
    print("\n--- Creating Offer Letter Client Script ---")

    name = "Job Offer - Send Offer Letter Button"

    if frappe.db.exists("Client Script", name):
        frappe.delete_doc("Client Script", name, ignore_permissions=True)

    cs = frappe.new_doc("Client Script")
    cs.name = name
    cs.dt = "Job Offer"
    cs.module = "HRMS Custom"
    cs.enabled = 1
    cs.script = """
frappe.ui.form.on('Job Offer', {
    refresh(frm) {
        if (!frm.is_new()) {

            // Show offer response status
            if (frm.doc.custom_offer_response === 'Accepted') {
                frm.set_intro('Candidate has ACCEPTED the offer!', 'green');
            } else if (frm.doc.custom_offer_response === 'Rejected') {
                frm.set_intro('Candidate has DECLINED the offer.', 'red');
            } else if (frm.doc.custom_offer_sent) {
                frm.set_intro('Offer Letter sent. Awaiting candidate response...', 'orange');
            }

            if (frm.doc.custom_offer_sent) {
                // Resend button
                frm.add_custom_button(__('Resend Offer Letter'), function() {
                    send_offer_letter(frm);
                }, __('Offer Letter')).addClass('btn-warning');
            } else {
                // Send button
                frm.add_custom_button(__('Send Offer Letter'), function() {
                    send_offer_letter(frm);
                }, __('Offer Letter')).addClass('btn-success');
            }
        }
    }
});

function send_offer_letter(frm) {
    let candidate = frm.doc.applicant_name || frm.doc.job_applicant;
    frappe.confirm(
        __('Send Offer Letter to <b>{0}</b>?<br><br>Candidate will receive an email with Accept/Reject buttons.', [candidate]),
        function() {
            frappe.call({
                method: 'hrms_custom.api.send_offer_letter',
                args: { job_offer: frm.doc.name },
                freeze: true,
                freeze_message: __('Sending Offer Letter...'),
                callback: function(r) {
                    if (!r.exc && r.message && r.message.success) {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'green'
                        }, 7);
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
