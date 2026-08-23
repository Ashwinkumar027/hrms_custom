import frappe

def execute():
    try:
        fields = frappe.get_all("Custom Field", filters={"dt": "Job Requisition", "fieldname": ["like", "%reject%"]}, fields=["fieldname", "label"])
        print("Fields containing 'reject':", fields)
        
        # Also check standard fields just in case
        meta = frappe.get_meta("Job Requisition")
        standard_fields = [f.fieldname for f in meta.fields if "reject" in f.fieldname]
        print("Standard fields containing 'reject':", standard_fields)
    except Exception as e:
        print(f"Error: {e}")
