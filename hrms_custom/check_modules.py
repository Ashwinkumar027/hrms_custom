import frappe

def execute():
    try:
        # 1. Client Script
        cs = frappe.get_doc("Client Script", "Job Requisition Enhancements")
        print(f"Client Script '{cs.name}' module: {cs.module}")
        if cs.module != "HRMS custom":
            cs.module = "HRMS custom"
            cs.save()
            print("Fixed Client Script module.")
            
        # 2. Server Script
        ss = frappe.get_doc("Server Script", "Job Requisition Workflow Emails")
        print(f"Server Script '{ss.name}' module: {ss.module}")
        if ss.module != "HRMS custom":
            ss.module = "HRMS custom"
            ss.save()
            print("Fixed Server Script module.")
            
        # 3. Custom Field
        cf = frappe.get_doc("Custom Field", "Job Requisition-custom_rejection_reason")
        print(f"Custom Field '{cf.name}' module: {cf.module}")
        if cf.module != "HRMS custom":
            cf.module = "HRMS custom"
            cf.save()
            print("Fixed Custom Field module.")
            
        # 4. Property Setter (Reason for Requesting)
        exists = frappe.db.exists("Property Setter", {
            "doc_type": "Job Requisition",
            "field_name": "reason_for_requesting",
            "property": "hidden"
        })
        if exists:
            ps = frappe.get_doc("Property Setter", exists)
            print(f"Property Setter '{ps.name}' module: {ps.module}")
            if ps.module != "HRMS custom":
                ps.module = "HRMS custom"
                ps.save()
                print("Fixed Property Setter module.")
        
        frappe.db.commit()
        print("All modules verified.")
            
    except Exception as e:
        print(f"Error: {e}")
