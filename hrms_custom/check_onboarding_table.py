import frappe

def execute():
    try:
        fields = frappe.get_meta("Employee Onboarding").fields
        for f in fields:
            if f.fieldtype == "Table" or f.fieldname == "activities":
                print(f"Field: {f.fieldname} ({f.fieldtype}) - Depends On: {f.depends_on} - Hidden: {f.hidden}")
    except Exception as e:
        print(f"Error: {e}")
