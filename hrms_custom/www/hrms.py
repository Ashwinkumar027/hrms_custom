import frappe
from hrms.www.hrms import get_context as stock_get_context

no_cache = 1

HIDE_CSS = """
<style>
a[href^="/hrms/shift-requests"],
a[href^="/hrms/employee-advances"] { display: none !important; }

@media (min-width: 640px) {
    .sm\\:w-96 {
        margin-left: auto !important;
        margin-right: auto !important;
    }
}
</style>
"""

# JINJA WARNING: GATE_JS is spliced into the stock HTML and the whole page
# is then passed through frappe.render_template() (Jinja). No two closing
# braces are currently adjacent, so nothing here parses as a Jinja
# expression — but any future edit that produces "}}" (e.g. reformatting
# nested blocks) will be interpreted by Jinja and can break the page.
# Watch for that when editing this block.
#
# FRAGILITY: this gates on stock HRMS UI text ("Latitude" in the coordinate
# span, "Unable to retrieve your location" for the geolocation-error state,
# "Confirm Check" in the button label). If a future hrms/Frappe HR upgrade
# changes any of that wording or adds translations, the corresponding match
# silently stops firing. For "Latitude" or "Confirm Check" this fails closed
# (safe) — the confirm button stays disabled forever. For the error string,
# it degrades rather than breaks: the error branch just never fires and the
# button falls through to the generic "Fetching your location…" state
# instead of the more specific enable-location message. Re-check this block
# after any hrms app upgrade.
GATE_JS = """
<script>
(function () {
	var ORIGINAL_LABEL_ATTR = "data-gate-original-label";
	var FETCHING_LABEL = "Fetching your location\\u2026";
	var pending = null;

	function findCoordSpans() {
		return document.querySelectorAll("span.font-medium.text-gray-500.text-sm");
	}

	function findConfirmButtons() {
		// Match on label text OR on our own tag: once applyGate() overwrites
		// the label node with FETCHING_LABEL, "Confirm Check" no longer
		// appears anywhere under the button, so the tag is what keeps a
		// gated button findable on the next pass (otherwise it can never be
		// re-enabled once coordinates resolve).
		var buttons = document.querySelectorAll("button");
		var matches = [];
		for (var i = 0; i < buttons.length; i++) {
			var btn = buttons[i];
			var hasConfirmLabel = btn.textContent && btn.textContent.indexOf("Confirm Check") !== -1;
			if (hasConfirmLabel || btn.hasAttribute(ORIGINAL_LABEL_ATTR)) {
				matches.push(btn);
			}
		}
		return matches;
	}

	// Vue owns the button's child vnodes. Writing btn.textContent replaces
	// that whole subtree with a bare text node, which fights Vue's own
	// re-renders. Instead descend to the innermost element that actually
	// carries the label text (skipping empty icon-only siblings) and write
	// only there.
	function findLabelNode(el) {
		var textChildren = [];
		for (var i = 0; i < el.children.length; i++) {
			var child = el.children[i];
			if (child.textContent && child.textContent.trim().length > 0) {
				textChildren.push(child);
			}
		}
		if (textChildren.length === 1) {
			return findLabelNode(textChildren[0]);
		}
		return el;
	}

	// Three states share the same span (span.font-medium.text-gray-500.text-sm),
	// distinguished only by text. "resolved" takes priority over "error" in
	// case both substrings somehow co-occur; anything unrecognised (including
	// the literal "Locating...") falls into "locating".
	function findGeoState() {
		var spans = findCoordSpans();
		for (var i = 0; i < spans.length; i++) {
			var text = spans[i].textContent || "";
			if (text.indexOf("Latitude") !== -1) {
				return "resolved";
			}
		}
		for (var i = 0; i < spans.length; i++) {
			var text = spans[i].textContent || "";
			if (text.indexOf("Unable to retrieve your location") !== -1) {
				return "error";
			}
		}
		return "locating";
	}

	function errorLabelFor(original) {
		if (original.indexOf("Check In") !== -1) {
			return "Enable location to check in";
		}
		if (original.indexOf("Check Out") !== -1) {
			return "Enable location to check out";
		}
		return "Enable location access";
	}

	function applyGate() {
		var state = findGeoState();

		var buttons = findConfirmButtons();
		for (var j = 0; j < buttons.length; j++) {
			var btn = buttons[j];
			var labelNode = findLabelNode(btn);

			// findLabelNode() falls back to the button itself when it can't
			// find a single text-bearing child element (label not yet
			// rendered, or a bare text node). Writing to the button in that
			// case is exactly the subtree-destroying write we're avoiding —
			// skip until the label has its own node to write into.
			if (labelNode === btn) {
				continue;
			}

			if (!btn.hasAttribute(ORIGINAL_LABEL_ATTR)) {
				// Only capture once the real label is visible. A pass that
				// lands before Vue has populated the text would otherwise
				// permanently store "" and later restore a blank button.
				var seen = labelNode.textContent || "";
				if (seen.indexOf("Confirm Check") !== -1) {
					btn.setAttribute(ORIGINAL_LABEL_ATTR, seen);
				} else {
					continue;
				}
			}
			var original = btn.getAttribute(ORIGINAL_LABEL_ATTR);

			if (state === "resolved") {
				if (btn.disabled) btn.disabled = false;
				if (labelNode.textContent !== original) labelNode.textContent = original;
			} else if (state === "error") {
				if (!btn.disabled) btn.disabled = true;
				var errorLabel = errorLabelFor(original);
				if (labelNode.textContent !== errorLabel) labelNode.textContent = errorLabel;
			} else {
				if (!btn.disabled) btn.disabled = true;
				if (labelNode.textContent !== FETCHING_LABEL) labelNode.textContent = FETCHING_LABEL;
			}
		}
	}

	function scheduleApply() {
		if (pending) return;
		pending = requestAnimationFrame(function () {
			pending = null;
			applyGate();
		});
	}

	var observer = new MutationObserver(scheduleApply);
	observer.observe(document.body, {
		subtree: true,
		childList: true,
		characterData: true
	});

	scheduleApply();
})();
</script>
"""


