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
# span, "Confirm Check" in the button label). If a future hrms/Frappe HR
# upgrade changes that wording or adds translations, the match silently
# stops working and the confirm button stays disabled forever — it fails
# closed (safe), not open. Re-check this block after any hrms app upgrade.
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

	function applyGate() {
		var spans = findCoordSpans();
		var located = false;
		for (var i = 0; i < spans.length; i++) {
			if (spans[i].textContent && spans[i].textContent.indexOf("Latitude") !== -1) {
				located = true;
				break;
			}
		}

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

			if (located) {
				if (btn.disabled) btn.disabled = false;
				if (labelNode.textContent !== original) labelNode.textContent = original;
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


def get_context(context):
	ctx = stock_get_context(context)

	stock_path = frappe.get_app_path("hrms", "www", "hrms.html")
	with open(stock_path, "r") as f:
		html = f.read()

	html = html.replace("</head>", HIDE_CSS + "</head>")
	html = html.replace("</body>", GATE_JS + "</body>")

	ctx.stock_html = frappe.render_template(html, ctx)
	return ctx
