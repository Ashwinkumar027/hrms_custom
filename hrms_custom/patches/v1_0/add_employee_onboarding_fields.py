import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Employee Onboarding": [
            {
                "fieldname": "custom_onboarding_section",
                "label": "Asset & Access Requirements",
                "fieldtype": "Section Break",
                "insert_after": "holiday_list",
            },
            {
                "fieldname": "custom_laptop_type",
                "label": "Desktop or Laptop",
                "fieldtype": "Select",
                "options": "\nLaptop\nDesktop\nNo",
                "insert_after": "custom_onboarding_section",
            },
            {
                "fieldname": "custom_sim_card",
                "label": "SIM Card",
                "fieldtype": "Select",
                "options": "\nNew\nReplace\nNo",
                "insert_after": "custom_laptop_type",
            },
            {
                "fieldname": "custom_sim_replacement_name",
                "label": "SIM Replacement Name",
                "fieldtype": "Data",
                "depends_on": 'eval:doc.custom_sim_card == "Replace"',
                "mandatory_depends_on": 'eval:doc.custom_sim_card == "Replace"',
                "insert_after": "custom_sim_card",
            },
            {
                "fieldname": "custom_email_id",
                "label": "Email ID",
                "fieldtype": "Select",
                "options": "\nNew\nReplace\nNo",
                "insert_after": "custom_sim_replacement_name",
            },
            {
                "fieldname": "custom_email_replacement_name",
                "label": "Email Replacement Name",
                "fieldtype": "Data",
                "depends_on": 'eval:doc.custom_email_id == "Replace"',
                "mandatory_depends_on": 'eval:doc.custom_email_id == "Replace"',
                "insert_after": "custom_email_id",
            },
            {
                "fieldname": "custom_software_access",
                "label": "Software / Tool Access (CRM)",
                "fieldtype": "Data",
                "insert_after": "custom_email_replacement_name",
            },
            {
                "fieldname": "custom_id_card",
                "label": "ID Card Required",
                "fieldtype": "Check",
                "insert_after": "custom_software_access",
            },
            {
                "fieldname": "custom_business_card",
                "label": "Business Card Required",
                "fieldtype": "Check",
                "insert_after": "custom_id_card",
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)
