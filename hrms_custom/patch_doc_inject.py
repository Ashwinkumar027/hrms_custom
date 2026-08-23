import frappe

def execute():
    try:
        # Patch Client Script
        cs = frappe.get_doc("Client Script", "Job Requisition Enhancements")
        script = cs.script
        
        target_block = """                        frappe.call({
                            method: "frappe.client.set_value",
                            args: {
                                doctype: "Job Requisition",
                                name: frm.doc.name,
                                fieldname: "custom_rejection_reason",
                                value: values.reason
                            },
                            callback: function(r) {
                                d.hide();
                                resolve();
                            }
                        });"""
                        
        replacement_block = """                        frm.doc.custom_rejection_reason = values.reason;
                        frappe.call({
                            method: "frappe.client.set_value",
                            args: {
                                doctype: "Job Requisition",
                                name: frm.doc.name,
                                fieldname: "custom_rejection_reason",
                                value: values.reason
                            },
                            callback: function(r) {
                                d.hide();
                                resolve();
                            }
                        });"""
        
        if target_block in script:
            script = script.replace(target_block, replacement_block)
            cs.script = script
            cs.save()
            frappe.db.commit()
            print("Successfully patched Client Script to inject value into frm.doc.")
        else:
            print("Could not find the target block in Client Script.")
            
    except Exception as e:
        print(f"Error: {e}")
