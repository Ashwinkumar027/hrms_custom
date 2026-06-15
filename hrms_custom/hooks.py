app_name = "hrms_custom"
app_title = "HRMS custom"
app_publisher = "ASHWIN"
app_description = "Customizations for HRMS"
app_email = "ashwinkumark59@gmail.com"
app_license = "mit"

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "in", ["HRMS Custom", "HRMS custom"]]],
    },
    {
        "dt": "Custom Field",
        "filters": [["dt", "=", "Job Applicant"]],
    },
    {
        "dt": "Custom Field",
        "filters": [["dt", "=", "Shift Type"]],
    },
    {
        "dt": "Property Setter",
        "filters": [["module", "in", ["HRMS Custom", "HRMS custom"]]],
    },
    {
        "dt": "Client Script",
        "filters": [["module", "in", ["HRMS Custom", "HRMS custom"]]],
    },
    {
        "dt": "Server Script",
        "filters": [["module", "in", ["HRMS Custom", "HRMS custom"]]],
    },
    {
        "dt": "Custom DocPerm",
        "filters": [["parent", "in", ["Attendance Request", "Shift Request", "Expense Claim", "Employee Advance"]]],

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

override_doctype_class = {
    "Employee Checkin": "hrms_custom.overrides.employee_checkin.MultiLocationEmployeeCheckin",
    "Attendance Request": "hrms_custom.overrides.attendance_request.CustomAttendanceRequest",
}

permission_query_conditions = {
    "Attendance Request": "hrms_custom.permissions.attendance_request.get_permission_query_conditions",
}
# Whitelisted API methods
whitelist_methods = {
    "probation_action": "hrms_custom.api.probation_action"
}
scheduler_events = {
    "monthly": [
        "hrms_custom.hrms_custom.utils.late_lop_processor.process_late_deductions"
    ]
}
