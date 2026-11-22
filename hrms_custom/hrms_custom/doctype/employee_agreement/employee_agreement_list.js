frappe.listview_settings["Employee Agreement"] = {
	onload(listview) {
		const is_hr = frappe.user_roles.some(r => ["HR Manager", "HR User", "System Manager", "Administrator"].includes(r));
		if (is_hr) {
			listview.page.add_inner_button(__("Download All Agreements (ZIP)"), function () {
				window.open(frappe.urllib.get_full_url(
					"/api/method/hrms_custom.hrms_custom.doctype.employee_agreement.employee_agreement.download_all_agreements_zip"
				));
			});
		}
	}
};
