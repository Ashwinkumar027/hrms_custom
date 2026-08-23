import frappe
import json

def execute():
    try:
        wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
        
        # Get all fieldnames from web form
        wf_fields = [f.fieldname for f in wf.web_form_fields if f.fieldname and f.fieldtype not in ["Section Break", "Column Break", "HTML"]]
        
        # Read the current server script
        ss = frappe.get_doc("Server Script", "Merge Pre-Offer Form to Job Applicant")
        
        missing = []
        for wf_f in wf_fields:
            if wf_f not in ss.script:
                missing.append(wf_f)
                
        print("Fields in Web Form but missing from Merge Script:")
        for m in missing:
            print(f"- {m}")
            
    except Exception as e:
        print(f"Error: {e}")
