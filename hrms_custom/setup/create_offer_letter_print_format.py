import frappe

def create_offer_letter_print_format():
    print("Creating Offer Letter Print Format...")

    name = "Offer Letter - Quanticus"

    if frappe.db.exists("Print Format", name):
        frappe.delete_doc("Print Format", name, force=True)

    pf = frappe.new_doc("Print Format")
    pf.name = name
    pf.doc_type = "Job Offer"
    pf.print_format_type = "Jinja"
    pf.module = "HRMS Custom"
    pf.disabled = 0
    pf.html = open("/home/ashwin/frappe/my-bench/apps/hrms_custom/hrms_custom/setup/offer_letter_template.html").read()
    pf.insert(ignore_permissions=True)
    frappe.db.commit()
    print("Created: " + name)
