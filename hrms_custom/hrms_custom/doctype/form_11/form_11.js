// Copyright (c) 2026, ASHWIN and contributors
// For license information, please see license.txt

frappe.ui.form.on("Form 11", {
	refresh(frm) {
		frm.add_custom_button(__("Download PDF"), function () {
			frappe.db.get_value("Print Format", "Form 11", "pdf_generator", (r) => {
				const pdf_generator = r.pdf_generator || "wkhtmltopdf";
				const url = frappe.urllib.get_full_url(
					"/api/method/frappe.utils.print_format.download_pdf"
					+ "?doctype=" + encodeURIComponent("Form 11")
					+ "&name=" + encodeURIComponent(frm.doc.name)
					+ "&format=" + encodeURIComponent("Form 11")
					+ "&no_letterhead=0"
					+ "&pdf_generator=" + encodeURIComponent(pdf_generator)
				);
				window.open(url, "_blank");
			});
		}, __("")).addClass("btn-primary");
	},
});
