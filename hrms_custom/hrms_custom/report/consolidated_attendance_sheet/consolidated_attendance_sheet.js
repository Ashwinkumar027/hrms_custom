frappe.query_reports["Consolidated Attendance Sheet"] = {
    filters: [
        {
            fieldname: "filter_based_on",
            label: __("Filter Based On"),
            fieldtype: "Select",
            options: ["Month", "Date Range"],
            default: "Date Range",
            reqd: 1,
            on_change: (report) => {
                let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");

                if (filter_based_on == "Month") {
                    set_reqd_filter("month", true);
                    set_reqd_filter("year", true);
                    set_reqd_filter("start_date", false);
                    set_reqd_filter("end_date", false);
                }
                if (filter_based_on == "Date Range") {
                    set_reqd_filter("month", false);
                    set_reqd_filter("year", false);
                    set_reqd_filter("start_date", true);
                    set_reqd_filter("end_date", true);
                }
                report.refresh();
            },
        },
        {
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            options: [
                { value: 1, label: __("Jan") },
                { value: 2, label: __("Feb") },
                { value: 3, label: __("Mar") },
                { value: 4, label: __("Apr") },
                { value: 5, label: __("May") },
                { value: 6, label: __("June") },
                { value: 7, label: __("July") },
                { value: 8, label: __("Aug") },
                { value: 9, label: __("Sep") },
                { value: 10, label: __("Oct") },
                { value: 11, label: __("Nov") },
                { value: 12, label: __("Dec") },
            ],
            default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1,
            depends_on: "eval:doc.filter_based_on == 'Month'",
        },
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            depends_on: "eval:doc.filter_based_on == 'Date Range'",
            default: get_payroll_period_start(),
            on_change: validate_date_range,
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            depends_on: "eval:doc.filter_based_on == 'Date Range'",
            default: get_payroll_period_end(),
            on_change: validate_date_range,
        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            depends_on: "eval:doc.filter_based_on == 'Month'",
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
            get_query: () => {
                var company = frappe.query_report.get_filter_value("company");
                return {
                    filters: {
                        company: company,
                    },
                };
            },
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
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
            get_query: () => {
                var company = frappe.query_report.get_filter_value("company");
                return {
                    filters: {
                        company: company,
                    },
                };
            },
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "Link",
            options: "Branch",
        },
        {
            fieldname: "group_by",
            label: __("Group By"),
            fieldtype: "Select",
            options: ["", "Branch", "Grade", "Department", "Designation"],
        },
        {
            fieldname: "include_company_descendants",
            label: __("Include Company Descendants"),
            fieldtype: "Check",
            default: 1,
        },
        {
            fieldname: "summarized_view",
            label: __("Summarized View"),
            fieldtype: "Check",
            default: 0,
        },
    ],
    onload: function () {
        return frappe.call({
            method: "hrms.hr.report.monthly_attendance_sheet.monthly_attendance_sheet.get_attendance_years",
            callback: function (r) {
                var year_filter = frappe.query_report.get_filter("year");
                year_filter.df.options = r.message;
                year_filter.df.default = r.message.split("\n")[0];
                year_filter.refresh();
                year_filter.set_input(year_filter.df.default);
            },
        });
    },
    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        const summarized_view = frappe.query_report.get_filter_value("summarized_view");
        const group_by = frappe.query_report.get_filter_value("group_by");

        if (group_by && column.colIndex === 1) {
            value = "<strong>" + value + "</strong>";
        }

        if (!summarized_view && value) {
            // Strip any existing HTML tags to inspect the raw code
            const cleanVal = String(value).replace(/<[^>]*>/g, "").trim();
            if (!cleanVal) return value;

            // 1. Pending Approvals (Pure Red dashed micro-pill)
            if (cleanVal.endsWith("-PND")) {
                value = "<span style='color: #e74c3c; background: #fff5f5; border: 1px dashed #e74c3c; padding: 2px 5px; border-radius: 4px; font-weight: 700; font-size: 10.5px; display: inline-block; white-space: nowrap; letter-spacing: 0.2px;'>" + cleanVal + "</span>";
            }
            // 2. Absent (Bold Pure Red)
            else if (cleanVal === "A") {
                value = "<span style='color: #dc2626; font-weight: 800; font-size: 12px;'>" + cleanVal + "</span>";
            }
            // 3. Missing Checkout & Loss of Pay (Pure Red solid micro-pill)
            else if (cleanVal === "M(CO)" || cleanVal === "LOP") {
                value = "<span style='color: #ffffff; background: #e74c3c; border: 1px solid #c0392b; padding: 2px 5px; border-radius: 4px; font-weight: 700; font-size: 10.5px; display: inline-block; white-space: nowrap; box-shadow: 0 1px 2px rgba(231,76,60,0.2);'>" + cleanVal + "</span>";
            }
            // 4. Regularization, On Duty, Week Off Credit (Teal micro-pill)
            else if (cleanVal === "REG" || cleanVal === "OD" || cleanVal === "WOC") {
                value = "<span style='color: #0f766e; background: #f0fdfa; border: 1px solid #99f6e4; padding: 2px 5px; border-radius: 4px; font-weight: 600; font-size: 10.5px; display: inline-block; white-space: nowrap;'>" + cleanVal + "</span>";
            }
            // 5. Permissions (Purple micro-pill)
            else if (cleanVal === "PER/LI" || cleanVal === "PER/EO") {
                value = "<span style='color: #6d28d9; background: #f5f3ff; border: 1px solid #ddd6fe; padding: 2px 5px; border-radius: 4px; font-weight: 600; font-size: 10.5px; display: inline-block; white-space: nowrap;'>" + cleanVal + "</span>";
            }
            // 6. Present & Work From Home (Crisp Forest Green)
            else if (cleanVal === "P" || cleanVal === "WFH") {
                value = "<span style='color: #15803d; font-weight: 700; font-size: 12px;'>" + cleanVal + "</span>";
            }
            // 7. Half Days (Subtle amber/purple micro-pills)
            else if (cleanVal === "HD/A") {
                value = "<span style='color: #c2410c; background: #fff7ed; border: 1px solid #ffedd5; padding: 2px 5px; border-radius: 4px; font-weight: 600; font-size: 10.5px; display: inline-block; white-space: nowrap;'>" + cleanVal + "</span>";
            } else if (cleanVal === "HD/P" || cleanVal.startsWith("HD/")) {
                value = "<span style='color: #7c3aed; background: #faf5ff; border: 1px solid #f3e8ff; padding: 2px 5px; border-radius: 4px; font-weight: 600; font-size: 10.5px; display: inline-block; white-space: nowrap;'>" + cleanVal + "</span>";
            }
            // 8. Approved Leaves (Soft Sky Blue micro-pill)
            else if (["CL", "CO", "SL", "RH", "EL", "PCL", "PL", "ML", "LWP", "L"].includes(cleanVal)) {
                value = "<span style='color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; padding: 2px 5px; border-radius: 4px; font-weight: 600; font-size: 10.5px; display: inline-block; white-space: nowrap;'>" + cleanVal + "</span>";
            }
            // 9. Weekly Off & Holiday (Muted Slate)
            else if (cleanVal === "WO" || cleanVal === "H") {
                value = "<span style='color: #94a3b8; font-weight: 600; font-size: 11px;'>" + cleanVal + "</span>";
            }
            else {
                value = "<span style='color: #64748b;'>" + value + "</span>";
            }
        }

        return value;
    },
};
function set_reqd_filter(fieldname, is_reqd) {
    let filter = frappe.query_report.get_filter(fieldname);
    filter.df.reqd = is_reqd;
    filter.refresh();
}
function validate_date_range(report) {
    let start_date = frappe.query_report.get_filter_value("start_date");
    let end_date = frappe.query_report.get_filter_value("end_date");
    if (!(start_date && end_date)) return;

    let start = frappe.datetime.str_to_obj(start_date);
    let end = frappe.datetime.str_to_obj(end_date);
    let milli_seconds_in_a_day = 24 * 60 * 60 * 1000;
    let day_diff = Math.floor((end - start) / milli_seconds_in_a_day);
    if (day_diff > 90) {
        frappe.throw({
            message: __("Please set a date range less than 90 days."),
            title: __("Date Range Exceeded"),
        });
    }
    report.refresh();
}
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
    if (today.getDate() < 26) {
        // stay in current month, end is 25th of this month
    } else {
        month = month + 1;
    }
    let end = new Date(year, month, 25);
    return frappe.datetime.obj_to_str(end);
}
