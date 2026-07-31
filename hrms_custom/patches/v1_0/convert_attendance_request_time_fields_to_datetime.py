import frappe

COLUMNS = ["custom_permission_from_time", "custom_permission_to_time"]
DOCTYPE = "Attendance Request"


def execute():
    """Convert custom_permission_from_time/custom_permission_to_time from
    Time to Datetime ourselves, before fixtures sync the fieldtype change.

    A fixture-driven Custom Field fieldtype change bypasses Frappe's own
    "disallowed conversion" guard (fixture import deletes and reinserts the
    Custom Field doc rather than loading-and-saving it), so `ALTER TABLE
    ... MODIFY DATETIME` runs unattended. On MariaDB this silently rewrites
    every existing row's date portion to the migration day while preserving
    the time-of-day — verified empirically, and reconfirmed against this
    site's live MariaDB using frappe.db.change_column_type()'s exact
    generated SQL (the wrapper changes nothing about MariaDB's own
    conversion behavior, only how Frappe's transaction tracking issues the
    ALTER). Since this doctype enforces from_date == to_date for every
    request, from_date is the source of truth for what the date portion
    should have been; reconstruct it before fixture sync gets a chance to
    run the same ALTER TABLE uncontrolled.

    Uses frappe.db.change_column_type() rather than a raw ALTER TABLE via
    frappe.db.sql() - the raw form trips frappe.exceptions.ImplicitCommitError
    as soon as any prior write happened in the same transaction (including
    the reconstruction UPDATE for an earlier column in this same loop, or
    writes from an earlier patch in the same migrate run - MariaDB DDL always
    causes an implicit commit, and Frappe refuses to run alter/drop/create
    statements once transaction_writes is nonzero). change_column_type()
    calls sql_ddl(), which commits first, so it never trips this guard
    regardless of what ran before it. nullable=True is mandatory - the
    default is NOT NULL, and these columns are legitimately blank for most
    rows (only reasons that actually use them populate them).

    The per-column type check and the reconstruction UPDATE are
    deliberately decoupled: the UPDATE always runs (not just on a fresh
    conversion), guarded only by its own WHERE clause (DATE(column) <>
    from_date). That WHERE clause makes it a no-op against rows already
    correctly reconstructed - confirmed empirically (0 rows affected on a
    repeat run) - so this is safe to resume from any partial-failure state:
    a column already converted-and-reconstructed by a prior aborted run is
    left untouched; a column converted but not yet reconstructed (should
    that ever happen) still gets fixed; a column not yet converted at all
    gets both steps.

    Must run post_model_sync (after frappe.model.sync.sync_all(), before
    sync_fixtures()) - running pre_model_sync risks sync_all() reloading
    stale (still-Time) doctype meta and reverting this conversion.
    """
    table = "tabAttendance Request"

    for column in COLUMNS:
        if not frappe.db.has_column(DOCTYPE, column):
            continue

        current_type = frappe.db.get_column_type(DOCTYPE, column)
        if not (current_type and current_type.lower().startswith("datetime")):
            frappe.db.change_column_type(DOCTYPE, column, "datetime(6)", nullable=True)

        frappe.db.sql(
            f"""
            UPDATE `{table}`
            SET `{column}` = TIMESTAMP(from_date, TIME(`{column}`))
            WHERE `{column}` IS NOT NULL
              AND from_date IS NOT NULL
              AND DATE(`{column}`) <> from_date
            """
        )
        frappe.db.commit()
