import frappe


def create_notifications():
    """
    Creates 3 joining reminder notifications for Employee Onboarding.
    Run with:
    bench --site hrms.local execute hrms_custom.setup.create_notifications.create_notifications
    """

    notifications = [
        {
            "name": "Joining Reminder 45 Days",
            "channel": "Email",
            "event": "Days Before",
            "document_type": "Employee Onboarding",
            "enabled": 1,
            "is_standard": 0,
            "subject": "Your Joining Date is in 45 Days - {{ doc.employee_name }}",
            "date_changed": "date_of_joining",
            "days_in_advance": 45,
            "send_system_notification": 0,
            "condition_type": "Python",
            "message_type": "Markdown",
            "message": """<p>Dear {{ doc.employee_name }},</p>

<p>We are excited to welcome you to the team!</p>

<p>Your joining date is confirmed as
<strong>{{ doc.date_of_joining }}</strong> -
that is <strong>45 days</strong> from today.</p>

<p>Please ensure the following before your joining:</p>
<ul>
<li>Serve your notice period at your current organization</li>
<li>Complete all exit formalities well in advance</li>
<li>Keep your documents ready for Day 1</li>
</ul>

<p>If you have any questions feel free to reach out to us at any time.</p>

<p>Looking forward to having you on board!<br>HR Team</p>""",
            "recipients": [
                {"receiver_by_document_field": "user,activities"}
            ]
        },
        {
            "name": "Joining Reminder 10 Days",
            "channel": "Email",
            "event": "Days Before",
            "document_type": "Employee Onboarding",
            "enabled": 1,
            "is_standard": 0,
            "subject": "Reminder: Your Joining Date is in 10 Days - {{ doc.employee_name }}",
            "date_changed": "date_of_joining",
            "days_in_advance": 10,
            "send_system_notification": 0,
            "condition_type": "Python",
            "message_type": "Markdown",
            "message": """<p>Dear {{ doc.employee_name }},</p>

<p>Just a reminder - your joining date is
<strong>{{ doc.date_of_joining }}</strong>.
Only <strong>10 days</strong> to go!</p>

<p>Please make sure the following are done:</p>
<ul>
<li>Relieving letter is arranged from current employer</li>
<li>All exit formalities are completed</li>
<li>You are ready to join on the confirmed date</li>
</ul>

<p>Please reach out if you need any help from our side.</p>

<p>Looking forward to seeing you soon!<br>HR Team</p>""",
            "recipients": [
                {"receiver_by_document_field": "user,activities"}
            ]
        },
        {
            "name": "Joining Reminder 1 Day",
            "channel": "Email",
            "event": "Days Before",
            "document_type": "Employee Onboarding",
            "enabled": 1,
            "is_standard": 0,
            "subject": "Your Joining Date is Tomorrow - {{ doc.employee_name }}",
            "date_changed": "date_of_joining",
            "days_in_advance": 1,
            "send_system_notification": 1,
            "condition_type": "Python",
            "message_type": "Markdown",
            "message": """<p>Dear {{ doc.employee_name }},</p>

<p>This is a reminder that your joining date is
<strong>TOMORROW</strong> - {{ doc.date_of_joining }}.</p>

<p>Please carry the following on Day 1:</p>
<ul>
<li>Government ID proof (Original + photocopy)</li>
<li>Relieving letter from previous employer</li>
<li>Educational certificates</li>
<li>Passport size photographs</li>
</ul>

<p>Report at 9:30 AM and ask for the HR team.</p>

<p>See you tomorrow!<br>HR Team</p>""",
            "recipients": [
                {"receiver_by_document_field": "user,activities"}
            ]
        }
    ]

    for notification in notifications:
        name = notification["name"]

        # Delete existing to avoid duplicates
        if frappe.db.exists("Notification", name):
            frappe.delete_doc("Notification", name, force=True)
            print(f"  Deleted existing: {name}")

        # Create new
        doc = frappe.new_doc("Notification")

        # Pop recipients before update
        recipients = notification.pop("recipients", [])
        doc.update(notification)

        # Add recipients child table
        doc.set("recipients", [])
        for recipient in recipients:
            doc.append("recipients", recipient)

        doc.insert(ignore_permissions=True)
        print(f"  Created: {name}")

    frappe.db.commit() 
    print("\nAll 3 joining reminder notifications created successfully!")
