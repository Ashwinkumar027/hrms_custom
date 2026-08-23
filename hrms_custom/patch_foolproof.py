import frappe

def execute():
    try:
        # 1. Update Custom Field Depends On
        cf = frappe.get_doc("Custom Field", "Job Requisition-custom_rejection_reason")
        cf.depends_on = "eval:doc.workflow_state == 'Rejected'"
        cf.save()
        print("Updated Custom Field depends_on.")

        # 2. Patch Client Script for fool-proof save
        cs = frappe.get_doc("Client Script", "Job Requisition Enhancements")
        script = cs.script
        
        # Remove the old refresh hide logic since we use depends_on now
        refresh_logic = "frm.set_df_property('custom_rejection_reason', 'hidden', frm.doc.workflow_state !== 'Rejected');"
        if refresh_logic in script:
            script = script.replace(refresh_logic, "")
            
        # Update the before_workflow_action to actually perform a save!
        target_block = """                        frm.set_df_property('custom_rejection_reason', 'hidden', 0);
                        frm.doc.custom_rejection_reason = values.reason;
                        frm.set_value('custom_rejection_reason', values.reason);
                        frm.dirty();
                        d.hide();
                        resolve();"""
                        
        replacement_block = """                        frm.set_value('custom_rejection_reason', values.reason).then(() => {
                            frm.save('Save').then(() => {
                                d.hide();
                                resolve();
                            });
                        });"""
        
        if target_block in script:
            script = script.replace(target_block, replacement_block)
            print("Successfully patched Client Script for DB save.")
        else:
            print("Could not find the target block in Client Script.")
            
        cs.script = script
        cs.save()
        
        frappe.db.commit()
        print("All patches applied.")
            
    except Exception as e:
        print(f"Error: {e}")
