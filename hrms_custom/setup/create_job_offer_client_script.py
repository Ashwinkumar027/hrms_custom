import frappe

def create_job_offer_client_script():
    print("\n--- Creating Job Offer Client Script ---")

    name = "Job Offer - Fetch CTC from Job Requisition"

    if frappe.db.exists("Client Script", name):
        frappe.delete_doc("Client Script", name, ignore_permissions=True)
        print("  Deleted existing")

    cs = frappe.new_doc("Client Script")
    cs.name = name
    cs.dt = "Job Offer"
    cs.module = "HRMS Custom"
    cs.enabled = 1
    cs.script = """
frappe.ui.form.on('Job Offer', {

    job_requisition(frm) {
        if (frm.doc.job_requisition) {
            frappe.db.get_value(
                'Job Requisition',
                frm.doc.job_requisition,
                ['custom_proposed_salary', 'designation', 'department',
                 'custom_urgency_level', 'no_of_positions'],
                function(r) {
                    if (r) {
                        // Set Proposed CTC from Job Requisition
                        if (r.custom_proposed_salary) {
                            frm.set_value('custom_proposed_ctc',
                                r.custom_proposed_salary);
                            frappe.show_alert({
                                message: __('Proposed CTC fetched from Job Requisition: {0}',
                                    [r.custom_proposed_salary]),
                                indicator: 'green'
                            }, 5);
                        }

                        // Auto-fill Designation if empty
                        if (r.designation && !frm.doc.designation) {
                            frm.set_value('designation', r.designation);
                        }
                    }
                }
            );
        } else {
            // Clear CTC if requisition is cleared
            frm.set_value('custom_proposed_ctc', '');
        }
    },

    refresh(frm) {
        // Show Job Requisition details if linked
        if (frm.doc.job_requisition && !frm.is_new()) {
            frappe.db.get_value(
                'Job Requisition',
                frm.doc.job_requisition,
                ['custom_proposed_salary', 'custom_urgency_level',
                 'no_of_positions', 'workflow_state'],
                function(r) {
                    if (r) {
                        frm.set_intro(
                            __('Linked Requisition: {0} | Budget: {1} | Urgency: {2}',
                            [
                                frm.doc.job_requisition,
                                r.custom_proposed_salary || 'Not set',
                                r.custom_urgency_level || 'Not set'
                            ]),
                            'blue'
                        );
                    }
                }
            );
        }
    }
});
"""

    cs.insert(ignore_permissions=True)
    frappe.db.commit()
    print("  Created: " + name)
    print("Done!")
