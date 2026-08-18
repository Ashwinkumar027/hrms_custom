import frappe

def execute():
    ss = frappe.get_doc('Server Script', 'Create Helpdesk Tickets - Employee Onboarding')
    with open('/home/ashwinkumark_quanti/frappe/my-bench/ss_code.txt', 'w') as f:
        f.write(ss.script)

execute()
