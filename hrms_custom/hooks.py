app_name = "hrms_custom"
app_title = "HRMS custom"
app_publisher = "ASHWIN"
app_description = "Customizations for HRMS"
app_email = "ashwinkumark59@gmail.com"
app_license = "mit"

doctype_js = {
    "Employee": "public/js/employee.js",
}

fixtures = [
    "Onboarding Task Contact",
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "HRMS custom"]],
    },
    {
        "dt": "Property Setter",
        "filters": [["module", "=", "HRMS custom"]],
    },
    {
        "dt": "Client Script",
        "filters": [["module", "=", "HRMS custom"]],
    },
    {
        "dt": "Server Script",
        "filters": [["module", "=", "HRMS custom"]],
    },
    {
        "dt": "Custom DocPerm",
        "filters": [["parent", "in", ["Attendance Request", "Shift Request", "Expense Claim", "Employee Advance", "Employee"]]],
    },
    {
        "dt": "Workflow",
        "filters": [["name", "=", "Attendance Request Approval"]],
    },
    {
        "dt": "Workflow State",
        "filters": [["name", "in", ["Draft", "Pending Approval", "Approved", "Rejected"]]],
    },
    {
        "dt": "Workflow Action Master",
        "filters": [["name", "in", ["Submit for Approval", "Approve", "Reject"]]],
    },
    {
        "dt": "Attendance Reason Type",
        "filters": [["name", "in", [
            "Permission",
            "On Duty",
            "Missed Attendance",
            "Work From Home Allowance",
        ]]],
    },
    {
        "dt": "Attendance Reason Allocation",
        "filters": [
            ["applies_to", "=", "Company"],
            ["company", "=", "AIONION CAPITAL (Demo)"],
            ["docstatus", "=", 1],
        ],
    },
    {
        "dt": "Employee Allowed Shift Location",
        "filters": [["enabled", "=", 1]],
    },
    {
        "dt": "Print Format",
        "filters": [["module", "=", "HRMS custom"]],
    },
    {
        "dt": "Report",
        "filters": [["module", "=", "HRMS custom"]],
    },
    {
        "dt": "Notification",
        "filters": [["name", "in", [
            "Joining Reminder 1 Day",
            "Joining Reminder 10 Days",
            "Joining Reminder 45 Days",
            "Notify Director After BH Approval",
        ]]],
    },
    {
        "dt": "Web Form",
        "filters": [["name", "in", [
            "job-application",
            "candidate-pre-offer-form",
        ]]],
    },
]

# Single merged override_doctype_class (removed duplicate)
override_doctype_class = {
    "Employee Checkin": "hrms_custom.overrides.employee_checkin.MultiLocationEmployeeCheckin",
    "Attendance Request": "hrms_custom.overrides.attendance_request.CustomAttendanceRequest",
    "Employee Onboarding": "hrms_custom.overrides.employee_onboarding.CustomEmployeeOnboarding",
}

# Fixed: replaced wrong 'whitelist_methods' with correct key
override_whitelisted_methods = {
    "erpnext.setup.doctype.employee.employee.deactivate_sales_person":
    "hrms_custom.overrides.employee.deactivate_sales_person"
}

permission_query_conditions = {
    "Attendance Request": "hrms_custom.permissions.attendance_request.get_permission_query_conditions",
    "Employee": "hrms_custom.permissions.employee.get_permission_query_conditions",
}

scheduler_events = {
    "cron": {
        "0 9 * * *": [
            "hrms_custom.hrms_custom.utils.upcoming_holiday_notification.send_upcoming_holiday_notifications"
        ]
    },
    "daily": [
        "hrms_custom.hrms_custom.utils.missing_attendance_email.send_missing_attendance_emails_for_yesterday",
        "hrms_custom.hrms_custom.utils.lop_summary_email.send_lop_summary_emails",
        "hrms_custom.hrms_custom.utils.document_alerts.send_document_alerts"
    ],
    "monthly": [
        "hrms_custom.hrms_custom.utils.late_lop_processor.process_late_deductions"
    ]
}

doc_events = {
    "Salary Slip": {
        "before_save": "hrms_custom.hrms_custom.utils.salary_slip_tracker.log_salary_component_changes"
    },
    "Attendance": {
        "validate": "hrms_custom.hrms_custom.utils.attendance_lock.check_attendance_lock",
        "before_cancel": "hrms_custom.hrms_custom.utils.attendance_lock.check_attendance_lock"
    },
    "Leave Application": {
        "before_submit": "hrms_custom.hrms_custom.utils.attendance_lock.check_leave_application_lock",
        "validate": "hrms_custom.hrms_custom.utils.probation_leave_restriction.check_probation_leave_type"
    },
    "Attendance Request": {
        "before_submit": "hrms_custom.hrms_custom.utils.attendance_lock.check_attendance_request_lock"
    }
}
