import frappe

def execute():
    notifications = frappe.get_all('Notification', fields=['name', 'subject', 'message'])
    for n in notifications:
        if n.subject and 'ID Card' in n.subject:
            print('Found Notification:', n.name)
            with open('/home/ashwinkumark_quanti/frappe/my-bench/id_notification.txt', 'w') as f:
                f.write(n.message)
