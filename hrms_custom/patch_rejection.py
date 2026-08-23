import frappe

def execute():
    try:
        # 1. Patch Client Script
        cs = frappe.get_doc("Client Script", "Job Requisition Enhancements")
        script = cs.script
        
        target = 'if (frm.selected_workflow_action === "Reject") {'
        replacement = 'if (["HR Reject", "Final Reject", "Reject"].includes(frm.selected_workflow_action)) {'
        
        if target in script:
            script = script.replace(target, replacement)
            cs.script = script
            cs.save()
            print("Successfully patched 'Job Requisition Enhancements' Client Script.")
        else:
            print("Could not find the target string in the Client script.")

        # 2. Patch Server Script
        ss = frappe.get_doc("Server Script", "Job Requisition Workflow Emails")
        ss_script = ss.script
        
        # We need to add HR Manager to CC for Rejected emails.
        # Find the Rejected block and modify recipients/cc.
        reject_target = '''        if recipient_email:
            form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
            frappe.sendmail(
                recipients=[recipient_email],'''
        
        reject_replacement = '''        if recipient_email:
            # Also get HR Managers for CC
            hr_users = frappe.get_all("Has Role", filters={"role": "HR Manager", "parenttype": "User"}, fields=["parent"])
            hr_cc = []
            for u in hr_users:
                email = frappe.db.get_value("User", u.parent, "email")
                if email and email != recipient_email: hr_cc.append(email)
                
            form_url = frappe.utils.get_url_to_form(doc.doctype, doc.name)
            frappe.sendmail(
                recipients=[recipient_email],
                cc=hr_cc,'''
                
        if reject_target in ss_script:
            ss_script = ss_script.replace(reject_target, reject_replacement)
            ss.script = ss_script
            ss.save()
            print("Successfully patched 'Job Requisition Workflow Emails' Server Script.")
        else:
            print("Could not find the target string in the Server script.")
            
        frappe.db.commit()
            
    except Exception as e:
        print(f"Error: {e}")
