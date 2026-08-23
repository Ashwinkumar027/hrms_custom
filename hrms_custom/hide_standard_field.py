import frappe

def execute():
    try:
        # Check if Property Setter already exists
        exists = frappe.db.exists("Property Setter", {
            "doc_type": "Job Requisition",
            "field_name": "reason_for_requesting",
            "property": "hidden"
        })
        
        if not exists:
            # Create a new Property Setter to hide the field
            doc = frappe.get_doc({
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": "Job Requisition",
                "field_name": "reason_for_requesting",
                "property": "hidden",
                "property_type": "Check",
                "value": "1",
                "module": "HRMS custom"
            })
            doc.insert()
            frappe.db.commit()
            print("Property Setter created: Hidden 'reason_for_requesting'.")
        else:
            # Update existing if needed
            doc = frappe.get_doc("Property Setter", exists)
            doc.value = "1"
            doc.module = "HRMS custom"
            doc.save()
            frappe.db.commit()
            print("Property Setter updated: Hidden 'reason_for_requesting'.")
            
    except Exception as e:
        print(f"Error: {e}")
