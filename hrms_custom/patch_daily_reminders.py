import frappe

def execute():
    try:
        ss = frappe.get_doc("Server Script", "Job Requisition Daily Reminders")
        old_script = ss.script
        
        # Replace the forbidden getattr calls
        # getattr(doc, "fieldname", "") -> doc.get("fieldname", "")
        # getattr(doc, 'fieldname', '') -> doc.get('fieldname', '')
        
        new_script = old_script.replace("getattr(doc, \"", "doc.get(\"")
        new_script = new_script.replace("getattr(doc, '", "doc.get('")
        
        if old_script != new_script:
            ss.script = new_script
            ss.save()
            frappe.db.commit()
            print("Successfully patched 'Job Requisition Daily Reminders' in the database.")
        else:
            print("No changes made. 'getattr' not found exactly as expected.")
            
    except Exception as e:
        print(f"Error: {e}")
