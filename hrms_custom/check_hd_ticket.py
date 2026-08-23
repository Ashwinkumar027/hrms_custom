import frappe

def execute():
    try:
        ss = frappe.get_doc("Server Script", "Sync HD Ticket Status")
        print(f"Script Name: {ss.name}")
        print(f"DocType: {ss.reference_doctype}")
        print(f"Event: {ss.doctype_event}")
        print("\n--- Script Content ---")
        print(ss.script)
    except Exception as e:
        print(f"Error: {e}")
