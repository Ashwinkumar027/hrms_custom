frappe.query_reports["Bank Transfer Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company")
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
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
            fieldtype: "Data",
            reqd: 1
        },
        {
            fieldname: "transaction_date",
            label: __("Transaction Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.nowdate()
        }
    ]
};
