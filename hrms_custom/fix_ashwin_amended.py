import frappe

def execute():
    try:
        onb_name = "HR-EMP-ONB-2026-00005-1"
        onb = frappe.get_doc("Employee Onboarding", onb_name)
        
        tickets = frappe.get_all("HD Ticket", filters={"subject": ["like", "%Ashwinkumar%"]}, fields=["name", "subject", "status"], order_by="creation desc", limit=13)
        
        if not tickets:
            print("No tickets found.")
            return
            
        onb.set("activities", [])
        tickets.reverse()
        
        for t in tickets:
            onb.append("activities", {
                "activity_name": t.subject,
                "custom_ticket_id": t.name,
                "custom_status": t.status
            })
            
        onb.flags.ignore_validate_update_after_submit = True
        onb.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Successfully linked tickets to {onb_name}!")
        
    except Exception as e:
        print(f"Error: {e}")
