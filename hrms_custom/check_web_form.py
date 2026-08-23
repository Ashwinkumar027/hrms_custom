import frappe

def execute():
    try:
        wf = frappe.get_doc("Web Form", "candidate-pre-offer-form")
        print(f"Web Form: {wf.name}")
        print(f"DocType: {wf.doc_type}")
        print(f"Allow Edit: {wf.allow_edit}")
        print(f"Allow Multiple: {wf.allow_multiple}")
        print(f"Is Standard: {wf.is_standard}")
    except Exception as e:
        print(f"Error: {e}")
