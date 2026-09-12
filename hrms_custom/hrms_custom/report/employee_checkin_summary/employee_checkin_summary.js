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
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: ["", "Completed", "Missing Check-out", "Missing Check-in", "Auto Closed"],
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

        if (!data) return value;

        // 1. Missing Check In
        if (column.fieldname === "check_in" && !data.check_in) {
            value = "<span style='background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px;'>MISSING</span>";
        }

        // 2. Missing Check Out
        if (column.fieldname === "check_out") {
            if (!data.check_out) {
                value = "<span style='background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10.5px;'>MISSING</span>";
            } else if (data.auto_closed === "AUTO") {
                value = "<span style='color: #ea580c; font-weight: 600;'>" + value + "</span>";
            }
        }

        // 3. Checkout Type / Auto Closed Badge
        if (column.fieldname === "auto_closed") {
            if (data.auto_closed === "AUTO") {
                value = "<span style='background: #fff7ed; color: #ea580c; border: 1px solid #ffedd5; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 10.5px;'>AUTO</span>";
            } else if (data.check_in && data.check_out) {
                value = "<span style='background: #f0fdf4; color: #16a34a; border: 1px solid #dcfce7; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 10.5px;'>REGULAR</span>";
            } else {
                value = "<span style='color: #94a3b8;'>-</span>";
            }
        }

        // 4. Working Hours styling
        if (column.fieldname === "working_hours") {
            if (data.working_hours && data.working_hours !== "-") {
                value = "<span style='font-weight: 600; color: #1e293b; font-size: 11.5px;'>" + data.working_hours + "</span>";
            } else {
                value = "<span style='color: #cbd5e1;'>-</span>";
            }
        }

        // 5. Clickable Google Maps Pin for Coordinates
        if ((column.fieldname === "check_in_lat_long" || column.fieldname === "check_out_lat_long") && value) {
            const raw = String(value).replace(/<[^>]*>/g, "").trim();
            if (raw && raw.includes(",")) {
                const parts = raw.split(",");
                const lat = parseFloat(parts[0].trim());
                const lon = parseFloat(parts[1].trim());
                if (!isNaN(lat) && !isNaN(lon) && lat !== 0 && lon !== 0) {
                    const shortCoords = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
                    const mapsUrl = `https://www.google.com/maps?q=${lat},${lon}`;
                    value = `<a href="${mapsUrl}" target="_blank" rel="noopener noreferrer" style="color: #0284c7; text-decoration: none; font-weight: 500; font-size: 11px; display: inline-flex; align-items: center; gap: 3px;" title="Open in Google Maps (${raw})">📍 ${shortCoords}</a>`;
                }
            }
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
