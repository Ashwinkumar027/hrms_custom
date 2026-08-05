// Copyright (c) 2026, ASHWIN and contributors
// For license information, please see license.txt

frappe.ui.form.on("ESI Enrollment", {
	refresh(frm) {
		frm.add_custom_button(__("Download PDF"), function () {
			const url = frappe.urllib.get_full_url(
				"/api/method/frappe.utils.print_format.download_pdf"
				+ "?doctype=" + encodeURIComponent("ESI Enrollment")
				+ "&name=" + encodeURIComponent(frm.doc.name)
				+ "&format=" + encodeURIComponent("ESI EPF Enrollment - Form Print")
				+ "&no_letterhead=0"
				+ "&pdf_generator=chrome"
			);
			window.open(url, "_blank");
		}, __("")).addClass("btn-primary");
	},
});
