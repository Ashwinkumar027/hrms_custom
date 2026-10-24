frappe.query_reports["Bank Transfer Report"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            on_change: function(report) {
                let company = report.get_values().company;
                if (company) {
                    frappe.call({
                        method: "hrms_custom.hrms_custom.report.bank_transfer_report.bank_transfer_report.resolve_company_debit_account",
                        args: { company: company },
                        callback: function(r) {
                            if (r.message) {
                                report.set_filter_value("debit_account_number", r.message);
                            }
                        }
                    });
                }
            }
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
            fieldtype: "Data",
            default: "10173678610"
        },
        {
            fieldname: "transaction_date",
            label: __("Transaction Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate()
        }
    ],

    onload: function(report) {
        // Dedicated IDFC Bank Bulk Disbursal Template (.xlsx) download button
        report.page.add_inner_button(__('🏛️ Download IDFC Bank Excel (.xlsx)'), function() {
            let filters = report.get_values();
            if (!filters) {
                frappe.msgprint(__('Please set the report filters before downloading.'));
                return;
            }
            let filters_str = encodeURIComponent(JSON.stringify(filters));
            window.open(`/api/method/hrms_custom.hrms_custom.report.bank_transfer_report.bank_transfer_report.download_idfc_payroll_bank_excel?filters=${filters_str}`, '_blank');
        }).addClass('btn-primary idfc-payroll-btn').css({
            'background-color': '#1e3a8a',
            'border-color': '#172554',
            'color': '#ffffff',
            'font-weight': '700',
            'display': 'inline-flex',
            'align-items': 'center'
        });
    }
};
