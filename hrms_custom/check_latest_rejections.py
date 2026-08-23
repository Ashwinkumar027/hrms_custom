import frappe

def execute():
    try:
        # Get the latest Rejected job requisition
        reqs = frappe.db.sql("""
            SELECT name, custom_rejection_reason 
            FROM `tabJob Requisition` 
            WHERE workflow_state = 'Rejected' 
            ORDER BY modified DESC LIMIT 5
        """, as_dict=True)
        
        for req in reqs:
            print(f"{req.name}: {req.custom_rejection_reason}")
    except Exception as e:
        print(f"Error: {e}")
