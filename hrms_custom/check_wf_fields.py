import frappe

def execute():
    try:
        wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
        for f in wf.web_form_fields:
            print(f"{f.fieldname} ({f.fieldtype}) - Hidden: {f.hidden}")
    except Exception as e:
        print(f"Error: {e}")
