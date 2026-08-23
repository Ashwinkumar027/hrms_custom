import frappe

def execute():
    try:
        scripts = frappe.get_all("Server Script", filters={"reference_doctype": "Job Applicant"}, fields=["name", "script"])
        for s in scripts:
            if "custom_original_applicant_id" in s.script:
                print(f"--- {s.name} ---")
                print(s.script)
    except Exception as e:
        print(f"Error: {e}")
