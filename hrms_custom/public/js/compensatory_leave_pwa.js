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

	// 2. Toast Notification Helper
	function showToast(message, isError) {
		var existing = document.getElementById("comp-leave-custom-toast");
		if (existing) existing.remove();

		var toast = document.createElement("div");
		toast.id = "comp-leave-custom-toast";
		toast.className = "flex items-center gap-2 px-4 py-3 bg-white text-gray-800 rounded-full shadow-lg border border-gray-200 text-sm font-medium transition-all duration-300 pointer-events-auto";
		toast.style.cssText = "position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); z-index: 1000001;";

		var iconSvg = isError
			? '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 text-red-500"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
			: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 text-emerald-500"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';

		toast.innerHTML = iconSvg + '<span>' + message + '</span>';
		document.body.appendChild(toast);

		setTimeout(function () {
			toast.style.opacity = "0";
			toast.style.transform = "translateX(-50%) translateY(10px)";
			setTimeout(function () {
				if (toast.parentElement) toast.remove();
			}, 300);
		}, 3500);
	}

	// 3. Inject Quick Links Entry
	function ensureQuickLink() {
		if (document.getElementById("quick-link-compensatory-leave")) return;

		var headings = document.querySelectorAll("div.text-lg.font-medium.text-gray-900");
		var quickLinksBox = null;
		for (var i = 0; i < headings.length; i++) {
			if ((headings[i].textContent || "").trim() === "Quick Links") {
				var nextEl = headings[i].nextElementSibling;
				if (nextEl && nextEl.classList.contains("flex-col")) {
					quickLinksBox = nextEl;
					break;
				}
			}
		}

		if (!quickLinksBox) {
			var attLink = document.querySelector('a[href*="leave-applications"]') || document.querySelector('a[href*="attendance-requests"]');
			if (attLink && attLink.parentElement) {
				quickLinksBox = attLink.parentElement;
			}
		}

		if (!quickLinksBox) return;

		var item = document.createElement("a");
		item.id = "quick-link-compensatory-leave";
		item.className = "flex flex-row flex-start p-4 items-center justify-between border-b cursor-pointer hover:bg-gray-50 transition active:bg-gray-100";
		item.href = "#compensatory-leave-request";

		item.innerHTML = [
			'<div class="flex flex-row items-center gap-3 grow pointer-events-none">',
			'  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-gray-500">',
			'    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>',
			'    <line x1="16" y1="2" x2="16" y2="6"></line>',
			'    <line x1="8" y1="2" x2="8" y2="6"></line>',
			'    <line x1="3" y1="10" x2="21" y2="10"></line>',
			'    <line x1="12" y1="13" x2="12" y2="17"></line>',
			'    <line x1="10" y1="15" x2="14" y2="15"></line>',
			'  </svg>',
			'  <div class="text-base font-normal text-gray-800">Compensatory Leave Request</div>',
			'</div>',
			'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-gray-500 pointer-events-none">',
			'  <polyline points="9 18 15 12 9 6"></polyline>',
			'</svg>',
		].join("\n");

		item.addEventListener("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			window.location.hash = "compensatory-leave-request";
			openCompensatoryLeavePage();
		});

		var leaveLink = quickLinksBox.querySelector('a[href*="leave-applications"]');
		if (leaveLink && leaveLink.nextElementSibling) {
			quickLinksBox.insertBefore(item, leaveLink.nextElementSibling);
		} else {
			quickLinksBox.appendChild(item);
		}
	}

	// 4. Compensatory Leave Page View Container & Event Delegation
	function getOrCreatePage() {
		var page = document.getElementById("compensatory-leave-page-container");
		if (!page) {
			page = document.createElement("div");
			page.id = "compensatory-leave-page-container";
			page.style.cssText = "position: fixed; inset: 0; z-index: 99999; background: #ffffff; overflow-y: auto; -webkit-overflow-scrolling: touch; display: none; flex-direction: column; align-items: center; pointer-events: auto;";
			document.body.appendChild(page);

			renderPageSkeleton(page);
			attachPageEventListeners(page);
		}
		return page;
	}

	function renderPageSkeleton(page) {
		var html = [
			'<div class="w-full h-full bg-white sm:w-96 flex flex-col box-border">',
			'  <!-- Header Bar -->',
			'  <header class="flex flex-row bg-white shadow-sm py-4 px-3 items-center sticky top-0 z-[1000] w-full border-b border-gray-100">',
			'    <button id="comp-leave-back-btn" type="button" class="p-2 -ml-1 text-gray-700 hover:text-gray-900 rounded-full hover:bg-gray-100 active:scale-95 transition cursor-pointer">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pointer-events-none">',
			'        <polyline points="15 18 9 12 15 6"></polyline>',
			'      </svg>',
			'    </button>',
			'    <h2 class="text-xl font-semibold text-gray-900 ml-2">New Compensatory Leave Request</h2>',
			'  </header>',

			'  <!-- Form Content -->',
			'  <div class="bg-white grow overflow-y-auto p-4 flex flex-col space-y-4">',
			'    <!-- Employee Field (Locked) -->',
			'    <div class="flex flex-col gap-1.5">',
			'      <span class="block text-sm leading-5 text-gray-700 font-medium">Employee</span>',
			'      <input type="text" id="comp-leave-employee-display" class="w-full px-3 py-2 text-sm bg-gray-50 text-gray-700 border border-gray-200 rounded-md cursor-not-allowed outline-none select-none" readonly value="Loading..." />',
			'    </div>',

			'    <!-- Leave Type Field (Locked to Compensatory Off) -->',
			'    <div class="flex flex-col gap-1.5">',
			'      <span class="block text-sm leading-5 text-gray-700 font-medium">Leave Type</span>',
			'      <input type="text" id="comp-leave-type" class="w-full px-3 py-2 text-sm bg-gray-50 text-gray-700 border border-gray-200 rounded-md cursor-not-allowed outline-none select-none" readonly value="Compensatory Off" />',
			'    </div>',

			'    <!-- Work From Date Field -->',
			'    <div class="flex flex-col gap-1.5">',
			'      <span class="block text-sm leading-5 text-gray-700 font-medium after:content-[\'_*\'] after:text-red-600">Work From Date</span>',
			'      <input type="date" id="comp-leave-from-date" class="w-full px-3 py-2 text-sm bg-white text-gray-800 border border-gray-300 rounded-md focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none transition" />',
			'    </div>',

			'    <!-- Work End Date Field -->',
			'    <div class="flex flex-col gap-1.5">',
			'      <span class="block text-sm leading-5 text-gray-700 font-medium after:content-[\'_*\'] after:text-red-600">Work End Date</span>',
			'      <input type="date" id="comp-leave-to-date" class="w-full px-3 py-2 text-sm bg-white text-gray-800 border border-gray-300 rounded-md focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none transition" />',
			'      <span id="comp-leave-date-error" class="text-xs text-red-600 font-normal hidden mt-0.5">To Date cannot be before From Date</span>',
			'    </div>',

			'    <!-- Half Day Checkbox -->',
			'    <div class="flex flex-col gap-2 pt-1">',
			'      <label class="inline-flex items-center gap-2 cursor-pointer select-none">',
			'        <input type="checkbox" id="comp-leave-half-day" class="w-4 h-4 text-gray-900 rounded border-gray-300 focus:ring-gray-900 cursor-pointer" />',
			'        <span class="text-sm text-gray-700 font-medium">Half Day</span>',
			'      </label>',
			'      <div id="comp-leave-half-day-container" class="hidden flex-col gap-1.5 pl-6 mt-1">',
			'        <span class="block text-sm leading-5 text-gray-700 font-medium after:content-[\'_*\'] after:text-red-600">Half Day Date</span>',
			'        <input type="date" id="comp-leave-half-day-date" class="w-full px-3 py-2 text-sm bg-white text-gray-800 border border-gray-300 rounded-md focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none transition" />',
			'      </div>',
			'    </div>',

			'    <!-- Reason Field -->',
			'    <div class="flex flex-col gap-1.5">',
			'      <span class="block text-sm leading-5 text-gray-700 font-medium after:content-[\'_*\'] after:text-red-600">Reason</span>',
			'      <textarea id="comp-leave-reason" rows="3" placeholder="Enter Reason" class="w-full px-3 py-2 text-sm bg-white text-gray-800 border border-gray-300 rounded-md focus:border-gray-900 focus:ring-1 focus:ring-gray-900 outline-none transition resize-none"></textarea>',
			'    </div>',
			'  </div>',

			'  <!-- Sticky Bottom Action Bar -->',
			'  <div class="px-4 pt-4 pb-4 standalone:pb-safe-bottom sm:w-96 bg-white sticky bottom-0 w-full drop-shadow-xl z-40 border-t border-gray-200">',
			'    <div id="comp-leave-form-error" class="hidden mb-3 p-3 bg-red-50 text-red-700 text-xs font-medium rounded-md border border-red-200"></div>',
			'    <button id="comp-leave-save-btn" type="button" class="w-full rounded py-4 text-base font-medium bg-gray-900 text-white hover:bg-gray-800 active:scale-[0.99] transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-2">',
			'      <span id="comp-leave-btn-label">Save</span>',
			'    </button>',
			'  </div>',
			'</div>',
		].join("\n");

		page.innerHTML = html;
	}

	function attachPageEventListeners(page) {
		var backBtn = page.querySelector("#comp-leave-back-btn");
		if (backBtn) {
			backBtn.addEventListener("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				closeCompensatoryLeavePage();
			});
		}

		var fromDateInput = page.querySelector("#comp-leave-from-date");
		var toDateInput = page.querySelector("#comp-leave-to-date");
		var halfDayCheckbox = page.querySelector("#comp-leave-half-day");
		var halfDayContainer = page.querySelector("#comp-leave-half-day-container");
		var halfDayDateInput = page.querySelector("#comp-leave-half-day-date");
		var saveBtn = page.querySelector("#comp-leave-save-btn");

		if (fromDateInput) {
			fromDateInput.addEventListener("change", function () {
				if (!toDateInput.value || toDateInput.getAttribute("data-auto-synced") === "true") {
					toDateInput.value = fromDateInput.value;
					toDateInput.setAttribute("data-auto-synced", "true");
				}
				validateDateRange();
				updateHalfDayDateRange();
			});
		}

		if (toDateInput) {
			toDateInput.addEventListener("change", function () {
				toDateInput.removeAttribute("data-auto-synced");
				validateDateRange();
				updateHalfDayDateRange();
			});
		}

		if (halfDayCheckbox) {
			halfDayCheckbox.addEventListener("change", function () {
				if (halfDayCheckbox.checked) {
					halfDayContainer.classList.remove("hidden");
					halfDayContainer.classList.add("flex");
					updateHalfDayDateRange();
				} else {
					halfDayContainer.classList.add("hidden");
					halfDayContainer.classList.remove("flex");
				}
			});
		}

		if (saveBtn) {
			saveBtn.addEventListener("click", function (e) {
				e.preventDefault();
				handleFormSubmit();
			});
		}
	}

	function validateDateRange() {
		var fromDateInput = document.getElementById("comp-leave-from-date");
		var toDateInput = document.getElementById("comp-leave-to-date");
		var dateError = document.getElementById("comp-leave-date-error");

		if (!fromDateInput || !toDateInput || !dateError) return true;

		var fromDate = fromDateInput.value;
		var toDate = toDateInput.value;

		if (fromDate && toDate && fromDate > toDate) {
			dateError.classList.remove("hidden");
			toDateInput.classList.add("border-red-500");
			toDateInput.classList.remove("border-gray-300");
			return false;
		} else {
			dateError.classList.add("hidden");
			toDateInput.classList.remove("border-red-500");
			toDateInput.classList.add("border-gray-300");
			return true;
		}
	}

	function updateHalfDayDateRange() {
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

		isSubmitting = true;
		if (saveBtn) saveBtn.disabled = true;
		if (btnLabel) btnLabel.textContent = "Saving...";

		var payload = {
			doc: {
				doctype: "Compensatory Leave Request",
				employee: sessionEmployee.name,
				leave_type: "Compensatory Off",
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

	// 5. Watch for hash / popstate changes
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
			if (target && target.closest && target.closest("#compensatory-leave-page-container")) {
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

	scheduleScan();
	setInterval(scheduleScan, 1000);
})();