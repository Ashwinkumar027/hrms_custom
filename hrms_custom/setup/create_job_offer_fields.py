import frappe

def create_job_offer_fields():
    print("\n--- Creating Job Offer Custom Fields ---")

    fields = [
        # ── Section: Offer Discussion Details ──────
        {
            "dt": "Job Offer",
            "fieldname": "custom_section_offer_discussion",
            "fieldtype": "Section Break",
            "label": "Offer & Budget Details",
            "insert_after": "designation",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_proposed_ctc",
            "fieldtype": "Currency",
            "label": "Proposed CTC (Per Annum)",
            "insert_after": "custom_section_offer_discussion",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_variable_pay",
            "fieldtype": "Currency",
            "label": "Variable Pay",
            "insert_after": "custom_proposed_ctc",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_col_break_offer",
            "fieldtype": "Column Break",
            "insert_after": "custom_variable_pay",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_tentative_joining_date",
            "fieldtype": "Date",
            "label": "Tentative Joining Date",
            "insert_after": "custom_col_break_offer",
            "reqd": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_notice_period_buyout",
            "fieldtype": "Select",
            "label": "Notice Period Buyout",
            "options": "\nYes\nNo\nPartial",
            "insert_after": "custom_tentative_joining_date",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_budget_code",
            "fieldtype": "Data",
            "label": "Budget Code",
            "insert_after": "custom_notice_period_buyout",
            "reqd": 0,
            "module": "HRMS Custom"
        },

        # ── Section: Approval Details ───────────────
        {
            "dt": "Job Offer",
            "fieldname": "custom_section_approval",
            "fieldtype": "Section Break",
            "label": "Approval Details",
            "insert_after": "custom_budget_code",
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_bh_comments",
            "fieldtype": "Text",
            "label": "Comments by Branch Head",
            "insert_after": "custom_section_approval",
            "reqd": 0,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_bh_approved_by",
            "fieldtype": "Link",
            "label": "Approved By (BH)",
            "options": "User",
            "insert_after": "custom_bh_comments",
            "read_only": 1,
            "module": "HRMS Custom"
        },
        {
            "dt": "Job Offer",
            "fieldname": "custom_bh_approval_date",
            "fieldtype": "Date",
            "label": "BH Approval Date",
            "insert_after": "custom_bh_approved_by",
            "read_only": 1,
            "module": "HRMS Custom"
        },
    ]

    for field in fields:
        name = f"{field['dt']}-{field['fieldname']}"
        if not frappe.db.exists("Custom Field", name):
            cf = frappe.new_doc("Custom Field")
            cf.update(field)
            cf.insert(ignore_permissions=True)
            print(f"  Created: {field.get('label', field['fieldname'])}")
        else:
            print(f"  Already exists: {field.get('label', field['fieldname'])}")

    frappe.db.commit()
    print("\nJob Offer fields created!")
