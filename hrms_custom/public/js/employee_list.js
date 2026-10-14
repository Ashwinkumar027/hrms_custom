// Copyright (c) 2026, ASHWIN and contributors
// License: mit

frappe.listview_settings["Employee"] = {
	add_fields: ["status", "branch", "department", "designation", "image", "custom_probation_status"],
	filters: [["status", "=", "Active"]],
	get_indicator(doc) {
		return [
			__(doc.status, null, "Employee"),
			{ Active: "green", Inactive: "red", Left: "gray", Suspended: "orange" }[doc.status],
			"status,=," + doc.status,
		];
	},
	formatters: {
		custom_probation_status(val) {
			if (!val) return "";
			const color = val === "Confirmed" ? "green" : "orange";
			return `<span class="indicator-pill ${color}">${__(val)}</span>`;
		}
	}
};
