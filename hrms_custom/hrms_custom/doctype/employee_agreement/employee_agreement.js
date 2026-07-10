frappe.ui.form.on("Employee Agreement", {
	refresh(frm) {
		render_agreement(frm);
	},
	company(frm) {
		render_agreement(frm);
	},
	designation(frm) {
		render_agreement(frm);
	},
	aadhaar_name(frm) {
		render_agreement(frm);
	},
	father_name(frm) {
		render_agreement(frm);
	},
	age(frm) {
		render_agreement(frm);
	},
	full_address(frm) {
		render_agreement(frm);
	},
	date_of_joining(frm) {
		render_agreement(frm);
	},
	ctc_amount(frm) {
		render_agreement(frm);
	},
	ctc_in_words(frm) {
		render_agreement(frm);
	},
	place(frm) {
		render_agreement(frm);
	},
});

function render_agreement(frm) {
	if (!frm.fields_dict.agreement_html) return;

	if (!frm.doc.company) {
		frm.fields_dict.agreement_html.$wrapper.html(
			'<div style="padding:12px; color:#888;">Select a Company to preview the agreement.</div>'
		);
		return;
	}

	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Offer Letter Print Settings",
			filters: { company: frm.doc.company },
			fieldname: [
				"registered_address",
				"compliance_email",
				"cin_number",
				"sebi_registration_no",
				"amfi_registration_no",
				"company_logo",
			],
		},
		callback: function (r) {
			const settings = (r && r.message) || {};
			frappe.db.get_value("Company", frm.doc.company, "company_name").then((res) => {
				const company_name = (res.message && res.message.company_name) || frm.doc.company;
				const html = build_agreement_html(frm, company_name, settings);
				frm.fields_dict.agreement_html.$wrapper.html(html);
			});
		},
	});
}

function esc(v) {
	return v === undefined || v === null || v === "" ? "____" : frappe.utils.escape_html(String(v));
}

function fmt_date(d) {
	return d ? frappe.datetime.str_to_user(d) : "____";
}

