import frappe
templates = frappe.get_all('Employee Onboarding Template', fields=['name'])
for t in templates:
    doc = frappe.get_doc('Employee Onboarding Template', t.name)
    print(t.name)
    for a in doc.activities:
        print('  -', a.activity_name, '->', a.user)
