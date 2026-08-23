import frappe

def execute():
    try:
        # Create or update property setter to unhide the section break
        if not frappe.db.exists("Property Setter", "Employee Onboarding-table_for_activity-hidden"):
            frappe.get_doc({
                "doctype": "Property Setter",
                "doc_type": "Employee Onboarding",
                "field_name": "table_for_activity",
                "property": "hidden",
                "value": "0",
                "property_type": "Check",
                "module": "HRMS custom"
            }).insert()
        else:
            ps = frappe.get_doc("Property Setter", "Employee Onboarding-table_for_activity-hidden")
            ps.value = "0"
            ps.save()
            
        frappe.db.commit()
        print("Successfully unhidden the 'Onboarding Activities' Section Break!")
        
    except Exception as e:
        print(f"Error: {e}")
