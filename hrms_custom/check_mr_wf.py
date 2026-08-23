import frappe

def execute():
    try:
        wf = frappe.get_doc("Workflow", "Manpower Requisition Flow")
        print(f"Workflow: {wf.name} (Active: {wf.is_active})")
        print("States and Permissions:")
        for s in wf.states:
            roles = frappe.get_all("Workflow Document State", filters={"parent": wf.name, "state": s.state}, fields=["allow_edit"])
            allow_roles = [r.allow_edit for r in roles]
            print(f"- State: {s.state}, Roles allowed: {', '.join(allow_roles)}")
            
    except Exception as e:
        print(f"Error: {e}")
