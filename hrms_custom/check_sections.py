import frappe

def execute():
    try:
        meta = frappe.get_meta("Employee Onboarding")
        found = False
        for f in meta.fields:
            if f.fieldname == "activities":
                found = True
                print(f"--- ACTIVITIES TABLE FOUND ---")
            
            if f.fieldtype == "Section Break" and not found:
                print(f"Section Break: {f.fieldname} ({f.label}) - Hidden: {f.hidden}, Depends On: {f.depends_on}")
                
            if found:
                break
    except Exception as e:
        print(f"Error: {e}")