function build_agreement_html(frm, company_name, settings) {
	const d = frm.doc;
	const designation = esc(d.designation);
	const aadhaar_name = esc(d.aadhaar_name);
	const father_name = esc(d.father_name);
	const age = esc(d.age);
	const full_address = esc(d.full_address);
	const place = esc(d.place || "Chennai");
	const doj = fmt_date(d.date_of_joining);
	const ctc = d.ctc_amount ? format_currency(d.ctc_amount, frappe.defaults.get_default("currency")) : "____";
	const ctc_words = esc(d.ctc_in_words);
	const address = settings.registered_address || "";
	const email = settings.compliance_email || "";
	const cin = settings.cin_number || "";
	const sebi = settings.sebi_registration_no || "";
	const amfi = settings.amfi_registration_no || "";
	const logo = settings.company_logo || "";

	return `
	<style>
		.ea-preview { font-family: Tahoma, Arial, sans-serif; font-size: 12.5px; line-height: 1.5; color: #222;
			border: 1px solid #d1d8dd; border-radius: 6px; padding: 20px 24px; max-height: 520px; overflow-y: auto; background: #fff; }
		.ea-preview p { margin: 0 0 10px 0; text-align: justify; }
		.ea-preview .ea-hdr { text-align: center; margin-bottom: 14px; }
		.ea-preview .ea-hdr img { height: 45px; margin-bottom: 4px; }
		.ea-preview .ea-hdr .cname { font-weight: bold; font-size: 13px; }
		.ea-preview .ea-hdr .caddr { font-size: 10px; color: #555; margin-top: 4px; }
		.ea-preview .ea-title { text-align: center; font-weight: bold; font-size: 14px; text-decoration: underline; margin: 10px 0 16px; }
		.ea-preview table.desig { border-collapse: collapse; width: 60%; margin: 10px auto; font-size: 12px; }
		.ea-preview table.desig td { border: 1px solid #999; padding: 4px 8px; text-align: center; }
		.ea-preview .sub { margin-left: 18px; }
	</style>
	<div class="ea-preview">
		<div class="ea-hdr">
			${logo ? `<img src="${logo}">` : ""}
			<div class="cname">${frappe.utils.escape_html(company_name).toUpperCase()}</div>
			<div class="caddr">
				${address ? frappe.utils.escape_html(address) + "<br>" : ""}
				${sebi ? "SEBI REGISTRATION NO : " + frappe.utils.escape_html(sebi) + " &nbsp; " : ""}
				${cin ? "CIN: " + frappe.utils.escape_html(cin) : ""}<br>
				${email ? frappe.utils.escape_html(email).toUpperCase() + " &nbsp; " : ""}
				${amfi ? "AMFI NO : " + frappe.utils.escape_html(amfi) : ""}
			</div>
		</div>

		<div class="ea-title">EMPLOYMENT AGREEMENT</div>

		<p>This Employment Agreement is made and entered into upon the parties below mentioned at ${place} on this the ${doj}, BETWEEN, M/s ${frappe.utils.escape_html(company_name)}${address ? ", " + frappe.utils.escape_html(address) : ""}.</p>

		<p><b>AND</b> ${aadhaar_name}, S/O ${father_name}, aged about ${age} years, residing at ${full_address}.</p>

		<p>The Employer and the Employee shall be collectively referred to as Parties and individually as Party.</p>

		<p>WHEREAS, the Employer is engaged in the business of financial planning.</p>

		<p>WHEREAS, the Employee has agreed to terminate his/her previous terms of engagement either with any other employer or with the Employer, if any.</p>

		<p>WHEREAS, in supersession of the previous terms of engagement of the Employee, the Employer wishes to employ the Employee on the terms and conditions agreed upon in this Agreement.</p>

		<p>WHEREAS, the Employer has offered and the Employee has accepted the position with the Employer as a &ldquo;${designation}&rdquo;, On the terms and conditions as agreed upon in this Agreement.</p>

		<p><b>NOW THEREFORE IN CONSIDERATION OF THE PROMISES AND MUTUAL COVENANTS SET FORTH HEREIN, THE PARTIES HERETO, INTENDING TO BE LEGALLY BOUND, HEREBY COVANENT AND AGREE AS FOLLOWS:</b></p>

		<p>1. The Employer appoint the Employee as the &ldquo;${designation}&rdquo;, Employer and the employee agrees to be employed with the Employer a &ldquo;${designation}&rdquo;, the Effective Date and thereby be bound by the terms and conditions agreed upon under this Agreement.</p>

		<p>2. The Employee's principal place of employment shall be in Chennai, Tamil Nadu, India. The Employee may be required to relocate to other locations within India or abroad and during the term of the Employee's employment under this Agreement the Employee shall undertake to such travel from time to time as may be necessary in the interests of the Employer's business.</p>

		<p>3. The term of the Employee's employment with the Employer shall commence on the Effective Date and shall be valid from the date thereof. In view of the training costs incurred by the employer in training the employee and subject to Clause 14 (Termination) of this Agreement, the Employee agrees to remain employed with the Employer for a period of at least 2 years from the Effective Date ${doj}, (Hereinafter 'Term'). Otherwise, in addition to the damages mentioned in other clauses of this agreement, the employee shall pay a sum equal towards the training costs to the employer.</p>

		<p>4. The Employee shall provide the Employer with his/her Bank account or other financial details along with other relevant details such as Parents, Spouse, and Siblings etc., as and when requested by the Employer.</p>

		<p>5. The Parties acknowledge that the employment of the Employee shall vary between the following levels established by the Employer</p>

		<table class="desig">
			<tr><td><b>LEVELS</b></td><td><b>DESIGNATIONS</b></td></tr>
			<tr><td>L1A</td><td>Junior Associate</td></tr>
			<tr><td>L1B</td><td>Senior Associate</td></tr>
			<tr><td>L2A</td><td>Junior Executive</td></tr>
			<tr><td>L2B</td><td>Senior Executive</td></tr>
			<tr><td>L3A</td><td>Team Leader</td></tr>
			<tr><td>L3B</td><td>Assistant Manager</td></tr>
			<tr><td>L4A</td><td>Manager</td></tr>
			<tr><td>L4B</td><td>Senior Manager</td></tr>
			<tr><td>L5A</td><td>Director</td></tr>
		</table>

		<p>6. The employee shall report to the assigned manager upon commencement of employment and will be under the overall supervision and control of the Employer's Board of Directors.</p>

		<p>7. The Employee agrees to comply with the various policies, rules and regulations of the Employer as maybe updated from time to time unilaterally by the Employer.</p>

		<p>8. The Employee shall work full time for the organization, devoting his/her time and attention and skill to the duties of his/her office and shall faithfully, efficiently, competently and diligently perform duties and exercise such powers as may from time to time be assigned to or vested in him and shall comply with all lawful directions given to him by or under the authority of the Board of Directors of the Employer and use his/her best endeavors to promote and extend the business of the Employer.</p>

		<p>9. The Employee shall act diligently and to the best of his/her ability discharge of his/her duties and subject to any restricts or limitations imposed by the concerned officer or policy of the Employer in this regard. The Employee's responsibilities will include but not limited to the following;</p>
		<p class="sub">a. Identify client needs, offer tailored solutions, and ensure customer satisfaction and retention.<br>
		b. Meet sales targets through upselling, cross-selling, and effective client engagement.<br>
		c. Maintain CRM records, resolve issues, and collaborate with internal teams.</p>

		<p>10. During the term of this Agreement, the Employee shall not directly or indirectly engage himself in any other business, occupation or employment whatsoever, without the approval of the Employer.</p>

		<p>11. In consideration of the Employee's services to the Employer, the Employer shall pay to the Employee during the term of this Agreement, a CTC of ${ctc}${d.ctc_in_words ? " (" + ctc_words + ")" : ""} Per Annum, subject to deduction of tax at the source.</p>

		<p>12. Save and except as otherwise provided in this Agreement or as may be decided by the Board of Directors of the Employer from time to time, the Employee shall be entitled to all such benefits that may be available to him as per law and as per the polices of the Employer for its employees as in effect from time to time.</p>

		<p>13. The Employer shall have the right to terminate this Agreement at any time with immediate effect by providing notice for any one or more of the following reasons:</p>
		<p class="sub">
		a. If the Employee is absent without permitted leave for a period of 7 days consecutively.<br>
		b. If the Employee is found guilty of any act or omission adversely affecting the goodwill, reputation, credit, operations or business of the Employer or commission of any crime involving material dishonesty or moral turpitude, in the opinion of the Employer.<br>
		c. Employee is found guilty of any dishonesty, fraud, breach of statutory duties, breach of confidentiality obligations, pilferage and theft, attending work under the influence of alcohol, drugs or other intoxicating substances, breach of the Employer's rules and policies, disobedience of reasonable orders from the superiors or the Board of Directors of the Employer, causing actual or threating to cause physical harm or damage to property or any other act of misconduct, in the opinion of the Employer.
		</p>

		<p>14. The Employee may voluntarily resign from his/her employment at any time by giving prior written notice to the Employer or payment of his/her gross salary in lieu thereof without assigning reason, subject to the following conditions in this clause. However, the Employer may at its sole discretion waive all or part of the notice. The following notice period shall be applicable to the Employee as per their levels:</p>
		<p class="sub">
		a. 30-day notice period for L1A and L1B;<br>
		b. 60-day notice period for L2A to L3B;<br>
		c. and 90-day notice period for L4A to L5A
		</p>
		<p>The notice period might change according to the company policy, which will be communicated to the employee upon implementation of the same.</p>

		<p>15. In the event of termination of this Agreement due to the Employee's death or disability, the Employee shall be entitled to the basic salary prorated to the date of termination. All other obligations of the Employer towards the Employee pursuant to this Agreement shall automatically terminate and extinguish.</p>

		<p>16. In the event of termination of this Agreement pursuant to clause 11, the employee will be responsible for paying either three months' gross salary or an amount equivalent to the damages incurred, whichever is greater.</p>

		<p>17. The age of retirement of the Employee from the services of the Employer shall be 58 years. The Employer at its sole discretion may extend the age of retirement subject to the approval of the Board of Directors of the Employer. If the Employee shall at any time be prevented from ill-health or accident or any disability from performing his/her duties hereunder, he shall if inform the Employer and supply it with such details that the Employee is unable by reason of health or accident or disability for a period of 30 days or more in any period of 12 consecutive calendar months, to perform his/her duties hereunder, the Employer may or may not forthwith terminate this agreement.</p>

		<p>18. Notwithstanding anything to the contrary herein contained the Employer shall be entitled to terminate this Agreement at any time by giving the Employee 1 months' notice in writing or payment of his/her gross salary in lieu thereof without assigning reason.</p>

		<p>19. Upon termination of this Agreement for any reason, the Employee shall hand over charge to such person nominated for that purpose by the Organisation and shall deliver to such person such papers, documents and other property of the Employer as may be in his/her possession, custody, control or power, including but not limited to any phones, computers, vehicles, etc provided by the Employer.</p>

		<p>20. The Employee shall not during the continuation of this Agreement or thereafter, divulge or make use of any trade secret or confidential information concerning the business of the Employee or any of its dealings, transactions and affairs or any information concerning any of its suppliers, agents, distributors or customers which the Employee possesses or comes into possession while in the employment of the Employer or which he may make or discover while in the service of the Employer. All data, documents, plans, drawings, photographs, reports, statements, correspondence etc, and technical information, know-how and instructions as well as business details or commercial policies that pass to the Employee or which come to the Employee's knowledge shall be treated as confidential information and the Employee shall be bound to keep secret all such confidential information and shall not disclose, communicate, reproduce, or distribute the same or copies thereof to anyone except in the course of the rightful discharge of his/her duties as the Employee of the Employer.</p>

		<p>21. The Employee shall not at any time hereafter in any way make known or divulge to any person, firm or body corporate any of the methods, systems or other information of any kind in relation to the affairs of the Employer whether such information is or was acquired by him before the execution of this Agreement or in the course of his/her employment with the Employer or otherwise.</p>

		<p>22. The Employee acknowledges that is in the course of his/her employment with the Employer likely from time to time obtain knowledge of trade secrets, Intellectual Properties and other confidential information of the Employer and its affiliates and to have dealings with its existing and future or potential customers and suppliers.
		the Employee acknowledges the importance and commercial significance of the covenants under this clause and admits and acknowledges that he has various other technologies and information which if deployed by him elsewhere or for a third party during the course of his/her employment or after he ceases to be an employee or ceases to be associated with the Employer would result in him competing against the Employer. Hence the Employee warrants and undertakes to the Employer that he shall not for the duration of employment with the organisation and for a period of 12 months after the date on which he ceases to be employed by the Employer, either personally or through an agent, or through a partnership or as a shareholder, joint venture, collaborator, consultant, advisor, principal contractor or sub-contractor, director, trustee, committee member or office bearer or in any other manner whatsoever, whether for profit or otherwise;</p>
		<p class="sub">
		a. Be concerned in any business directly or indirectly manufacturing, operating, selling or distributing products or services which compete with any business carried then on by the Employer.<br>
		b. Except on behalf of the Employer, canvass or solicit business or custom for products of a similar type to those being manufactured or dealt in or for service similar to those being provided by the Employer from or to any person who is an existing, future or potential customer of the Employer.
		</p>

		<p>23. For 24 months following the termination of the Employee's employment the Employee shall not</p>
		<p class="sub">
		a. solicit, encourage, or induce any employee, marketing agent or consultant of the Employer to terminate his/her employment, agency, or consultancy with the Employer or any prospective employee with whom the Employer has had discussions or negotiations within six months prior to the Employee's termination of employment, not to establish a relationship with the Employer.<br>
		b. Induce or attempt to induce any current customer to terminate its relationship with the Employer or induce any potential customer with whom the Employer has had discussions or negotiations within the six months prior to the Employee's termination of employment, not to establish a relationship with the Employer.<br>
		c. Induce or attempt to induce any current lead or induce any potential lead with whom the Employer has had or is willing to have discussions or negotiations, not to establish a relationship with the Employer.
		</p>

		<p>24. The Employee agrees that any material breach or threatened breach of these clauses may not be sufficiently remedied solely by monetary damages, and that in addition to any other remedies, the Employee is entitled to institute criminal action against the Employee apart from also being entitled to seek injunctive relief against the Employee in a forum of competent jurisdiction for any such breach.</p>

		<p>25. The Employee agrees and acknowledges that the restrictions contained in Clause 18 to 21 are deemed to be reasonable in all circumstances for the protection of the legitimate interests of the Employer.</p>

		<p>26. If any provision of this Agreement is invalid and unenforceable according to the laws of any jurisdiction where the obligations herein are to be performed, the remaining provisions of this Agreement shall remain in force to carry out the intention of the Parties and the invalidity or the unenforceability of any of the provisions herein shall not affect the validity or the enforceability of other provisions. Further, the Parties shall endeavour to replace such invalid terms or provisions with valid terms and provisions.</p>

		<p>27. The Parties hereto agree that this Agreement herein, and any dispute or claim arising out of or in connection with it or its subject matter or formation shall be governed by and construed in accordance with the laws of India.</p>

		<p>28. The Parties herein agree that the Courts of Chennai shall have exclusive jurisdiction to settle any dispute or claim whatsoever that arises out of or in connection with this Agreement and its subject or formation of this Agreement herein.</p>

		<p>29. If any claim or controversy arises out of this Agreement, the parties shall first make a good faith attempt to resolve the matter through the management. In the event such good faith negotiation fails to settle any dispute within thirty (30) days from notice of such dispute, the dispute shall be settled by binding arbitration by a single arbitrator mutually agreed and appointed by the Parties. The proceedings shall take place at Chennai in accordance with the Indian Arbitration and Conciliation Act, 1996 and would be conducted in English. Nothing herein shall be deemed to limit either Party's right to seek injunctive relief in any court of competent jurisdiction. The parties hereto agree to submit to the exclusive jurisdiction of the Courts at Chennai for matters incidental to the arbitration proceedings.</p>

		<p>30. This Agreement may be executed in any number of counterparts, each of which shall be deemed to be an original as against both Parties whose signature appears thereon, and all of such shall together constitute one and the same instrument.</p>

		<p>31. Except as expressly provided under this Agreement, the forbearance or delay of either Party in exercising any rights hereunder shall not be deemed to be a waiver or release of any other rights which may subsequently arise unless expressly set forth in writing by such Party. Waiver of a breach of the Agreement shall not be deemed to be a waiver of any similar breaches before or after such breach.</p>

		<p>32. This Agreement shall contain the entire agreement and understanding between the Parties hereto with respect to the subject matter hereof.</p>

		<p style="margin-top:14px;"><b>IN WITNESS WHEREOF</b> the parties hereunto have executed this Agreement by affixing their respective signature on the date and place above mentioned in the presence of the following witness.</p>

		<p style="margin-top:10px; font-weight:bold; color:#555;">Please scroll up and review all clauses above, then sign below to accept this Employment Agreement.</p>
	</div>
	`;
}
