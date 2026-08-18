import frappe

def check_rejection(dt):
    meta = frappe.get_meta(dt)
    fields = [f.fieldname for f in meta.fields if 'reject' in f.fieldname.lower() or 'reason' in f.fieldname.lower()]
    
    scripts = frappe.get_all('Client Script', filters={'dt': dt}, fields=['name', 'script'])
    has_intercept = False
    for s in scripts:
        if 'before_workflow_action' in s.script and 'Reject' in s.script:
            has_intercept = True
            
    print(f"{dt} - Fields: {fields} - Intercept Script: {has_intercept}")

print('--- REJECTION CHECK ---')
check_rejection('Interview')
check_rejection('Job Offer')
check_rejection('Job Requisition')
print('-----------------------')
