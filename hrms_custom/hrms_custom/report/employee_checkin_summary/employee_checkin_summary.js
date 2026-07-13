frappe.query_reports["Employee Checkin Summary"] = {
    filters: [
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            default: get_payroll_period_start(),
            reqd: 1,
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            default: get_payroll_period_end(),
            reqd: 1,
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
        },
        {
            fieldname: "reports_to",
            label: __("Reports To"),
            fieldtype: "Link",
            options: "Employee",
            description: __("Shows this employee's full reporting chain, including indirect reports"),
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
        },
    ],
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "auto_closed" && data && data.auto_closed === "AUTO") {
            value = "<span style='color:#e65100; font-weight:bold;'>AUTO</span>";
        }

        if (column.fieldname === "check_out" && data && data.auto_closed === "AUTO") {
            value = "<span style='color:#e65100;'>" + value + "</span>";
        }

        if (column.fieldname === "check_out" && data && !data.check_out) {
            value = "<span style='color:red;'>MISSING</span>";
        }

        return value;
    },
};

function get_payroll_period_start() {
    let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
    let year = today.getFullYear();
    let month = today.getMonth();
    if (today.getDate() < 26) {
        month = month - 1;
    }
    let start = new Date(year, month, 26);
    return frappe.datetime.obj_to_str(start);
}

function get_payroll_period_end() {
    let today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
    let year = today.getFullYear();
    let month = today.getMonth();
    if (today.getDate() >= 26) {
        month = month + 1;
    }
    let end = new Date(year, month, 25);
    return frappe.datetime.obj_to_str(end);
}
