// Compensatory Leave Request PWA Extension
(function () {
	var sessionEmployee = null;
	var isEmployeeFetchPending = false;
	var isSubmitting = false;

	// 1. Fetch Session Employee
	function fetchSessionEmployee(callback) {
		if (sessionEmployee && sessionEmployee.name) {
			if (callback) callback(sessionEmployee);
			return;
		}

		// Try loading from localStorage cached by frappe-ui
		try {
			var cached = localStorage.getItem("hrms:employee");
			if (cached) {
				var parsed = JSON.parse(cached);
				if (parsed && parsed.name) {
					sessionEmployee = parsed;
					if (callback) callback(sessionEmployee);
					return;
				}
			}
		} catch (e) {}

		if (isEmployeeFetchPending) return;
		isEmployeeFetchPending = true;

		fetch("/api/method/hrms.api.get_current_employee_info", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
		})
			.then(function (res) {
				return res.json();
			})
			.then(function (data) {
				isEmployeeFetchPending = false;
				if (data && data.message && data.message.name) {
					sessionEmployee = data.message;
					updateEmployeeDisplay();
					if (callback) callback(sessionEmployee);
				}
			})
			.catch(function () {
				isEmployeeFetchPending = false;
			});
	}

	function updateEmployeeDisplay() {
		var empInput = document.getElementById("comp-leave-employee-display");
		if (empInput && sessionEmployee) {
			var label = sessionEmployee.employee_name
				? sessionEmployee.employee_name + " (" + sessionEmployee.name + ")"
				: sessionEmployee.name;
			empInput.value = label;
		}
	}

	var compensatoryLeaveTypes = null;
	var isLeaveTypeFetchPending = false;

	// Fetch Compensatory Leave Types
	function fetchCompensatoryLeaveTypes(callback) {
		if (compensatoryLeaveTypes && compensatoryLeaveTypes.length > 0) {
			if (callback) callback(compensatoryLeaveTypes);
			return;
		}

		if (isLeaveTypeFetchPending) {
			if (callback) {
				var interval = setInterval(function () {
					if (!isLeaveTypeFetchPending) {
						clearInterval(interval);
						if (callback) callback(compensatoryLeaveTypes || ["Comp-Off"]);
					}
				}, 50);
			}
			return;
		}
		isLeaveTypeFetchPending = true;

		fetch("/api/method/hrms_custom.api.compensatory_leave.get_compensatory_leave_types", {
			method: "GET",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
		})
			.then(function (res) {
				return res.json();
			})
			.then(function (data) {
				isLeaveTypeFetchPending = false;
				if (data && data.message && data.message.length > 0) {
					compensatoryLeaveTypes = data.message;
				} else {
					return fetch("/api/method/frappe.client.get_list?doctype=Leave+Type&filters=" + encodeURIComponent(JSON.stringify({ is_compensatory: 1 })) + "&fields=" + encodeURIComponent(JSON.stringify(["name"])))
						.then(function (res2) { return res2.json(); })
						.then(function (data2) {
							if (data2 && data2.message && data2.message.length > 0) {
								compensatoryLeaveTypes = data2.message.map(function (m) { return m.name; });
							} else {
								compensatoryLeaveTypes = ["Comp-Off"];
							}
						});
				}
			})
			.catch(function () {
				isLeaveTypeFetchPending = false;
				compensatoryLeaveTypes = ["Comp-Off"];
			})
			.finally(function () {
				isLeaveTypeFetchPending = false;
				if (!compensatoryLeaveTypes || compensatoryLeaveTypes.length === 0) {
					compensatoryLeaveTypes = ["Comp-Off"];
				}
				updateLeaveTypeDisplay();
				if (callback) callback(compensatoryLeaveTypes);
			});
	}

	function updateLeaveTypeDisplay() {
		var container = document.getElementById("comp-leave-type-container");
		if (!container) return;

		var types = compensatoryLeaveTypes || ["Comp-Off"];
		if (types.length <= 1) {
			var val = types[0] || "Comp-Off";
			container.innerHTML = '<input type="text" id="comp-leave-type-input" value="' + val + '" class="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 cursor-not-allowed" readonly />';
		} else {
			var optionsHtml = types.map(function (t) {
				return '<option value="' + t + '">' + t + '</option>';
			}).join("");
			container.innerHTML = '<select id="comp-leave-type-select" class="w-full px-3 py-2.5 bg-white border border-gray-300 rounded-lg text-sm text-gray-900 focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none transition-colors">' + optionsHtml + '</select>';
		}
	}

	// 2. Toast Notification Helper
	function showToast(message, isError) {
		var existing = document.getElementById("comp-leave-toast");
		if (existing) existing.remove();

		var toast = document.createElement("div");
		toast.id = "comp-leave-toast";
		toast.className = "fixed bottom-6 left-1/2 transform -translate-x-1/2 z-[99999] px-4 py-3 rounded-lg shadow-lg text-sm font-medium flex items-center gap-2 transition-all duration-300";
		if (isError) {
			toast.className += " bg-red-600 text-white";
			toast.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg><span>' + message + '</span>';
		} else {
			toast.className += " bg-gray-900 text-white";
			toast.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg><span>' + message + '</span>';
		}

		document.body.appendChild(toast);
		setTimeout(function () {
			toast.style.opacity = "0";
			setTimeout(function () {
				if (toast.parentNode) toast.parentNode.removeChild(toast);
			}, 300);
		}, 3000);
	}

	// 3. Quick Link Injection
	function ensureQuickLink() {
		var isHome = window.location.pathname.indexOf("/hrms/home") !== -1 || window.location.pathname === "/hrms" || window.location.pathname === "/hrms/";
		if (!isHome) return;

		var headers = document.querySelectorAll("div, h2, h3, span");
		var quickLinksHeader = null;
		for (var i = 0; i < headers.length; i++) {
			if ((headers[i].textContent || "").trim() === "Quick Links") {
				quickLinksHeader = headers[i];
				break;
			}
		}
		if (!quickLinksHeader) return;

		var listContainer = quickLinksHeader.nextElementSibling;
		if (!listContainer || !listContainer.classList.contains("bg-white")) {
			if (quickLinksHeader.parentElement) {
				listContainer = quickLinksHeader.parentElement.querySelector(".bg-white.rounded");
			}
		}
		if (!listContainer) return;

		if (listContainer.querySelector("#quick-link-compensatory-leave")) {
			return;
		}

		var link = document.createElement("div");
		link.id = "quick-link-compensatory-leave";
		link.className = "flex flex-row flex-start p-4 items-center justify-between border-b cursor-pointer transition-colors hover:bg-gray-50";
		link.innerHTML = [
			'<div class="flex flex-row items-center gap-3 grow">',
			'  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-gray-500">',
			'    <rect width="18" height="18" x="3" y="4" rx="2" ry="2"></rect>',
			'    <line x1="16" y1="2" x2="16" y2="6"></line>',
			'    <line x1="8" y1="2" x2="8" y2="6"></line>',
			'    <line x1="3" y1="10" x2="21" y2="10"></line>',
			'  </svg>',
			'  <div class="text-base font-normal text-gray-800">Compensatory Leave Request</div>',
			'</div>',
			'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevron-right shrink-0 h-5 w-5 text-gray-500">',
			'  <polyline points="9 18 15 12 9 6"></polyline>',
			'</svg>'
		].join("");

		link.onclick = function (e) {
			e.preventDefault();
			e.stopPropagation();
			window.location.hash = "#compensatory-leave-request";
			openCompensatoryLeavePage();
		};

		var leaveLink = null;
		var children = listContainer.children;
		for (var j = 0; j < children.length; j++) {
			var text = (children[j].textContent || "").trim();
			if (text.indexOf("Request Leave") !== -1 || text.indexOf("Leave Application") !== -1) {
				leaveLink = children[j];
				break;
			}
		}

		if (leaveLink && leaveLink.nextSibling) {
			listContainer.insertBefore(link, leaveLink.nextSibling);
		} else {
			listContainer.appendChild(link);
		}
	}

	// 4. Modal Form UI for New Compensatory Leave Request
	function getOrCreatePage() {
		var page = document.getElementById("compensatory-leave-page-container");
		if (page) return page;

		page = document.createElement("div");
		page.id = "compensatory-leave-page-container";
		page.className = "fixed inset-0 z-[10000] bg-gray-100 flex flex-col items-center justify-start overflow-hidden";
		page.style.display = "none";

		var html = [
			'<div class="w-full h-full bg-white sm:w-96 flex flex-col shadow-sm relative overflow-hidden">',
			'  <!-- Header matching Frappe HR FormView -->',
			'  <header class="flex flex-row bg-white shadow-sm py-4 px-3 items-center sticky top-0 z-10 shrink-0">',
			'    <button id="comp-leave-back-btn" class="p-1 -ml-1 text-gray-700 hover:text-gray-900 rounded-full hover:bg-gray-100 flex items-center justify-center mr-2 cursor-pointer">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>',
			'    </button>',
			'    <h2 class="text-xl font-bold text-gray-900 truncate">New Compensatory Leave Request</h2>',
			'  </header>',
			'  <!-- Form Body -->',
			'  <div class="flex-1 overflow-y-auto p-4 space-y-4 bg-white pb-6">',
			'    <div class="flex flex-col gap-1.5">',
			'      <label class="block text-sm font-medium text-gray-700">Employee</label>',
			'      <input type="text" id="comp-leave-employee-display" class="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 cursor-not-allowed" readonly placeholder="Loading employee..." />',
			'    </div>',
			'    <div class="flex flex-col gap-1.5">',
			'      <label class="block text-sm font-medium text-gray-700">Leave Type</label>',
			'      <div id="comp-leave-type-container">',
			'        <input type="text" id="comp-leave-type-input" value="' + ((compensatoryLeaveTypes && compensatoryLeaveTypes[0]) || "Loading...") + '" class="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 cursor-not-allowed" readonly />',
			'      </div>',
			'    </div>',
			'    <div class="flex flex-col gap-1.5">',
			'      <label class="block text-sm font-medium text-gray-700">Work From Date <span class="text-red-500">*</span></label>',
			'      <input type="date" id="comp-leave-from-date" class="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:bg-white focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none transition-colors" />',
			'    </div>',
			'    <div class="flex flex-col gap-1.5">',
			'      <label class="block text-sm font-medium text-gray-700">Work End Date <span class="text-red-500">*</span></label>',
			'      <input type="date" id="comp-leave-to-date" class="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:bg-white focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none transition-colors" />',
			'      <p id="comp-leave-date-error" class="hidden text-xs text-red-500 mt-0.5">Work End Date cannot be before Work From Date</p>',
			'    </div>',
			'    <div class="flex items-center pt-1">',
			'      <input type="checkbox" id="comp-leave-half-day" class="h-4 w-4 text-gray-900 focus:ring-gray-900 border-gray-300 rounded cursor-pointer" />',
			'      <label for="comp-leave-half-day" class="ml-2 block text-sm font-medium text-gray-700 cursor-pointer">Half Day</label>',
			'    </div>',
			'    <div id="comp-leave-half-day-container" class="hidden flex-col gap-1.5">',
			'      <label class="block text-sm font-medium text-gray-700">Half Day Date <span class="text-red-500">*</span></label>',
			'      <input type="date" id="comp-leave-half-day-date" class="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:bg-white focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none transition-colors" />',
			'    </div>',
			'    <div class="flex flex-col gap-1.5">',
			'      <label class="block text-sm font-medium text-gray-700">Reason <span class="text-red-500">*</span></label>',
			'      <textarea id="comp-leave-reason" rows="3" placeholder="Enter reason for compensatory leave..." class="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-900 focus:bg-white focus:ring-1 focus:ring-gray-900 focus:border-gray-900 outline-none transition-colors resize-none"></textarea>',
			'    </div>',
			'    <div id="comp-leave-form-error" class="hidden p-3 bg-red-50 text-red-600 rounded-lg text-sm border border-red-200"></div>',
			'  </div>',
			'  <!-- Actions Footer matching Frappe HR FormView -->',
			'  <footer class="p-4 bg-white border-t sticky bottom-0 z-10 shrink-0">',
			'    <button id="comp-leave-save-btn" class="w-full py-3 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-black transition-colors disabled:bg-gray-400 flex items-center justify-center gap-2 cursor-pointer">',
			'      <span id="comp-leave-btn-label">Save</span>',
			'    </button>',
			'  </footer>',
			'</div>'
		].join("");

		page.innerHTML = html;
		document.body.appendChild(page);

		document.getElementById("comp-leave-back-btn").onclick = function () {
			closeCompensatoryLeavePage();
		};

		document.getElementById("comp-leave-save-btn").onclick = function () {
			handleFormSubmit();
		};

		var fromInput = document.getElementById("comp-leave-from-date");
		var toInput = document.getElementById("comp-leave-to-date");
		var halfDayCb = document.getElementById("comp-leave-half-day");

		fromInput.onchange = function () {
			if (!toInput.value || toInput.getAttribute("data-auto-synced") === "true") {
				toInput.value = fromInput.value;
				toInput.setAttribute("data-auto-synced", "true");
			}
			validateDateRange();
			updateHalfDayDateConstraints();
		};

		toInput.onchange = function () {
			toInput.removeAttribute("data-auto-synced");
			validateDateRange();
			updateHalfDayDateConstraints();
		};

		halfDayCb.onchange = function () {
			var hContainer = document.getElementById("comp-leave-half-day-container");
			if (halfDayCb.checked) {
				hContainer.classList.remove("hidden");
				hContainer.classList.add("flex");
				updateHalfDayDateConstraints();
			} else {
				hContainer.classList.add("hidden");
				hContainer.classList.remove("flex");
			}
		};

		return page;
	}

	function validateDateRange() {
		var fromDateInput = document.getElementById("comp-leave-from-date");
		var toDateInput = document.getElementById("comp-leave-to-date");
		var errorEl = document.getElementById("comp-leave-date-error");
		if (!fromDateInput || !toDateInput) return true;

		var fromDate = fromDateInput.value;
		var toDate = toDateInput.value;

		if (fromDate && toDate && toDate < fromDate) {
			if (errorEl) errorEl.classList.remove("hidden");
			toDateInput.classList.add("border-red-500");
			toDateInput.classList.remove("border-gray-300");
			return false;
		} else {
			if (errorEl) errorEl.classList.add("hidden");
			toDateInput.classList.remove("border-red-500");
			toDateInput.classList.add("border-gray-300");
			return true;
		}
	}

	function updateHalfDayDateConstraints() {
		var fromDateInput = document.getElementById("comp-leave-from-date");
		var toDateInput = document.getElementById("comp-leave-to-date");
		var halfDayDateInput = document.getElementById("comp-leave-half-day-date");

		if (!halfDayDateInput) return;

		var fromDate = fromDateInput ? fromDateInput.value : "";
		var toDate = toDateInput ? toDateInput.value : "";

		if (fromDate) halfDayDateInput.min = fromDate;
		if (toDate) halfDayDateInput.max = toDate;

		if (!halfDayDateInput.value && fromDate) {
			halfDayDateInput.value = fromDate;
		} else if (halfDayDateInput.value && fromDate && halfDayDateInput.value < fromDate) {
			halfDayDateInput.value = fromDate;
		} else if (halfDayDateInput.value && toDate && halfDayDateInput.value > toDate) {
			halfDayDateInput.value = toDate;
		}
	}

	function setFormError(msg) {
		var errorBox = document.getElementById("comp-leave-form-error");
		if (!errorBox) return;
		if (msg) {
			errorBox.textContent = msg;
			errorBox.classList.remove("hidden");
		} else {
			errorBox.textContent = "";
			errorBox.classList.add("hidden");
		}
	}

	function handleFormSubmit() {
		if (isSubmitting) return;

		setFormError("");

		if (!sessionEmployee || !sessionEmployee.name) {
			setFormError("Employee details not loaded. Please wait or reload.");
			return;
		}

		var fromDateInput = document.getElementById("comp-leave-from-date");
		var toDateInput = document.getElementById("comp-leave-to-date");
		var halfDayCheckbox = document.getElementById("comp-leave-half-day");
		var halfDayDateInput = document.getElementById("comp-leave-half-day-date");
		var reasonInput = document.getElementById("comp-leave-reason");
		var saveBtn = document.getElementById("comp-leave-save-btn");
		var btnLabel = document.getElementById("comp-leave-btn-label");

		var fromDate = fromDateInput ? fromDateInput.value : "";
		var toDate = toDateInput ? toDateInput.value : "";
		var isHalfDay = halfDayCheckbox ? halfDayCheckbox.checked : false;
		var halfDayDate = halfDayDateInput ? halfDayDateInput.value : "";
		var reason = reasonInput ? (reasonInput.value || "").trim() : "";

		var missingFields = [];
		if (!fromDate) missingFields.push("Work From Date");
		if (!toDate) missingFields.push("Work End Date");
		if (isHalfDay && !halfDayDate) missingFields.push("Half Day Date");
		if (!reason) missingFields.push("Reason");

		if (missingFields.length > 0) {
			setFormError(missingFields.join(", ") + (missingFields.length > 1 ? " are mandatory" : " is mandatory"));
			return;
		}

		if (!validateDateRange()) {
			setFormError("Work End Date cannot be before Work From Date");
			return;
		}

		if (isHalfDay && halfDayDate) {
			if (halfDayDate < fromDate || halfDayDate > toDate) {
				setFormError("Half Day Date must be between Work From Date and Work End Date");
				return;
			}
		}

		var leaveType = "";
		var selectEl = document.getElementById("comp-leave-type-select");
		var inputEl = document.getElementById("comp-leave-type-input");
		if (selectEl && selectEl.value) {
			leaveType = selectEl.value;
		} else if (inputEl && inputEl.value && inputEl.value !== "Loading...") {
			leaveType = inputEl.value;
		} else if (compensatoryLeaveTypes && compensatoryLeaveTypes.length > 0) {
			leaveType = compensatoryLeaveTypes[0];
		} else {
			leaveType = "Comp-Off";
		}

		isSubmitting = true;
		if (saveBtn) saveBtn.disabled = true;
		if (btnLabel) btnLabel.textContent = "Saving...";

		var payload = {
			doc: {
				doctype: "Compensatory Leave Request",
				employee: sessionEmployee.name,
				leave_type: leaveType,
				work_from_date: fromDate,
				work_end_date: toDate,
				half_day: isHalfDay ? 1 : 0,
				half_day_date: isHalfDay ? halfDayDate : null,
				reason: reason,
				docstatus: 0,
			},
		};

		fetch("/api/method/frappe.client.insert", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
			body: JSON.stringify(payload),
		})
			.then(function (response) {
				return response.text().then(function (text) {
					var data = null;
					try {
						data = JSON.parse(text);
					} catch (e) {}

					if (!response.ok) {
						var serverMsg = null;
						if (data && data._server_messages) {
							try {
								var parsed = JSON.parse(data._server_messages);
								var msgs = [];
								for (var i = 0; i < parsed.length; i++) {
									var mObj = JSON.parse(parsed[i]);
									if (mObj && mObj.message) {
										var div = document.createElement("div");
										div.innerHTML = mObj.message;
										msgs.push((div.textContent || div.innerText || "").trim());
									}
								}
								if (msgs.length > 0) serverMsg = msgs.join(" ");
							} catch (e) {}
						}
						throw new Error(serverMsg || (data && data.exception) || "Failed to create Compensatory Leave Request");
					}
					return data;
				});
			})
			.then(function (data) {
				isSubmitting = false;
				if (saveBtn) saveBtn.disabled = false;
				if (btnLabel) btnLabel.textContent = "Save";

				showToast("Compensatory Leave Request created successfully!", false);
				resetForm();
				closeCompensatoryLeavePage();
				triggerPanelRefresh();
			})
			.catch(function (err) {
				isSubmitting = false;
				if (saveBtn) saveBtn.disabled = false;
				if (btnLabel) btnLabel.textContent = "Save";
				setFormError(err.message || "An error occurred while saving.");
			});
	}

	function resetForm() {
		setFormError("");
		var fromDateInput = document.getElementById("comp-leave-from-date");
		var toDateInput = document.getElementById("comp-leave-to-date");
		var halfDayCheckbox = document.getElementById("comp-leave-half-day");
		var halfDayContainer = document.getElementById("comp-leave-half-day-container");
		var halfDayDateInput = document.getElementById("comp-leave-half-day-date");
		var reasonInput = document.getElementById("comp-leave-reason");
		var dateError = document.getElementById("comp-leave-date-error");

		if (fromDateInput) fromDateInput.value = "";
		if (toDateInput) {
			toDateInput.value = "";
			toDateInput.removeAttribute("data-auto-synced");
			toDateInput.classList.remove("border-red-500");
			toDateInput.classList.add("border-gray-300");
		}
		if (dateError) dateError.classList.add("hidden");
		if (halfDayCheckbox) halfDayCheckbox.checked = false;
		if (halfDayContainer) {
			halfDayContainer.classList.add("hidden");
			halfDayContainer.classList.remove("flex");
		}
		if (halfDayDateInput) halfDayDateInput.value = "";
		if (reasonInput) reasonInput.value = "";
	}

	function openCompensatoryLeavePage() {
		var page = getOrCreatePage();
		page.style.display = "flex";
		document.body.style.overflow = "hidden";

		fetchSessionEmployee(function (emp) {
			updateEmployeeDisplay();
		});

		fetchCompensatoryLeaveTypes(function (types) {
			updateLeaveTypeDisplay();
		});
	}

	function closeCompensatoryLeavePage() {
		var page = document.getElementById("compensatory-leave-page-container");
		if (page) {
			page.style.display = "none";
		}
		document.body.style.overflow = "";
		if (window.location.hash === "#compensatory-leave-request") {
			if (window.history.length > 1) {
				window.history.back();
			} else {
				window.location.hash = "";
			}
		}
	}

	// =========================================================================
	// 5. TEAM REQUESTS & MY REQUESTS INTEGRATION
	// =========================================================================
	var teamRequestsCache = [];
	var myRequestsCache = [];
	var lastFetchTeam = 0;
	var lastFetchMy = 0;
	var isFetchingTeam = false;
	var isFetchingMy = false;

	function triggerPanelRefresh() {
		lastFetchTeam = 0;
		lastFetchMy = 0;
		syncRequestsPanel();
	}

	function getActiveRequestsTab() {
		var tabContainers = document.querySelectorAll(".bg-gray-200.rounded");
		for (var i = 0; i < tabContainers.length; i++) {
			var buttons = tabContainers[i].querySelectorAll("button");
			for (var j = 0; j < buttons.length; j++) {
				var txt = (buttons[j].textContent || "").trim();
				var isActive = buttons[j].className.indexOf("bg-white") !== -1 || buttons[j].className.indexOf("drop-shadow") !== -1;
				if (txt.indexOf("Team Requests") !== -1 && isActive) return "team";
				if (txt.indexOf("My Requests") !== -1 && isActive) return "my";
			}
		}
		return null;
	}

	function getTabContainer() {
		var tabContainers = document.querySelectorAll(".bg-gray-200.rounded");
		for (var i = 0; i < tabContainers.length; i++) {
			var text = tabContainers[i].textContent || "";
			if (text.indexOf("Team Requests") !== -1 || text.indexOf("My Requests") !== -1) {
				return tabContainers[i];
			}
		}
		return null;
	}

	function formatDateLabel(fromDate, toDate) {
		if (!fromDate) return "";
		try {
			var d1 = new Date(fromDate);
			var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
			var str1 = d1.getDate() + " " + months[d1.getMonth()];
			if (!toDate || toDate === fromDate) return str1;
			var d2 = new Date(toDate);
			var str2 = d2.getDate() + " " + months[d2.getMonth()];
			return str1 + " - " + str2;
		} catch (e) {
			return fromDate;
		}
	}

	function fetchCompensatoryRequests(forApproval, callback) {
		var now = Date.now();
		if (forApproval) {
			if (now - lastFetchTeam < 4000 && !isFetchingTeam) {
				if (callback) callback(teamRequestsCache);
				return;
			}
			if (isFetchingTeam) return;
			isFetchingTeam = true;
		} else {
			if (now - lastFetchMy < 4000 && !isFetchingMy) {
				if (callback) callback(myRequestsCache);
				return;
			}
			if (isFetchingMy) return;
			isFetchingMy = true;
		}

		fetch("/api/method/hrms_custom.api.compensatory_leave.get_compensatory_leave_requests?for_approval=" + (forApproval ? 1 : 0) + "&limit=10", {
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" }
		})
			.then(function (res) { return res.json(); })
			.then(function (res) {
				var data = (res && res.message) || [];
				if (forApproval) {
					teamRequestsCache = data;
					lastFetchTeam = Date.now();
					isFetchingTeam = false;
				} else {
					myRequestsCache = data;
					lastFetchMy = Date.now();
					isFetchingMy = false;
				}
				if (callback) callback(data);
			})
			.catch(function () {
				if (forApproval) isFetchingTeam = false;
				else isFetchingMy = false;
			});
	}

	function syncRequestsPanel() {
		var isHome = window.location.pathname.indexOf("/hrms/home") !== -1 || window.location.pathname === "/hrms" || window.location.pathname === "/hrms/";
		if (!isHome) return;

		var activeTab = getActiveRequestsTab();
		var tabContainer = getTabContainer();
		if (!activeTab || !tabContainer) return;

		var parentPanel = tabContainer.parentElement;
		if (!parentPanel) return;

		var isTeam = (activeTab === "team");

		fetchCompensatoryRequests(isTeam, function (requests) {
			renderRequestsIntoDOM(requests, isTeam, parentPanel, tabContainer);
		});
	}

	function renderRequestsIntoDOM(requests, isTeam, parentPanel, tabContainer) {
		var listContainer = parentPanel.querySelector(".flex.flex-col.bg-white.rounded.mt-5");
		var emptyState = parentPanel.querySelector(".flex.flex-col.items-center.rounded.p-5.text-sm.text-gray-600");

		if (!requests || requests.length === 0) {
			// Remove any injected rows
			var oldRows = parentPanel.querySelectorAll("[data-comp-leave-row]");
			for (var r = 0; r < oldRows.length; r++) oldRows[r].remove();

			// If we created a custom list wrapper, remove it and restore empty state
			var customWrapper = parentPanel.querySelector("[data-comp-leave-wrapper]");
			if (customWrapper) {
				customWrapper.remove();
				if (emptyState) emptyState.style.display = "";
			}
			return;
		}

		// We have requests to display
		if (emptyState) {
			emptyState.style.display = "none";
		}

		if (!listContainer) {
			listContainer = document.createElement("div");
			listContainer.className = "flex flex-col bg-white rounded mt-5 overflow-auto";
			listContainer.setAttribute("data-comp-leave-wrapper", "1");
			if (tabContainer.nextSibling) {
				parentPanel.insertBefore(listContainer, tabContainer.nextSibling);
			} else {
				parentPanel.appendChild(listContainer);
			}
		}

		// Render each request
		for (var i = 0; i < requests.length; i++) {
			var req = requests[i];
			var existingRow = listContainer.querySelector('[data-comp-leave-row="' + req.name + '"]');
			if (existingRow) continue;

			var row = createRequestRow(req, isTeam);
			if (listContainer.firstChild) {
				listContainer.insertBefore(row, listContainer.firstChild);
			} else {
				listContainer.appendChild(row);
			}
		}
	}

	function createRequestRow(req, isTeam) {
		var row = document.createElement("div");
		row.className = "flex flex-row p-3.5 items-center justify-between border-b cursor-pointer transition-colors hover:bg-gray-50";
		row.setAttribute("data-comp-leave-row", req.name);

		var isDraft = (req.docstatus === 0);
		var badgeText = isDraft ? "Pending Approval" : "Approved";
		var dateStr = formatDateLabel(req.work_from_date, req.work_end_date);
		var initial = (req.employee_name || req.employee || "E").charAt(0).toUpperCase();

		var badgeClass = isDraft
			? "text-ink-gray-6 bg-transparent border border-outline-gray-1"
			: "text-ink-green-3 bg-transparent border border-outline-green-2";
		var badgeStyle = isDraft
			? "color: rgb(82, 82, 82); border: 1px solid rgb(237, 237, 237); background-color: transparent; border-radius: 9999px; font-size: 12px; height: 20px; padding: 0 6px; white-space: nowrap; flex-shrink: 0;"
			: "color: rgb(39, 143, 94); border: 1px solid rgb(134, 224, 168); background-color: transparent; border-radius: 9999px; font-size: 12px; height: 20px; padding: 0 6px; white-space: nowrap; flex-shrink: 0;";

		var html = [
			'<div class="flex flex-col w-full justify-center gap-2.5">',
			'  <div class="flex flex-row items-center justify-between">',
			'    <div class="flex flex-row items-start gap-3 grow overflow-hidden">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-gray-500 mt-0.5 shrink-0">',
			'        <rect width="18" height="18" x="3" y="4" rx="2" ry="2"></rect>',
			'        <line x1="16" y1="2" x2="16" y2="6"></line>',
			'        <line x1="8" y1="2" x2="8" y2="6"></line>',
			'        <line x1="3" y1="10" x2="21" y2="10"></line>',
			'      </svg>',
			'      <div class="flex flex-col items-start gap-1.5 truncate">',
			'        <div class="text-base font-normal text-gray-800 truncate">Compensatory Leave Request</div>',
			'        <div class="text-xs font-normal text-gray-500 flex items-center">',
			'          <span>' + dateStr + '</span>',
			'          <span class="whitespace-pre"> &middot; </span>',
			'          <span class="whitespace-nowrap">' + (req.half_day ? "0.5d" : "1d") + '</span>',
			'        </div>',
			'      </div>',
			'    </div>',
			'    <div class="flex flex-row justify-end items-center gap-2 shrink-0">',
			'      <div class="inline-flex select-none items-center gap-1 rounded-full h-5 text-xs px-1.5 whitespace-nowrap ' + badgeClass + '" style="' + badgeStyle + '">' + badgeText + '</div>',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-chevron-right shrink-0 h-5 w-5 text-gray-500">',
			'        <polyline points="9 18 15 12 9 6"></polyline>',
			'      </svg>',
			'    </div>',
			'  </div>',
			(isTeam ? [
			'  <div class="flex flex-row items-center gap-2 pl-8">',
			'    <div class="relative inline-block shrink-0 w-5 h-5 rounded-full" style="width: 20px; height: 20px;"><div class="flex h-full w-full items-center justify-center rounded-full text-xs font-medium uppercase" style="background-color: #f3f4f6; color: #6b7280; width: 100%; height: 100%; border-radius: 9999px;">' + initial + '</div></div>',
			'    <div class="text-sm text-gray-600 grow">' + (req.employee_name || req.employee) + '</div>',
			'  </div>'
			].join("") : ''),
			'</div>'
		].join("");

		row.innerHTML = html;
		row.onclick = function (e) {
			e.preventDefault();
			e.stopPropagation();
			openCompensatoryLeaveDetailModal(req, isTeam);
		};

		return row;
	}

	// 6. Action Sheet Detail Modal (Approve & Reject)
	function openCompensatoryLeaveDetailModal(req, isTeam) {
		var existingModal = document.getElementById("comp-leave-detail-modal-container");
		if (existingModal) existingModal.remove();

		var modal = document.createElement("div");
		modal.id = "comp-leave-detail-modal-container";
		modal.className = "fixed inset-0 z-[100000] flex flex-col justify-end transition-opacity";
		modal.style.backgroundColor = "rgba(0, 0, 0, 0.32)";

		var isDraft = (req.docstatus === 0);
		var initial = (req.employee_name || req.employee || "E").charAt(0).toUpperCase();
		var dateFormatted = formatDateLabel(req.work_from_date, req.work_end_date) || req.work_from_date;
		var badgeClass = isDraft
			? "text-ink-gray-6 bg-transparent border border-outline-gray-1"
			: "text-ink-green-3 bg-transparent border border-outline-green-2";
		var badgeStyle = isDraft
			? "color: rgb(82, 82, 82); border: 1px solid rgb(237, 237, 237); background-color: transparent; border-radius: 9999px; font-size: 12px; height: 20px; padding: 0 6px; white-space: nowrap; flex-shrink: 0;"
			: "color: rgb(39, 143, 94); border: 1px solid rgb(134, 224, 168); background-color: transparent; border-radius: 9999px; font-size: 12px; height: 20px; padding: 0 6px; white-space: nowrap; flex-shrink: 0;";

		var html = [
			'<div class="bg-white rounded-t-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-slide-up w-full max-w-lg mx-auto" style="border-top-left-radius: 1rem; border-top-right-radius: 1rem; background-color: #ffffff; max-width: 480px;">',
			'  <!-- Header -->',
			'  <div class="w-full flex flex-row gap-2 pt-8 pb-5 border-b justify-center items-center sticky top-0 z-[100] bg-white shrink-0" style="border-bottom: 1px solid #f3f4f6;">',
			'    <span class="text-gray-900 font-bold text-lg text-center">Compensatory Leave Request</span>',
			'  </div>',
			'  <!-- Request Summary -->',
			'  <div class="w-full p-4 overflow-auto flex-1">',
			'    <div class="flex flex-col items-center justify-center gap-5">',
			'      <div class="flex flex-row items-center justify-between flex w-full">',
			'        <div class="text-gray-600 text-base">ID</div>',
			'        <div class="text-gray-900 text-base font-normal">' + req.name + '</div>',
			'      </div>',
			'      <div class="flex flex-row items-center justify-between flex w-full">',
			'        <div class="text-gray-600 text-base">Leave Type</div>',
			'        <div class="text-gray-900 text-base font-normal">' + (req.leave_type || (compensatoryLeaveTypes && compensatoryLeaveTypes[0]) || "Comp-Off") + '</div>',
			'      </div>',
			'      <div class="flex flex-row items-center justify-between flex w-full">',
			'        <div class="text-gray-600 text-base">Work Dates</div>',
			'        <div class="text-gray-900 text-base font-normal">' + dateFormatted + '</div>',
			'      </div>',
			'      <div class="flex flex-row items-center justify-between flex w-full">',
			'        <div class="text-gray-600 text-base">Half Day</div>',
			'        <div class="text-gray-900 text-base font-normal">' + (req.half_day ? "Yes" : "No") + '</div>',
			'      </div>',
			'      <div class="flex flex-row items-center justify-between flex w-full">',
			'        <div class="text-gray-600 text-base">Employee</div>',
			'        <div class="flex flex-row items-center gap-2">',
			'          <div class="relative inline-block shrink-0 w-6 h-6 rounded-full" style="width: 24px; height: 24px;"><div class="flex h-full w-full items-center justify-center rounded-full text-xs font-medium uppercase" style="background-color: #f3f4f6; color: #6b7280; width: 100%; height: 100%; border-radius: 9999px;">' + initial + '</div></div>',
			'          <div class="text-gray-900 text-base font-normal">' + (req.employee_name || req.employee) + '</div>',
			'        </div>',
			'      </div>',
			'      <div class="flex flex-row items-center justify-between flex w-full">',
			'        <div class="text-gray-600 text-base">Status</div>',
			'        <div class="inline-flex select-none items-center gap-1 rounded-full h-5 text-xs px-1.5 whitespace-nowrap ' + badgeClass + '" style="' + badgeStyle + '">' + (isDraft ? 'Pending Approval' : 'Approved') + '</div>',
			'      </div>',
			'      <div class="flex flex-col flex w-full">',
			'        <div class="text-gray-600 text-base">Reason</div>',
			'        <div class="text-gray-900 text-base bg-gray-100 rounded py-3 pl-3 pr-3 mt-2 whitespace-pre-wrap" style="background-color: #f3f4f6; border-radius: 0.375rem;">' + (req.reason || "—") + '</div>',
			'      </div>',
			'      <div id="comp-modal-error-box" class="hidden w-full p-3 rounded-lg text-sm" style="background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca;"></div>',
			'    </div>',
			'  </div>',
			'  <!-- Actions -->',
			'  <div class="flex w-full flex-row items-center justify-between gap-3 sticky bottom-0 border-t z-[100] p-4 bg-white shrink-0" style="background-color: #ffffff; border-top: 1px solid #f3f4f6;">',
			(isTeam && isDraft ? [
			'    <button id="comp-btn-reject" class="w-full py-5 inline-flex items-center justify-center gap-2 transition-colors focus:outline-none text-red-700 bg-surface-red-2 hover:bg-surface-red-3 active:bg-surface-red-4 focus-visible:ring focus-visible:ring-outline-red-2 h-7 text-base px-2 rounded cursor-pointer" style="background-color: #fee2e2; color: #b91c1c; height: 2.75rem; border-radius: 0.375rem; font-weight: 500; border: none;">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
			'      <span>Reject</span>',
			'    </button>',
			'    <button id="comp-btn-approve" class="w-full py-5 inline-flex items-center justify-center gap-2 transition-colors focus:outline-none text-ink-white bg-surface-green-3 hover:bg-green-700 active:bg-green-800 focus-visible:ring focus-visible:ring-outline-green-2 h-7 text-base px-2 rounded cursor-pointer" style="background-color: #15803d; color: #ffffff; height: 2.75rem; border-radius: 0.375rem; font-weight: 500; border: none;">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4"><polyline points="20 6 9 17 4 12"></polyline></svg>',
			'      <span>Approve</span>',
			'    </button>'
			].join("") : [
			'    <button id="comp-btn-dismiss" class="w-full py-5 inline-flex items-center justify-center gap-2 transition-colors focus:outline-none text-gray-700 bg-gray-100 hover:bg-gray-200 h-7 text-base px-2 rounded cursor-pointer" style="background-color: #f3f4f6; color: #374151; height: 2.75rem; border-radius: 0.375rem; font-weight: 500; border: none;">',
			'      <span>Close</span>',
			'    </button>'
			].join("")),
			'  </div>',
			'</div>'
		].join("");

		modal.innerHTML = html;
		document.body.appendChild(modal);

		function closeModal() {
			if (modal.parentNode) modal.parentNode.removeChild(modal);
		}

		modal.onclick = function (e) {
			if (e.target === modal) closeModal();
		};

		var dismissBtn = document.getElementById("comp-btn-dismiss");
		if (dismissBtn) dismissBtn.onclick = closeModal;

		var approveBtn = document.getElementById("comp-btn-approve");
		var rejectBtn = document.getElementById("comp-btn-reject");
		var errorBox = document.getElementById("comp-modal-error-box");

		if (approveBtn) {
			approveBtn.onclick = function () {
				if (approveBtn.disabled) return;
				approveBtn.disabled = true;
				if (rejectBtn) rejectBtn.disabled = true;
				approveBtn.innerHTML = '<span>Approving...</span>';
				if (errorBox) errorBox.classList.add("hidden");

				fetch("/api/method/hrms_custom.api.compensatory_leave.approve_compensatory_leave_request", {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": window.csrf_token || "",
					},
					body: JSON.stringify({ docname: req.name }),
				})
					.then(function (res) {
						return res.json().then(function (data) {
							if (!res.ok) {
								var msg = (data && (data._server_messages || data.exception)) || "Failed to approve request";
								try {
									var parsed = JSON.parse(data._server_messages);
									var mObj = JSON.parse(parsed[0]);
									msg = mObj.message || msg;
								} catch (e) {}
								throw new Error(msg);
							}
							return data;
						});
					})
					.then(function () {
						closeModal();
						showToast("Compensatory Leave Request approved successfully!", false);
						triggerPanelRefresh();
					})
					.catch(function (err) {
						approveBtn.disabled = false;
						if (rejectBtn) rejectBtn.disabled = false;
						approveBtn.innerHTML = '<span>Approve</span>';
						if (errorBox) {
							errorBox.textContent = err.message || "An error occurred during approval.";
							errorBox.classList.remove("hidden");
						}
					});
			};
		}

		if (rejectBtn) {
			rejectBtn.onclick = function () {
				if (rejectBtn.disabled) return;
				rejectBtn.disabled = true;
				if (approveBtn) approveBtn.disabled = true;
				rejectBtn.innerHTML = '<span>Rejecting...</span>';
				if (errorBox) errorBox.classList.add("hidden");

				fetch("/api/method/hrms_custom.api.compensatory_leave.reject_compensatory_leave_request", {
					method: "POST",
					headers: {
						"Content-Type": "application/json",
						"X-Frappe-CSRF-Token": window.csrf_token || "",
					},
					body: JSON.stringify({ docname: req.name }),
				})
					.then(function (res) {
						return res.json().then(function (data) {
							if (!res.ok) {
								var msg = (data && (data._server_messages || data.exception)) || "Failed to reject request";
								try {
									var parsed = JSON.parse(data._server_messages);
									var mObj = JSON.parse(parsed[0]);
									msg = mObj.message || msg;
								} catch (e) {}
								throw new Error(msg);
							}
							return data;
						});
					})
					.then(function () {
						closeModal();
						showToast("Compensatory Leave Request rejected.", false);
						triggerPanelRefresh();
					})
					.catch(function (err) {
						rejectBtn.disabled = false;
						if (approveBtn) approveBtn.disabled = false;
						rejectBtn.innerHTML = '<span>Reject</span>';
						if (errorBox) {
							errorBox.textContent = err.message || "An error occurred during rejection.";
							errorBox.classList.remove("hidden");
						}
					});
			};
		}
	}

	// 7. Watch for hash / popstate changes
	window.addEventListener("hashchange", function () {
		if (window.location.hash === "#compensatory-leave-request") {
			openCompensatoryLeavePage();
		} else {
			var page = document.getElementById("compensatory-leave-page-container");
			if (page && page.style.display !== "none") {
				page.style.display = "none";
				document.body.style.overflow = "";
			}
		}
	});

	window.addEventListener("popstate", function () {
		if (window.location.hash !== "#compensatory-leave-request") {
			var page = document.getElementById("compensatory-leave-page-container");
			if (page && page.style.display !== "none") {
				page.style.display = "none";
				document.body.style.overflow = "";
			}
		}
	});

	function scan() {
		ensureQuickLink();
		if (window.location.hash === "#compensatory-leave-request") {
			var page = document.getElementById("compensatory-leave-page-container");
			if (!page || page.style.display === "none") {
				openCompensatoryLeavePage();
			}
		}
		syncRequestsPanel();
	}

	var scanPending = null;
	function scheduleScan() {
		if (scanPending) return;
		scanPending = requestAnimationFrame(function () {
			scanPending = null;
			scan();
		});
	}

	var observer = new MutationObserver(function (mutations) {
		var hasExternalMutation = false;
		for (var i = 0; i < mutations.length; i++) {
			var target = mutations[i].target;
			if (target && target.closest && (target.closest("#compensatory-leave-page-container") || target.closest("#comp-leave-detail-modal-container"))) {
				continue;
			}
			hasExternalMutation = true;
			break;
		}
		if (hasExternalMutation) {
			scheduleScan();
		}
	});

	observer.observe(document.body, { subtree: true, childList: true });

	fetchCompensatoryLeaveTypes();
	scheduleScan();
	setInterval(scheduleScan, 1500);
})();