# The PWA's own onError() handlers discard the real server error and show a
# generic toast instead, even though the failing response carries the real
# message in `_server_messages` (frappe-ui itself parses this into
# `error.messages` internally, but the callbacks below don't accept the
# error argument, so it's read and then thrown away). We can't touch
# apps/hrms, so this patches around it from outside: wrap window.fetch to
# capture the real message from any failed request, then watch for a
# generic toast's text node and swap it in before it renders. Two
# components generate these generic toasts with different wording:
#   - FormView.vue (save/submit/cancel/delete on the detail form):
#     "Error creating/updating/deleting {doctype}"
#   - RequestActionSheet.vue (Approve/Reject/Submit/Cancel from the "My
#     Requests" action sheet, via getFailureMessage()): "Approval failed!",
#     "Rejection failed!", "Document submission failed!", "Document
#     cancellation failed!"
#
# FRAGILITY: matches toast text against the literal strings/prefixes each
# component currently generates. If a future hrms upgrade rewords either
# toast, matching for that one stops firing and the generic message is
# shown as before (fails closed, no breakage) — re-check after any hrms
# app upgrade, same as GATE_JS above.
#
# LIMITATION: the captured message is a single global "last error", keyed
# only by response failure + a short TTL, not by request. Concurrent
# in-flight requests (e.g. a failing save racing a parallel attachment
# upload) could in theory attribute the wrong message to a toast. Accepted
# as a low-probability edge case for a lightweight, non-invasive patch.
ERROR_TOAST_JS = """
<script>
(function () {
	var GENERIC_TOAST_PREFIX = /^Error (creating|updating|deleting) /;
	var GENERIC_TOAST_EXACT = [
		"Approval failed!",
		"Rejection failed!",
		"Document submission failed!",
		"Document cancellation failed!",
	];
	var MESSAGE_TTL_MS = 5000;
	var lastServerMessage = null;
	var lastServerMessageAt = 0;

	function isGenericToast(text) {
		if (GENERIC_TOAST_PREFIX.test(text)) return true;
		return GENERIC_TOAST_EXACT.indexOf(text) !== -1;
	}

	// Textarea trick: assigning to .innerHTML on a <textarea> is parsed in
	// RCDATA mode, which decodes entities but never creates child elements
	// (no <img onerror>, no script execution) — a safe way to decode
	// entities in untrusted text without a real HTML-parsing sanitizer.
	function decodeEntities(str) {
		var textarea = document.createElement("textarea");
		textarea.innerHTML = str;
		return textarea.value;
	}

	function stripHtml(str) {
		var withoutTags = String(str).replace(/<[^>]*>/g, "");
		return decodeEntities(withoutTags).trim();
	}

	// Mirrors the parsing frappe-ui's own frappeRequest.js does for
	// error._server_messages (JSON array of JSON-encoded {message: ...}
	// objects), since we have no access to its internal parsed error here.
	function extractServerMessage(bodyText) {
		try {
			var data = JSON.parse(bodyText);
			if (!data._server_messages) return null;
			var raw = JSON.parse(data._server_messages);
			var messages = [];
			for (var i = 0; i < raw.length; i++) {
				try {
					var obj = JSON.parse(raw[i]);
					if (obj && obj.message) messages.push(stripHtml(obj.message));
				} catch (e) {}
			}
			return messages.length ? messages.join(" ") : null;
		} catch (e) {}
		return null;
	}

	var originalFetch = window.fetch;
	window.fetch = function () {
		return originalFetch.apply(this, arguments).then(
			function (response) {
				if (!response.ok) {
					// Read a clone so the app's own response.text()/.json()
					// further down the chain still sees an unconsumed body.
					// Chained (not fire-and-forget) so lastServerMessage is
					// set before the caller's own .then() runs and triggers
					// the toast. Deliberately NOT cleared on response.ok: by
					// the time the scan (one rAF later) runs, a later fetch
					// could already have started and not yet resolved,
					// clearing a message that hasn't been consumed yet. A
					// generic toast can only follow a failed request, and
					// that failure sets (or explicitly nulls) this itself.
					return response
						.clone()
						.text()
						.then(function (text) {
							lastServerMessage = extractServerMessage(text);
							lastServerMessageAt = Date.now();
							return response;
						})
						.catch(function () {
							lastServerMessage = null;
							return response;
						});
				}
				return response;
			},
			function (err) {
				// Network-level failure never reaches the branch above, so
				// clear here too — otherwise a stale message from an
				// earlier failed request could wrongly attach to an
				// unrelated later toast within the TTL window.
				lastServerMessage = null;
				throw err;
			}
		);
	};

	function scanForGenericToasts() {
		var paragraphs = document.querySelectorAll("p:not([data-error-toast-checked])");
		for (var i = 0; i < paragraphs.length; i++) {
			var p = paragraphs[i];
			p.setAttribute("data-error-toast-checked", "1");
			var text = p.textContent || "";
			if (!isGenericToast(text)) continue;

			if (lastServerMessage && Date.now() - lastServerMessageAt < MESSAGE_TTL_MS) {
				p.textContent = lastServerMessage;
			}
			lastServerMessage = null;
		}
	}

	var pending = null;
	function scheduleScan() {
		if (pending) return;
		pending = requestAnimationFrame(function () {
			pending = null;
			scanForGenericToasts();
		});
	}

	var observer = new MutationObserver(scheduleScan);
	observer.observe(document.body, { subtree: true, childList: true });
})();
</script>
"""


