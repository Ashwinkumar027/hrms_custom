import frappe

def execute():
    try:
        # Patch Client Script
        cs = frappe.get_doc("Client Script", "Job Requisition Enhancements")
        script = cs.script
        
        # 1. Hide custom_rejection_reason in refresh
        refresh_target = "frm.set_df_property('status', 'hidden', 1);"
        refresh_replacement = "frm.set_df_property('status', 'hidden', 1);\n        frm.set_df_property('custom_rejection_reason', 'hidden', frm.doc.workflow_state !== 'Rejected');"
        if refresh_target in script:
            script = script.replace(refresh_target, refresh_replacement)
            
        # 2. Fix the white blur screen in before_workflow_action by unfreezing
        before_action_target = 'if (["HR Reject", "Final Reject", "Reject"].includes(frm.selected_workflow_action)) {\n            return new Promise((resolve, reject) => {'
        before_action_replacement = 'if (["HR Reject", "Final Reject", "Reject"].includes(frm.selected_workflow_action)) {\n            frappe.dom.unfreeze();\n            return new Promise((resolve, reject) => {'
        if before_action_target in script:
            script = script.replace(before_action_target, before_action_replacement)
            
        # 3. Enhance dialog fields
        dialog_target = "label: 'Reason',"
        dialog_replacement = "label: 'Reason for Rejection',"
        if dialog_target in script:
            script = script.replace(dialog_target, dialog_replacement)

        cs.script = script
        cs.save()
        frappe.db.commit()
        print("Successfully patched 'Job Requisition Enhancements' Client Script.")
            
    except Exception as e:
        print(f"Error: {e}")
