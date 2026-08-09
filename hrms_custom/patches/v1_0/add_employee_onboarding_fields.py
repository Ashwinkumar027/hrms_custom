# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
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
            {
                "fieldname": "custom_biometric_access",
                "label": "Biometric Access",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "reqd": 1,
                "insert_after": "custom_business_card",
            },
            {
                "fieldname": "custom_tech_excel_access",
                "label": "Tech Excel Access",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "insert_after": "custom_biometric_access",
            },
            {
                "fieldname": "custom_crm_platform_access",
                "label": "CRM Platform Access",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "insert_after": "custom_tech_excel_access",
            },
            {
                "fieldname": "custom_sales_tracker_access",
                "label": "20 Point Sales Tracker Access",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "insert_after": "custom_crm_platform_access",
            },
            {
                "fieldname": "custom_portfolio_plus_access",
                "label": "Portfolio Plus Access",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "insert_after": "custom_sales_tracker_access",
            },
            {
                "fieldname": "custom_kyc_individual_link",
                "label": "KYC Individual Link",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "insert_after": "custom_portfolio_plus_access",
            },
            {
                "fieldname": "custom_novac_id_login",
                "label": "Novac ID / Login",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "reqd": 1,
                "insert_after": "custom_kyc_individual_link",
            },
            {
                "fieldname": "custom_other_tool_required",
                "label": "Other Tool Required",
                "fieldtype": "Select",
                "options": "\nYes\nNo",
                "insert_after": "custom_novac_id_login",
            },
            {
                "fieldname": "custom_other_tool_name",
                "label": "Specify Other Tool",
                "fieldtype": "Data",
                "depends_on": 'eval:doc.custom_other_tool_required == "Yes"',
                "mandatory_depends_on": 'eval:doc.custom_other_tool_required == "Yes"',
                "insert_after": "custom_other_tool_required",
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)
