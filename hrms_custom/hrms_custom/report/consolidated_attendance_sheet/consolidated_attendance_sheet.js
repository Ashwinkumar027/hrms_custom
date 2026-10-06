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
    onload: function (report) {
        let rep = report || frappe.query_report;
        if (rep && !rep.__checkin_click_bound) {
            rep.__checkin_click_bound = true;
            if (!$("head style#attendance-cell-style").length) {
                $("head").append(
                    "<style id='attendance-cell-style'>.attendance-date-cell:hover { text-decoration: underline dotted #64748b !important; }</style>"
                );
            }
            rep.page.main.on("click", ".attendance-date-cell", function (e) {
                e.preventDefault();
                let $cell = $(this);
                let employee = $cell.attr("data-employee");
                let emp_name = $cell.attr("data-employee-name");
                let date_ymd = $cell.attr("data-date");
                let display_date = $cell.attr("data-display-date");
                if (employee && date_ymd) {
                    show_checkin_dialog(employee, emp_name, date_ymd, display_date);
                }
            });
        }

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

            // Wrap in clickable element if row has employee and column is a date column
            if (data && data.employee && is_date_col(column.fieldname)) {
                let parts = column.fieldname.split("-");
                let date_ymd = parts[2] + "-" + parts[1] + "-" + parts[0];
                let escaped_emp = frappe.utils.escape_html(data.employee);
                let escaped_emp_name = frappe.utils.escape_html(data.employee_name || data.employee);
                let escaped_date = frappe.utils.escape_html(date_ymd);
                let escaped_display_date = frappe.utils.escape_html(column.fieldname);

                value = '<span class="attendance-date-cell" data-employee="' + escaped_emp + '" data-employee-name="' + escaped_emp_name + '" data-date="' + escaped_date + '" data-display-date="' + escaped_display_date + '" style="cursor: pointer; display: inline-block;">' + value + '</span>';
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

function is_date_col(val) {
    if (!val || typeof val !== "string" || val.length !== 10) return false;
    let parts = val.split("-");
    return parts.length === 3 && parts[0].length === 2 && parts[1].length === 2 && parts[2].length === 4;
}

function show_checkin_dialog(employee, emp_name, date_ymd, display_date) {
    frappe.call({
        method: "hrms_custom.api.attendance_report.get_checkin_log",
        args: {
            employee: employee,
            date: date_ymd,
        },
        freeze: true,
        freeze_message: __("Fetching check-in logs..."),
        callback: function (r) {
            if (r.exc) return;
            const res = r.message || {};
            const logs = res.logs || [];
            const att_status = res.attendance_status || "No Attendance record";
            const att_req = res.attendance_request;

            let in_display = "-";
            let out_display = "-";

            const has_logs = logs.length > 0;
            const has_in = !!res.first_in;
            const has_out = !!res.last_out;

            if (has_in) {
                in_display = "<strong>" + frappe.utils.escape_html(res.first_in) + "</strong>";
            } else if (has_logs && !has_in) {
                in_display = '<span style="color: #dc2626; font-weight: 600;">Missing check-in</span>';
            }

            if (has_out) {
                let out_str = frappe.utils.escape_html(res.last_out);
                if (res.last_out_auto_closed) {
                    out_display = "<strong>" + out_str + '</strong> <span style="color: #ea580c; font-size: 11px; font-weight: 600;">(Auto-closed by system - no real check-out)</span>';
                } else {
                    out_display = "<strong>" + out_str + "</strong>";
                }
            } else if (has_logs && !has_out) {
                out_display = '<span style="color: #dc2626; font-weight: 600;">Missing check-out</span>';
            }

            let duration_html = "";
            if (res.total_duration) {
                duration_html = '<div style="font-size: 12px; color: #475569; margin-top: 4px;">' +
                    '<span>Total Duration:</span> <strong style="color: #0f766e;">' + frappe.utils.escape_html(res.total_duration) + '</strong>' +
                    '</div>';
            }

            let status_note_html = "";
            if (!has_logs) {
                let req_link = "";
                if (att_req) {
                    req_link = '<div style="margin-top: 6px; font-size: 11.5px;">Linked Attendance Request: <a href="/app/attendance-request/' + encodeURIComponent(att_req) + '" target="_blank" style="color: #0284c7; font-weight: 600;">' + frappe.utils.escape_html(att_req) + '</a></div>';
                }
                status_note_html = '<div style="padding: 10px 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; color: #64748b; font-size: 12px; margin-top: 10px;">' +
                    'No check-in/check-out logs for this date.' +
                    req_link +
                    '</div>';
            }

            let rows_html = "";
            if (has_logs) {
                rows_html = logs.map(function (l) {
                    let badge = l.log_type === "IN"
                        ? '<span style="background: #f0fdf4; color: #16a34a; border: 1px solid #dcfce7; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px;">IN</span>'
                        : '<span style="background: #eff6ff; color: #2563eb; border: 1px solid #dbeafe; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px;">OUT</span>';

                    let note_content = l.note
                        ? '<span style="color: #ea580c; font-weight: 500; font-size: 11px;">' + frappe.utils.escape_html(l.note) + '</span>'
                        : '<span style="color: #94a3b8;">-</span>';

                    return '<tr style="border-bottom: 1px solid #f1f5f9;">' +
                        '<td style="padding: 8px 10px; font-size: 12px; font-weight: 600; color: #1e293b;">' + frappe.utils.escape_html(l.time) + '</td>' +
                        '<td style="padding: 8px 10px; text-align: center;">' + badge + '</td>' +
                        '<td style="padding: 8px 10px; font-size: 11.5px; color: #475569;">' + frappe.utils.escape_html(l.shift || "-") + '</td>' +
                        '<td style="padding: 8px 10px; font-size: 11.5px; color: #475569;">' + frappe.utils.escape_html(l.device_id || "-") + '</td>' +
                        '<td style="padding: 8px 10px; font-size: 11.5px;">' + note_content + '</td>' +
                        '</tr>';
                }).join("");
            }

            let logs_table_html = "";
            if (has_logs) {
                logs_table_html = '<div style="margin-top: 14px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;">' +
                    '<table style="width: 100%; border-collapse: collapse; text-align: left; font-family: -apple-system, BlinkMacSystemFont, \x27Segoe UI\x27, Roboto, sans-serif;">' +
                    '<thead>' +
                    '<tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">' +
                    '<th style="padding: 8px 10px; font-weight: 600;">Time</th>' +
                    '<th style="padding: 8px 10px; font-weight: 600; text-align: center;">Log Type</th>' +
                    '<th style="padding: 8px 10px; font-weight: 600;">Shift</th>' +
                    '<th style="padding: 8px 10px; font-weight: 600;">Device ID</th>' +
                    '<th style="padding: 8px 10px; font-weight: 600;">Note</th>' +
                    '</tr>' +
                    '</thead>' +
                    '<tbody>' +
                    rows_html +
                    '</tbody>' +
                    '</table>' +
                    '</div>';
            }

            let dialog_body = '<div style="font-family: -apple-system, BlinkMacSystemFont, \x27Segoe UI\x27, Roboto, sans-serif;">' +
                '<div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">' +
                '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">' +
                '<div style="font-size: 12.5px; color: #334155;">' +
                '<span>Attendance Status:</span> <strong style="color: #0f172a; padding: 1px 6px; background: #e2e8f0; border-radius: 4px; font-size: 11.5px;">' + frappe.utils.escape_html(att_status) + '</strong>' +
                '</div>' +
                duration_html +
                '</div>' +
                '<div style="display: flex; gap: 24px; padding-top: 8px; border-top: 1px dashed #cbd5e1; font-size: 12.5px; color: #1e293b; flex-wrap: wrap;">' +
                '<div><span style="color: #64748b;">Check-in:</span> ' + in_display + '</div>' +
                '<div><span style="color: #64748b;">Check-out:</span> ' + out_display + '</div>' +
                '</div>' +
                '</div>' +
                status_note_html +
                logs_table_html +
                '</div>';

            let d = new frappe.ui.Dialog({
                title: frappe.utils.escape_html(emp_name) + " - " + frappe.utils.escape_html(display_date),
                size: "large",
            });
            d.$body.html(dialog_body);
            d.show();
        },
    });
}
