// Copyright (c) 2026, ASHWIN and contributors
// License: mit

frappe.listview_settings["Employee"] = frappe.listview_settings["Employee"] || {};

frappe.listview_settings["Employee"].formatters = frappe.listview_settings["Employee"].formatters || {};

frappe.listview_settings["Employee"].formatters["custom_probation_status"] = function(val) {
	if (!val) return "";
	const color = val === "Confirmed" ? "green" : (val === "Not Confirmed" ? "orange" : "gray");
	return `<span class="indicator-pill ${color} filterable ellipsis" data-filter="custom_probation_status,=,${val}">
		<span class="indicator ${color}"></span>
		<span class="ellipsis">${__(val)}</span>
	</span>`;
};
