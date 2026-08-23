import frappe

def execute():
    try:
        meta = frappe.get_meta("Job Applicant")
        
        print("Job Applicant Fields:")
        for f in meta.fields:
            label = f.label.lower() if f.label else ""
            fname = f.fieldname.lower() if f.fieldname else ""
            if "mother" in fname or "mother" in label:
                print(f"  Doctype -> Label: {f.label}, Fieldname: {f.fieldname}")
            if "emergency" in fname or "emergency" in label:
                print(f"  Doctype -> Label: {f.label}, Fieldname: {f.fieldname}")
                
        print("\nWeb Form Fields:")
        wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
        for f in wf.web_form_fields:
            label = f.label.lower() if f.label else ""
            fname = f.fieldname.lower() if f.fieldname else ""
            if "mother" in fname or "mother" in label:
                print(f"  WebForm -> Label: {f.label}, Fieldname: {f.fieldname}")
            if "emergency" in fname or "emergency" in label:
                print(f"  WebForm -> Label: {f.label}, Fieldname: {f.fieldname}")
                
    except Exception as e:
        print(f"Error: {e}")
