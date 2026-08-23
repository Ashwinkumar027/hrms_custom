import frappe
import json
import re

def execute():
    try:
        wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
        
        # Get all valid data fieldnames from web form
        wf_fields = [f.fieldname for f in wf.web_form_fields if f.fieldname and f.fieldtype not in ["Section Break", "Column Break", "HTML", "Button"]]
        
        # Always include resume_attachment just in case it's missed
        if "resume_attachment" not in wf_fields:
            wf_fields.append("resume_attachment")
            
        ss = frappe.get_doc("Server Script", "Merge Pre-Offer Form to Job Applicant")
        old_script = ss.script
        
        # Format the new fields_to_merge array
        new_array_str = "    fields_to_merge = [\n"
        for field in wf_fields:
            new_array_str += f'        "{field}",\n'
        new_array_str += "    ]"
        
        # Regex to replace the old fields_to_merge array
        # It looks for `fields_to_merge = [` followed by anything until `]`
        new_script = re.sub(r'    fields_to_merge = \[[^\]]+\]', new_array_str, old_script)
        
        if new_script != old_script:
            ss.script = new_script
            ss.save()
            frappe.db.commit()
            print("Successfully updated Merge Pre-Offer Form script with all Web Form fields!")
            print(f"Total fields to merge: {len(wf_fields)}")
        else:
            print("Regex replacement failed or no changes needed.")
            
    except Exception as e:
        print(f"Error: {e}")