# RequestActionSheet.vue (the "My Requests" action sheet) shows Approve/Reject for a
# Leave Application whenever the viewer holds doctype/permlevel write access to the
# status field (Leave Approver/HR User role), never checking whether
# frappe.session.user is the specific document's leave_approver. So any
# Leave-Approver-role holder sees Approve/Reject on every pending Leave Application,
# not just ones assigned to them -- the backend rejects a resulting self-approval
# (see hrms_custom/overrides/leave_application.py) but otherwise doesn't stop it via
# this UI path. We can't touch apps/hrms, so this hides the buttons client-side.
#
# MECHANISM:
# - Session user: read from the "user_id" cookie, the same way the PWA's own
#   src/data/session.js does -- Frappe sets this cookie non-httponly specifically
#   for client-side reads.
# - Current document identity: RequestActionSheet.vue (and FormView.vue, harmlessly)
#   call frappe.client.get_doc_permissions with {doctype, docname} in the POST body on
#   every mount (uncached, always fires), so we intercept that request (not its
#   response) to learn which doc is on screen. Gating on doctype === "Leave
#   Application" here is what keeps this from touching Expense Claim's Approve/Reject
#   (same component, different approval field) or any workflow-driven Approve/Reject
#   for other doctypes (WorkflowActionSheet) -- Leave Application has no Frappe
#   Workflow configured, so that branch never applies to it.
# - leave_approver lookup: createDocumentResource caches by [doctype, name], so the
#   full-doc frappe.client.get fetch may not re-fire on a second view of the same
#   record. We opportunistically cache leave_approver from that response when it does
#   fire, and fall back to an explicit frappe.client.get_value call when it doesn't.
# - Fail-open: only hide once we have a *confirmed* mismatching leave_approver. While
#   the lookup is still pending, the buttons are left as-is rather than hidden, since
#   a false hide would block a real approver's only path to act, while a brief false
#   show only reproduces today's behavior for a moment.
#
# FRAGILITY: matches on the literal English button label "Approve" (untranslated PWA
# labels, same convention as GATE_JS/ERROR_TOAST_JS above). Re-check after any hrms
# app upgrade that changes RequestActionSheet.vue's structure or wording.
LEAVE_APPROVAL_GATE_JS = """
<script>
(function () {
	function getSessionUser() {
		var match = document.cookie.match(/(?:^|; )user_id=([^;]*)/);
		var user = match ? decodeURIComponent(match[1]) : null;
		return (user && user !== "Guest") ? user : null;
	}

	var currentDoc = { doctype: null, docname: null };
	var leaveApproverByName = {};
	var pendingApproverFetch = {};

	function parseJsonBody(init) {
		try {
			return init && init.body ? JSON.parse(init.body) : null;
		} catch (e) {
			return null;
		}
	}

	var originalFetch = window.fetch;
	window.fetch = function (input, init) {
		var url = typeof input === "string" ? input : (input && input.url) || "";

		if (url === "/api/method/frappe.client.get_doc_permissions") {
			var requestParams = parseJsonBody(init);
			if (requestParams) {
				currentDoc = {
					doctype: requestParams.doctype || null,
					docname: requestParams.docname || null,
				};
			}
		}

		return originalFetch.apply(this, arguments).then(function (response) {
			if (response.ok && url === "/api/method/frappe.client.get") {
				response
					.clone()
					.json()
					.then(function (data) {
						var doc = data && data.message;
						if (doc && doc.doctype === "Leave Application" && doc.name) {
							leaveApproverByName[doc.name] = doc.leave_approver || "";
						}
					})
					.catch(function () {});
			}
			return response;
		});
	};

	function fetchApproverIfNeeded(docname) {
		if (docname in leaveApproverByName) return;
		if (pendingApproverFetch[docname]) return;
		pendingApproverFetch[docname] = true;

		originalFetch("/api/method/frappe.client.get_value", {
			method: "POST",
			headers: { "Content-Type": "application/json; charset=utf-8" },
			body: JSON.stringify({
				doctype: "Leave Application",
				fieldname: "leave_approver",
				filters: docname,
			}),
		})
			.then(function (r) {
				return r.json();
			})
			.then(function (data) {
				var value = data && data.message && data.message.leave_approver;
				leaveApproverByName[docname] = value || "";
				scheduleScan();
			})
			.catch(function () {
				delete pendingApproverFetch[docname];
			});
	}

	function findApprovalButtonsContainer() {
		var buttons = document.querySelectorAll("button");
		for (var i = 0; i < buttons.length; i++) {
			var text = (buttons[i].textContent || "").trim();
			if (text === "Approve") return buttons[i].parentElement;
		}
		return null;
	}

	function applyApprovalGate() {
		if (currentDoc.doctype !== "Leave Application" || !currentDoc.docname) return;

		var container = findApprovalButtonsContainer();
		if (!container) return;

		var approver = leaveApproverByName[currentDoc.docname];
		if (approver === undefined) {
			fetchApproverIfNeeded(currentDoc.docname);
			return;
		}

		var sessionUser = getSessionUser();
		var mismatched = !sessionUser || approver !== sessionUser;
		container.style.display = mismatched ? "none" : "";
	}

	var pending = null;
	function scheduleScan() {
		if (pending) return;
		pending = requestAnimationFrame(function () {
			pending = null;
			applyApprovalGate();
		});
	}

	var observer = new MutationObserver(scheduleScan);
	observer.observe(document.body, { subtree: true, childList: true });
	scheduleScan();
})();
</script>
"""


def get_context(context):
	ctx = stock_get_context(context)

	stock_path = frappe.get_app_path("hrms", "www", "hrms.html")
	with open(stock_path, "r") as f:
		html = f.read()

	html = html.replace("</head>", HIDE_CSS + "</head>")
	html = html.replace("</body>", GATE_JS + ERROR_TOAST_JS + LEAVE_APPROVAL_GATE_JS + "</body>")

	ctx.stock_html = frappe.render_template(html, ctx)
	return ctx
