import frappe

def execute():
    try:
        meta = frappe.get_meta("Employee Onboarding")
        f = meta.get_field("activities")
        print(f"Field: {f.fieldname}, Hidden: {f.hidden}, Depends On: {f.depends_on}, Read Only: {f.read_only}")
    except Exception as e:
        print(f"Error: {e}")
