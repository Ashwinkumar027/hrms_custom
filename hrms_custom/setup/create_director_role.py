import frappe

def create_director_role():
    print("\n--- Creating Director Role ---")

    if not frappe.db.exists("Role", "Director"):
        role = frappe.new_doc("Role")
        role.role_name = "Director"
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        print("  Created: Director role")
    else:
        print("  Already exists: Director role")
    print("Done!")
