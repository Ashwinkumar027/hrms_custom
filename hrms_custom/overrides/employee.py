import frappe

@frappe.whitelist()
def deactivate_sales_person(status: str, employee: str = None):
    if not employee:
        return  # safely skip if no employee passed

    frappe.has_permission("Employee", doc=employee, ptype="write", throw=True)
    
    if status == "Left":
        sales_person = frappe.db.get_value(
            "Sales Person", {"Employee": employee}
        )
        if sales_person:
            frappe.db.set_value("Sales Person", sales_person, "enabled", 0)
