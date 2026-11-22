frappe.ui.form.on("Employee Agreement", {
	onload(frm) {
		const is_hr = frappe.user_roles.some(r => ["HR Manager", "HR User", "System Manager", "Administrator"].includes(r));
		if (frm.is_new() && !is_hr) {
			frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "employee_name", "company", "designation", "date_of_joining"], (r) => {
				if (r && r.name) {
					frm.set_value("employee", r.name);
					if (r.company) frm.set_value("company", r.company);
					if (r.designation) frm.set_value("designation", r.designation);
					if (r.date_of_joining) frm.set_value("date_of_joining", r.date_of_joining);
					if (!frm.doc.aadhaar_name && r.employee_name) {
						frm.set_value("aadhaar_name", r.employee_name);
					}
					frm.trigger("employee");
				} else {
					frm.set_df_property("employee", "read_only", 1);
					frappe.msgprint({
						title: __("No Linked Employee Profile"),
						indicator: "orange",
						message: __("Your user account (<b>{0}</b>) is not linked to any Employee profile in HRMS.<br><br>Please contact HR/Administrator to set your User ID in your Employee profile before submitting your agreement.", [frappe.session.user])
					});
				}
			});
		} else {
			if (frm.doc.employee && !frm.doc.reporting_manager) {
				fetch_and_set_reporting_manager(frm);
			}
			setup_field_rules(frm);
			check_missing_fields_alert(frm);
		}
	},

	refresh(frm) {
		const is_hr = frappe.user_roles.some(r => ["HR Manager", "HR User", "System Manager", "Administrator"].includes(r));
		if (frm.is_new() && !is_hr && !frm.doc.employee) {
			frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name", (r) => {
				if (r && r.name) {
					frm.set_value("employee", r.name);
					frm.trigger("employee");
				}
			});
		}

		if (frm.doc.employee && !frm.doc.reporting_manager) {
			fetch_and_set_reporting_manager(frm);
		}

		setup_field_rules(frm);
		check_missing_fields_alert(frm);
		render_agreement(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__("Download PDF"), function () {
				const url = frappe.urllib.get_full_url(
					"/api/method/frappe.utils.print_format.download_pdf"
					+ "?doctype=" + encodeURIComponent("Employee Agreement")
					+ "&name=" + encodeURIComponent(frm.doc.name)
					+ "&format=" + encodeURIComponent("Employee Agreement - Print")
					+ "&no_letterhead=0"
					+ "&pdf_generator=chrome"
				);
				window.open(url, "_blank");
			}).addClass("btn-primary");
		}
	},

	employee(frm) {
		if (frm.doc.employee) {
			fetch_and_set_reporting_manager(frm);
			frappe.call({
				method: "hrms_custom.hrms_custom.doctype.employee_agreement.employee_agreement.get_agreement_context",
				args: {
					employee: frm.doc.employee,
					company: frm.doc.company,
					doc_name: frm.doc.name,
				},
				callback: function (r) {
					if (r && r.message) {
						const ctx = r.message;
						frm.__master_empty_fields = frm.__master_empty_fields || {};
						if (!ctx.parent_spouse_name || ctx.parent_spouse_name === "____") {
							frm.__master_empty_fields.father_name = true;
						}
						if (!ctx.full_address || ctx.full_address === "____") {
							frm.__master_empty_fields.full_address = true;
						}

						if (!frm.doc.place && ctx.place) frm.set_value("place", ctx.place);
						if (!frm.doc.date) frm.set_value("date", frappe.datetime.get_today());
						if (!frm.doc.aadhaar_name && frm.doc.employee_name) frm.set_value("aadhaar_name", frm.doc.employee_name);
						if (!frm.doc.father_name && ctx.parent_spouse_name && ctx.parent_spouse_name !== "____") {
							frm.set_value("father_name", ctx.parent_spouse_name);
						}
						if (!frm.doc.age && ctx.age && ctx.age !== "____") {
							frm.set_value("age", parseInt(ctx.age, 10));
						}
						if (!frm.doc.full_address && ctx.full_address && ctx.full_address !== "____") {
							frm.set_value("full_address", ctx.full_address);
						}
						if (!frm.doc.reporting_manager && ctx.reporting_manager && ctx.reporting_manager !== "the Board") {
							frm.set_value("reporting_manager", ctx.reporting_manager);
						}
						if (!frm.doc.custom_employee_ctc && ctx.ctc_formatted && ctx.ctc_formatted !== "____") {
							frm.set_value("custom_employee_ctc", flt(ctx.ctc_formatted.replace(/,/g, "")));
						}
						if (!frm.doc.custom_roles__responsibilities && ctx.roles_responsibilities) {
							frm.set_value("custom_roles__responsibilities", ctx.roles_responsibilities);
						}
						setup_field_rules(frm);
						check_missing_fields_alert(frm);
						render_agreement(frm);
					}
				},
			});
		} else {
			setup_field_rules(frm);
			check_missing_fields_alert(frm);
			render_agreement(frm);
		}
	},

	company(frm) { render_agreement(frm); },
	designation(frm) { check_missing_fields_alert(frm); render_agreement(frm); },
	reporting_manager(frm) { render_agreement(frm); },
	aadhaar_name(frm) { render_agreement(frm); },
	father_name(frm) {
		check_missing_fields_alert(frm);
		render_agreement(frm);
	},
	age(frm) { render_agreement(frm); },
	full_address(frm) {
		check_missing_fields_alert(frm);
		render_agreement(frm);
	},
	date_of_joining(frm) { render_agreement(frm); },
	place(frm) { render_agreement(frm); },
	date(frm) { render_agreement(frm); },
	custom_employee_ctc(frm) {
		check_missing_fields_alert(frm);
		render_agreement(frm);
	},
	custom_roles__responsibilities(frm) { render_agreement(frm); },

	validate(frm) {
		const has_draw = Boolean(frm.doc.employee_signature && frm.doc.employee_signature.trim());
		const has_upload = Boolean(frm.doc.employee_signature_upload && frm.doc.employee_signature_upload.trim());

		if (!has_draw && !has_upload) {
			frappe.msgprint({
				title: __("Signature Required"),
				indicator: "red",
				message: __("Please provide your signature before saving — either <b>draw your signature</b> on the pad or <b>upload a signature image</b>.")
			});
			frappe.validated = false;
			return false;
		}

		if (has_draw && has_upload) {
			frappe.msgprint({
				title: __("Only One Signature Allowed"),
				indicator: "red",
				message: __("Please provide only one signature format — either drawn or uploaded, not both.")
			});
			frappe.validated = false;
			return false;
		}
	},

	before_submit(frm) {
		if (!frm.doc.father_name || !String(frm.doc.father_name).trim()) {
			frappe.msgprint({
				title: __("Father's Name Required"),
				indicator: "red",
				message: __("Please enter your <b>Father's / Spouse's Name</b> in the personal details section before submitting your agreement.")
			});
			frappe.validated = false;
			return false;
		}
		if (!frm.doc.full_address || !String(frm.doc.full_address).trim()) {
			frappe.msgprint({
				title: __("Residential Address Required"),
				indicator: "red",
				message: __("Please enter your <b>Full Residential Address</b> in the address section before submitting your agreement.")
			});
			frappe.validated = false;
			return false;
		}
		if (!frm.doc.custom_employee_ctc || flt(frm.doc.custom_employee_ctc) <= 0) {
			frappe.msgprint({
				title: __("Annual CTC Missing"),
				indicator: "red",
				message: __("Your <b>Annual CTC</b> is not set in your Employee profile. Legally binding employment agreements cannot be submitted without compensation details. Please contact HR before submitting.")
			});
			frappe.validated = false;
			return false;
		}
		if (!frm.doc.designation) {
			frappe.msgprint({
				title: __("Designation Missing"),
				indicator: "red",
				message: __("Your <b>Designation</b> is missing. Please contact HR to update your designation before submitting.")
			});
			frappe.validated = false;
			return false;
		}
	},

	employee_signature(frm) {
		if (frm.doc.employee_signature && frm.doc.employee_signature_upload) {
			frm.set_value("employee_signature_upload", "");
		}
		render_agreement(frm);
	},

	employee_signature_upload(frm) {
		if (frm.doc.employee_signature_upload && frm.doc.employee_signature) {
			frm.set_value("employee_signature", "");
		}
		render_agreement(frm);
	},
});


