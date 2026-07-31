import frappe


def execute():
    """Delete the Attendance Request-from_date-label Property Setter.

    Added earlier in the same round of PWA form work to relabel from_date
    to "Date" (when to_date was hidden and derived server-side). That
    approach was reverted - to_date is a normal visible field again - so
    this label override is no longer wanted; the core doctype's native
    label ("From Date") is correct again. Removing the entry from
    fixtures/property_setter.json does not delete an already-synced
    Property Setter row (fixture sync only creates/updates), so this
    patch removes it explicitly.
    """
    frappe.delete_doc(
        "Property Setter",
        "Attendance Request-from_date-label",
        ignore_missing=True,
        force=True,
    )
