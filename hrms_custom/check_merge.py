import frappe

def execute():
    try:
        ss = frappe.get_doc("Server Script", "Merge Pre-Offer Form to Job Applicant")
        print(f"Script Name: {ss.name}")
        print(f"DocType: {ss.reference_doctype}")
        print(f"DocType Event: {ss.doctype_event}")
        print("\n--- Script Content ---")
        print(ss.script)
    except Exception as e:
        print(f"Error: {e}")
