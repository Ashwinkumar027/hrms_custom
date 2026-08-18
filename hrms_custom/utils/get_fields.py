import frappe
import json

meta = frappe.get_meta('Employee Onboarding')
fields = []
for f in meta.fields:
    fields.append({"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype})

print(json.dumps(fields, indent=2))
