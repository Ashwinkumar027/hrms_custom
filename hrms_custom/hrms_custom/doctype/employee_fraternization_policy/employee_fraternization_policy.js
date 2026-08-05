// Copyright (c) 2026, ASHWIN and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Fraternization Policy", {
	refresh(frm) {
		frm.add_custom_button(__("Download PDF"), function () {
			frappe.db.get_value("Print Format", "Employee Fraternization Policy", "pdf_generator", (r) => {
				const pdf_generator = r.pdf_generator || "wkhtmltopdf";
				const url = frappe.urllib.get_full_url(
					"/api/method/frappe.utils.print_format.download_pdf"
					+ "?doctype=" + encodeURIComponent("Employee Fraternization Policy")
					+ "&name=" + encodeURIComponent(frm.doc.name)
					+ "&format=" + encodeURIComponent("Employee Fraternization Policy")
					+ "&no_letterhead=0"
					+ "&pdf_generator=" + encodeURIComponent(pdf_generator)
				);
				window.open(url, "_blank");
			});
		}, __("")).addClass("btn-primary");
	},
});
