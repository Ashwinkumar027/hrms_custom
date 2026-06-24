import frappe

def get_hr_sender():
    try:
        hr_settings = frappe.get_single("HR Settings")
        if hr_settings.sender_email:
            return hr_settings.sender_email
    except Exception:
        pass
    return None


def get_onboarding_contact(task_type, company=None):
    """
    Get responsible person email for onboarding task.
    First checks company-specific contact, then falls back to global.
    """
    try:
        # Company specific first
        if company:
            email = frappe.db.get_value(
                "Onboarding Task Contact",
                {"task_type": task_type, "company": company},
                "email"
            )
            if email:
                return email

        # Global fallback (no company filter)
        email = frappe.db.get_value(
            "Onboarding Task Contact",
            {"task_type": task_type, "company": ["is", "not set"]},
            "email"
        )
        return email or None
    except Exception:
        return None


def get_onboarding_team(task_type, company=None):
    """
    Get HD Team for onboarding task.
    First checks company-specific, then falls back to global.
    """
    try:
        if company:
            team = frappe.db.get_value(
                "Onboarding Task Contact",
                {"task_type": task_type, "company": company},
                "team"
            )
            if team:
                return team

        # Global fallback
        team = frappe.db.get_value(
            "Onboarding Task Contact",
            {"task_type": task_type, "company": ["is", "not set"]},
            "team"
        )
        return team or None
    except Exception:
        return None
