import frappe

def execute():
    try:
        cs = frappe.get_doc("Client Script", "Job Requisition Enhancements")
        script = cs.script
        
        target = "frm.set_value('custom_rejection_reason', values.reason);"
        replacement = """frm.set_df_property('custom_rejection_reason', 'hidden', 0);
                        frm.doc.custom_rejection_reason = values.reason;
                        frm.set_value('custom_rejection_reason', values.reason);
                        frm.dirty();"""
        
        if target in script:
            script = script.replace(target, replacement)
            cs.script = script
            cs.save()
            frappe.db.commit()
            print("Successfully patched 'Job Requisition Enhancements' Client Script.")
        else:
            print("Could not find target to patch.")
            
    except Exception as e:
        print(f"Error: {e}")
