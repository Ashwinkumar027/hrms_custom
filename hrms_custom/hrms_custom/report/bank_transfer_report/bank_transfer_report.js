frappe.query_reports["Bank Transfer Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "docstatus",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nSubmitted",
            default: ""
        },
        {
            fieldname: "payroll_entry",
            label: __("Payroll Entry"),
            fieldtype: "Link",
            options: "Payroll Entry"
        },
        {
            fieldname: "debit_account_number",
            label: __("Debit Account Number (Company IDFC Account)"),
            fieldtype: "Data"
        },
        {
            fieldname: "transaction_date",
            label: __("Transaction Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate()
        }
    ]
};
