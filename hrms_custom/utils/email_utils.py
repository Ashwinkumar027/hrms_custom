import frappe

def get_hr_sender():
    try:
        hr_settings = frappe.get_single("HR Settings")
        if hr_settings.sender_email:
            return hr_settings.sender_email
    except Exception:
        pass
    return None
