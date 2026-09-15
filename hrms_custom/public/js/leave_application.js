// Copyright (c) 2026, ASHWIN and contributors
// License: mit

frappe.ui.form.on("Leave Application", {
	refresh(frm) {
		toggle_half_day_for_optional_leave(frm);
	},
	leave_type(frm) {
		toggle_half_day_for_optional_leave(frm);
	},
	half_day(frm) {
		if (frm.doc.half_day && frm.doc.leave_type) {
			check_optional_leave_half_day(frm);
		}
	},
});

function toggle_half_day_for_optional_leave(frm) {
	if (!frm.doc.leave_type) {
		frm.set_df_property("half_day", "read_only", 0);
		frm.set_df_property("half_day", "hidden", 0);
		return;
	}
	frappe.db.get_value("Leave Type", frm.doc.leave_type, "is_optional_leave").then((r) => {
		if (r.message && r.message.is_optional_leave) {
			if (frm.doc.half_day) {
				frm.set_value("half_day", 0);
				frm.set_value("half_day_date", "");
			}
			frm.set_df_property("half_day", "read_only", 1);
			frm.set_df_property("half_day", "hidden", 1);
		} else {
			frm.set_df_property("half_day", "read_only", 0);
			frm.set_df_property("half_day", "hidden", 0);
		}
	});
}

function check_optional_leave_half_day(frm) {
	frappe.db.get_value("Leave Type", frm.doc.leave_type, "is_optional_leave").then((r) => {
		if (r.message && r.message.is_optional_leave && frm.doc.half_day) {
			frm.set_value("half_day", 0);
			frm.set_value("half_day_date", "");
			frappe.msgprint(__("Half day is not allowed for optional holidays. Please apply for full days only."));
		}
	});
}
