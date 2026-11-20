frappe.ui.form.on("Employee Agreement", {
	refresh(frm) {
		render_agreement(frm);

		frm.add_custom_button(__("Download PDF"), function () {
			frappe.db.get_value("Print Format", "Employee Agreement - Print", "pdf_generator", (r) => {
				const pdf_generator = r.pdf_generator || "wkhtmltopdf";
				const url = frappe.urllib.get_full_url(
					"/api/method/frappe.utils.print_format.download_pdf"
					+ "?doctype=" + encodeURIComponent("Employee Agreement")
					+ "&name=" + encodeURIComponent(frm.doc.name)
					+ "&format=" + encodeURIComponent("Employee Agreement - Print")
					+ "&no_letterhead=0"
					+ "&pdf_generator=" + encodeURIComponent(pdf_generator)
				);
				window.open(url, "_blank");
			});
		}, __("")).addClass("btn-primary");
	},

	employee(frm) {
		if (frm.doc.employee) {
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
						if (!frm.doc.place && ctx.place) frm.set_value("place", ctx.place);
						if (!frm.doc.date) frm.set_value("date", frappe.datetime.get_today());
						if (!frm.doc.father_name && ctx.parent_spouse_name) frm.set_value("father_name", ctx.parent_spouse_name);
						if (!frm.doc.age && ctx.age) frm.set_value("age", parseInt(ctx.age, 10));
						if (!frm.doc.full_address && ctx.full_address) frm.set_value("full_address", ctx.full_address);
						if (!frm.doc.custom_employee_ctc && ctx.ctc_formatted && ctx.ctc_formatted !== "____") {
							frm.set_value("custom_employee_ctc", flt(ctx.ctc_formatted.replace(/,/g, "")));
						}
						if (!frm.doc.custom_roles__responsibilities && ctx.roles_responsibilities) {
							frm.set_value("custom_roles__responsibilities", ctx.roles_responsibilities);
						}
						render_agreement(frm);
					}
				},
			});
		} else {
			render_agreement(frm);
		}
	},

	company(frm) { render_agreement(frm); },
	designation(frm) { render_agreement(frm); },
	aadhaar_name(frm) { render_agreement(frm); },
	father_name(frm) { render_agreement(frm); },
	age(frm) { render_agreement(frm); },
	full_address(frm) { render_agreement(frm); },
	date_of_joining(frm) { render_agreement(frm); },
	place(frm) { render_agreement(frm); },
	date(frm) { render_agreement(frm); },
	custom_employee_ctc(frm) { render_agreement(frm); },
	custom_roles__responsibilities(frm) { render_agreement(frm); },
});

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
	const relation = esc(ctx.relation || "S/o, D/o or W/o");
	const age = esc(d.age || ctx.age);
	const full_address = esc(d.full_address || ctx.full_address);
	const designation = esc(d.designation);
	const doj = fmt_date(d.date_of_joining);
	const execution_date = d.date ? fmt_date(d.date) : (ctx.execution_date || "____");
	const place = esc(d.place || ctx.place || "Chennai");
	const principal_place = esc(ctx.principal_place || (place + ", Tamil Nadu, India"));
	const reporting_manager = esc(ctx.reporting_manager || "the Board");

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

	const roles = d.custom_roles__responsibilities || ctx.roles_responsibilities || `
		<p class="ea-sub">• Identify client needs, offer tailored solutions, and ensure customer satisfaction and retention.<br>
		• Meet business performance metrics through effective client engagement.<br>
		• Maintain operational records, adhere to regulatory standards, and collaborate with internal teams.</p>
	`;

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
		.ea-preview { font-family: 'Times New Roman', Tahoma, Arial, sans-serif; font-size: 13px; line-height: 1.6; color: #111;
			border: 1px solid #d1d8dd; border-radius: 6px; padding: 25px 30px; max-height: 560px; overflow-y: auto; background: #fff; }
		.ea-preview p { margin: 0 0 12px 0; text-align: justify; }
		.ea-preview .ea-hdr { text-align: center; margin-bottom: 16px; border-bottom: 2px solid #333; padding-bottom: 12px; }
		.ea-preview .ea-hdr img { height: 50px; margin-bottom: 6px; }
		.ea-preview .ea-hdr .cname { font-weight: bold; font-size: 15px; letter-spacing: 0.5px; }
		.ea-preview .ea-hdr .caddr { font-size: 11px; color: #444; margin-top: 4px; line-height: 1.4; }
		.ea-preview .ea-title { text-align: center; font-weight: bold; font-size: 16px; text-decoration: underline; margin: 15px 0 20px; }
		.ea-preview table.ea-table { border-collapse: collapse; width: 80%; margin: 12px auto; font-size: 12px; }
		.ea-preview table.ea-table th, .ea-preview table.ea-table td { border: 1px solid #333; padding: 6px 12px; text-align: center; }
		.ea-preview table.ea-table th { background: #f2f2f2; font-weight: bold; }
		.ea-preview .ea-sec { font-weight: bold; margin-top: 18px; margin-bottom: 6px; text-transform: uppercase; font-size: 13.5px; }
		.ea-preview .ea-sub { margin-left: 20px; margin-bottom: 6px; }
		.ea-preview .ea-sub2 { margin-left: 40px; margin-bottom: 4px; }
		.ea-preview .ea-sig { width: 100%; margin-top: 35px; border-collapse: collapse; }
		.ea-preview .ea-sig td { vertical-align: top; width: 50%; padding: 10px; border: none; }
	</style>

	<div class="ea-preview">
		<div class="ea-hdr">
			${logo ? `<img src="${logo}"><br>` : ""}
			<div class="cname">${company_name.toUpperCase()}</div>
			<div class="caddr">
				${company_address ? company_address + "<br>" : ""}
				${cin !== "____" ? "<b>CIN:</b> " + cin + " &nbsp; " : ""}
				${sebi !== "____" ? "<b>SEBI REG:</b> " + sebi + " &nbsp; " : ""}
				${amfi !== "____" ? "<b>AMFI NO:</b> " + amfi + "<br>" : ""}
				${company_pan !== "____" ? "<b>PAN:</b> " + company_pan + " &nbsp; " : ""}
				${email !== "____" ? "<b>EMAIL:</b> " + email : ""}
			</div>
		</div>

		<div class="ea-title">EMPLOYMENT AGREEMENT</div>

		<p>This Employment Agreement (the <b>&ldquo;Agreement&rdquo;</b>) is made and entered into at <b>${place}</b> on <b>${execution_date}</b> (the <b>&ldquo;Execution Date&rdquo;</b>),</p>

		<p><b>BETWEEN:</b></p>

		<p><b>${company_name}</b>, a company incorporated under the Companies Act, 2013, having its registered office at ${company_address} and having PAN <b>${company_pan}</b> (hereinafter referred to as the <b>&ldquo;Company&rdquo;</b> or <b>&ldquo;Employer&rdquo;</b>, which expression shall, unless the context otherwise requires, include its successors and permitted assigns);</p>

		<p><b>AND</b></p>

		<p><b>${employee_name}</b>, ${relation} <b>${parent_spouse_name}</b>, aged about <b>${age}</b> years, residing at <b>${full_address}</b> (hereinafter referred to as the <b>&ldquo;Employee&rdquo;</b>).</p>

		<p>The Employer and the Employee shall be collectively referred to as the <b>&ldquo;Parties&rdquo;</b> and individually as a <b>&ldquo;Party&rdquo;</b>.</p>

		<p>WHEREAS the Company is engaged in the business of ${business_description};</p>

		<p>WHEREAS the Employee possesses the requisite qualifications, skills, experience and expertise for the said designation, and has represented the same to the Company;</p>

		<p>WHEREAS the Company has employed the Employee as <b>&ldquo;${designation}&rdquo;</b> from <b>${doj}</b> (Effective Date), and the Employee has agreed to accept such employment, on the terms and conditions set forth herein;</p>

		<p>WHEREAS, in supersession of any and all previous terms of engagement of the Employee, whether with the Company or any other entity, the Parties wish to record the terms of the Employee's employment under this Agreement.</p>

		<p><b>NOW THEREFORE, IN CONSIDERATION OF THE MUTUAL PROMISES, COVENANTS AND AGREEMENTS SET FORTH HEREIN, AND FOR OTHER GOOD AND VALUABLE CONSIDERATION, THE RECEIPT AND SUFFICIENCY OF WHICH ARE HEREBY ACKNOWLEDGED, THE PARTIES, INTENDING TO BE LEGALLY BOUND, AGREE AS FOLLOWS:</b></p>

		<div class="ea-sec">1. DEFINITIONS AND INTERPRETATION</div>
		<p>In this Agreement, unless the context otherwise requires:</p>
		<p class="ea-sub"><b>&ldquo;Applicable Law&rdquo;</b> means any statute, law, regulation, ordinance, rule, judgment, notification, order, decree, bye-law, permit, licence, direction or guideline of any Governmental Authority applicable to the Parties;</p>
		<p class="ea-sub"><b>&ldquo;Board&rdquo;</b> means the board of directors of the Company or any duly authorised committee thereof;</p>
		<p class="ea-sub"><b>&ldquo;Confidential Information&rdquo;</b> has the meaning ascribed to it in Clause 10;</p>
		<p class="ea-sub"><b>&ldquo;Governmental Authority&rdquo;</b> means any government or political subdivision thereof, any court, tribunal, regulatory or self-regulatory authority, or any other governmental or statutory body having jurisdiction over the Parties;</p>
		<p class="ea-sub"><b>&ldquo;Work Product&rdquo;</b> has the meaning ascribed to it in Clause 12.</p>
		<p>Headings are for convenience only and shall not affect the interpretation of this Agreement. References to the singular include the plural and vice versa; references to any gender include all genders; and references to a Clause are to a Clause of this Agreement.</p>

		<div class="ea-sec">2. APPOINTMENT AND DESIGNATION</div>
		<p>2.1 The Company hereby appoints the Employee as <b>&ldquo;${designation}&rdquo;</b>, and the Employee hereby accepts such appointment, subject to the terms and conditions of this Agreement.</p>
		<p>2.2 The Employee shall report to <b>${reporting_manager}</b> or such other person(s) as may be designated by the Board from time to time.</p>

		<div class="ea-sec">3. PLACE OF EMPLOYMENT</div>
		<p>3.1 The Employee's principal place of employment shall be <b>${principal_place}</b>.</p>
		<p>3.2 The Employee may be required to travel to other locations within India or abroad, and may be required to relocate, as may be necessary in the interests of the Company's business, at the Company's discretion.</p>

		<div class="ea-sec">4. TERM AND PROBATION</div>
		<p>4.1 The term of employment shall commence on the Effective Date and shall continue unless terminated in accordance with the provisions of this Agreement.</p>
		<p>4.2 The Employee shall be subject to a probation period based on the applicable employee level, as specified in the Probation Period Schedule below. During the probation period, the Employee may resign by providing written notice in accordance with the grade-wise notice period specified under Clause 15.4 of this Agreement. The Company reserves the right to terminate the Employee's employment during the probation period, without assigning any reason, without providing prior notice or payment in lieu of notice.</p>

		<table class="ea-table">
			<tr><th>Employee Level</th><th>Probation Period</th></tr>
			<tr><td>L1A – L2B</td><td>6 Months</td></tr>
			<tr><td>L3A – L4B</td><td>3 Months</td></tr>
			<tr><td>L5A & Above</td><td>2 Months</td></tr>
		</table>

		<p>4.3 Upon satisfactory completion of the applicable probation period, the Employee's services shall be confirmed in writing by the Company. The Company reserves the right to extend the probation period by up to three (3) months, based on the Employee's performance and suitability, subject to applicable law.</p>
		<p>4.4 During the Probation Period, the Employee shall not be entitled to any Performance-Linked Incentive under this Agreement.</p>
		<p>4.5 In view of the training costs, proprietary knowledge and client and business relationships to which the Employee will be exposed, the Employee agrees to remain employed with the Company for a minimum period of 1 year(s) from the date of confirmation of services (the <b>&ldquo;Lock-in Period&rdquo;</b>).</p>

		<div class="ea-sec">5. DUTIES AND RESPONSIBILITIES</div>
		<p>5.1 The Employee shall devote the Employee's full time, attention, skill and best efforts exclusively to the business and affairs of the Company. The Employee shall faithfully, efficiently, competently and diligently perform all duties and exercise such powers as may from time to time be assigned to or vested in the Employee.</p>
		<p>5.2 Without limiting the generality of the foregoing, the Employee's responsibilities shall include, but not be limited to:</p>
		<div style="margin-left:15px; margin-bottom:10px;">${roles}</div>
		<p class="ea-sub">and such other duties as may be assigned by the Company from time to time.</p>

		<div class="ea-sec">6. COMPENSATION AND BENEFITS</div>
		<p>6.1 <b>Fixed Compensation:</b> In consideration of the Employee's services, the Company shall pay the Employee an annual fixed compensation of <b>INR ${ctc_display}</b>, inclusive of all statutory contributions and subject to applicable tax deductions, payable in monthly instalments in accordance with the Company's payroll cycle.</p>
		<p>6.2 <b>Performance-Linked Incentive:</b> In addition to the Fixed Compensation, the Employee may be eligible for a performance-linked incentive (the <b>&ldquo;Performance Incentive&rdquo;</b>), subject to the following:</p>
		<p class="ea-sub">(a) <b>Quantum:</b> as determined by the Company, based on such performance metrics as may be notified by the Company from time to time;</p>
		<p class="ea-sub">(b) <b>Performance Period:</b> each financial year (1 April to 31 March), or such other period as may be determined by the Company;</p>
		<p class="ea-sub">(c) <b>Conditions:</b> the Performance Incentive shall be subject to the following conditions:</p>
		<p class="ea-sub2">(i) the Employee must be in active, confirmed employment with the Company on the date of disbursement, and must not have tendered resignation or been served a notice of termination;</p>
		<p class="ea-sub2">(ii) the Employee must not be in breach of any material obligation under this Agreement;</p>
		<p class="ea-sub2">(iii) the Performance Incentive shall be subject to applicable tax deductions and statutory contributions;</p>
		<p class="ea-sub2">(iv) the Company reserves the right to claw back all or part of the Performance Incentive in the event of any material misrepresentation, fraud or wilful breach by the Employee, for a period of twenty-four (24) months from the date of each disbursement; and</p>
		<p class="ea-sub2">(v) the Performance Incentive shall be pro-rated for any performance period during which the Employee was not employed for the entire period.</p>
		<p class="ea-sub">(d) <b>No Entitlement:</b> for the avoidance of doubt, the Performance Incentive is discretionary and contingent upon the conditions set out above. No right to the Performance Incentive shall accrue unless and until all conditions are satisfied and the payment is actually made.</p>
		<p>6.3 The Employee shall be entitled to such other benefits as may be available under the Company's policies and Applicable Law, as in effect from time to time.</p>
		<p>6.4 The Employee's compensation is strictly confidential. The Employee shall not disclose, discuss or share details of the Employee's compensation with any person, whether within or outside the organisation, other than the Company's authorised personnel or the Employee's immediate family and professional advisers bound by confidentiality.</p>

		<div class="ea-sec">7. COMPANY POLICIES</div>
		<p>7.1 The Employee's employment is subject to the Company's policies as may be issued and amended by the Board or management from time to time.</p>
		<p>7.2 The Employee shall be entitled to leaves in accordance with the Company's leave policy and shall adhere to the process for availing such leaves.</p>
		<p>7.3 The Company shall reimburse all reasonable travel, accommodation and other expenses incurred by the Employee on the Company's business, in accordance with the Company's policies.</p>
		<p>7.4 The Employee shall mandatorily undergo, complete and comply with all training programmes, compliance courses and assessments prescribed by the Company from time to time, including but not limited to Prevention of Sexual Harassment (POSH), Code of Conduct, Anti-Bribery and Anti-Corruption, Information Security, Data Protection and other statutory, regulatory or internal compliance requirements applicable to the Employee.</p>
		<p>7.5 The Employee will be provided with such equipment (including a laptop, if applicable) as is necessary for the performance of the Employee's duties. On resignation or termination, the Employee shall return all such equipment.</p>
		<p>7.6 In the event the Employee is sent for any training programme at the Company's expense, the Employee shall provide an undertaking to remain in employment with the Company for such period after such training as may be reasonably required by the Company.</p>

		<div class="ea-sec">8. REPRESENTATIONS AND WARRANTIES</div>
		<p>The Employee represents and warrants to the Company that all information furnished by the Employee to the Company is true, accurate and complete in all material respects, and the engagement shall not violate any agreement or restrictive covenant with any third party. The Employee shall faithfully and diligently perform all assigned duties.</p>

		<div class="ea-sec">9. CONFLICT OF INTEREST AND MATERIAL BENEFIT</div>
		<p>The Employee shall not directly or indirectly receive, accept, solicit or derive any financial or non-financial benefit, commission, fee, gift or consideration from any third party in connection with the Employee's role at the Company, unless expressly authorised in writing by the Board. The Employee shall promptly disclose any actual or potential conflict of interest.</p>

		<div class="ea-sec">10. CONFIDENTIALITY</div>
		<p>The Employee acknowledges that during employment, the Employee will have access to Confidential Information. The Employee shall hold all Confidential Information in strict confidence and shall not disclose, communicate, reproduce or distribute any Confidential Information during or after employment, except as strictly necessary in the discharge of duties with prior written consent. The obligations shall survive the termination of this Agreement.</p>

		<div class="ea-sec">11. NON-COMPETE AND NON-SOLICITATION</div>
		<p>11.1 During employment, the Employee shall not directly or indirectly engage in any other business or occupation without prior written approval of the Board.</p>
		<p>11.2 For twelve (12) months following termination, the Employee shall not solicit or canvass business from any client, customer or counterparty of the Company.</p>
		<p>11.3 For twenty-four (24) months following termination, the Employee shall not solicit, encourage or induce any employee or consultant to terminate their relationship with the Company, nor induce any client or lead to terminate or divert business away from the Company.</p>

		<div class="ea-sec">12. INTELLECTUAL PROPERTY</div>
		<p>All Work Product conceived, created, developed or contributed to by the Employee during the course of employment shall be the sole and exclusive property of the Company. The Employee irrevocably assigns all rights, title and interest in Work Product to the Company.</p>

		<div class="ea-sec">13. DATA PROTECTION</div>
		<p>The Employee shall comply with all applicable data protection and privacy laws, including the Digital Personal Data Protection Act, 2023. The Employee shall complete Information Security training within fifteen (15) days from the Date of Joining.</p>

		<div class="ea-sec">14. NON-DISPARAGEMENT</div>
		<p>During and after employment, the Employee shall not make any statements that are derogatory, misleading or harmful to the Company, its directors, officers or employees.</p>

		<div class="ea-sec">15. TERMINATION</div>
		<p>15.1 <b>Termination for Cause:</b> The Company may terminate with immediate effect, without notice or payment in lieu, for misconduct, fraud, breach of policies, unauthorized absence for 7+ consecutive days, or breach of confidentiality/conflict of interest.</p>
		<p>15.2 <b>Termination without Cause:</b> Upon confirmation, the Company may terminate by providing fifteen (15) days' prior written notice or payment of 15 days' gross salary in lieu thereof.</p>
		<p>15.3 <b>Resignation:</b> The Employee may resign by providing prior written notice in accordance with the schedule below:</p>

		<table class="ea-table">
			<tr><th>Employee Grade</th><th>During Probation</th><th>After Confirmation</th></tr>
			<tr><td>L1A – L2B</td><td>1 Month</td><td>1 Month</td></tr>
			<tr><td>L3A – L4B</td><td>1 Month</td><td>2 Months</td></tr>
			<tr><td>L5A & Above</td><td>1 Month</td><td>3 Months</td></tr>
		</table>

		<p>15.4 <b>Death or Disability:</b> Employment terminates automatically with salary prorated to date of termination.</p>
		<p>15.5 <b>Consequences:</b> Handover charge, return all property, devices and documents, and delete all confidential data.</p>

		<div class="ea-sec">16. INDEMNITY</div>
		<p>The Employee shall indemnify and hold harmless the Company, directors, officers and employees from any losses, liabilities or damages arising from breach of agreement, fraud, gross negligence or violation of Applicable Law.</p>

		<div class="ea-sec">17. FORCE MAJEURE</div>
		<p>Neither Party shall be liable for delay or failure caused by events beyond reasonable control.</p>

		<div class="ea-sec">18. GENERAL PROVISIONS</div>
		<p>18.1 <b>Governing Law:</b> Governed by and construed in accordance with the laws of India.</p>
		<p>18.2 <b>Jurisdiction:</b> Courts at Chennai shall have exclusive jurisdiction.</p>
		<p>18.3 <b>Dispute Resolution:</b> Good-faith negotiation, followed by binding arbitration under the Arbitration and Conciliation Act, 1996 with seat and venue at Chennai.</p>
		<p>18.4 <b>Entire Agreement:</b> Supersedes all prior agreements. Amendments must be in writing and signed by both Parties.</p>

		<p style="margin-top:25px;"><b>IN WITNESS WHEREOF, the Parties have executed this Agreement on the date and at the place first above written.</b></p>

		<table class="ea-sig">
			<tr>
				<td>
					<b>For and on behalf of the COMPANY:</b><br><br>
					${sig_img ? `<img src="${sig_img}" style="height:42px; object-fit:contain;"><br>` : `<div style="height:42px;"></div>`}
					_______________________________<br>
					<b>Authorised Signatory</b><br>
					${sig_name !== "____" ? sig_name + "<br>" : ""}
					${sig_desig !== "____" ? sig_desig : ""}
				</td>
				<td>
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
	`;
}