function fetch_and_set_reporting_manager(frm) {
	if (!frm.doc.employee) return;
	frappe.call({
		method: "hrms_custom.hrms_custom.doctype.employee_agreement.employee_agreement.get_reporting_manager",
		args: {
			employee: frm.doc.employee
		},
		callback: function (r) {
			if (r && r.message && r.message !== "the Board") {
				frm.set_value("reporting_manager", r.message);
			}
		}
	});
}

function setup_field_rules(frm) {
	const is_hr = frappe.user_roles.some(r => ["HR Manager", "HR User", "System Manager", "Administrator"].includes(r));
	const is_submitted = frm.doc.docstatus === 1;

	// Strictly Read-Only Corporate & Financial Fields (Employees cannot alter salary/designation)
	const corporate_fields = [
		"employee", "employee_name", "company", "designation",
		"reporting_manager", "date_of_joining", "age",
		"custom_employee_ctc", "custom_roles__responsibilities"
	];
	corporate_fields.forEach(f => {
		if (frm.fields_dict[f]) {
			frm.set_df_property(f, "read_only", (!is_hr || is_submitted) ? 1 : 0);
		}
	});

	// Personal / Self-Service Fields (Hybrid Lock)
	// If HR or empty in master -> Unlocked for self-entry
	// If submitted -> Strictly locked
	const personal_fields = ["father_name", "full_address", "aadhaar_name"];
	personal_fields.forEach(f => {
		if (frm.fields_dict[f]) {
			if (is_submitted) {
				frm.set_df_property(f, "read_only", 1);
			} else if (is_hr) {
				frm.set_df_property(f, "read_only", 0);
			} else {
				frm.__master_empty_fields = frm.__master_empty_fields || {};
				const was_master_empty = Boolean(frm.__master_empty_fields[f]);
				const cur_val = frm.doc[f];
				const has_val = cur_val !== undefined && cur_val !== null && String(cur_val).trim() !== "" && String(cur_val).trim() !== "____";

				if (was_master_empty || !has_val) {
					frm.set_df_property(f, "read_only", 0);
				} else {
					frm.set_df_property(f, "read_only", 1);
				}

				if (f === "father_name") {
					frm.set_df_property(f, "placeholder", __("Enter Father's Name / Spouse's Name"));
				} else if (f === "full_address") {
					frm.set_df_property(f, "placeholder", __("Enter complete residential address"));
				} else if (f === "aadhaar_name") {
					frm.set_df_property(f, "placeholder", __("Enter Name as per Aadhaar"));
				}
			}
		}
	});

	if (frm.fields_dict.place) frm.set_df_property("place", "read_only", is_submitted ? 1 : 0);
	if (frm.fields_dict.date) frm.set_df_property("date", "read_only", is_submitted ? 1 : 0);
	if (frm.fields_dict.witness_name) frm.set_df_property("witness_name", "read_only", is_submitted ? 1 : 0);
}

