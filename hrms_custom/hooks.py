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
    {
        "dt": "DocType",
        "filters": [["name", "=", "Offer Letter Print Settings"]],
    },
    {
        "dt": "DocType",
        "filters": [["name", "=", "Onboarding Task Contact"]],
    },
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
        "filters": [["parent", "in", [
            "Attendance Request",
            "Shift Request",
            "Expense Claim",
            "Employee Advance",
            "Employee",
            "TA Reimbursement Claim",
            "Client Visit Proposal"
        ]]],
    },
    {
        "dt": "Workflow",
        "filters": [["name", "in", [
            "Attendance Request Approval",
            "TA Reimbursement Workflow",
            "Employee Onboarding Workflow",
            "Manpower Requisition Flow",
	    "Client Visit Proposal Approval"
        ]]],
    },
    {
        "dt": "Workflow State",
        "filters": [["name", "in", [
            "Draft",
            "Pending Approval",
            "Approved",
            "Rejected",
            "Pending RM Approval",
            "RM Rejected",
            "Pending Admin Verification",
            "Admin Rejected",
            "Pending Accounts Processing",
            "On Hold",
            "Processed",
            "Accounts Rejected",
            "Pending Manager Input",
            "Pending HR Review",
            "Onboarding In Progress",
            "Pending Hr Approval",
            "Pending Final Approval"
        ]]],
    },
    {
        "dt": "Workflow Action Master",
        "filters": [["name", "in", [
            "Submit for Approval",
            "Approve",
            "Reject",
            "Verify",
            "Process",
            "Hold",
            "Assign to Manager",
            "Submit Activities",
            "HR Approve & Start",
            "Submit for HR Approval",
            "HR Approve",
            "HR Reject",
            "Final Approve",
            "Final Reject"
        ]]],
    },
    {
        "dt": "Role",
        "filters": [["name", "in", [
            "TA Reporting Manager",
            "TA Admin Verifier",
            "TA Accounts Approver"
        ]]],
    },
    {
        "dt": "Attendance Reason Type",
        "filters": [["name", "in", [
            "Permission",
            "On Duty",
            "Missed Attendance",
            "Work From Home Allowance"
        ]]],
    },
    {
        "dt": "Attendance Reason Allocation",
        "filters": [
            ["applies_to", "=", "Company"],
            ["company", "=", "AIONION CAPITAL (Demo)"],
            ["docstatus", "=", 1]
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
            "TA Claim Submitted - Notify RM",
            "TA Claim RM Approved - Notify Admin",
            "TA Claim RM Rejected - Notify Employee",
            "TA Claim Admin Verified - Notify Accounts",
            "TA Claim Admin Rejected - Notify Employee",
            "TA Claim Processed - Notify Employee",
            "TA Claim On Hold - Notify Employee",
            "TA Claim Accounts Rejected - Notify Employee",
        ]]],
    },
    {
        "dt": "Web Form",
        "filters": [["name", "in", [
            "job-application",
            "candidate-pre-offer-form",
            "employee-registration-form",
            "employee-fraternization-policy",
            "employee-agreement-form",
            "esi-enrollment",
            "employee-esi-pf"
        ]]],
    },
]

override_doctype_class = {
    "Employee Checkin": "hrms_custom.overrides.employee_checkin.MultiLocationEmployeeCheckin",
    "Attendance Request": "hrms_custom.overrides.attendance_request.CustomAttendanceRequest",
    "Employee Onboarding": "hrms_custom.overrides.employee_onboarding.CustomEmployeeOnboarding",
    "Shift Type": "hrms_custom.overrides.shift_type.CustomShiftType",
}

override_whitelisted_methods = {
    "erpnext.setup.doctype.employee.employee.deactivate_sales_person":
    "hrms_custom.overrides.employee.deactivate_sales_person"
}

permission_query_conditions = {
    "Attendance Request": "hrms_custom.permissions.attendance_request.get_permission_query_conditions",
    "Employee": "hrms_custom.permissions.employee.get_permission_query_conditions",
    "TA Reimbursement Claim": "hrms_custom.permissions.ta_reimbursement_claim.get_permission_query_conditions",
}

has_permission = {
    "TA Reimbursement Claim": "hrms_custom.permissions.ta_reimbursement_claim.has_permission",
}

scheduler_events = {
    "cron": {
        "0 9 * * *": [
            "hrms_custom.hrms_custom.utils.upcoming_holiday_notification.send_upcoming_holiday_notifications"
        ],
        "30 2 * * *": [
            "hrms_custom.hrms_custom.utils.missing_attendance_email.send_missing_attendance_emails_for_yesterday"
        ],
        "0 3 * * *": [
            "hrms_custom.hrms_custom.utils.lop_summary_email.send_lop_summary_emails"
        ]
    },
    "daily": [
        "hrms_custom.hrms_custom.utils.document_alerts.send_document_alerts"
    ],
    "monthly": [
        "hrms_custom.hrms_custom.utils.late_lop_processor.process_late_deductions"
    ],
    "hourly": [
        "hrms_custom.tasks.auto_close_stale_checkins.execute"
    ],
    "hourly_long": [
        "hrms_custom.hrms_custom.utils.force_absent_missing_checkout.execute"
    ]
}

after_migrate = [
    "hrms_custom.hrms_custom.utils.fix_employee_permission.fix_employee_role_permission"
]

doc_events = {
    "Employee": {
        "after_insert": "hrms_custom.hrms_custom.utils.user_permissions.create_user_permission_for_employee",
        "on_update": "hrms_custom.hrms_custom.utils.user_permissions.create_user_permission_for_employee"
    },
    "Salary Slip": {
        "before_save": "hrms_custom.hrms_custom.utils.salary_slip_tracker.log_salary_component_changes"
    },
    "Attendance": {
        "validate": "hrms_custom.hrms_custom.utils.attendance_lock.check_attendance_lock",
        "before_cancel": "hrms_custom.hrms_custom.utils.attendance_lock.check_attendance_lock"
    },
    "Leave Application": {
        "before_submit": "hrms_custom.hrms_custom.utils.attendance_lock.check_leave_application_lock"
    },
    "Attendance Request": {
        "before_submit": "hrms_custom.hrms_custom.utils.attendance_lock.check_attendance_request_lock"
    },
    "Employee Registration Form": {
        "on_update": "hrms_custom.hrms_custom.utils.form_fill_tracking.increment_fill_count"
    },
    "Employee Fraternization Policy": {
        "on_update": "hrms_custom.hrms_custom.utils.form_fill_tracking.increment_fill_count"
    },
    "Employee Agreement": {
        "on_update": "hrms_custom.hrms_custom.utils.form_fill_tracking.increment_fill_count"
    },
    "ESI Enrollment": {
        "on_update": "hrms_custom.hrms_custom.utils.form_fill_tracking.increment_fill_count"
    },
    "Form 11": {
        "on_update": "hrms_custom.hrms_custom.utils.form_fill_tracking.increment_fill_count"
    }
}
