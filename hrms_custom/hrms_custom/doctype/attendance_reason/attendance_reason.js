// Copyright (c) 2026, ASHWIN and contributors
// For license information, please see license.txt

frappe.ui.form.on("Attendance Reason", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.set_df_property("reason_name", "read_only", 1);
		}
	},
});
