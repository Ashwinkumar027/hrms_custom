import frappe

def create_id_card_operator_role():
    print("\n--- Creating ID Card Operator Role ---")

    if not frappe.db.exists("Role", "ID Card Operator"):
        role = frappe.new_doc("Role")
        role.role_name = "ID Card Operator"
        role.desk_access = 1
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        print("  Created: ID Card Operator role")
    else:
        print("  Already exists: ID Card Operator role")

    print("Done!")