function check_missing_fields_alert(frm) {
	frm.dashboard.clear_headline();

	if (frm.doc.docstatus === 1) {
		return;
	}

	const missing_hr = [];
	const missing_emp = [];

	if (!frm.doc.custom_employee_ctc || flt(frm.doc.custom_employee_ctc) <= 0) {
		missing_hr.push(__("Annual CTC"));
	}
	if (!frm.doc.designation) {
		missing_hr.push(__("Designation"));
	}
	if (!frm.doc.father_name || !String(frm.doc.father_name).trim()) {
		missing_emp.push(__("Father's / Spouse's Name"));
	}
	if (!frm.doc.full_address || !String(frm.doc.full_address).trim()) {
		missing_emp.push(__("Full Residential Address"));
	}

	let html = "";
	if (missing_hr.length > 0) {
		html += `<div style="font-size: 13px; line-height: 1.5; color: #b45309; font-weight: 500;">
			⚠️ <b>${__("Action Required with HR")}:</b> ${missing_hr.join(", ")} ${__("is missing from your Employee record. Please request HR to configure this before submitting.")}
		</div>`;
	}
	if (missing_emp.length > 0) {
		html += `<div style="font-size: 13px; line-height: 1.5; color: #1d4ed8; font-weight: 500; ${missing_hr.length ? 'margin-top:4px;' : ''}">
			✍️ <b>${__("Personal Details Required")}:</b> ${__("Please complete your")} <b>${missing_emp.join(" & ")}</b> ${__("in the unlocked fields below.")}
		</div>`;
	}

	if (html) {
		frm.dashboard.set_headline_alert(html, missing_hr.length > 0 ? "orange" : "blue");
	} else {
		frm.dashboard.clear_headline();
	}
}

function render_agreement(frm) {
	if (!frm.fields_dict.agreement_html) return;

	if (!frm.doc.company && !frm.doc.employee) {
		frm.fields_dict.agreement_html.$wrapper.html(
			'<div style="padding:16px; color:#888;">Select an Employee or Company to preview the agreement.</div>'
		);
		return;
	}

	frappe.call({
		method: "hrms_custom.hrms_custom.doctype.employee_agreement.employee_agreement.get_agreement_context",
		args: {
			employee: frm.doc.employee,
			company: frm.doc.company,
			doc_name: frm.doc.name,
		},
		callback: function (r) {
			const ctx = (r && r.message) || {};
			const html = build_agreement_html(frm, ctx);
			frm.fields_dict.agreement_html.$wrapper.html(html);
		},
	});
}

function esc(v) {
	return v === undefined || v === null || v === "" ? "____" : frappe.utils.escape_html(String(v));
}

function fmt_date(d) {
	return d ? frappe.datetime.str_to_user(d) : "____";
}

