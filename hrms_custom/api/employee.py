import frappe
import re

@frappe.whitelist()
def get_last_employee_id(company):
    last_emp = frappe.get_all("Employee", 
        filters={"company": company}, 
        fields=["name"], 
        order_by="creation desc", 
        limit=1
    )
    
    if not last_emp:
        return {"last_id": "No employees yet", "next_id": ""}
        
    last_id = last_emp[0].name
    
    next_id = ""
    match = re.search(r'(\d+)$', last_id)
    if match:
        number_str = match.group(1)
        number_len = len(number_str)
        next_number = int(number_str) + 1
        prefix = last_id[:match.start()]
        next_id = f"{prefix}{str(next_number).zfill(number_len)}"
        
    return {
        "last_id": last_id,
        "next_id": next_id
    }
