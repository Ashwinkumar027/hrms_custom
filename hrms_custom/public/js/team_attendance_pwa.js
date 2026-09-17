// Team Attendance PWA Extension
(function () {
	var isManager = null;
	var isManagerCheckPending = false;
	var activeDate = null; // YYYY-MM-DD
	var activeFilter = "ALL"; // 'ALL' | 'Not Yet In' | 'Late Arrivals' | 'On Time'
	var attendanceData = null;
	var isLoading = false;
	var loadError = null;

	function formatDate(d) {
		var year = d.getFullYear();
		var month = ("0" + (d.getMonth() + 1)).slice(-2);
		var day = ("0" + d.getDate()).slice(-2);
		return year + "-" + month + "-" + day;
	}

	function formatDisplayDate(dateStr) {
		if (!dateStr) return "";
		var parts = dateStr.split("-");
		var year = parseInt(parts[0], 10);
		var month = parseInt(parts[1], 10) - 1;
		var day = parseInt(parts[2], 10);
		var d = new Date(year, month, day);
		var days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
		var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
		return days[d.getDay()] + ", " + day + " " + months[month] + " " + year;
	}

	activeDate = formatDate(new Date());

	// 1. Check if user is a manager
	function checkManagerStatus(callback) {
		if (isManager !== null) {
			if (callback) callback(isManager);
			return;
		}
		if (isManagerCheckPending) return;
		isManagerCheckPending = true;

		var csrf = window.csrf_token || (window.frappe && window.frappe.csrf_token) || "";

		fetch("/api/method/hrms_custom.api.team_attendance.is_team_manager", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": csrf,
			},
		})
			.then(function (res) {
				if (!res.ok) {
					throw new Error("HTTP " + res.status);
				}
				return res.json();
			})
			.then(function (data) {
				isManagerCheckPending = false;
				if (data && (data.exc || data.exc_type)) {
					// Transient session or auth error, allow retry
					return;
				}
				isManager = Boolean(data && data.message);
				if (callback) callback(isManager);
				if (isManager) {
					ensureQuickLink();
				}
			})
			.catch(function (err) {
				isManagerCheckPending = false;
				// Do NOT latch isManager = false on transient error/CSRF race, allow retry on next scan
				console.warn("[Team Attendance PWA] Manager check error, will retry on next tick:", err);
			});
	}

	// 2. Fetch attendance data
	function fetchAttendanceData(dateStr, callback) {
		isLoading = true;
		loadError = null;
		renderPageContent();

		fetch("/api/method/hrms_custom.api.team_attendance.get_team_attendance_status", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
			body: JSON.stringify({ date: dateStr }),
		})
			.then(function (res) {
				return res.json();
			})
			.then(function (data) {
				isLoading = false;
				if (data && data.message) {
					attendanceData = data.message;
					loadError = null;
					// Pick initial filter based on available counts
					if (activeFilter === "ALL") {
						if (attendanceData.counts && attendanceData.counts.not_yet_in > 0) {
							activeFilter = "Not Yet In";
						} else if (attendanceData.counts && attendanceData.counts.late_in > 0) {
							activeFilter = "Late Arrivals";
						} else if (attendanceData.counts && attendanceData.counts.on_time > 0) {
							activeFilter = "On Time";
						}
					}
				} else {
					loadError = "Failed to load team attendance.";
				}
				renderPageContent();
				if (callback) callback();
			})
			.catch(function () {
				isLoading = false;
				loadError = "Failed to connect to server.";
				renderPageContent();
			});
	}

	// 3. Inject Quick Links Entry
	function ensureQuickLink() {
		if (!isManager) return;
		if (document.getElementById("quick-link-team-attendance")) return;

		var headers = document.querySelectorAll("div, h2, h3, span");
		var quickLinksHeader = null;
		for (var i = 0; i < headers.length; i++) {
			if ((headers[i].textContent || "").trim() === "Quick Links") {
				quickLinksHeader = headers[i];
				break;
			}
		}

		var quickLinksBox = null;
		if (quickLinksHeader) {
			var nextEl = quickLinksHeader.nextElementSibling;
			if (nextEl && nextEl.classList.contains("bg-white")) {
				quickLinksBox = nextEl;
			} else if (quickLinksHeader.parentElement) {
				quickLinksBox = quickLinksHeader.parentElement.querySelector(".bg-white.rounded") || nextEl;
			}
		}

		// Fallback: look for other quick link items in DOM
		if (!quickLinksBox) {
			var siblingLink = document.querySelector("#quick-link-compensatory-leave") || document.querySelector('a[href*="attendance-requests"]');
			if (siblingLink && siblingLink.parentElement) {
				quickLinksBox = siblingLink.parentElement;
			}
		}

		if (!quickLinksBox) {
			if (quickLinksHeader) {
				console.warn("[Team Attendance PWA] Quick Links container could not be resolved from header", quickLinksHeader);
			}
			return;
		}

		var item = document.createElement("div");
		item.id = "quick-link-team-attendance";
		item.className = "flex flex-row flex-start p-4 items-center justify-between border-b cursor-pointer transition-colors hover:bg-gray-50 active:bg-gray-100";

		item.innerHTML = [
			'<div class="flex flex-row items-center gap-3 grow pointer-events-none">',
			'  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-gray-500">',
			'    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />',
			'    <circle cx="9" cy="8" r="4" />',
			'    <path d="M22 21v-2a4 4 0 0 0-3-3.87" />',
			'    <path d="M16 3.13a4 4 0 0 1 0 7.75" />',
			'  </svg>',
			'  <div class="text-base font-normal text-gray-800">Team Attendance</div>',
			'</div>',
			'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-gray-500 pointer-events-none">',
			'  <polyline points="9 18 15 12 9 6"></polyline>',
			'</svg>',
		].join("\n");

		item.addEventListener("click", function (e) {
			e.preventDefault();
			e.stopPropagation();
			window.location.hash = "team-attendance";
			openTeamAttendancePage();
		});

		if (quickLinksBox.firstChild) {
			quickLinksBox.insertBefore(item, quickLinksBox.firstChild);
		} else {
			quickLinksBox.appendChild(item);
		}
	}

	// 4. Team Attendance Page View Container & Event Delegation
	function getOrCreatePage() {
		var page = document.getElementById("team-attendance-page-container");
		if (!page) {
			page = document.createElement("div");
			page.id = "team-attendance-page-container";
			page.style.cssText = "position: fixed; inset: 0; z-index: 99999; background: #f8fafc; overflow-y: auto; -webkit-overflow-scrolling: touch; display: none; flex-direction: column; align-items: center; pointer-events: auto;";
			document.body.appendChild(page);

			// Robust event delegation attached ONCE to the container
			page.addEventListener("click", function (e) {
				// 1. Back button
				var backBtn = e.target.closest("#team-att-back-btn");
				if (backBtn) {
					e.preventDefault();
					e.stopPropagation();
					closeTeamAttendancePage();
					return;
				}

				// 2. Date Trigger
				var dateTrigger = e.target.closest("#team-att-date-trigger");
				if (dateTrigger) {
					e.preventDefault();
					e.stopPropagation();
					openCalendarModal();
					return;
				}

				// 3. Not Yet In Filter Card
				var notYetCard = e.target.closest("#card-filter-not-yet-in");
				if (notYetCard) {
					e.preventDefault();
					e.stopPropagation();
					activeFilter = (activeFilter === "Not Yet In") ? "ALL" : "Not Yet In";
					renderPageContent();
					return;
				}

				// 4. Late Arrivals Filter Card
				var lateCard = e.target.closest("#card-filter-late-in");
				if (lateCard) {
					e.preventDefault();
					e.stopPropagation();
					activeFilter = (activeFilter === "Late Arrivals") ? "ALL" : "Late Arrivals";
					renderPageContent();
					return;
				}

				// 5. On Time Filter Card
				var onTimeCard = e.target.closest("#card-filter-on-time");
				if (onTimeCard) {
					e.preventDefault();
					e.stopPropagation();
					activeFilter = (activeFilter === "On Time") ? "ALL" : "On Time";
					renderPageContent();
					return;
				}

				// 6. Reset / Show All Filter Button
				var resetBtn = e.target.closest("#team-att-reset-filter");
				if (resetBtn) {
					e.preventDefault();
					e.stopPropagation();
					activeFilter = "ALL";
					renderPageContent();
					return;
				}

				// 7. Retry Button
				var retryBtn = e.target.closest("#team-att-retry-btn");
				if (retryBtn) {
					e.preventDefault();
					e.stopPropagation();
					fetchAttendanceData(activeDate);
					return;
				}
			});
		}
		return page;
	}

	function openTeamAttendancePage() {
		var page = getOrCreatePage();
		page.style.display = "flex";
		document.body.style.overflow = "hidden";

		if (!attendanceData || attendanceData.date !== activeDate) {
			fetchAttendanceData(activeDate);
		} else {
			renderPageContent();
		}
	}

	function closeTeamAttendancePage() {
		var page = document.getElementById("team-attendance-page-container");
		if (page) {
			page.style.display = "none";
		}
		document.body.style.overflow = "";
		if (window.location.hash === "#team-attendance") {
			if (window.history.length > 1) {
				window.history.back();
			} else {
				window.location.hash = "";
			}
		}
	}

	// 5. Render Page Content
	function renderPageContent() {
		var page = document.getElementById("team-attendance-page-container");
		if (!page || page.style.display === "none") return;

		var counts = (attendanceData && attendanceData.counts) || { not_yet_in: 0, late_in: 0, on_time: 0, total: 0 };
		var allEmployees = (attendanceData && attendanceData.employees) || [];

		// Filter employees
		var filtered = allEmployees;
		if (activeFilter === "Not Yet In") {
			filtered = allEmployees.filter(function (e) { return e.category === "Not Yet In"; });
		} else if (activeFilter === "Late Arrivals") {
			filtered = allEmployees.filter(function (e) { return e.category === "Late In"; });
		} else if (activeFilter === "On Time") {
			filtered = allEmployees.filter(function (e) { return e.category === "On Time"; });
		}

		var dateLabel = formatDisplayDate(activeDate);

		var html = [
			'<div class="w-full max-w-md min-h-screen px-4 py-4 pb-20 flex flex-col box-border">',
			'  <!-- Header Bar -->',
			'  <div class="flex items-center justify-between py-2 mb-2">',
			'    <button id="team-att-back-btn" class="p-2 -ml-2 text-gray-700 hover:text-gray-900 rounded-full hover:bg-gray-200/60 active:scale-95 transition cursor-pointer">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pointer-events-none">',
			'        <polyline points="15 18 9 12 15 6"></polyline>',
			'      </svg>',
			'    </button>',
			'    <h1 class="text-lg font-bold text-gray-900 grow text-center pr-6">Team Attendance</h1>',
			'  </div>',

			'  <!-- Date Selector Field -->',
			'  <div id="team-att-date-trigger" class="flex items-center justify-between p-3.5 bg-white rounded-xl border border-gray-200 shadow-sm cursor-pointer mb-3 hover:border-gray-300 active:bg-gray-50 transition">',
			'    <div class="flex items-center gap-3 pointer-events-none">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-500">',
			'        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>',
			'        <line x1="16" y1="2" x2="16" y2="6"></line>',
			'        <line x1="8" y1="2" x2="8" y2="6"></line>',
			'        <line x1="3" y1="10" x2="21" y2="10"></line>',
			'      </svg>',
			'      <span class="text-sm font-semibold text-gray-800">' + dateLabel + '</span>',
			'    </div>',
			'    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-gray-400 pointer-events-none">',
			'      <polyline points="6 9 12 15 18 9"></polyline>',
			'    </svg>',
			'  </div>',

			'  <!-- 3 Filter Cards -->',
			'  <div class="grid grid-cols-3 gap-2.5 my-2">',
			'    <!-- Not Yet In Card -->',
			'    <div id="card-filter-not-yet-in" class="p-3 bg-white rounded-xl border cursor-pointer transition active:scale-95 flex flex-col items-center justify-center text-center ' +
				(activeFilter === "Not Yet In" ? "border-gray-900 shadow ring-1 ring-gray-900" : "border-gray-200 shadow-sm hover:border-gray-300") +
				'">',
			'      <span class="text-2xl font-extrabold text-gray-900 pointer-events-none">' + counts.not_yet_in + '</span>',
			'      <span class="text-xs font-semibold text-gray-600 mt-1 pointer-events-none">Not Yet In</span>',
			'    </div>',
			'    <!-- Late Arrivals Card -->',
			'    <div id="card-filter-late-in" class="p-3 bg-white rounded-xl border cursor-pointer transition active:scale-95 flex flex-col items-center justify-center text-center ' +
				(activeFilter === "Late Arrivals" ? "border-gray-900 shadow ring-1 ring-gray-900" : "border-gray-200 shadow-sm hover:border-gray-300") +
				'">',
			'      <span class="text-2xl font-extrabold ' + (counts.late_in > 0 ? "text-amber-600" : "text-gray-900") + ' pointer-events-none">' + counts.late_in + '</span>',
			'      <span class="text-xs font-semibold text-gray-600 mt-1 pointer-events-none">Late Arrivals</span>',
			'    </div>',
			'    <!-- On Time Card -->',
			'    <div id="card-filter-on-time" class="p-3 bg-white rounded-xl border cursor-pointer transition active:scale-95 flex flex-col items-center justify-center text-center ' +
				(activeFilter === "On Time" ? "border-gray-900 shadow ring-1 ring-gray-900" : "border-gray-200 shadow-sm hover:border-gray-300") +
				'">',
			'      <span class="text-2xl font-extrabold ' + (counts.on_time > 0 ? "text-emerald-600" : "text-gray-900") + ' pointer-events-none">' + counts.on_time + '</span>',
			'      <span class="text-xs font-semibold text-gray-600 mt-1 pointer-events-none">On Time</span>',
			'    </div>',
			'  </div>',

			'  <!-- Section Header -->',
			'  <div class="flex items-center justify-between mt-5 mb-2 px-1">',
			'    <span class="text-xs font-bold uppercase tracking-wider text-gray-500">' + (activeFilter === "ALL" ? "All Team Members" : activeFilter) + ' (' + filtered.length + ')</span>',
			'    ' + (activeFilter !== "ALL" ? '<button id="team-att-reset-filter" class="text-xs text-blue-600 hover:text-blue-700 font-medium cursor-pointer">Show All</button>' : '') + '',
			'  </div>',

			'  <!-- Content Body -->',
		];

		if (isLoading) {
			html.push(
				'  <div class="flex flex-col items-center justify-center py-16 text-gray-500">',
				'    <svg class="animate-spin h-8 w-8 text-gray-600 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">',
				'      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>',
				'      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>',
				'    </svg>',
				'    <span class="text-sm font-medium">Loading attendance data...</span>',
				'  </div>'
			);
		} else if (loadError) {
			html.push(
				'  <div class="flex flex-col items-center justify-center py-12 px-4 bg-white rounded-xl border border-red-100 my-2 text-center">',
				'    <p class="text-sm text-red-600 font-medium mb-3">' + loadError + '</p>',
				'    <button id="team-att-retry-btn" class="px-4 py-2 bg-gray-900 text-white text-xs font-semibold rounded-lg cursor-pointer">Retry</button>',
				'  </div>'
			);
		} else if (filtered.length === 0) {
			html.push(
				'  <div class="flex flex-col items-center justify-center py-16 px-4 bg-white rounded-xl border border-gray-100 my-2 text-center">',
				'    <div class="w-12 h-12 rounded-full bg-gray-50 flex items-center justify-center text-gray-400 mb-3">',
				'      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">',
				'        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />',
				'        <circle cx="9" cy="7" r="4" />',
				'        <line x1="17" y1="8" x2="23" y2="14" />',
				'        <line x1="23" y1="8" x2="17" y2="14" />',
				'      </svg>',
				'    </div>',
				'    <span class="text-sm font-semibold text-gray-800 mb-1">No employees found</span>',
				'    <span class="text-xs text-gray-500">None in this category for the selected date.</span>',
				'  </div>'
			);
		} else {
			html.push('  <div class="flex flex-col gap-2.5">');
			for (var j = 0; j < filtered.length; j++) {
				var emp = filtered[j];
				var initials = (emp.employee_name || "E")
					.split(" ")
					.map(function (n) { return n[0]; })
					.slice(0, 2)
					.join("")
					.toUpperCase();

				var avatarHtml = emp.image
					? '<img src="' + emp.image + '" alt="' + emp.employee_name + '" class="w-10 h-10 rounded-full object-cover border border-gray-100 shrink-0" />'
					: '<div class="w-10 h-10 rounded-full bg-slate-100 text-slate-700 font-bold text-xs flex items-center justify-center shrink-0 border border-slate-200">' + initials + '</div>';

				var badgeHtml = "";
				if (emp.category === "On Time") {
					var onTimeText = emp.checkin_time ? ("Checked in: " + emp.checkin_time) : (emp.time_detail || "On Time");
					badgeHtml = '<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">' + onTimeText + '</span>';
				} else if (emp.category === "Late In") {
					badgeHtml = '<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">Late: ' + (emp.late_by || "") + ' (' + (emp.checkin_time || "") + ')</span>';
				} else {
					badgeHtml = '<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">Expected: ' + (emp.expected_time || emp.time_detail) + '</span>';
				}

				html.push(
					'    <div class="flex items-center justify-between p-3.5 bg-white rounded-xl border border-gray-100 shadow-sm gap-3">',
					'      <div class="flex items-center gap-3 min-w-0 grow">',
					'        ' + avatarHtml,
					'        <div class="flex flex-col min-w-0">',
					'          <span class="text-sm font-semibold text-gray-900 truncate">' + emp.employee_name + '</span>',
					'          <span class="text-xs text-gray-500 font-mono">' + emp.employee + '</span>',
					'        </div>',
					'      </div>',
					'      <div class="shrink-0">',
					'        ' + badgeHtml,
					'      </div>',
					'    </div>'
				);
			}
			html.push('  </div>');
		}

		html.push('</div>');

		page.innerHTML = html.join("\n");
	}

	// 6. Calendar Modal with month navigation and Cancel/Apply buttons
	var calViewYear = 2026;
	var calViewMonth = 8; // 0-indexed (8 = September)
	var calSelectedDate = null; // YYYY-MM-DD

	function getOrCreateCalendarModal() {
		var modal = document.getElementById("team-att-calendar-modal");
		if (!modal) {
			modal = document.createElement("div");
			modal.id = "team-att-calendar-modal";
			modal.style.cssText = "position: fixed; inset: 0; z-index: 100000; background: rgba(0,0,0,0.4); display: none; align-items: center; justify-content: center; padding: 16px; pointer-events: auto;";
			document.body.appendChild(modal);

			// Robust event delegation attached ONCE to the calendar modal
			modal.addEventListener("click", function (e) {
				// Click backdrop to dismiss
				if (e.target === modal) {
					closeCalendarModal();
					return;
				}

				// Prev Month
				var prevBtn = e.target.closest("#cal-prev-month");
				if (prevBtn) {
					e.preventDefault();
					e.stopPropagation();
					calViewMonth--;
					if (calViewMonth < 0) {
						calViewMonth = 11;
						calViewYear--;
					}
					renderCalendarModalContent();
					return;
				}

				// Next Month
				var nextBtn = e.target.closest("#cal-next-month");
				if (nextBtn) {
					e.preventDefault();
					e.stopPropagation();
					calViewMonth++;
					if (calViewMonth > 11) {
						calViewMonth = 0;
						calViewYear++;
					}
					renderCalendarModalContent();
					return;
				}

				// Day Cell
				var dayCell = e.target.closest(".cal-day-cell");
				if (dayCell) {
					e.preventDefault();
					e.stopPropagation();
					calSelectedDate = dayCell.getAttribute("data-date");
					renderCalendarModalContent();
					return;
				}

				// Cancel Button
				var cancelBtn = e.target.closest("#cal-cancel-btn");
				if (cancelBtn) {
					e.preventDefault();
					e.stopPropagation();
					closeCalendarModal();
					return;
				}

				// Apply Button
				var applyBtn = e.target.closest("#cal-apply-btn");
				if (applyBtn) {
					e.preventDefault();
					e.stopPropagation();
					activeDate = calSelectedDate;
					closeCalendarModal();
					fetchAttendanceData(activeDate);
					return;
				}
			});
		}
		return modal;
	}

	function openCalendarModal() {
		var parts = activeDate.split("-");
		calViewYear = parseInt(parts[0], 10);
		calViewMonth = parseInt(parts[1], 10) - 1;
		calSelectedDate = activeDate;

		var modal = getOrCreateCalendarModal();
		modal.style.display = "flex";
		renderCalendarModalContent();
	}

	function closeCalendarModal() {
		var modal = document.getElementById("team-att-calendar-modal");
		if (modal) modal.style.display = "none";
	}

	function renderCalendarModalContent() {
		var modal = document.getElementById("team-att-calendar-modal");
		if (!modal || modal.style.display === "none") return;

		var months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
		var monthName = months[calViewMonth] + " " + calViewYear;

		var firstDayOfWeek = new Date(calViewYear, calViewMonth, 1).getDay();
		var daysInMonth = new Date(calViewYear, calViewMonth + 1, 0).getDate();

		var html = [
			'<div class="bg-white rounded-2xl w-full max-w-sm shadow-2xl p-5 flex flex-col box-border animate-in fade-in zoom-in-95 duration-150">',
			'  <!-- Month Navigation -->',
			'  <div class="flex items-center justify-between mb-4">',
			'    <button id="cal-prev-month" class="p-2 text-gray-600 hover:text-gray-900 rounded-full hover:bg-gray-100 active:scale-95 transition cursor-pointer">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pointer-events-none">',
			'        <polyline points="15 18 9 12 15 6"></polyline>',
			'      </svg>',
			'    </button>',
			'    <span class="text-base font-bold text-gray-800">' + monthName + '</span>',
			'    <button id="cal-next-month" class="p-2 text-gray-600 hover:text-gray-900 rounded-full hover:bg-gray-100 active:scale-95 transition cursor-pointer">',
			'      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pointer-events-none">',
			'        <polyline points="9 18 15 12 9 6"></polyline>',
			'      </svg>',
			'    </button>',
			'  </div>',

			'  <!-- Day of Week Headers -->',
			'  <div class="grid grid-cols-7 gap-1 text-center mb-2">',
			'    <span class="text-xs font-bold text-gray-400">Su</span>',
			'    <span class="text-xs font-bold text-gray-400">Mo</span>',
			'    <span class="text-xs font-bold text-gray-400">Tu</span>',
			'    <span class="text-xs font-bold text-gray-400">We</span>',
			'    <span class="text-xs font-bold text-gray-400">Th</span>',
			'    <span class="text-xs font-bold text-gray-400">Fr</span>',
			'    <span class="text-xs font-bold text-gray-400">Sa</span>',
			'  </div>',

			'  <!-- Calendar Grid -->',
			'  <div class="grid grid-cols-7 gap-1 text-center mb-5">',
		];

		// Blank cells for days before month start
		for (var b = 0; b < firstDayOfWeek; b++) {
			html.push('    <div></div>');
		}

		for (var day = 1; day <= daysInMonth; day++) {
			var mStr = ("0" + (calViewMonth + 1)).slice(-2);
			var dStr = ("0" + day).slice(-2);
			var cellDate = calViewYear + "-" + mStr + "-" + dStr;
			var isSelected = (cellDate === calSelectedDate);

			var cellClass = isSelected
				? "bg-gray-900 text-white font-bold rounded-full shadow"
				: "text-gray-700 hover:bg-gray-100 font-medium rounded-full cursor-pointer";

			html.push(
				'    <button class="cal-day-cell h-9 w-9 mx-auto flex items-center justify-center text-sm transition active:scale-95 ' + cellClass + '" data-date="' + cellDate + '">',
				'      ' + day,
				'    </button>'
			);
		}

		html.push(
			'  </div>',
			'  <!-- Footer Buttons -->',
			'  <div class="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">',
			'    <button id="cal-cancel-btn" class="px-4 py-2 text-sm font-semibold text-gray-600 hover:text-gray-800 rounded-lg hover:bg-gray-100 transition cursor-pointer">Cancel</button>',
			'    <button id="cal-apply-btn" class="px-5 py-2 text-sm font-semibold text-white bg-gray-900 hover:bg-gray-800 rounded-lg shadow-sm active:scale-95 transition cursor-pointer">Apply</button>',
			'  </div>',
			'</div>'
		);

		modal.innerHTML = html.join("\n");
	}

	// 7. Watch for page navigation & hash changes
	window.addEventListener("hashchange", function () {
		if (window.location.hash === "#team-attendance") {
			openTeamAttendancePage();
		} else {
			var page = document.getElementById("team-attendance-page-container");
			if (page && page.style.display !== "none") {
				page.style.display = "none";
				document.body.style.overflow = "";
			}
		}
	});

	window.addEventListener("popstate", function () {
		if (window.location.hash !== "#team-attendance") {
			var page = document.getElementById("team-attendance-page-container");
			if (page && page.style.display !== "none") {
				page.style.display = "none";
				document.body.style.overflow = "";
			}
		}
	});

	function scan() {
		checkManagerStatus(function (isMgr) {
			if (isMgr) {
				ensureQuickLink();
				if (window.location.hash === "#team-attendance") {
					var page = document.getElementById("team-attendance-page-container");
					if (!page || page.style.display === "none") {
						openTeamAttendancePage();
					}
				}
			}
		});
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
		// Ignore any mutations occurring inside our own containers to prevent re-render loops
		var hasExternalMutation = false;
		for (var i = 0; i < mutations.length; i++) {
			var target = mutations[i].target;
			if (target && target.closest && (target.closest("#team-attendance-page-container") || target.closest("#team-att-calendar-modal"))) {
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

	// Initial scan
	scheduleScan();
	setInterval(scheduleScan, 1000);
})();
