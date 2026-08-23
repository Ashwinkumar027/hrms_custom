import frappe

def execute():
    try:
        # Find Ashwinkumar's onboarding document
        onb = frappe.get_doc("Employee Onboarding", "HR-EMP-ONB-2026-00005") # based on the screenshot URL
        
        # Find tickets created for this onboarding
        # Usually tickets are linked via subject or they are just all tickets raised today for this employee
        # Since it's Ashwinkumar, let's search HD Ticket by employee_name in subject
        tickets = frappe.get_all("HD Ticket", filters={"subject": ["like", "%Ashwinkumar%"]}, fields=["name", "subject", "status"])
        
        if not tickets:
            print("No tickets found for Ashwinkumar.")
            return

        print(f"Found {len(tickets)} tickets. Linking to Employee Onboarding...")
        
        onb.set("activities", [])
        
        for t in tickets:
            # Re-create the activity row
            onb.append("activities", {
                "activity_name": t.subject,
                "custom_ticket_id": t.name,
                "custom_status": t.status,
                "user": "admin@example.com" # fallback
            })
            
        onb.flags.ignore_validate_update_after_submit = True
        onb.save(ignore_permissions=True)
        frappe.db.commit()
        print("Successfully linked tickets to Ashwinkumar's activities!")
        
    except Exception as e:
        print(f"Error: {e}")
