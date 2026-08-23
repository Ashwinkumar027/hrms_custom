import frappe

def execute():
    try:
        ss = frappe.get_doc("Server Script", "Job Requisition Workflow Emails")
        old_script = ss.script
        
        # Replace the forbidden getattr call
        new_script = old_script.replace(
            "getattr(frappe.flags, 'in_test', False)",
            "frappe.flags.get('in_test', False)"
        )
        
        if old_script != new_script:
            ss.script = new_script
            ss.save()
            frappe.db.commit()
            print("Successfully patched 'Job Requisition Workflow Emails' in the database.")
        else:
            print("No changes made. 'getattr' not found exactly as expected.")
            
    except Exception as e:
        print(f"Error: {e}")
