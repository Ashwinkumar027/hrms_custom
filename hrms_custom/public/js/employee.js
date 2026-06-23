// Copyright (c) 2026, ASHWIN and contributors
// License: mit

frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (!frm.is_new() && frappe.user.has_role(["HR Manager", "HR User", "System Manager"])) {
			frm.add_custom_button(
				__("Download Documents"),
				() => show_download_dialog(frm),
				__("Documents")
			);
		}
	},
});

function show_download_dialog(frm) {
	if (!frm.doc.company) {
		frappe.msgprint(__("Please set the Company first."));
		return;
	}

	frappe.db.get_list("Document Type", { fields: ["name"], limit: 0 }).then((types) => {
		const dialog = new frappe.ui.Dialog({
			title: __("Download Documents"),
			fields: [
				{
					fieldname: "scope",
					fieldtype: "Select",
					label: __("Scope"),
					options: [
						{ label: __("This Employee Only ({0})", [frm.doc.name]), value: "employee" },
						{ label: __("Entire Company ({0})", [frm.doc.company]), value: "company" },
					],
					default: "employee",
					reqd: 1,
				},
				{
					fieldname: "document_type",
					fieldtype: "Select",
					label: __("Document Type"),
					options: ["All Documents", ...types.map((t) => t.name)],
					default: "All Documents",
					reqd: 1,
				},
			],
			primary_action_label: __("Download"),
			primary_action: (values) => {
				const docType = values.document_type === "All Documents" ? "" : values.document_type;
				let url;

				if (values.scope === "employee") {
					url = `/api/method/hrms_custom.hrms_custom.utils.document_management.download_employee_documents?employee=${encodeURIComponent(frm.doc.name)}`;
				} else {
					url = `/api/method/hrms_custom.hrms_custom.utils.document_management.download_company_documents?company=${encodeURIComponent(frm.doc.company)}`;
				}

				if (docType) {
					url += `&document_type=${encodeURIComponent(docType)}`;
				}

				window.open(url);
				dialog.hide();
			},
		});
		dialog.show();
	});
}

frappe.ui.form.on("Employee Document", {
	document_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.document_type) {
			frappe.db.get_value("Document Type", row.document_type, "is_expiry_based").then((r) => {
				if (r.message && !r.message.is_expiry_based) {
					frappe.model.set_value(cdt, cdn, "expiry_date", null);
				}
			});
		}
	},
});