function build_agreement_html(frm, ctx) {
	const d = frm.doc;
	const company_name = esc(ctx.company_name || d.company);
	const company_address = esc(ctx.company_address);
	const company_pan = esc(ctx.company_pan);
	const business_description = esc(ctx.business_description || "financial planning and corporate services");
	const logo = ctx.company_logo || "";
	const cin = esc(ctx.cin_number);
	const sebi = esc(ctx.sebi_registration_no);
	const amfi = esc(ctx.amfi_registration_no);
	const email = esc(ctx.compliance_email);

	const employee_name = esc(d.aadhaar_name || d.employee_name);
	const parent_spouse_name = esc(d.father_name || ctx.parent_spouse_name);
	let relation = esc(ctx.relation || "S/o, D/o or W/o");
	if (d.father_name && (!ctx.parent_spouse_name || ctx.parent_spouse_name === "____")) {
		const gender = (ctx.gender || "").toLowerCase();
		relation = gender === "female" ? "D/o" : "S/o";
	}
	const age = esc(d.age || ctx.age);
	const full_address = esc(d.full_address || ctx.full_address);
	const designation = esc(d.designation);
	const doj = fmt_date(d.date_of_joining);
	const execution_date = d.date ? fmt_date(d.date) : (ctx.execution_date || "____");
	const place = esc(d.place || ctx.place || "Chennai");
	const principal_place = esc(ctx.principal_place || (place + ", Tamil Nadu, India"));
	const reporting_manager = esc(d.reporting_manager || ctx.reporting_manager || "the Board");

	let ctc_num = "____";
	let ctc_words = "____";
	if (d.custom_employee_ctc) {
		ctc_num = format_currency(d.custom_employee_ctc, frappe.defaults.get_default("currency"));
		ctc_words = ctx.ctc_in_words || "";
	} else if (ctx.ctc_formatted && ctx.ctc_formatted !== "____") {
		ctc_num = "INR " + ctx.ctc_formatted;
		ctc_words = ctx.ctc_in_words || "";
	}

	const ctc_display = ctc_words && ctc_words !== "____" 
		? `${ctc_num} (${ctc_words})` 
		: ctc_num;

	const sig_name = esc(ctx.signatory_name);
	const sig_desig = esc(ctx.signatory_designation);
	const sig_img = ctx.signatory_signature || "";

	let emp_sig_html = `<div style="height:40px;"></div>`;
	if (d.employee_signature && !d.employee_signature.includes("signature-placeholder")) {
		emp_sig_html = `<img src="${d.employee_signature}" style="height:40px; object-fit:contain;"><br>`;
	} else if (d.employee_signature_upload) {
		emp_sig_html = `<img src="${d.employee_signature_upload}" style="height:40px; object-fit:contain;"><br>`;
	}

	return `
	<style>
		.ea-container {
			background: #eef2f5;
			padding: 20px 10px;
			max-height: 620px;
			overflow-y: auto;
		}
		.ea-sheet {
			background: #fff;
			width: 210mm;
			min-height: 297mm;
			margin: 0 auto 25px auto;
			padding: 20mm 20mm 20mm 20mm;
			box-shadow: 0 4px 12px rgba(0,0,0,0.12);
			border: 1px solid #d1d8dd;
			box-sizing: border-box;
			font-family: 'Times New Roman', serif;
			font-size: 11.5pt;
			line-height: 1.48;
			color: #111;
			position: relative;
		}
		.ea-sheet-header {
			text-align: center;
			margin-bottom: 12pt;
			border-bottom: 1.5pt solid #000;
			padding-bottom: 6pt;
		}
		.ea-sheet-header img {
			height: 48px;
			object-fit: contain;
			margin-bottom: 3pt;
		}
		.ea-cname {
			font-size: 13pt;
			font-weight: bold;
			letter-spacing: 0.5px;
		}
		.ea-caddr {
			font-size: 8.5pt;
			color: #333;
			line-height: 1.3;
			margin-top: 2pt;
		}
		.ea-page-badge {
			position: absolute;
			top: 10px;
			right: 15px;
			font-size: 9pt;
			font-weight: bold;
			color: #888;
		}
		table.ea-table {
			border-collapse: collapse;
			width: 85%;
			margin: 10pt auto;
			font-size: 10.5pt;
		}
		table.ea-table th, table.ea-table td {
			border: 1px solid #000;
			padding: 4pt 8pt;
			text-align: center;
		}
		table.ea-table th {
			background: #f2f2f2;
			font-weight: bold;
		}
		p {
			margin: 0 0 9pt 0;
			text-align: justify;
		}
	</style>

	<div class="ea-container">

		<div class="ea-sheet" id="sheet-page-1">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 1 of 9</div>
<p style="text-align:center; margin: 0 0 9pt 0;"><u><b>EMPLOYMENT AGREEMENT</b></u></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">This Employment Agreement (the "<b>Agreement</b>") is made and entered into at <b>${place}</b> on <b>${execution_date}</b> (the "<b>Execution</b><b> Date</b>"),</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>BETWEEN:</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>${company_name}</b>, a company incorporated under the <b>Companies Act, 2013</b>, having its registered office at ${company_address}<b> </b>and having PAN <b>${company_pan}</b> (hereinafter referred to as the "<b>Company</b>" or "<b>Employer</b>", which expression shall, unless the context otherwise requires, include its successors and permitted assigns);</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>AND</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>${employee_name}</b>, ${relation} <b>${parent_spouse_name}</b>, aged about <b>${age}</b> years, residing at <b>${full_address}</b> (hereinafter referred to as the "<b>Employee</b>").</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employer and the Employee shall be collectively referred to as the "<b>Parties</b>" and individually as a "<b>Party</b>".</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>WHEREAS</b> the Company is engaged in the business of <b>${business_description}</b>;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>WHEREAS</b> the Employee possesses the requisite qualifications, skills, experience and expertise for the said designation, and has represented the same to the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>WHEREA</b>S the Company has employed the Employee as <b>${designation}</b><b> </b>from<b> ${execution_date} (Effective Date)</b>, and the Employee has agreed to accept such employment, on the terms and conditions set forth herein;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>WHEREAS</b>, in supersession of any and all previous terms of engagement of the Employee, whether with the Company or any other entity, the Parties wish to record the terms of the Employee's employment under this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>NOW THEREFORE, IN CONSIDERATION OF THE MUTUAL PROMISES, COVENANTS AND AGREEMENTS SET FORTH HEREIN, AND FOR OTHER GOOD AND VALUABLE CONSIDERATION, THE RECEIPT AND SUFFICIENCY OF WHICH ARE HEREBY ACKNOWLEDGED, THE PARTIES, INTENDING TO BE LEGALLY BOUND, AGREE AS FOLLOWS:</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>DEFINITIONS AND INTERPRETATION</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">In this Agreement, unless the context otherwise requires:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>"Applicable Law"</b> means any statute, law, regulation, ordinance, rule, judgment, notification, order, decree, bye-law, permit, licence, direction or guideline of any Governmental Authority applicable to the Parties;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>"Board"</b> means the board of directors of the Company or any duly authorised committee thereof;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>"Confidential Information"</b> has the meaning ascribed to it in Clause 10;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>"Governmental Authority"</b> means any government or political subdivision thereof, any court, tribunal, regulatory or self-regulatory authority, or any other governmental or statutory body having jurisdiction over the Parties;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>"Work Product"</b> has the meaning ascribed to it in Clause 12.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">Headings are for convenience only and shall not affect the interpretation of this Agreement. References to the singular include the plural and vice versa; references to any gender include all genders; and references to a Clause are to a Clause of this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>APPOINTMENT AND DESIGNATION</b></p>
		</div>


		<div class="ea-sheet" id="sheet-page-2">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 2 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Company hereby appoints the Employee as <b>${designation}</b>, and the Employee hereby accepts such appointment, subject to the terms and conditions of this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall report to <b>${reporting_manager}</b> or such other person(s) as may be designated by the Board from time to time.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>PLACE OF EMPLOYMENT</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee's principal place of employment shall be <b>${principal_place}</b>.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee may be required to travel to other locations within India or abroad, and may be required to relocate, as may be necessary in the interests of the Company's business, at the Company's discretion.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>TERM AND PROBATION</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The term of employment shall commence on the Effective Date and shall continue unless terminated in accordance with the provisions of this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall be subject to a probation period based on the applicable employee level, as specified in the Probation Period Schedule below. During the probation period, the Employee may resign by providing written notice in accordance with the grade-wise notice period specified under Clause 15.4 of this Agreement. The Company reserves the right to terminate the Employee's employment during the probation period, without assigning any reason, without providing prior notice or payment in lieu of notice.</p>
<table class="ea-table" style="border-collapse:collapse; width:85%; margin:10pt auto; font-size:11pt;"><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">Employee Level</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">Probation Period</td></tr><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">L1A – L2B</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">6 Months</td></tr><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">L3A – L4B</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">3 Months</td></tr><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">L5A & Above</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">2 Months</td></tr></table>
<p style="text-align:justify; margin: 0 0 9pt 0;">Upon satisfactory completion of the applicable probation period, the Employee's services shall be confirmed in writing by the Company. The Company reserves the right to extend the probation period by up to three (3) months, based on the Employee's performance and suitability, subject to applicable law.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">During the Probation Period, the Employee shall not be entitled to any Performance-Linked Incentive under this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">In view of the training costs, proprietary knowledge and client and business relationships to which the Employee will be exposed, the Employee agrees to remain employed with the Company for a minimum period of <b>1</b> year(s) from the date of confirmation of services (the "<b>Lock-in Period</b>").</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>DUTIES AND RESPONSIBILITIES</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall devote the Employee's full time, attention, skill and best efforts exclusively to the business and affairs of the Company. The Employee shall faithfully, efficiently, competently and diligently perform all duties and exercise such powers as may from time to time be assigned to or vested in the Employee.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">Without limiting the generality of the foregoing, the Employee's responsibilities shall include, but not be limited to:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">Meet sales targets and performance metrics through active client engagement;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">Meet sales targets and performance metrics through active client engagement;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">Identify client needs, offer tailored solutions, and ensure customer satisfaction; and</p>
		</div>


		<div class="ea-sheet" id="sheet-page-3">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 3 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;">such other duties as may be assigned by the Company from time to time.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>COMPENSATION AND BENEFITS</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Fixed Compensation: </b>In consideration of the Employee's services, the Company shall pay the Employee an annual fixed compensation of INR <b>${ctc_display}</b>, inclusive of all statutory contributions and subject to applicable tax deductions, payable in monthly instalments in accordance with the Company's payroll cycle.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Performance-Linked Incentive: </b>In addition to the Fixed Compensation, the Employee may be eligible for a performance-linked incentive (the "<b>Performance Incentive</b>"), subject to the following:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Quantum: </b>as determined by the Company, based on such performance metrics as may be notified by the Company from time to time;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Performance Period: </b>each financial year (1 April to 31 March), or such other period as may be determined by the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Conditions: </b>the Performance Incentive shall be subject to the following conditions:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">the Employee must be in active, confirmed employment with the Company on the date of disbursement, and must not have tendered resignation or been served a notice of termination;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">the Employee must not be in breach of any material obligation under this Agreement;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">the Performance Incentive shall be subject to applicable tax deductions and statutory contributions;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">the Company reserves the right to claw back all or part of the Performance Incentive in the event of any material misrepresentation, fraud or wilful breach by the Employee, for a period of twenty-four (24) months from the date of each disbursement; and</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">the Performance Incentive shall be pro-rated for any performance period during which the Employee was not employed for the entire period.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>No Entitlement: </b>for the avoidance of doubt, the Performance Incentive is discretionary and contingent upon the conditions set out above. No right to the Performance Incentive shall accrue unless and until all conditions are satisfied and the payment is actually made.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall be entitled to such other benefits as may be available under the Company's policies and Applicable Law, as in effect from time to time.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee's compensation is strictly confidential. The Employee shall not disclose, discuss or share details of the Employee's compensation with any person, whether within or outside the organisation, other than the Company's authorised personnel or the Employee's immediate family and professional advisers bound by confidentiality.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>COMPANY POLICIES</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee's employment is subject to the Company's policies as may be issued and amended by the Board or management from time to time.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall be entitled to leaves in accordance with the Company's leave policy and shall adhere to the process for availing such leaves.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Company shall reimburse all reasonable travel, accommodation and other expenses incurred by the Employee on the Company's business, in accordance with the Company's policies.</p>
		</div>


		<div class="ea-sheet" id="sheet-page-4">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 4 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall mandatorily undergo, complete and comply with all training programmes, compliance courses and assessments prescribed by the Company from time to time, including but not limited to Prevention of Sexual Harassment (POSH), Code of Conduct, Anti-Bribery and Anti-Corruption, Information Security, Data Protection and other statutory, regulatory or internal compliance requirements applicable to the Employee. The Employee shall complete such programmes within the timelines stipulated by the Company, participate in any assessments or evaluations, and provide such acknowledgements, declarations or confirmations as may be required. The Employee shall also remain informed of and comply with any amendments or updates to the Company's policies and applicable compliance requirements. Failure to complete the prescribed training or comply with the applicable requirements shall constitute a breach of the Employee's obligations under this Agreement and may attract appropriate disciplinary action in accordance with the Company's policies and applicable law.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee will be provided with such equipment (including a laptop, if applicable) as is necessary for the performance of the Employee's duties. On resignation or termination, the Employee shall return all such equipment; the Company may recover the cost of any damage (other than fair wear and tear) from the Employee.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">In the event the Employee is sent for any training programme at the Company's expense, the Employee shall provide an undertaking to remain in employment with the Company for such period after such training as may be reasonably required by the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>REPRESENTATIONS AND WARRANTIES</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee represents and warrants to the Company that, as on the Effective Date:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">the Employee has the right to enter into this Agreement without violation of any third-party rights, and the engagement with the Company shall not result in a violation of any agreement or restrictive covenant that the Employee may have with any third party;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">the Employee is not a party to any arrangement or agreement which shall compromise the Employee's ability to carry out the duties for the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">all information furnished by the Employee to the Company in connection with the Employee's engagement is true, accurate and complete in all material respects.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">During the term of employment, the Employee shall:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">faithfully, efficiently and diligently perform such duties and exercise such powers as may from time to time be assigned to or vested in the Employee, and shall comply with all reasonable and lawful directions given by the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">use best endeavours to promote and extend the business, and to protect the interests and reputation, of the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">take all reasonable steps to maintain a satisfactory level of professional and practical knowledge relevant to the employment; and</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">ensure safekeeping of the Company's property and assets and observe all safety protocols as required by the Company from time to time.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>CONFLICT OF INTEREST AND MATERIAL BENEFIT</b></p>
		</div>


		<div class="ea-sheet" id="sheet-page-5">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 5 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall not, during the term of this Agreement, directly or indirectly, receive, accept, solicit or derive any financial or non-financial benefit, advantage, compensation, commission, fee, gift, favour, hospitality, referral fee, introduction fee or any other consideration of any nature whatsoever (collectively, "<b>Material Benefits</b>") from any person, entity, client, customer, counterparty, service provider or any other third party, in connection with or arising from the Employee's role, position or activities at the Company, unless expressly authorised in writing by the Board.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall promptly disclose to the Company any actual or potential conflict of interest that may arise in the course of the Employee's employment, including any external engagements, financial interests or personal relationships that may affect the Employee's ability to act in the best interests of the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>CONFIDENTIALITY</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee acknowledges that in the course of the Employee's employment, the Employee will have access to and be entrusted with Confidential Information of the Company and its customers, clients, counterparties and other stakeholders.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b> </b><b>"Confidential Information"</b> shall mean any and all information, whether in oral, written, electronic or any other form, that is not generally available to the public and that relates to the business, operations, finances, personnel, customers, clients, counterparties, suppliers, technology, products, services, strategies or affairs of the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">hold all Confidential Information in strict confidence and shall not, during or after the term of employment, disclose, communicate, publish, reproduce or distribute any Confidential Information to any person or entity, except as strictly necessary in the discharge of the Employee's duties and with the prior written consent of the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">use Confidential Information solely for the purposes of performing the Employee's duties under this Agreement;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">take all reasonable measures to prevent unauthorised access to or disclosure of Confidential Information; and</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">not make copies, notes or extracts of Confidential Information except as necessary for the performance of the Employee's duties, and shall return or destroy all such copies upon request or upon termination of employment.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The obligations under this Clause 10 shall survive the termination or expiry of this Agreement and shall continue for such maximum period as is enforceable under Applicable Law.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The restrictions in this Clause 10 shall not apply to information that: (a) is or becomes publicly available through no fault of the Employee; (b) was lawfully known to the Employee prior to receipt from the Company; or (c) is required to be disclosed by law, regulation or order of a court or Governmental Authority, provided that the Employee gives prompt written notice to the Company (to the extent lawful) and cooperates with any efforts to obtain a protective order.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>NON-COMPETE AND NON-SOLICITATION</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">During the term of this Agreement, the Employee shall not, directly or indirectly, engage in any other business, occupation, employment or activity, whether or not for compensation, without the prior written approval of the Board.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">For a period of twelve (12) months following the termination of this Agreement (howsoever caused), the Employee shall not, directly or indirectly, whether personally or through any agent, partner, associate or entity, solicit or canvass business from any person or entity that is or was, at any time during the twelve (12) months preceding termination, a client, customer or counterparty of the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">For a period of twenty-four (24) months following the termination of the Employee's employment, the Employee shall not:</p>
		</div>


		<div class="ea-sheet" id="sheet-page-6">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 6 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;">solicit, encourage or induce any employee, consultant, advisor or agent of the Company to terminate their relationship with the Company; or</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">solicit, induce or attempt to induce any client, customer, counterparty or prospective client of the Company to terminate or reduce their relationship with the Company or to divert any business or opportunity away from the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee acknowledges that the restrictions in this Clause 11 are reasonable and necessary to protect the legitimate business interests of the Company. If any such restriction is held to be unenforceable, the Parties agree that it shall be modified to the minimum extent necessary to make it enforceable.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>INTELLECTUAL PROPERTY</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">All intellectual property, including but not limited to inventions, discoveries, improvements, designs, models, research, analyses, reports, presentations, software, databases, processes, methodologies, trade secrets and all works of authorship (collectively, "<b>Work Product</b>"), conceived, created, developed or contributed to by the Employee, whether alone or jointly, during the course of the Employee's employment or using the Company's resources, time or Confidential Information, shall be the sole and exclusive property of the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee hereby irrevocably assigns to the Company all rights, title and interest (including all intellectual property rights) in and to all Work Product. The Employee shall execute all documents and take all actions reasonably necessary to perfect, register or enforce the Company's rights in such Work Product.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee waives all moral rights in the Work Product to the fullest extent permitted by Applicable Law.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The obligations under this Clause 12 shall survive the termination of this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>DATA PROTECTION</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall comply with all applicable data protection and privacy laws, including the Digital Personal Data Protection Act, 2023 and the rules made thereunder, and any other applicable data protection legislation.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">process personal data of employees, customers, clients and other data subjects only to the extent necessary for the performance of the Employee's duties and in accordance with the Company's data protection policies;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">not transfer, share, copy or transmit any personal data or customer/client data to any personal device, account or third party, without the prior written approval of the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">immediately report any actual or suspected data breach, loss or unauthorised access to the Company's designated data protection officer or such other officer as the Company may notify; and</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">upon termination of employment, delete or return all personal data and customer/client data in the Employee's possession, custody or control, and certify in writing that such deletion or return has been completed.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall mandatorily complete the Company's Information Security training within fifteen (15) days from the Date of Joining (DOJ). The Employee shall also acknowledge and confirm, in writing or through the Company's designated onboarding system, their understanding of and commitment to comply with the Company's Information Security, Data Protection and related policies as part of the onboarding process. Such acknowledgement shall be completed on the Date of Joining or within such timeframe as prescribed by the Company.</p>
		</div>


		<div class="ea-sheet" id="sheet-page-7">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 7 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>NON-DISPARAGEMENT</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">During the term of this Agreement and after the termination hereof, the Employee shall not engage in any activity or make any statements that are derogatory, misleading or harmful to the Company, including its employees, directors and officers, or that may disparage or reflect negatively on the Company or its goodwill in any manner whatsoever.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>TERMINATION</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Termination by the Company for Cause: </b>The Company shall have the right to terminate this Agreement with immediate effect, without notice or payment in lieu, for any one or more of the following reasons: (a) absence without permitted leave for a period of seven (7) or more consecutive days; (b) commission of any act or omission adversely affecting the goodwill, reputation or business of the Company; (c) dishonesty, fraud, breach of fiduciary duty, breach of confidentiality or breach of the conflict of interest or Material Benefit provisions of this Agreement; (d) conviction for any criminal offence involving material dishonesty or moral turpitude; (e) breach of any Applicable Law or any material term of this Agreement; (f) failure to disclose any Material Benefit, conflict of interest or misrepresentation of any material fact; (g) disobedience of reasonable and lawful instructions from the Board or authorised officers; or (h) attending work under the influence of alcohol, drugs or other intoxicating substances.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Termination by the Company without Cause</b>: Upon confirmation of the Employee's services, the Company may terminate this Agreement at any time, without assigning any reason, by providing fifteen (15) days' prior written notice or payment of fifteen (15) days' gross salary in lieu thereof, irrespective of the Employee's grade or designation.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Resignation by the Employee: </b>The Employee may resign by providing prior written notice to the Company in accordance with the grade-wise notice periods specified in Clause 15.4. This notice period shall apply during probation as well as after confirmation. The Company may, at its discretion, waive all or part of the applicable notice period or accept payment of gross salary in lieu of the remaining notice period, subject to the Company's approval.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Employee Resignation Notice Period</b></p>
<table class="ea-table" style="border-collapse:collapse; width:85%; margin:10pt auto; font-size:11pt;"><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">Employee Grade</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">During Probation</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">After Confirmation</td></tr><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">L1A – L2B</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">1 Month</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">1 Month</td></tr><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">L3A – L4B</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">1 Month</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">2 Months</td></tr><tr><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">L5A & Above</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">1 Month</td><td style="border:1px solid #000; padding:4pt 8pt; text-align:center;">3 Months</td></tr></table>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Death or Disability: </b>In the event of the Employee's death or permanent disability, this Agreement shall terminate automatically. The Employee (or the Employee's estate/nominee) shall be entitled to receive salary prorated to the date of termination. All other obligations of the Company shall terminate, subject to Applicable Law.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Consequences of Termination: </b>Upon termination for any reason, the Employee shall:</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">immediately hand over charge to such person as nominated by the Company;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">return all property, documents, records, devices, access credentials and materials belonging to the Company, in the Employee's possession, custody or control;</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">delete all Confidential Information and customer/client data from personal devices and accounts, and provide written certification of the same; and</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">cooperate with any transition, handover or audit process as may be required by the Company.</p>
		</div>


		<div class="ea-sheet" id="sheet-page-8">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 8 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee's full and final settlement is subject to completion of the Employee's duties under Clause 15.6 to the satisfaction of the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>INDEMNITY</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The Employee shall indemnify and hold harmless the Company, its directors, officers, employees and agents from and against any and all losses, liabilities, damages, claims, penalties, costs and expenses (including reasonable legal fees) arising out of or in connection with: (a) any breach of this Agreement by the Employee, including any breach of the confidentiality, conflict of interest, Material Benefit, fiduciary or regulatory compliance provisions; (b) any negligent, fraudulent or wilful act or omission of the Employee in the discharge of the Employee's duties; (c) any misrepresentation or non-disclosure by the Employee; (d) any violation of Applicable Law by the Employee; and (e) any claim by a third party arising from the Employee's conduct.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The indemnity obligations under this Clause 16 shall survive the termination of this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>FORCE MAJEURE</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;">Neither Party shall be liable for any failure or delay in performing its obligations under this Agreement to the extent that such failure or delay is caused by a Force Majeure Event.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>"Force Majeure Event"</b> means any event beyond the reasonable control of the affected Party, including acts of God, natural disasters, epidemics, pandemics, fire, flood, earthquake, war, terrorism, civil unrest, strikes, lockouts, government action, regulatory change, or any other event that could not have been reasonably foreseen or prevented.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;">The affected Party shall promptly notify the other Party of the Force Majeure Event and shall use all reasonable efforts to mitigate its impact. If the Force Majeure Event continues for a period exceeding ninety (90) days, the Company may terminate this Agreement by providing written notice to the Employee.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>GENERAL PROVISIONS</b></p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Governing Law: </b>This Agreement shall be governed by and construed in accordance with the laws of India.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Jurisdiction: </b>Subject to Clause 18.3, the courts at <b>Chennai</b> shall have exclusive jurisdiction to settle any dispute or claim arising out of or in connection with this Agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Dispute Resolution: </b>Any dispute or claim arising out of this Agreement shall first be attempted to be resolved through good-faith negotiation. If such negotiation fails to settle the dispute within thirty (30) days, the dispute shall be referred to and finally settled by binding arbitration by a sole arbitrator mutually appointed by the Parties, in accordance with the Arbitration and Conciliation Act, 1996. The seat and venue of arbitration shall be <b>Chennai</b>, and the proceedings shall be conducted in English.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Injunctive Relief: </b>Nothing in this Agreement shall limit either Party's right to seek injunctive or other equitable relief in any court of competent jurisdiction, including in aid of arbitration under Section 9 of the Arbitration and Conciliation Act, 1996.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Severability: </b>If any provision of this Agreement is held to be invalid, illegal or unenforceable, the remaining provisions shall continue in full force and effect. The Parties shall endeavour to replace such invalid provision with a valid provision that achieves the same economic effect and intent.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Entire Agreement: </b>This Agreement, together with the Offer Letter and any annexures and schedules, constitutes the entire agreement between the Parties with respect to the subject matter hereof and supersedes all prior negotiations, representations and agreements. In the event of any inconsistency between this Agreement and the Offer Letter, this Agreement shall prevail.</p>
		</div>


		<div class="ea-sheet" id="sheet-page-9">
			<div class="ea-sheet-header">
				${logo ? `<img src="${logo}"><br>` : ""}
				<div class="ea-cname">${company_name.toUpperCase()}</div>
				<div class="ea-caddr">
					${company_address ? company_address + " &nbsp;|&nbsp; " : ""}
					${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp;|&nbsp; " : ""}
					${email !== "____" ? "<b>Email:</b> " + email : ""}
				</div>
			</div>
			<div class="ea-page-badge">Page 9 of 9</div>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Amendment: </b>No amendment or modification of this Agreement shall be valid unless made in writing and signed by both Parties.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Waiver: </b>The failure of either Party to enforce any right under this Agreement shall not constitute a waiver of such right or any future right. A waiver of any breach shall not be deemed a waiver of any subsequent or similar breach.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Counterparts: </b>This Agreement may be executed in counterparts (including electronic counterparts), each of which shall be deemed an original and all of which together shall constitute one agreement.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Notices: </b>All notices under this Agreement shall be in writing and delivered by hand, registered post or email to the addresses set out above (or such other address as may be notified in writing).</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>Assignment: </b>The Employee shall not be entitled to assign or transfer this Agreement or any rights or obligations hereunder, without the prior written consent of the Company.</p>
<p style="text-align:justify; margin: 0 0 9pt 0;"><b>IN WITNESS WHEREOF</b>, the Parties have executed this Agreement on the date and at the place first above written.</p>

<table class="ea-sig-table" style="width:100%; margin-top:25pt; border-collapse:collapse; border:none; font-size:11pt;">
  <tr>
    <td style="width:50%; border:none; vertical-align:top; padding:8pt 10pt;">
      <b>For and on behalf of the COMPANY:</b><br><br>
      ${sig_img ? `<img src="${sig_img}" style="height:42px; object-fit:contain;"><br>` : `<div style="height:42px;"></div>`}
      _______________________________<br>
      <b>Authorised Signatory</b><br>
      ${sig_name !== "____" ? sig_name + "<br>" : ""}
      ${sig_desig !== "____" ? sig_desig : ""}
    </td>
    <td style="width:50%; border:none; vertical-align:top; padding:8pt 10pt;">
      <b>EMPLOYEE:</b><br><br>
      ${emp_sig_html}
      _______________________________<br>
      <b>${employee_name}</b><br>
      Date: ${execution_date}<br>
      Place: ${place}
    </td>
  </tr>
</table>

		</div>

	</div>
	`;
}
