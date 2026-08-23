import frappe

def execute():
    try:
        fields = frappe.get_meta("Job Applicant").fields
        for f in fields:
            if "job" in f.fieldname or "title" in f.fieldname or "open" in f.fieldname:
                print(f"{f.fieldname} ({f.fieldtype}) - {f.label}")
    except Exception as e:
        print(f"Error: {e}")
