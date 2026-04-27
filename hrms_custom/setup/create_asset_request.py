import frappe

def create_new_joiner_asset_request():
    print("\n--- Creating New Joiner Asset Request DocType ---")

    # Delete existing if in wrong module
    if frappe.db.exists("DocType", "New Joiner Asset Request"):
        frappe.delete_doc("DocType", "New Joiner Asset Request",
            ignore_permissions=True, force=True)
        print("  Deleted existing DocType")

    dt = frappe.new_doc("DocType")
    dt.name = "New Joiner Asset Request"
    dt.module = "HRMS Custom"
    dt.custom = 0
    dt.is_submittable = 1
    dt.track_changes = 1
    dt.autoname = "HR-ASSET-.YYYY.-.#####"

    # Fields
    dt.append("fields", {
        "fieldname": "new_joiner_name",
        "fieldtype": "Link",
        "label": "New Joiner Name",
        "options": "Employee",
        "reqd": 1,
        "in_list_view": 1
    })
    dt.append("fields", {
        "fieldname": "department_head",
        "fieldtype": "Link",
        "label": "Department Head",
        "options": "Employee",
        "reqd": 1
    })
    dt.append("fields", {
        "fieldname": "column_break_details",
        "fieldtype": "Column Break"
    })
    dt.append("fields", {
        "fieldname": "status",
        "fieldtype": "Select",
        "label": "Status",
        "options": "Draft\nPending Manager Approval\nApproved\nRejected",
        "default": "Draft",
        "read_only": 1,
        "in_list_view": 1
    })
    dt.append("fields", {
        "fieldname": "section_break_account_setup",
        "fieldtype": "Section Break",
        "label": "Account Setup"
    })
    dt.append("fields", {
        "fieldname": "email_action",
        "fieldtype": "Select",
        "label": "Email Action",
        "options": "\nCreate a Fresh Email ID\nRename the Email with Relieving Employee\nDo Not Create an Email ID",
        "reqd": 1
    })
    dt.append("fields", {
        "fieldname": "rename_email_employee",
        "fieldtype": "Data",
        "label": "Mention Employee Name for Email Rename",
        "depends_on": "eval:doc.email_action=='Rename the Email with Relieving Employee'",
        "mandatory_depends_on": "eval:doc.email_action=='Rename the Email with Relieving Employee'"
    })
    dt.append("fields", {
        "fieldname": "column_break_assets",
        "fieldtype": "Column Break"
    })
    dt.append("fields", {
        "fieldname": "system_requirement",
        "fieldtype": "Select",
        "label": "System Requirement",
        "options": "\nRequire a Desktop\nRequire a Laptop\nReplacement Available\nSystem is Not Required",
        "reqd": 1
    })
    dt.append("fields", {
        "fieldname": "sim_card",
        "fieldtype": "Select",
        "label": "SIM Card",
        "options": "\nRequire a New Prepaid SIM Card\nRequire a New Postpaid SIM Card\nReplacement Available\nSIM Card is Not Required",
        "reqd": 1
    })
    dt.append("fields", {
        "fieldname": "seating_location",
        "fieldtype": "Data",
        "label": "Seating Location",
        "reqd": 1
    })
    dt.append("fields", {
        "fieldname": "buddy",
        "fieldtype": "Link",
        "label": "Buddy",
        "options": "Employee",
        "reqd": 1
    })
    dt.append("fields", {
        "fieldname": "visiting_cards",
        "fieldtype": "Select",
        "label": "Visiting Cards",
        "options": "\nYes\nNo",
        "reqd": 1
    })
    dt.append("fields", {
        "fieldname": "comments",
        "fieldtype": "Text Editor",
        "label": "Additional Comments by Department Head"
    })

    # Permissions
    dt.append("permissions", {
        "role": "HR User",
        "read": 1,
        "write": 1,
        "create": 1,
        "submit": 1,
        "email": 1,
        "print": 1
    })
    dt.append("permissions", {
        "role": "HR Manager",
        "read": 1,
        "write": 1,
        "create": 1,
        "submit": 1,
        "cancel": 1,
        "email": 1,
        "print": 1
    })
    dt.append("permissions", {
        "role": "Business Head",
        "read": 1,
        "write": 1,
        "email": 1,
        "print": 1
    })

    dt.insert(ignore_permissions=True)
    frappe.db.commit()
    print("New Joiner Asset Request DocType created in HRMS Custom!")
