// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Shared UI kit of the Auri PMS dashboards (Project Hub, Portfolio, My Work, Quality, Status Report):
// themes (light + dark), base styles and small HTML helpers. Loaded on demand with
// frappe.require("auri_hub.bundle.js"), so it is not downloaded on other Desk pages.
/* global auri_pms */
frappe.provide("auri_pms.ui");

(() => {
// Hub themes. Every theme has a light and a dark palette and follows Frappe's own light/dark switch.
// Tokens: bg, b1/b3 (backdrop glows), glass, strong (raised surface), border, text, muted, nl/nd (soft-UI light/dark
// shadow colours), acc (accent), bar (progress gradient), blur (px), d (shadow offset px), bm (shadow blur multiplier),
// r (radius px).
const NONE = "rgba(0,0,0,0)";
const THEMES = {
	glass: {
		label: "Glass + Soft",
		light: { bg: "linear-gradient(135deg,#dfe7ff 0%,#ece4ff 45%,#d3f3f7 100%)", b1: "rgba(99,102,241,.30)", b3: "rgba(20,184,166,.24)", glass: "rgba(255,255,255,.45)", strong: "rgba(255,255,255,.72)", border: "rgba(255,255,255,.8)", text: "#1f2937", muted: "#6b7280", nl: "rgba(255,255,255,.95)", nd: "rgba(148,163,184,.40)", acc: "#6366f1", bar: "linear-gradient(90deg,#6366f1,#ec4899)", blur: 18, d: 7, bm: 2.2, r: 22 },
		dark: { bg: "linear-gradient(135deg,#141733 0%,#1d1440 50%,#0c2a30 100%)", b1: "rgba(99,102,241,.45)", b3: "rgba(20,184,166,.32)", glass: "rgba(34,39,62,.50)", strong: "rgba(44,50,82,.70)", border: "rgba(255,255,255,.12)", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.045)", nd: "rgba(0,0,0,.55)", acc: "#818cf8", bar: "linear-gradient(90deg,#6366f1,#ec4899)", blur: 18, d: 7, bm: 2.2, r: 22 },
	},
	soft: {
		label: "Soft UI (Neumorphism)",
		light: { bg: "#e4e8ef", b1: "transparent", b3: "transparent", glass: "#e4e8ef", strong: "#e9edf3", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(163,177,198,.75)", acc: "#4f46e5", bar: "linear-gradient(90deg,#4f46e5,#7c3aed)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#2a2521", b1: "transparent", b3: "transparent", glass: "#2a2521", strong: "#312b26", border: "transparent", text: "#f2ebe3", muted: "#b3a597", nl: "rgba(255,236,214,.06)", nd: "rgba(0,0,0,.6)", acc: "#fbbf24", bar: "linear-gradient(90deg,#f59e0b,#fb7185)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-convex": {
		label: "Soft UI - Convex",
		light: { bg: "#e6e9ef", b1: "transparent", b3: "transparent", glass: "#e6e9ef", strong: "#e6e9ef", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(163,177,198,.75)", acc: "#4f46e5", bar: "linear-gradient(90deg,#4f46e5,#7c3aed)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#1d2535", b1: "transparent", b3: "transparent", glass: "#1d2535", strong: "#1d2535", border: "transparent", text: "#e6ebf5", muted: "#9aa6bd", nl: "rgba(148,170,220,.10)", nd: "rgba(0,0,0,.6)", acc: "#93c5fd", bar: "linear-gradient(90deg,#6366f1,#a78bfa)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-pressed": {
		label: "Soft UI - Pressed",
		light: { bg: "#e1e5ec", b1: "transparent", b3: "transparent", glass: "#e1e5ec", strong: "#e1e5ec", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(155,170,192,.8)", acc: "#0f766e", bar: "linear-gradient(90deg,#0f766e,#22c55e)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#11272a", b1: "transparent", b3: "transparent", glass: "#11272a", strong: "#11272a", border: "transparent", text: "#e2f3f1", muted: "#8fb3ae", nl: "rgba(94,234,212,.07)", nd: "rgba(0,0,0,.6)", acc: "#2dd4bf", bar: "linear-gradient(90deg,#14b8a6,#4ade80)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-glow": {
		label: "Soft UI - Glow",
		light: { bg: "#e7e8f2", b1: "transparent", b3: "transparent", glass: "#e7e8f2", strong: "#e7e8f2", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(165,170,200,.75)", acc: "#6366f1", bar: "linear-gradient(90deg,#6366f1,#ec4899)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#140e24", b1: "transparent", b3: "transparent", glass: "#1a1230", strong: "#1a1230", border: "rgba(192,132,252,.14)", text: "#efe7ff", muted: "#a89bc4", nl: "rgba(192,132,252,.10)", nd: "rgba(0,0,0,.7)", acc: "#c084fc", bar: "linear-gradient(90deg,#c084fc,#f472b6)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-pearl": {
		label: "Soft UI - Pearl",
		light: { bg: "#eceff4", b1: "transparent", b3: "transparent", glass: "#eceff4", strong: "#eceff4", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(170,182,203,.7)", acc: "#2563eb", bar: "linear-gradient(90deg,#2563eb,#06b6d4)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#323a48", b1: "transparent", b3: "transparent", glass: "#323a48", strong: "#323a48", border: "transparent", text: "#f1f5f9", muted: "#b4bfcf", nl: "rgba(255,255,255,.10)", nd: "rgba(0,0,0,.40)", acc: "#7dd3fc", bar: "linear-gradient(90deg,#38bdf8,#a5f3fc)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	minimal: {
		label: "Minimal Clean",
		light: { bg: "#f7f7f8", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "#e5e7eb", text: "#111827", muted: "#6b7280", nl: "rgba(255,255,255,0)", nd: "rgba(17,24,39,.10)", acc: "#2563eb", bar: "linear-gradient(90deg,#2563eb,#2563eb)", blur: 0, d: 1, bm: 3, r: 12 },
		dark: { bg: "#000000", b1: "transparent", b3: "transparent", glass: "#0c0c0d", strong: "#0c0c0d", border: "#27272a", text: "#fafafa", muted: "#a1a1aa", nl: "rgba(255,255,255,0)", nd: "rgba(0,0,0,0)", acc: "#e4e4e7", bar: "linear-gradient(90deg,#e4e4e7,#e4e4e7)", blur: 0, d: 1, bm: 3, r: 12 },
	},
	"flat-solid": {
		label: "Flat - Solid colour",
		light: { bg: "#eef1f6", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "#dfe4ec", text: "#1b2430", muted: "#5f6c7b", nl: NONE, nd: NONE, acc: "#2563eb", bar: "linear-gradient(90deg,#2563eb,#2563eb)", blur: 0, d: 0, bm: 0, r: 8 },
		dark: { bg: "#10151d", b1: "transparent", b3: "transparent", glass: "#19212c", strong: "#202a37", border: "#2a3544", text: "#e8edf3", muted: "#98a5b5", nl: NONE, nd: NONE, acc: "#4f8df7", bar: "linear-gradient(90deg,#4f8df7,#4f8df7)", blur: 0, d: 0, bm: 0, r: 8 },
	},
};
const THEME_KEY = "auri_hub_theme";
const PERIODS = { "1m": "1 month", "3m": "3 months", "6m": "6 months", all: "Overall" };
const PERIOD_NOTE = { "1m": "last month", "3m": "last 3 months", "6m": "last 6 months", all: "overall" };

function themeCss() {
	const vars = (t) =>
		`--g-bg:${t.bg};--g-blob1:${t.b1};--g-blob3:${t.b3};--g-glass:${t.glass};--g-glass-strong:${t.strong};--g-border:${t.border};` +
		`--g-text:${t.text};--g-muted:${t.muted};--n-light:${t.nl};--n-dark:${t.nd};--acc:${t.acc};--bar:${t.bar};` +
		`--blur:${t.blur}px;--d:${t.d}px;--bm:${t.bm};--radius:${t.r}px;`;
	return Object.entries(THEMES)
		.map(
			([key, t]) =>
				`.auri-hub[data-hub-theme="${key}"]{${vars(t.light)}}` +
				`html[data-theme="dark"] .auri-hub[data-hub-theme="${key}"]{${vars(t.dark)}}`
		)
		.join("\n");
}


const ui = auri_pms.ui;
ui.THEMES = THEMES;
ui.PERIODS = PERIODS;
ui.PERIOD_NOTE = PERIOD_NOTE;
ui.PALETTE = { blue: "#3b82f6", green: "#10b981", orange: "#f59e0b", purple: "#8b5cf6", cyan: "#06b6d4", red: "#ef4444", pink: "#ec4899" };
ui.days = (n) => (cint(n) === 1 ? __("1 day") : __("{0} days", [n]));
// Pages that take an argument in their address (project-hub/PROJ-0001, status-report/PROJ-0001) would otherwise show an
// empty sidebar after a refresh or from a direct link: Frappe looks the sidebar up by the argument, not by the page.
ui.showSidebar = () => {
	try {
		const sidebar = frappe.app && frappe.app.sidebar;
		// not show_sidebar_for_module: it keeps whatever sidebar the previous screen had when that one lists this route's name
		if (sidebar && sidebar.sidebar_title !== "Auri PMS") sidebar.setup("Auri PMS");
		else if (sidebar) sidebar.set_active_workspace_item();
	} catch (e) {
		/* the sidebar is a convenience: never break the page for it */
	}
};

ui.esc = (value) => frappe.utils.escape_html(value === null || value === undefined ? "" : String(value));

ui.setFlag = (key, value) => {
	try {
		localStorage.setItem(key, value ? String(value) : "");
	} catch (e) {
		/* storage blocked: the setting applies for this visit only */
	}
};

ui.getFlag = (key, fallback) => {
	try {
		return localStorage.getItem(key) || fallback;
	} catch (e) {
		return fallback;
	}
};

ui.getTheme = () => {
	const key = ui.getFlag(THEME_KEY, "glass");
	return THEMES[key] ? key : "glass";
};

ui.applyTheme = ($el) => $el.attr("data-hub-theme", ui.getTheme());

// Adds the Theme dropdown to a page toolbar; onChange re-renders the page after a new theme was chosen.
ui.addThemeMenu = (page, onChange) => {
	const current = ui.getTheme();
	Object.entries(THEMES).forEach(([key, theme]) => {
		page.add_inner_button(
			`${key === current ? "✓ " : " "}${__(theme.label)}`,
			() => {
				ui.setFlag(THEME_KEY, key);
				onChange();
			},
			__("Theme")
		);
	});
};

ui.getPeriod = () => {
	const key = ui.getFlag("auri_hub_period", "3m");
	return PERIODS[key] ? key : "3m";
};

// Adds the Range dropdown (1 month / 3 months / 6 months / Overall).
ui.addPeriodMenu = (page, onChange) => {
	Object.entries(PERIODS).forEach(([key, text]) => {
		page.add_inner_button(
			`${ui.getPeriod() === key ? "✓ " : " "}${__(text)}`,
			() => {
				ui.setFlag("auri_hub_period", key);
				onChange();
			},
			__("Range")
		);
	});
};

// ---- small HTML helpers shared by the dashboards
ui.tile = (value, label, cls, sub, route) => {
	// route: a string (Project Hub's own handler) or ui.go(...) = open a list or report with filters
	let attr = "";
	if (route && typeof route === "object") attr = `data-go="${frappe.utils.escape_html(JSON.stringify(route))}" tabindex="0" role="link"`;
	else if (route) attr = `data-route='${route}'`;
	return `<div class="hub-tile ${cls || ""}" ${attr}><b>${value}</b><span>${label}</span>${sub ? `<em>${sub}</em>` : ""}</div>`;
};

// where a tile leads: a Desk list (ui.go("Work Item", {is_closed: 0})) or a query report (ui.goReport("Client Dependencies", {...}))
ui.go = (doctype, filters) => ({ route: ["List", doctype, "List"], filters: filters && Object.keys(filters).length ? filters : { docstatus: ["<", 2] } });
ui.goAttr = (target) => `data-go="${frappe.utils.escape_html(JSON.stringify(target))}" tabindex="0" role="link"`;
ui.OPEN_RISK = ["Identified", "Mitigating", "Monitoring"];
ui.goReport = (report, filters) => ({ route: ["query-report", report], filters: filters || {} });
ui.openTarget = (target) => {
	const go = () => {
		frappe.route_options = target.filters;
		frappe.set_route(...target.route);
	};
	if (target.route[0] !== "List") return go();
	// A list reopens with the filters the person last used, which would mix an old filter into this link's.
	// Those are stored per list view (List, Report) and only loaded once the list has been opened, so load
	// them first, clear their filters one after the other, then also empty the filter boxes of a list that is
	// already open in this tab.
	const doctype = target.route[1];
	const settings = frappe.model.user_settings;
	const loaded = settings[doctype]
		? Promise.resolve(settings[doctype])
		: settings.get(doctype).then((saved) => (settings[doctype] = saved || {}));
	loaded
		.then((saved) => {
			let chain = settings.save(doctype, "filters", []);
			["List", "Report"].forEach((view) => {
				if (saved && saved[view] && (saved[view].filters || []).length) chain = chain.then(() => settings.save(doctype, view, { filters: [] }));
			});
			return chain;
		})
		.catch(() => null)
		.then(() => {
			Object.values(frappe.views.list_view || {}).forEach((view) => {
				try {
					if (view && view.doctype === doctype && view.filter_area) view.filter_area.clear(false);
				} catch (e) {
					// nothing to clear
				}
			});
			go();
		});
};
ui.bindTiles = ($body) => {
	const open = (el) => ui.openTarget(JSON.parse(el.getAttribute("data-go")));
	// idempotent: an element is bound once however often its container is searched; the click stays on the count, so a
	// card or table row around it does not also react
	$body.find("[data-go]").filter((_i, el) => !el.__goBound).each((_i, el) => (el.__goBound = true)).on("click", (e) => {
		e.stopPropagation();
		e.preventDefault(); // a link inside a <summary> must not also open or close its group
		open(e.currentTarget);
	}).on("keydown", (e) => {
		if (e.key === "Enter" || e.key === " ") {
			e.preventDefault();
			e.stopPropagation();
			open(e.currentTarget);
		}
	});
};

ui.viewAll = (target, label) => `<a class="hub-viewall" ${ui.goAttr(target)}>${label || __("View all")} →</a>`;

// A ring dial with its label and a line of detail; ``value`` is a percentage (null draws an empty ring), ``tone`` one of
// g-green, g-blue, g-teal, g-orange, g-red, g-purple, ``target`` what a click opens.
ui.ring = (value, label, sub, tone, target) => `<div class="hub-panel ph3-gauge ph2-in" ${target ? ui.goAttr(target) : ""}>
	<div class="ph2-ring ph3-ring ${tone || ""}" style="--p:${value === null ? 0 : value}">
		<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="ph2-ring-bg"/><circle cx="60" cy="60" r="52" class="ph2-ring-fg" pathLength="100"/></svg>
		<div><div class="ph2-ring-num"><b>${value === null ? "–" : value}</b>${value === null ? "" : "<span>%</span>"}</div></div>
	</div><strong>${label}</strong><small>${sub || ""}</small></div>`;

ui.panel = (title, body, cls) => `<div class="hub-panel ${cls || ""}"><h6>${title}</h6>${body}</div>`;

ui.bar = (label, value, max, cls) =>
	`<div class="hub-bar"><span>${ui.esc(label)}</span><div><i class="${cls || ""}" style="width:${max ? (value / max) * 100 : 0}%"></i></div><b>${flt(value, 1)}</b></div>`;

// Stacked rows with full labels (charts truncate long names): rows are [label, value1, value2, ...], one value per segment.
ui.stack = (rows, names, classes, routes) => {
	const sum = (r) => r.slice(1).reduce((a, b) => a + b, 0);
	const max = Math.max(1, ...rows.map(sum));
	const legend = `<div class="hub-legend">${names.map((n, i) => `<span><i class="${classes[i]}"></i>${n}</span>`).join("")}</div>`;
	return (
		legend +
		(rows.length
			? rows
					.map(
						(r, k) => `<div class="hub-stack" ${routes && routes[k] ? ui.goAttr(routes[k]) : ""}><span title="${ui.esc(r[0])}">${ui.esc(r[0])}</span><div>${r
							.slice(1)
							.map((v, i) => `<i class="${classes[i]}" style="width:${(v / max) * 100}%"></i>`)
							.join("")}</div><b>${flt(sum(r), 1)}</b></div>`
					)
					.join("")
			: `<div class="text-muted small">${__("Nothing yet")}</div>`)
	);
};

ui.table = (rows, head, cells) =>
	rows.length
		? `<table class="table table-sm hub-table"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map(cells).join("")}</tbody></table>`
		: `<div class="text-muted small">${__("None yet")}</div>`;

// Risk Register helpers shared by the hub, My Work and Portfolio.
// "Start 10 Sep 2026 · End 24 Dec 2026 · 62 days left" from the Project's expected dates; empty when neither is set.
ui.projectDates = (info) => {
	const [start, end] = [info.expected_start_date, info.expected_end_date];
	if (!start && !end) return "";
	const left = end ? frappe.datetime.get_diff(end, frappe.datetime.get_today()) : null;
	const dates = [
		start ? `${__("Start")} ${frappe.datetime.str_to_user(start)}` : "",
		end ? `${__("End")} ${frappe.datetime.str_to_user(end)}` : "",
	].filter(Boolean);
	const days = left === null ? "" : left < 0 ? __("{0} days overdue", [-left]) : __("{0} days left", [left]);
	return `<span class="hub-dates text-muted"><span>${dates.join(" · ")}</span>${days ? `<em class="${left < 0 ? "text-danger" : ""}">${days}</em>` : ""}</span>`;
};

ui.riskBadge = (level, score) => `<span class="hub-badge hub-rb hub-rb-${String(level || "low").toLowerCase()}">${__(level || "Low")}${score ? ` · ${score}` : ""}</span>`;

ui.riskLevelCounts = (by_level, project) =>
	`<div class="hub-risk-levels">${["Critical", "High", "Medium", "Low"].map((l) => `<span class="hub-rb hub-rb-${l.toLowerCase()}" ${project ? ui.goAttr(ui.go("Risk Register", { project, risk_level: l, status: ["in", ui.OPEN_RISK] })) : ""}><b>${cint((by_level || {})[l])}</b> ${__(l)}</span>`).join("")}</div>`;

ui.riskTable = (rows, with_project) =>
	ui.table(
		rows,
		[__("Risk"), __("Level"), __("Due")],
		(r) =>
			`<tr><td>${ui.link("Risk Register", r.name, r.title)}${r.overdue ? ` <span class="hub-badge hub-badge-bad">${__("Overdue")}</span>` : ""}<div class="hub-sub">${ui.esc(__(r.status))}${with_project ? ` · ${ui.esc(r.project_label)}` : r.owner ? ` · ${ui.esc(r.owner)}` : ""}</div></td>
			<td style="white-space:nowrap">${ui.riskBadge(r.risk_level, r.risk_score)}</td>
			<td style="white-space:nowrap" class="${r.overdue ? "text-danger" : ""}">${r.mitigation_due ? frappe.datetime.str_to_user(r.mitigation_due) : ""}</td></tr>`
	);

// 5 x 5 probability / impact matrix; ``matrix[0]`` is probability 5 and the columns are impact 1..5.
ui.heatmap = (matrix, project) => {
	const cell = (p, i, n) => {
		const score = p * i;
		const limits = frappe.boot.auri_pms_risk_thresholds || { medium: 5, high: 10, critical: 15 };
		const level = score >= limits.critical ? "critical" : score >= limits.high ? "high" : score >= limits.medium ? "medium" : "low";
		const go = project && n ? ui.goAttr(ui.go("Risk Register", { project, probability: ["like", `${p} - %`], impact: ["like", `${i} - %`], status: ["in", ui.OPEN_RISK] })) : "";
		return `<div class="hub-heat-cell hub-heat-${level} ${n ? "has" : ""}" title="${__("Probability {0} x Impact {1}", [p, i])}" ${go}>${n || ""}</div>`;
	};
	const rows = matrix.map((row, idx) => `<div class="hub-heat-axis">${5 - idx}</div>${row.map((n, col) => cell(5 - idx, col + 1, n)).join("")}`).join("");
	return `<div class="hub-heat"><div class="hub-heat-axis"></div>${[1, 2, 3, 4, 5].map((i) => `<div class="hub-heat-axis">${i}</div>`).join("")}${rows}</div>
		<div class="hub-sub" style="margin-top:6px">${__("Rows: probability (5 = almost certain). Columns: impact (5 = severe).")}</div>`;
};

ui.link = (doctype, name, label) => `<a href="/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}">${ui.esc(label || name)}</a>`;

// onPick(index): called with the position of the bar or point that was clicked
ui.chart = ($root, selector, config, onPick) => {
	const el = $root.find(selector)[0];
	if (!el) return;
	new frappe.Chart(el, { height: 230, ...config });
	if (!onPick) return;
	el.style.cursor = "pointer";
	el.addEventListener("click", (e) => {
		const unit = e.target.closest && e.target.closest("[data-point-index]");
		if (unit) onPick(cint(unit.getAttribute("data-point-index")));
	});
};

// ---------------------------------------------------------------- notes on a project (Portfolio and Project Health)
// A note is a comment on the Project, so it also shows on the project's own page. ``p`` is {name, notes: {count, last}}.
ui.noteButton = (p) => {
	const n = (p.notes || {}).count || 0;
	const last = (p.notes || {}).last;
	return `<span class="pf-note-btn" data-project="${ui.esc(p.name)}" title="${ui.esc(last ? `${last.by_name}: ${last.text}` : __("Add a note"))}">✎ ${n ? n : ""}</span>`;
};

ui.noteFoot = (p) => {
	const n = (p.notes || {}).count || 0;
	const last = (p.notes || {}).last;
	const text = last ? (last.text.length > 90 ? `${last.text.slice(0, 90)}…` : last.text).replace(/\n/g, " ") : "";
	return `<span class="pf-note-btn pf-note-add" data-project="${ui.esc(p.name)}">✎ ${n ? (n === 1 ? __("1 note") : __("{0} notes", [n])) : __("Add note")}</span>${last ? `<span class="pf-card-last" title="${ui.esc(last.text)}"><b>${ui.esc(last.by_name)}</b> ${ui.esc(text)}</span>` : ""}`;
};

// every note button under ``$root`` calls ``open(project)``; bound once, and a click does not reach the card or row around it
ui.bindNotes = ($root, open) => {
	$root.find(".pf-note-btn").filter((_i, el) => !el.__noteBound).each((_i, el) => (el.__noteBound = true)).on("click keypress", (e) => {
		if (e.type === "keypress" && e.key !== "Enter") return;
		e.stopPropagation();
		open($(e.currentTarget).data("project"));
	});
};

// The notes of a project in a dialog: read, add, and delete (its author or an admin). ``on_change(notes)`` runs after every change.
ui.openNotes = (project, label, on_change) => {
	const esc = ui.esc;
	const dialog = new frappe.ui.Dialog({
		title: __("Notes · {0}", [label]),
		fields: [
			{ fieldtype: "HTML", fieldname: "list" },
			{ fieldtype: "Small Text", fieldname: "note", label: __("Add a note") },
		],
		primary_action_label: __("Add note"),
		primary_action: (values) => {
			if (!values.note || !values.note.trim()) return;
			frappe.xcall("auri_pms.auri_pms.api.add_project_note", { project, note: values.note }).then((notes) => {
				fill(notes);
				dialog.set_value("note", "");
				if (on_change) on_change(notes);
				frappe.show_alert({ message: __("Note added"), indicator: "green" });
			});
		},
	});
	const fill = (notes) => {
		dialog.fields_dict.list.$wrapper.html(notes.length
			? `<div class="pf-nt-list">${notes.map((n) => `<div class="pf-nt"><div class="pf-nt-h"><b>${esc(n.by_name || n.by)}</b><span>${frappe.datetime.comment_when(n.on)}${n.can_delete ? ` · <a class="pf-nt-del" data-note="${esc(n.name)}">${__("Delete")}</a>` : ""}</span></div><div class="pf-nt-t">${esc(n.text)}</div></div>`).join("")}</div>`
			: `<div class="text-muted small" style="margin-bottom:8px">${__("No notes yet for this project.")}</div>`);
		dialog.fields_dict.list.$wrapper.find(".pf-nt-del").on("click", (e) => {
			const note = $(e.currentTarget).data("note");
			frappe.confirm(__("Delete this note?"), () =>
				frappe.xcall("auri_pms.auri_pms.api.delete_project_note", { project, note }).then((left) => {
					fill(left);
					if (on_change) on_change(left);
					frappe.show_alert({ message: __("Note deleted"), indicator: "orange" });
				})
			);
		});
	};
	dialog.onhide = () => setTimeout(() => dialog.$wrapper.remove(), 400); // a closed dialog is removed, so they do not pile up in the page
	dialog.show();
	fill([]);
	frappe.xcall("auri_pms.auri_pms.api.get_project_notes", { project }).then(fill);
};

// ---------------------------------------------------------------- billing widgets (Portfolio and Project Health)
// ``billings`` are the ``billing`` blocks of one or more projects; the result is the ticket groups and the hours by category.
ui.mergeBilling = (billings) => {
	const bill = { billable: 0, non_billable: 0, no_time: 0, hours_b: 0, hours_n: 0, names: { billable: [], non_billable: [], no_time: [] }, capped: false };
	const cats = {};
	billings.forEach((b) => {
		if (!b) return;
		bill.billable += b.tickets.billable;
		bill.non_billable += b.tickets.non_billable;
		bill.no_time += b.tickets.no_time;
		bill.hours_b += b.hours.billable;
		bill.hours_n += b.hours.non_billable;
		Object.keys(bill.names).forEach((group) => bill.names[group].push(...((b.names || {})[group] || [])));
		bill.capped = bill.capped || !!b.names_capped;
		b.categories.forEach((c) => {
			cats[c.label] = cats[c.label] || [0, 0, new Set()];
			cats[c.label][0] += c.billable;
			cats[c.label][1] += c.non_billable;
			(c.docnames || []).forEach((name) => cats[c.label][2].add(name));
		});
	});
	return { bill, cats };
};

// Billable vs non-billable tickets: a ring and the three counts, each opening its tickets. ``project`` is a project name or ["in", names].
ui.billableTicketsPanel = (bill, project) => {
	const tk_total = bill.billable + bill.non_billable + bill.no_time;
	// a count opens its tickets; past the cap of names the time entries (or the tickets without hours) stand in
	const group_route = (group) => {
		if (!bill[group]) return null;
		if (!bill.capped) return ui.go("Work Item", { name: ["in", bill.names[group]] });
		return group === "no_time" ? ui.go("Work Item", { project, spent_hours: 0 }) : ui.go("Time Entry", { project, is_billable: group === "billable" ? 1 : 0 });
	};
	const parts = [[__("Billable"), bill.billable, "#10b981", group_route("billable")], [__("Non-billable only"), bill.non_billable, "#f59e0b", group_route("non_billable")], [__("No time logged"), bill.no_time, "#94a3b8", group_route("no_time")]];
	let offset = 0;
	const arcs = parts.filter(([, v]) => v).map(([label, v, colour, route]) => {
		const share = (v / (tk_total || 1)) * 100;
		const arc = `<circle cx="60" cy="60" r="44" pathLength="100" stroke="${colour}" stroke-dasharray="${share} ${100 - share}" stroke-dashoffset="${-offset}" ${route ? ui.goAttr(route) : ""}><title>${label}: ${v}</title></circle>`;
		offset += share;
		return arc;
	});
	return ui.panel(__("Billable vs non-billable tickets") + ui.viewAll(ui.go("Time Entry", { project })), tk_total
		? `<div class="ph3-donut-wrap pf-tk-donut"><div class="ph3-donut"><svg viewBox="0 0 120 120">${arcs.join("")}</svg><div><b>${tk_total}</b><small>${__("tickets")}</small></div></div>
			<div class="pf-btk">${parts.map(([label, v, colour, route]) => `<div ${route ? ui.goAttr(route) : ""}><i style="background:${colour}"></i><span>${label}</span><b>${v}</b><small>${Math.round((v / tk_total) * 100)}%</small></div>`).join("")}</div></div>
			<div class="pf-note pf-btk-note">${__("A ticket is billable when billable hours were logged on it.")} ${flt(bill.hours_b, 1)} ${__("h billable")} · ${flt(bill.hours_n, 1)} ${__("h non-billable")}</div>`
		: `<div class="ph2-empty">${__("No tickets yet")}</div>`, "ph2-card");
};

// Time spent by ticket category as a treemap: a box of fixed size, one tile per category sized by its hours, so more categories make
// smaller tiles and never a taller panel. Returns {html, bind($root)}; bind adds the hover that shows a tile's billable split.
ui.categoryPanel = (cats, project) => {
	const esc = ui.esc;
	const sorted = Object.entries(cats).map(([label, v]) => ({ label, billable: v[0], non_billable: v[1], value: v[0] + v[1], docs: [...v[2]] })).filter((c) => c.value > 0).sort((a, b) => b.value - a.value || a.label.localeCompare(b.label));
	const total = sorted.reduce((t, c) => t + c.value, 0);
	const hues = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#06b6d4", "#8b5cf6", "#f97316", "#84cc16", "#0ea5e9", "#e11d48"];
	const TW = 175, TH = 100;
	const tiles = [];
	if (total) {
		const items = sorted.map((c, i) => ({ ...c, i, area: (c.value / total) * TW * TH }));
		let [x, y, w, h] = [0, 0, TW, TH];
		let row = [];
		const sum_area = (r) => r.reduce((t, c) => t + c.area, 0);
		const worst = (r, side) => {
			const s = sum_area(r);
			const areas = r.map((c) => c.area);
			return Math.max((side * side * Math.max(...areas)) / (s * s), (s * s) / (side * side * Math.min(...areas)));
		};
		const place = (r) => {
			const s = sum_area(r);
			if (w >= h) {
				const cw = s / h;
				let cy = y;
				r.forEach((c) => { tiles.push({ ...c, x, y: cy, w: cw, h: c.area / cw }); cy += c.area / cw; });
				x += cw;
				w -= cw;
			} else {
				const rh = s / w;
				let cx = x;
				r.forEach((c) => { tiles.push({ ...c, x: cx, y, w: c.area / rh, h: rh }); cx += c.area / rh; });
				y += rh;
				h -= rh;
			}
		};
		items.forEach((c) => {
			const side = Math.min(w, h);
			if (!row.length || worst(row.concat(c), side) <= worst(row, side)) row.push(c);
			else {
				place(row);
				row = [c];
			}
		});
		if (row.length) place(row);
	}
	const note_default = __("{0} h on {1} categories, all time · hover a tile for the billable split", [flt(total, 1), sorted.length]);
	const html = ui.panel(__("Time spent by ticket category") + ui.viewAll(ui.go("Time Entry", { project })), total
		? `<div class="pf-tree">${tiles.map((c) => {
				const pct = Math.round((c.value / total) * 100);
				const big = c.w >= 34 && c.h >= 22;
				const mid = c.w >= 18 && c.h >= 13;
				const route = c.label === __("No ticket") ? ui.go("Time Entry", { project, work_item: ["is", "not set"] }) : c.label === __("No category") ? ui.go("Work Item", { project, category: ["is", "not set"] }) : c.docs.length ? ui.go("Work Item", { category: ["in", c.docs] }) : null;
				return `<div class="pf-tile" ${route ? ui.goAttr(route) : ""} data-i="${c.i}" style="left:${(c.x / TW) * 100}%;top:${(c.y / TH) * 100}%;width:${(c.w / TW) * 100}%;height:${(c.h / TH) * 100}%;--c:${hues[c.i % hues.length]}">
					<div class="pf-tile-in" title="${esc(c.label)}: ${flt(c.value, 1)} h">${big ? `<span>${esc(c.label)}</span><b>${flt(c.value, 1)} h</b><small>${pct}%</small>` : mid ? `<b>${flt(c.value, 0)}</b>` : ""}
					<i class="pf-tile-bill" style="--g:${c.value ? (c.billable / c.value) * 100 : 0}%"></i></div></div>`;
			}).join("")}</div>
			<div class="pf-note pf-cat-note" data-default="${esc(note_default)}">${esc(note_default)}</div>`
		: `<div class="ph2-empty">${__("No hours logged yet")}</div>`, "ph2-card");
	const bind = ($root) => {
		const $tree = $root.find(".pf-tree");
		const $note = $root.find(".pf-cat-note");
		$tree.find(".pf-tile").on("mouseenter", (e) => {
			const c = sorted[+$(e.currentTarget).data("i")];
			$tree.find(".pf-tile").each((_k, el) => $(el).toggleClass("dim", el !== e.currentTarget));
			$note.text(`${c.label}: ${flt(c.billable, 1)} ${__("h billable")} · ${flt(c.non_billable, 1)} ${__("h non-billable")} · ${Math.round((c.value / total) * 100)}%`);
		}).on("mouseleave", () => {
			$tree.find(".pf-tile").removeClass("dim");
			$note.text($note.data("default"));
		});
	};
	return { html, bind };
};

// The billing graph: billable and non-billable hours per week (or month) as stacked columns, and the billable share of the hours as a line.
ui.billingPanel = (project) => ui.panel(__("Billing graph") + ui.viewAll(ui.go("Time Entry", { project })), `<div class="pf-bill-key"><span><i style="background:#10b981"></i>${__("Billable hours")}</span><span><i style="background:#f59e0b"></i>${__("Non-billable hours")}</span><span><u></u>${__("Billable % (right axis)")}</span></div>
	<div class="pf-bill-wrap"><div class="pf-bill-svg"></div><div class="pf-trend-tip"></div></div>`, "ph2-card");

// ``o``: labels, starts (first day of every period), billable and non_billable (hours per period), project (name or ["in", names]).
ui.drawBilling = ($root, o) => {
	const esc = ui.esc;
	const { labels, billable, non_billable } = o;
	const n = labels.length;
	const bucket = (i) => [o.starts[i], i + 1 < o.starts.length ? frappe.datetime.add_days(o.starts[i + 1], -1) : frappe.datetime.get_today()];
	const W = 560, H = 196, left = 34, right = 36, top = 14, base = 162;
	const slot = (W - left - right) / n;
	const x = (i) => left + (i + 0.5) * slot;
	const totals = billable.map((b, i) => b + non_billable[i]);
	const peak = Math.max(1, ...totals);
	const step = Math.max(1, Math.ceil(peak / 3 / (peak > 15 ? 5 : 1)) * (peak > 15 ? 5 : 1));
	const max = Math.ceil((peak * 1.08) / step) * step;
	const y = (v) => base - (v / max) * (base - top);
	const yp = (pct) => base - (pct / 100) * (base - top);
	const share = totals.map((t, i) => (t > 0 ? (billable[i] / t) * 100 : null));
	const grid = [];
	for (let v = 0; v <= max; v += step) grid.push(`<line x1="${left}" x2="${W - right}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="pt-grid"/><text x="${left - 7}" y="${(y(v) + 3.5).toFixed(1)}" class="pt-y">${v}</text>`);
	[0, 50, 100].forEach((v) => grid.push(`<text x="${W - right + 7}" y="${(yp(v) + 3.5).toFixed(1)}" class="pt-y2">${v}%</text>`));
	const every = Math.max(1, Math.ceil(n / 7));
	const xl = labels.map((label, i) => (i % every === 0 || i === n - 1 ? `<text x="${x(i).toFixed(1)}" y="${base + 17}" class="pt-x">${esc(label)}</text>` : "")).join("");
	const bw = Math.min(20, slot * 0.6);
	const bars = billable.map((b, i) => `<rect x="${(x(i) - bw / 2).toFixed(1)}" y="${y(b).toFixed(1)}" width="${bw.toFixed(1)}" height="${(base - y(b)).toFixed(1)}" rx="2" fill="#10b981" class="pb-bar" style="--d:${i * 30}ms"/>
		<rect x="${(x(i) - bw / 2).toFixed(1)}" y="${y(b + non_billable[i]).toFixed(1)}" width="${bw.toFixed(1)}" height="${(y(b) - y(b + non_billable[i])).toFixed(1)}" rx="2" fill="#f59e0b" class="pb-bar" style="--d:${i * 30}ms"/>`).join("");
	let path = "";
	let pen = false;
	share.forEach((v, i) => {
		if (v === null) {
			pen = false;
			return;
		}
		path += `${pen ? "L" : "M"}${x(i).toFixed(1)} ${yp(v).toFixed(1)} `;
		pen = true;
	});
	const dots = share.map((v, i) => (v === null ? "" : `<circle cx="${x(i).toFixed(1)}" cy="${yp(v).toFixed(1)}" r="2.2" class="pb-dot"/>`)).join("");
	const $svg = $root.find(".pf-bill-svg").html(`<svg viewBox="0 0 ${W} ${H}" class="pt-svg">${grid.join("")}<line x1="${left}" x2="${W - right}" y1="${base}" y2="${base}" class="pt-axis"/>${xl}${bars}
		<path d="${path}" class="pb-line" pathLength="1"/>${dots}<line class="pt-guide" y1="${top}" y2="${base}" x1="0" x2="0"/>
		${labels.map((_l, i) => `<rect x="${(x(i) - slot / 2).toFixed(1)}" y="${top}" width="${slot.toFixed(1)}" height="${base - top}" fill="transparent" class="pb-hit" data-i="${i}"/>`).join("")}</svg>`);
	const $tip = $root.find(".pf-bill-wrap .pf-trend-tip").removeClass("show");
	$svg.find(".pb-hit").on("click", (e) => {
		const [from, to] = bucket(+$(e.currentTarget).data("i"));
		ui.openTarget(ui.go("Time Entry", { project: o.project, date: ["between", [from, to]] }));
	});
	$svg.find(".pb-hit").on("mousemove", (e) => {
		const i = +$(e.currentTarget).data("i");
		$svg.find(".pt-guide").attr({ x1: x(i), x2: x(i) }).addClass("show");
		$tip.html(`<b>${esc(labels[i])}</b><span><i style="background:#10b981"></i>${__("Billable")}<em>${flt(billable[i], 1)} h</em></span><span><i style="background:#f59e0b"></i>${__("Non-billable")}<em>${flt(non_billable[i], 1)} h</em></span><span><i style="background:var(--ph-acc, #6366f1)"></i>${__("Billable %")}<em>${share[i] === null ? "–" : `${Math.round(share[i])}%`}</em></span>`)
			.css({ left: `${Math.min(70, Math.max(2, (x(i) / W) * 100 + (x(i) / W > 0.55 ? -34 : 3)))}%` }).addClass("show");
	}).on("mouseleave", () => {
		$svg.find(".pt-guide").removeClass("show");
		$tip.removeClass("show");
	});
};

// Traffic-light banner: {level, label, score, reasons: [{level, text}]}
// "100 - 3 off track x 15 - 3 at risk x 5 = 40": how a health score is worked out (calc comes from the server)
ui.scoreCalc = (calc, score) => {
	if (!calc) return "";
	const raw = 100 - calc.red * calc.red_penalty - calc.amber * calc.amber_penalty;
	return __("100 − {0} off track × {1} − {2} at risk × {3} = {4}", [calc.red, calc.red_penalty, calc.amber, calc.amber_penalty, raw < 0 ? `${raw}, ${__("shown as")} ${score}` : score]);
};

ui.statusBanner = (st, scoreLabel) =>
	`<div class="hub-status hub-${st.level}">
		<div class="hub-status-dial"><b>${st.score === null || st.score === undefined ? "-" : st.score}</b><span><strong style="font-weight:800;font-size:10px;color:inherit">${scoreLabel || __("health")}</strong></span></div>
		<div><h5>${ui.esc(st.label)}</h5><ul>${(st.reasons || []).map((r) => `<li class="hub-reason hub-${r.level}" ${r.link ? ui.goAttr(r.link) : ""}><i></i>${ui.esc(r.text)}${st.calc && (r.level === "red" || r.level === "amber") ? `<span class="hub-pts" title="${__("Points taken off the score")}">−${r.level === "red" ? st.calc.red_penalty : st.calc.amber_penalty}</span>` : ""}</li>`).join("")}</ul>
			${st.calc_lines && st.calc_lines.length ? `<div class="hub-calc"><b>${__("How the score is worked out")}</b>${st.calc_lines.map((l) => `<div>${ui.esc(l)}</div>`).join("")}${st.calc ? `<div class="hub-calc-note">${ui.esc(__("The score starts at 100. Each Off Track (red) reason takes off {0} points (PMS Settings: Health Score Penalty per Off Track Reason) and each At Risk (amber) reason takes off {1} (Health Score Penalty per At Risk Reason).", [st.calc.red_penalty, st.calc.amber_penalty])).replace("PMS Settings", `<a href="/desk/pms-settings">PMS Settings</a>`)}</div>` : ""}</div>` : ""}</div>
	</div>`;

// Creates the app page and the themed container every dashboard renders into.
ui.initPage = (wrapper, title) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __(title), single_column: true });
	const $body = $(`<div class="auri-hub"></div>`).appendTo(page.main);
	ui.injectStyle();
	ui.applyTheme($body);
	return { page, $body };
};

ui.injectStyle = () => {
	$("#auri-hub-style, #auri-hub-style-v2, #auri-hub-style-v3, #auri-hub-style-v4, #auri-hub-style-v5").remove();
	if ($("#auri-hub-style-v6").length) return;
	$(`<style id="auri-hub-style-v6">
		${themeCss()}
			.auri-hub {
				--n-raised: var(--d) var(--d) calc(var(--d) * var(--bm)) var(--n-dark), calc(var(--d) * -1) calc(var(--d) * -1) calc(var(--d) * var(--bm)) var(--n-light);
				--n-soft: calc(var(--d) * .6) calc(var(--d) * .6) calc(var(--d) * var(--bm) * .6) var(--n-dark), calc(var(--d) * -.6) calc(var(--d) * -.6) calc(var(--d) * var(--bm) * .6) var(--n-light);
				--n-inset: inset calc(var(--d) * .45) calc(var(--d) * .45) calc(var(--d) * var(--bm) * .45) var(--n-dark), inset calc(var(--d) * -.45) calc(var(--d) * -.45) calc(var(--d) * var(--bm) * .45) var(--n-light);
				position: relative; overflow: hidden; border-radius: calc(var(--radius) + 4px); padding: 26px 24px 34px; margin: 6px 0 24px;
				color: var(--g-text);
				background: radial-gradient(520px 340px at 0% 0%, var(--g-blob1), transparent 70%), radial-gradient(560px 400px at 100% 100%, var(--g-blob3), transparent 70%), var(--g-bg);
			}
			.auri-hub > * { position: relative; z-index: 1; }
			.auri-hub .text-muted, .auri-hub .small { color: var(--g-muted) !important; }
			.auri-hub a { color: var(--acc); font-weight: 500; }

			.hub-title { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; }
			.hub-dates { margin-left: auto; display: grid; justify-items: end; gap: 2px; font-size: 12px; line-height: 1.4; white-space: nowrap; } .hub-dates em { font-style: normal; font-weight: 700; }
			.hub-title h4 { margin: 0; font-weight: 700; letter-spacing: -.01em; color: var(--g-text); }
			.hub-ident { font-size: 11px; font-weight: 600; letter-spacing: .04em; padding: 4px 12px; border-radius: 999px; color: var(--acc);
				background: var(--g-glass-strong); border: 1px solid var(--g-border); box-shadow: var(--n-soft); }
			.hub-warn { color: #b45309; }
			.hub-search { max-width: 380px; margin-bottom: 20px; }
			.hub-search input { border: 1px solid var(--g-border); border-radius: 999px; padding: 10px 18px; height: auto; color: var(--g-text);
				background: var(--g-glass); box-shadow: var(--n-inset); }

			.hub-card, .hub-panel {
				background: var(--g-glass); border: 1px solid var(--g-border); border-radius: var(--radius);
				-webkit-backdrop-filter: blur(var(--blur)) saturate(160%); backdrop-filter: blur(var(--blur)) saturate(160%);
				box-shadow: var(--n-raised);
			}
			/* backdrop-filter gives every panel its own stacking context: lift the panel whose search dropdown is open above its neighbours */
			.hub-panel:focus-within { position: relative; z-index: 30; }
			.hub-panel .awesomplete > ul { z-index: 40; }
			.hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 22px; grid-auto-rows: 1fr; }
			.hub-card { padding: 18px 20px; cursor: pointer; transition: transform .18s ease; display: flex; flex-direction: column; }
			.hub-card .hub-stats { margin-bottom: auto; } .hub-card .hub-sprint, .hub-card .hub-nosprint { margin-top: 14px; min-height: 40px; }
			.hub-card:hover, .hub-card:focus { transform: translateY(-3px); outline: none; }
			.hub-card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 14px; font-size: 15px; }
			.hub-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; margin-bottom: 14px; }
			.hub-stats > div { padding: 8px 2px; border-radius: calc(var(--radius) * .6); box-shadow: var(--n-inset); }
			.hub-stats b { display: block; font-size: 19px; font-weight: 700; }
			.hub-stats span, .hub-tile span { font-size: 11px; color: var(--g-muted); letter-spacing: .02em; }

			.hub-tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; margin-bottom: 22px; } @media (max-width: 900px) { .hub-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
			.hub-tile { --acc: #6366f1; padding: 16px 18px; border-radius: calc(var(--radius) * .9); background: var(--g-glass-strong); border: 1px solid var(--g-border);
				box-shadow: var(--n-raised); position: relative; transition: transform .15s ease; }
			.hub-tile::before { content: ""; position: absolute; left: 18px; top: 0; width: 34px; height: 4px; border-radius: 0 0 6px 6px; background: var(--acc); box-shadow: 0 2px calc(var(--bm) * 4px) var(--acc); }
			.hub-tile b { display: block; margin-top: 4px; font-size: 28px; font-weight: 700; line-height: 1.1; color: var(--acc); }
			.hub-tile[data-route], .hub-tile[data-go] { cursor: pointer; } .hub-tile[data-route]:hover, .hub-tile[data-go]:hover { transform: translateY(-2px); }
			.hub-tile[data-route]:active, .hub-tile[data-go]:active { transform: none; box-shadow: var(--n-inset); }
			.hub-blue { --acc: #3b82f6; } .hub-red { --acc: #ef4444; } .hub-purple { --acc: #8b5cf6; } .hub-orange { --acc: #f59e0b; }
			.hub-cyan { --acc: #06b6d4; } .hub-green { --acc: #10b981; } .hub-teal { --acc: #14b8a6; }
			.auri-hub[data-hub-theme="mono"] .hub-tile { --acc: var(--g-text); }
			.auri-hub[data-hub-theme="mono"] .hub-tile.hub-red b { text-decoration: underline; }

			.hub-cols { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 22px; align-items: stretch; }
			/* overview rows: panels side by side share one height, so nothing drifts further down than its neighbour */
			.hub-row { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 22px; align-items: stretch; margin-bottom: 22px; }
			.hub-row > .hub-panel { margin-bottom: 0; height: 100%; }
			.hub-row-even { grid-template-columns: repeat(2, minmax(0, 1fr)); } .hub-risk-split { display: grid; grid-template-columns: minmax(190px, 240px) minmax(0, 1fr); gap: 18px; align-items: stretch; } .hub-risk-split > div:first-child { display: flex; flex-direction: column; } .hub-risk-split .hub-heat { flex: 1; max-width: none; grid-template-rows: auto repeat(5, minmax(24px, 1fr)); } .hub-risk-split .hub-heat-cell { aspect-ratio: auto; } .hub-risk-split .hub-table { width: 100%; font-size: 11px; } .hub-risk-split .hub-table td, .hub-risk-split .hub-table th { padding: 4px 8px; } .hub-risk-split .hub-heat-cell { font-size: 12px; } @media (max-width: 992px) { .hub-risk-split { grid-template-columns: 1fr; } }
			.hub-row-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); } .hub-row-one { grid-template-columns: minmax(0, 1fr); }
			@media (max-width: 992px) { .hub-row, .hub-row-3 { grid-template-columns: 1fr; } }
			/* both columns end on the same line: the last panel of the shorter column grows to fill the gap */
			.hub-col { display: flex; flex-direction: column; min-width: 0; }
			.hub-col > .hub-panel:last-child { flex: 1 1 auto; }
			.hub-col > .hub-panel { flex: 0 0 auto; } .hub-col > .hub-panel:last-child { margin-bottom: 0; }
			@media (max-width: 992px) { .hub-cols { grid-template-columns: 1fr; } .auri-hub { padding: 18px 14px 26px; } }
			.hub-panel { padding: 18px 20px; margin-bottom: 22px; } .hub-panel h6 { margin: 0 0 12px; font-weight: 700; letter-spacing: .02em; color: var(--g-text); }

			.auri-hub .progress, .hub-sprint .progress { height: 10px; border-radius: 999px; background: transparent; box-shadow: var(--n-inset); overflow: hidden; border: 1px solid var(--g-border); }
			.auri-hub .progress-bar { border-radius: 999px; background: var(--bar); box-shadow: 0 0 calc(var(--bm) * 4px) var(--acc); }
			.hub-bar { display: grid; grid-template-columns: 104px 1fr 28px; align-items: center; gap: 10px; font-size: 12px; margin-bottom: 8px; }
			.hub-bar div { height: 9px; border-radius: 999px; box-shadow: var(--n-inset); overflow: hidden; border: 1px solid var(--g-border); }
			.hub-bar i { display: block; height: 100%; border-radius: 999px; background: var(--bar); }
			.hub-bar b { text-align: right; }

			.hub-table { font-size: 12px; margin: 0; color: var(--g-text); background: transparent; }
			.hub-table th { color: var(--g-muted); font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: .06em; border-top: 0; border-bottom: 1px solid var(--g-border); }
			.hub-table td { border-top: 1px solid var(--g-border); vertical-align: middle; }
			.hub-table tbody tr:hover { background: var(--g-glass-strong); }
			.hub-chart { margin-top: 6px; border-radius: calc(var(--radius) * .7); padding: 6px 4px 0; box-shadow: var(--n-inset); }
			.hub-chart text { fill: var(--g-muted); }

			.hub-tile em { display: block; font-style: normal; font-size: 10.5px; color: var(--g-muted); margin-top: 2px; }
			.hub-cols-even { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
			@media (max-width: 992px) { .hub-cols-even { grid-template-columns: 1fr; } }
			.hub-status { --lvl: #9ca3af; display: flex; gap: 22px; align-items: center; padding: 20px 24px; margin-bottom: 22px; border-radius: var(--radius);
				background: var(--g-glass); border: 1px solid var(--g-border); box-shadow: var(--n-raised); border-left: 6px solid var(--lvl);
				-webkit-backdrop-filter: blur(var(--blur)); backdrop-filter: blur(var(--blur)); }
			.hub-status.hub-green { --lvl: #10b981; } .hub-status.hub-amber { --lvl: #f59e0b; } .hub-status.hub-red { --lvl: #ef4444; }
			.hub-status-dial { flex: 0 0 auto; width: 92px; height: 92px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center;
				box-shadow: var(--n-inset); border: 4px solid var(--lvl); }
			.hub-status-dial b { font-size: 28px; line-height: 1; color: var(--lvl); } .hub-status-dial span { font-size: 9px; color: var(--g-muted); text-transform: uppercase; letter-spacing: .05em; }
			.hub-status h5 { margin: 0 0 8px; font-weight: 700; color: var(--lvl); font-size: 20px; }
			.hub-status ul { list-style: none; margin: 0; padding: 0; }
			.hub-reason { font-size: 13px; margin: 3px 0; display: flex; align-items: center; gap: 8px; }
			.hub-reason i { width: 8px; height: 8px; border-radius: 50%; background: #9ca3af; flex: 0 0 auto; }
			.hub-reason.hub-red i { background: #ef4444; } .hub-reason.hub-amber i { background: #f59e0b; } .hub-reason.hub-green i { background: #10b981; }
			/* My Work timeline tables: fixed column widths, numbers right-aligned, headers aligned with their values. */
			.mw-table .hub-table { table-layout: fixed; width: 100%; } .mw-table .hub-table th, .mw-table .hub-table td { padding: 8px 10px; vertical-align: top; overflow-wrap: anywhere; }
			.mw-table .hub-table th:first-child, .mw-table .hub-table td:first-child { padding-left: 0; } .mw-table .hub-table th:last-child, .mw-table .hub-table td:last-child { padding-right: 0; }
			.mw-blocking col:nth-child(1) { width: 46%; } .mw-blocking col:nth-child(2) { width: 18%; } .mw-blocking col:nth-child(3) { width: 36%; }
			.mw-releases col:nth-child(1) { width: 28%; } .mw-releases col:nth-child(2) { width: 20%; } .mw-releases col:nth-child(3) { width: 14%; } .mw-releases col:nth-child(4) { width: 24%; } .mw-releases col:nth-child(5) { width: 14%; }
			.mw-projects col:nth-child(1) { width: 32%; } .mw-projects col:nth-child(2) { width: 24%; } .mw-projects col:nth-child(3) { width: 12%; } .mw-projects col:nth-child(4) { width: 14%; } .mw-projects col:nth-child(5) { width: 18%; }
			.mw-releases :is(th, td):nth-child(3), .mw-releases :is(th, td):nth-child(4), .mw-projects :is(th, td):nth-child(n+3) { text-align: right; white-space: nowrap; }
			.mw-releases :is(th, td):nth-child(5) { text-align: center; white-space: nowrap; } .mw-blocking :is(th, td):nth-child(2) { white-space: nowrap; }
			/* My Work: one compact line per ticket. */
			.mw-list { display: grid; } .mw-row { display: grid; grid-template-columns: 10px minmax(0, 1fr) 72px 92px 84px; gap: 12px; align-items: center; padding: 9px 2px; border-top: 1px solid var(--g-border); font-size: 13px; } .mw-row:first-child { border-top: 0; }
			.mw-head { padding: 4px 2px 6px; border-top: 0 !important; font-size: 10px; font-weight: 700; color: var(--g-muted); text-transform: uppercase; letter-spacing: .06em; } .mw-head .mw-due { font-size: 10px; color: var(--g-muted); }
			.mw-dot { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; } .mw-dot-red { background: #ef4444; } .mw-dot-orange { background: #f59e0b; } .mw-dot-blue { background: #3b82f6; } .mw-dot-grey { background: #cbd5e1; }
			.mw-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .mw-text span { font-weight: 600; margin-right: 6px; } .mw-text em { font-style: normal; font-size: 11px; color: var(--g-muted); margin-left: 8px; }
			.mw-flag { justify-self: start; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 999px; } .mw-flag-bad { color: #dc2626; background: rgba(239, 68, 68, .12); } .mw-flag-warn { color: #b45309; background: rgba(245, 158, 11, .16); }
			.mw-due { font-size: 12px; color: var(--g-muted); min-width: 64px; text-align: right; white-space: nowrap; } .mw-due-late { color: #dc2626; font-weight: 700; } .mw-due-today { color: #b45309; font-weight: 700; }
			@media (max-width: 700px) { .mw-row { grid-template-columns: 10px minmax(0, 1fr) 92px; } .mw-flag, .mw-row .hub-btn, .mw-head span:nth-child(3), .mw-head span:nth-child(5) { display: none; } }
			.hub-calc { margin-top: 12px; padding-top: 10px; border-top: 1px dashed var(--g-border); font-size: 12px; color: var(--g-muted); } .hub-reason[data-go]:hover { text-decoration: underline; }
			.hub-pts { margin-left: 8px; font-size: 11px; font-weight: 700; color: var(--g-muted); } .hub-calc-note { margin-top: 6px; max-width: 760px; font-size: 11.5px; line-height: 1.45; }
			.hub-calc b { display: block; color: var(--g-text); margin-bottom: 3px; }
			/* Project Hub overview (ph2): clean cards, one indigo accent, red/amber only for problems, gentle motion. */
			.ph2 { --ph-acc: var(--acc, #4f46e5); --ph-acc-soft: color-mix(in srgb, var(--ph-acc) 12%, transparent); --ph-bad: #dc2626; --ph-warn: #d97706; --ph-ok: #059669; }
			.ph2 .ph2-in { animation: ph2-up .45s ease-out both; }
			@keyframes ph2-up { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
			@keyframes ph2-grow { from { width: 0; } }
			.ph2-hero { display: grid; grid-template-columns: minmax(0, 1fr) 150px; gap: 28px; align-items: center; padding: 26px 30px; margin-bottom: 18px; border-radius: 18px;
				background: linear-gradient(135deg, var(--ph-acc-soft), transparent 60%), var(--g-glass-strong); border: 1px solid var(--g-border); }
			.ph2-hero h2 { margin: 6px 0 14px; font-size: 26px; font-weight: 800; letter-spacing: -.02em; color: var(--g-text); }
			.ph2-eyebrow { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--g-muted); }
			.ph2-pill { padding: 2px 10px; border-radius: 999px; background: var(--ph-acc-soft); color: var(--ph-acc); font-weight: 700; font-size: 11px; letter-spacing: .04em; }
			.ph2-actions { display: flex; flex-wrap: wrap; gap: 8px; }
			.ph2-timeline { margin-top: 18px; max-width: 640px; }
			.ph2-tl-labels { display: flex; justify-content: space-between; font-size: 11px; color: var(--g-muted); margin-bottom: 6px; } .ph2-tl-labels b { color: var(--g-text); }
			.ph2-tl-track { position: relative; height: 6px; border-radius: 999px; background: var(--g-border); }
			.ph2-tl-track i { display: block; height: 100%; width: var(--w); border-radius: 999px; background: var(--ph-acc); animation: ph2-grow .9s ease-out both; }
			.ph2-tl-track em { position: absolute; top: -4px; width: 14px; height: 14px; margin-left: -7px; border-radius: 50%; background: #fff; border: 3px solid var(--ph-acc); }
			.ph2-ring { position: relative; width: 150px; height: 150px; }
			.ph2-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
			.ph2-ring circle { fill: none; stroke-width: 10; } .ph2-ring-bg { stroke: var(--g-border); }
			.ph2-ring-fg { stroke: var(--ph-acc); stroke-linecap: round; stroke-dasharray: calc(var(--p) * 1) 100; animation: ph2-ring 1.1s ease-out both; }
			@keyframes ph2-ring { from { stroke-dasharray: 0 100; } }
			.ph2-ring > div { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; }
			.ph2-ring b { font-size: 34px; font-weight: 800; color: var(--g-text); line-height: 1; } .ph2-ring span { font-size: 16px; font-weight: 700; color: var(--g-muted); }
			.ph2-ring small { display: block; font-size: 11px; color: var(--g-muted); margin-top: 4px; }
			.ph2-kpis { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
			.ph2-kpi { padding: 16px 18px; border-radius: 14px; background: var(--g-glass-strong); border: 1px solid var(--g-border); cursor: pointer; transition: transform .15s, box-shadow .15s; }
			.ph2-kpi:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(15, 23, 42, .08); }
			.ph2-kpi b { display: block; font-size: 30px; font-weight: 800; color: var(--g-text); line-height: 1.1; }
			.ph2-kpi span { font-size: 12px; color: var(--g-muted); } .ph2-kpi em { display: block; font-style: normal; font-size: 11px; color: var(--g-muted); margin-top: 4px; }
			.ph2-tone-bad b { color: var(--ph-bad); } .ph2-tone-warn b { color: var(--ph-warn); }
			.ph2-grid { display: grid; gap: 18px; margin-bottom: 18px; } .ph2-grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); } .ph2-grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
			.ph2-card { min-width: 0; margin-bottom: 0; }
			.ph2-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; } .ph2-card-head h6 { margin: 0; font-weight: 800; font-size: 14px; color: var(--g-text); }
			.ph2-card-head > a, .ph2-card-head > .ph2-sub { font-size: 12px; } .ph2-card-head > .ph2-sub { margin-left: 0; } .ph2-card-head > .hub-viewall { margin-left: auto; } .ph2-card-head > .ph2-chip { margin-left: auto; }
			.ph2-card-head h6 + a { margin-left: 0; font-weight: 600; } .ph2-card-head h6 + a + .ph2-chip { margin-left: auto; }
			.ph2-sub { font-size: 12px; color: var(--g-muted); } .ph2-bad { color: var(--ph-bad) !important; }
			.ph2-label { margin: 12px 0 6px; font-size: 11px; font-weight: 700; color: var(--g-muted); text-transform: uppercase; letter-spacing: .05em; }
			.ph2-bar { height: 8px; border-radius: 999px; background: var(--g-border); margin: 12px 0 6px; overflow: hidden; } .ph2-bar-sm { height: 6px; margin: 8px 0 4px; }
			.ph2-bar i { display: block; height: 100%; width: var(--w); background: var(--ph-acc); border-radius: 999px; animation: ph2-grow .9s ease-out both; }
			.ph2-burn { margin-top: 6px; }
			.ph2-stack { display: flex; height: 14px; border-radius: 999px; overflow: hidden; background: var(--g-border); }
			.ph2-stack i { display: block; height: 100%; cursor: pointer; animation: ph2-grow .9s ease-out both; }
			.ph2-legend { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 8px; font-size: 12px; color: var(--g-muted); } .ph2-legend span { cursor: pointer; }
			.ph2-legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; } .ph2-legend b { color: var(--g-text); margin-left: 2px; }
			.ph2-hbar { display: grid; grid-template-columns: 90px minmax(0, 1fr) 30px; gap: 10px; align-items: center; font-size: 12px; margin-bottom: 7px; cursor: pointer; }
			.ph2-hbar div { height: 8px; border-radius: 999px; background: var(--g-border); overflow: hidden; }
			.ph2-hbar i { display: block; height: 100%; width: var(--w); background: #818cf8; border-radius: 999px; animation: ph2-grow .9s ease-out both; } .ph2-hbar b { text-align: right; }
			.ph2-hbar:hover span, .ph2-legend span:hover { color: var(--ph-acc); }
			.ph2-chip { display: inline-flex; align-items: center; gap: 4px; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; background: var(--g-border); color: var(--g-text); white-space: nowrap; }
			.ph2-chip-ok { background: rgba(5, 150, 105, .12); color: var(--ph-ok); } .ph2-chip-warn { background: rgba(217, 119, 6, .14); color: var(--ph-warn); } .ph2-chip-bad { background: rgba(220, 38, 38, .12); color: var(--ph-bad); }
			.ph2-chips { display: flex; flex-wrap: wrap; gap: 8px; } .ph2-chips .ph2-chip { cursor: pointer; }
			.ph2-rel { display: block; padding: 10px 0; border-top: 1px solid var(--g-border); color: inherit !important; text-decoration: none !important; } .ph2-rel:first-of-type { border-top: 0; }
			.ph2-rel > div:first-child { display: flex; justify-content: space-between; align-items: center; gap: 8px; } .ph2-rel b { font-size: 13px; }
			.ph2-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-top: 1px solid var(--g-border); font-size: 13px; color: inherit !important; text-decoration: none !important; }
			.ph2-card-head + .ph2-row, .ph2-chips + .ph2-row, .ph2-sub + .ph2-row { border-top: 0; }
			a.ph2-row:hover .ph2-grow { color: var(--ph-acc); }
			.ph2-grow { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .ph2-grow small { display: block; font-size: 11px; color: var(--g-muted); }
			.ph2-id { font-size: 11px; font-weight: 700; color: var(--g-muted); white-space: nowrap; } .ph2-when { font-size: 11px; color: var(--g-muted); white-space: nowrap; min-width: 70px; text-align: right; }
			.ph2-avatar { display: inline-grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--ph-acc-soft); color: var(--ph-acc); font-size: 11px; font-weight: 800; flex: 0 0 auto; }
			.ph2-avatar-sm { width: 24px; height: 24px; font-size: 10px; } .ph2-avatar-empty { background: var(--g-border); color: var(--g-muted); }
			.ph2-dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; background: #cbd5e1; } .ph2-dot-bad, .ph2-dot-critical { background: var(--ph-bad); } .ph2-dot-warn, .ph2-dot-high { background: var(--ph-warn); }
			.ph2-dot-medium { background: #a5b4fc; } .ph2-dot-low { background: #6ee7b7; }
			.ph2-empty { font-size: 12px; color: var(--g-muted); padding: 8px 0; }
			@media (max-width: 1200px) { .ph2-kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); } .ph2-grid-3 { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
			@media (max-width: 800px) { .ph2-hero { grid-template-columns: 1fr; } .ph2-ring { margin: 0 auto; } .ph2-grid-2, .ph2-grid-3 { grid-template-columns: 1fr; } .ph2-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
			@media (prefers-reduced-motion: reduce) { .ph2 *, .ph2 { animation: none !important; transition: none !important; } }
			.hub-viewall { float: right; font-size: 12px; font-weight: 600; color: var(--ph-acc, #4f46e5) !important; cursor: pointer; text-decoration: none !important; } .hub-viewall:hover { text-decoration: underline !important; }
			.ph2-card-head .hub-viewall { float: none; margin-left: auto; }
			.ph2-ring-num { display: flex; align-items: baseline; justify-content: center; gap: 1px; }
			.ph2-burn .legend-dataset-text { font-size: 11px !important; } .ph2-burn .chart-legend { transform: scale(.9); transform-origin: left; }
			/* Project Hub overview (ph3), drawn inside the theme's own panels and tiles */
			.ph3 .ph3-gauges { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; margin-bottom: 22px; }
			.ph3 .ph3-gauge { display: grid; grid-template-columns: 104px minmax(0, 1fr); column-gap: 18px; align-items: center; justify-items: start; margin: 0; cursor: pointer; text-align: left; }
			.ph3 .ph3-gauge strong { align-self: end; font-size: 14px; color: var(--g-text); } .ph3 .ph3-gauge small { align-self: start; font-size: 12px; color: var(--g-muted); min-height: 14px; }
			.ph3 .ph3-ring { width: 104px; height: 104px; grid-row: span 2; } .ph3 .ph3-ring b { font-size: 24px; }
			.ph3 .g-green { --ph-acc: #10b981; } .ph3 .g-blue { --ph-acc: #3b82f6; } .ph3 .g-teal { --ph-acc: #14b8a6; } .ph3 .g-purple { --ph-acc: #8b5cf6; }
			.ph3 .g-orange { --ph-acc: #f59e0b; } .ph3 .g-red { --ph-acc: #ef4444; }
			.ph3 .ph3-grid-wide { grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); }
			.ph3 .ph2-grid { gap: 22px; margin-bottom: 22px; }
			/* tickets card: status columns + priority split */
			.tk, .wl { display: flex; flex-direction: column; }
			.tk-cols { display: flex; gap: 10px; align-items: stretch; height: 170px; margin: 4px 0 16px; }
			.tk-col { flex: 1; min-width: 0; display: grid; grid-template-rows: auto 1fr auto auto; justify-items: center; gap: 4px; cursor: pointer; }
			.tk-col b { font-size: 15px; font-weight: 800; color: var(--g-text); }
			.tk-col-bar { width: 100%; max-width: 46px; display: flex; align-items: flex-end; border-radius: 10px; background: color-mix(in srgb, var(--g-text) 5%, transparent); overflow: hidden; }
			.tk-col-bar i { display: block; width: 100%; height: var(--h); min-height: 4px; border-radius: 10px; background: linear-gradient(180deg, color-mix(in srgb, var(--c) 75%, #fff), var(--c)); transform-origin: bottom; animation: tk-rise .9s cubic-bezier(.2, .8, .2, 1) both; }
			@keyframes tk-rise { from { transform: scaleY(0); } }
			.tk-col span { font-size: 11.5px; color: var(--g-text); max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .tk-col small { font-size: 10.5px; color: var(--g-muted); }
			.tk-col:hover .tk-col-bar i { filter: brightness(1.08); } .tk-col:hover span { color: var(--ph-acc); }
			.tk-prio { margin-top: auto; padding-top: 12px; border-top: 1px solid color-mix(in srgb, var(--g-text) 8%, transparent); }
			.tk-prio-head { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--g-muted); margin-bottom: 8px; }
			.tk-prio-bar { display: flex; gap: 3px; height: 10px; margin-bottom: 10px; } .tk-prio-bar i { border-radius: 4px; min-width: 6px; cursor: pointer; }
			.tk-prio-keys { display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 6px; }
			.tk-prio-keys span { display: grid; grid-template-columns: 8px auto; column-gap: 6px; align-items: center; font-size: 11px; color: var(--g-muted); cursor: pointer; padding: 6px 8px; border-radius: 8px; background: color-mix(in srgb, var(--g-text) 4%, transparent); }
			.tk-prio-keys span i { width: 8px; height: 8px; border-radius: 3px; } .tk-prio-keys span b { grid-column: 2; font-size: 15px; font-weight: 800; color: var(--g-text); line-height: 1.1; } .tk-prio-keys span small { grid-column: 2; font-size: 10px; }
			.tk-prio-keys span:hover { background: color-mix(in srgb, var(--g-text) 8%, transparent); }
			/* workload card */
			.wl-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
			.wl-stat { display: grid; gap: 1px; padding: 9px 12px; border-radius: 10px; cursor: pointer; background: color-mix(in srgb, var(--tone) 10%, transparent); border-left: 3px solid var(--tone); }
			.wl-stat b { font-size: 20px; font-weight: 800; line-height: 1.1; color: var(--g-text); } .wl-stat span { font-size: 11px; color: var(--g-muted); } .wl-stat:hover { background: color-mix(in srgb, var(--tone) 16%, transparent); }
			.wl-acc { --tone: var(--ph-acc); } .wl-bad { --tone: #ef4444; } .wl-warn { --tone: #f59e0b; } .wl-ok { --tone: #10b981; }
			.wl-list { display: grid; align-content: start; flex: 1; }
			.wl-row { display: grid; grid-template-columns: 32px minmax(0, 1fr) minmax(70px, 1fr) 26px; gap: 10px; align-items: center; padding: 7px 0; cursor: pointer; border-bottom: 1px solid color-mix(in srgb, var(--g-text) 6%, transparent); }
			.wl-row:last-child { border-bottom: 0; } .wl-row .ph2-avatar { width: 32px; height: 32px; }
			.wl-who { min-width: 0; } .wl-who b { display: block; font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .wl-who small { font-size: 10.5px; color: var(--g-muted); }
			.wl-row:hover .wl-who b { color: var(--ph-acc); }
			.wl-bar { display: flex; height: 10px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 7%, transparent); overflow: hidden; }
			.wl-bar i { display: block; height: 100%; width: var(--w); animation: ph2-grow .9s ease-out both; } .wl-bar .wl-ok { background: var(--ph-acc); } .wl-bar .wl-bad { background: #ef4444; } .wl-bar .wl-warn { background: #f59e0b; }
			.wl-row > em { font-style: normal; font-size: 14px; font-weight: 800; color: var(--g-text); text-align: right; }
			.wl-more { margin-top: 6px; font-size: 11px; color: var(--g-muted); }
			/* portfolio */
			.pf-split-chips { display: flex; gap: 8px; align-items: flex-start; } .pf-split-chips span { display: grid; grid-template-columns: auto auto; column-gap: 8px; align-items: baseline; padding: 8px 14px; border-radius: 12px; font-size: 11.5px; font-weight: 600; cursor: pointer; color: var(--g-muted); background: color-mix(in srgb, var(--tone) 10%, transparent); border: 1px solid color-mix(in srgb, var(--tone) 30%, transparent); }
			.pf-split-chips b { font-size: 18px; font-weight: 800; color: var(--g-text); } .pf-split-chips span:hover { background: color-mix(in srgb, var(--tone) 18%, transparent); }
			.pf-chip-red { --tone: #e11d48; } .pf-chip-amber { --tone: #f59e0b; } .pf-chip-green { --tone: #10b981; }
			.pf .hx-hero .hx-meta { margin-top: 2px; }
			.pf .hub-chip { cursor: pointer; } .pf .hub-chip.active { background: var(--ph-acc, #6366f1); color: var(--on-acc, #fff); border-color: transparent; box-shadow: none; }
			.pf-ident { margin-left: 6px; padding: 1px 8px; border-radius: 6px; font-size: 10.5px; font-weight: 700; letter-spacing: .04em; background: color-mix(in srgb, var(--ph-acc, #6366f1) 14%, transparent); color: var(--ph-acc, #6366f1); } .pf-na { color: var(--g-muted); }
			.pf-health { display: inline-flex; align-items: center; gap: 7px; padding: 3px 11px 3px 9px; border-radius: 999px; font-size: 11.5px; font-weight: 700; white-space: nowrap; background: color-mix(in srgb, var(--tone) 12%, transparent); color: var(--tone); }
			.pf-health i { width: 8px; height: 8px; border-radius: 50%; background: var(--tone); } .pf-health b { font-weight: 800; opacity: .8; }
			.pf-red { --tone: #e11d48; } .pf-amber { --tone: #d97706; } .pf-green { --tone: #059669; }
			.pf .al-cap-bar > i:nth-child(n) { opacity: .95; }
			.pf-note { font-size: 11px; color: var(--g-muted); margin: -4px 0 10px; }
			/* portfolio, in the Hub's style: verdict, dials, tiles, project cards, why, details */
			.pf .ph3-gauges { grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr)); } .pf .hub-chart { box-shadow: none; background: transparent; } .pf .hub-tiles { margin-bottom: 22px; }
			.pf-verdict { --tone: #10b981; display: flex; flex-wrap: wrap; align-items: center; gap: 10px 18px; padding: 12px 20px; margin: 0 0 18px; border-left: 5px solid var(--tone); } .pf-verdict > i { width: 12px; height: 12px; border-radius: 50%; background: var(--tone); box-shadow: 0 0 0 5px color-mix(in srgb, var(--tone) 20%, transparent); }
			.pf-verdict > b { font-size: 16px; font-weight: 800; color: var(--g-text); } .pf-verdict .pf-split-chips { margin-left: auto; } .pf-v-red { --tone: #ef4444; } .pf-v-amber { --tone: #f59e0b; } .pf-v-green { --tone: #10b981; }
			.pf-sec { display: flex; align-items: baseline; gap: 12px; margin: 8px 0 12px; } .pf-sec h5 { margin: 0; font-size: 15px; font-weight: 800; color: var(--g-text); } .pf-sec span { font-size: 12px; color: var(--g-muted); }
			.pf-why-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 18px 32px; } .pf-why-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; } .pf-why-head > b { font-size: 13.5px; color: var(--g-text); }
			.pf-reason { display: grid; grid-template-columns: 8px minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 5px 0; font-size: 12.5px; color: var(--g-text); } .pf-reason[data-go] { cursor: pointer; } .pf-reason[data-go]:hover span { color: var(--ph-acc); text-decoration: underline; }
			.pf-reason > i { width: 8px; height: 8px; border-radius: 50%; background: #94a3b8; } .pf-r-red > i { background: #ef4444; } .pf-r-amber > i { background: #f59e0b; } .pf-r-info > i { background: #3b82f6; } .pf-r-green > i { background: #10b981; } .pf-reason > b { font-size: 11px; color: var(--g-muted); }
			.pf-calc { display: grid; gap: 4px; margin-top: 16px; padding-top: 12px; border-top: 1px solid color-mix(in srgb, var(--g-text) 8%, transparent); font-size: 12px; color: var(--g-muted); } .pf-calc > b { color: var(--g-text); } .pf-calc > span { font-size: 13px; font-weight: 700; color: var(--g-text); font-variant-numeric: tabular-nums; } .pf-calc small { font-size: 11.5px; line-height: 1.5; }
			.pf-fold { margin-bottom: 22px; } .pf-fold > summary { cursor: pointer; list-style: none; user-select: none; } .pf-fold > summary::-webkit-details-marker { display: none; } .pf-fold > summary:hover h5 { color: var(--ph-acc); }
			.pf-chev { width: 7px; height: 7px; align-self: center; border-right: 2px solid var(--g-muted); border-bottom: 2px solid var(--g-muted); transform: rotate(-45deg); transition: transform .2s ease; } .pf-fold[open] .pf-chev { transform: rotate(45deg); }
			.pf-fold .pf-why { margin-top: 4px; }
			.pf-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 18px; margin-bottom: 22px; }
			.pf-card { display: grid; gap: 14px; padding: 16px 18px; margin: 0; cursor: pointer; transition: transform .15s ease, box-shadow .15s ease; } .pf-card:hover, .pf-card:focus-visible { transform: translateY(-3px); outline: none; box-shadow: var(--n-raised), 0 10px 26px color-mix(in srgb, var(--ph-acc) 18%, transparent); }
			.pf-card-top { display: grid; grid-template-columns: 52px minmax(0, 1fr) auto; gap: 14px; align-items: center; }
			.pf-card-nums { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; } .pf-card-nums > div { display: grid; gap: 1px; padding: 7px 10px; border-radius: 10px; background: color-mix(in srgb, var(--g-text) 4%, transparent); }
			.pf-card-nums b { font-size: 15px; font-weight: 800; line-height: 1.15; color: var(--g-text); } .pf-card-nums span { font-size: 10.5px; color: var(--g-muted); } .pf-card-nums .pf-bad b { color: #ef4444; } .pf-card-nums .pf-warn b { color: #f59e0b; }
			.pf-projects .hub-toolbar { margin-bottom: 10px; } .pf-projects .hub-search input { height: 36px; border-radius: 999px; }
			.pf-table { width: 100%; border-collapse: separate; border-spacing: 0; } .pf-table th, .pf-table td { text-align: left !important; padding: 11px 10px; vertical-align: middle; border-top: 0; }
			.pf-table th { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--g-muted); font-weight: 700; border-bottom: 1px solid var(--g-border); white-space: nowrap; cursor: pointer; user-select: none; }
			.pf-table th.sorted { color: var(--g-text); } .pf-table th.sorted::after { content: " ▾"; } .pf-table th.sorted.asc::after { content: " ▴"; }
			.pf-table td { border-bottom: 1px solid color-mix(in srgb, var(--g-text) 7%, transparent); font-size: 12.5px; color: var(--g-text); }
			.pf-table tr:last-child td { border-bottom: 0; } .pf-table tbody tr { cursor: pointer; } .pf-table tbody tr:hover td { background: color-mix(in srgb, var(--ph-acc, #6366f1) 6%, transparent); }
			.pf-table td:first-child, .pf-table th:first-child { min-width: 250px; } .pf-table td:first-child b { margin-right: 4px; }
			.pf-mini { display: inline-grid; grid-template-columns: 44px 44px; align-items: center; gap: 8px; } .pf-mini b { font-weight: 700; }
			.pf-mini i { display: block; height: 6px; border-radius: 999px; background: linear-gradient(90deg, var(--ph-acc, #6366f1) var(--w), color-mix(in srgb, var(--g-text) 9%, transparent) var(--w)); }
			.pf-mini.pf-bad i { background: linear-gradient(90deg, #e11d48 var(--w), color-mix(in srgb, var(--g-text) 9%, transparent) var(--w)); } .pf-mini.pf-bad b { color: #e11d48; }
			.pf-tag { display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: 11px; font-weight: 700; } .pf-tag-warn { background: rgba(251, 146, 60, .16); color: #ea580c; } .pf-tag-bad { background: rgba(225, 29, 72, .12); color: #e11d48; }
			.pf-trend { padding: 12px 18px 8px; margin-bottom: 22px; } .pf-trend-tools { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 20px; margin-bottom: 2px; }
			.pf-tabs { display: inline-flex; padding: 3px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 7%, transparent); } .pf-tabs span { padding: 4px 13px; border-radius: 999px; font-size: 12px; font-weight: 700; cursor: pointer; color: var(--g-muted); transition: background .15s, color .15s; }
			.pf-tabs span:hover { color: var(--g-text); } .pf-tabs span.active { background: var(--ph-acc, #6366f1); color: var(--on-acc, #fff); box-shadow: 0 4px 12px color-mix(in srgb, var(--ph-acc, #6366f1) 35%, transparent); }
			.pf-legend { display: flex; flex-wrap: wrap; gap: 6px 8px; } .pf-legend span { display: inline-flex; align-items: center; gap: 6px; padding: 3px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 600; cursor: pointer; color: var(--g-text); background: color-mix(in srgb, var(--c) 12%, transparent); border: 1px solid color-mix(in srgb, var(--c) 35%, transparent); transition: opacity .15s; }
			.pf-legend span i { width: 9px; height: 9px; border-radius: 50%; background: var(--c); } .pf-legend span.off { opacity: .4; background: transparent; text-decoration: line-through; } .pf-legend span:hover { opacity: 1; }
			.pf-trend-wrap { position: relative; } .pt-svg { width: 100%; height: auto; display: block; overflow: visible; }
			.pt-grid { stroke: color-mix(in srgb, var(--g-text) 8%, transparent); stroke-width: 1; stroke-dasharray: 4 5; } .pt-axis { stroke: color-mix(in srgb, var(--g-text) 20%, transparent); } .pt-y { font-size: 11px; fill: var(--g-muted); text-anchor: end; } .pt-x { font-size: 11px; fill: var(--g-muted); text-anchor: middle; }
			.pt-stroke { fill: none; stroke: var(--c); stroke-width: 1; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1; stroke-dashoffset: 1; animation: pt-draw 1.1s cubic-bezier(.4, 0, .2, 1) forwards; animation-delay: var(--d); }
			.pt-area { opacity: 0; animation: pt-fade .9s ease forwards; animation-delay: calc(var(--d) + .5s); } .pt-dot { fill: var(--c); stroke: #fff; stroke-width: 1.2; opacity: 0; animation: pt-fade .4s ease forwards; animation-delay: calc(var(--d) + 1s); filter: drop-shadow(0 0 4px var(--c)) drop-shadow(0 0 9px var(--c)); }
			.pt-shine { fill: #fff; opacity: 0; animation: pt-shine .4s ease forwards; animation-delay: calc(var(--d) + 1.1s); } @keyframes pt-shine { to { opacity: .85; } }
			.pt-pulse { fill: var(--c); opacity: 0; transform-box: fill-box; transform-origin: center; animation: pt-pulse 2.2s ease-out infinite; animation-delay: calc(var(--d) + 1.2s); } @keyframes pt-pulse { 0% { transform: scale(1); opacity: .55; } 100% { transform: scale(4.2); opacity: 0; } }
			.pt-end { font-size: 11px; font-weight: 700; fill: var(--c); opacity: 0; animation: pt-fade .4s ease forwards; animation-delay: calc(var(--d) + 1s); }
			@keyframes pt-draw { to { stroke-dashoffset: 0; } } @keyframes pt-fade { to { opacity: 1; } }
			.pt-guide { stroke: color-mix(in srgb, var(--g-text) 35%, transparent); stroke-width: 1; stroke-dasharray: 4 4; opacity: 0; } .pt-guide.show { opacity: 1; } .pt-point { stroke: var(--g-glass-strong, #fff); stroke-width: 1.5; pointer-events: none; } .pt-hit { cursor: crosshair; }
			.pf-trend-tip { position: absolute; top: 4px; min-width: 150px; padding: 9px 12px; border-radius: 12px; font-size: 12px; pointer-events: none; opacity: 0; transition: opacity .12s; color: var(--g-text); background: var(--g-glass-strong); border: 1px solid var(--g-border); box-shadow: 0 10px 28px rgba(0, 0, 0, .22); z-index: 2; }
			.pf-trend-tip.show { opacity: 1; } .pf-trend-tip b { display: block; margin-bottom: 5px; font-size: 11.5px; color: var(--g-muted); } .pf-trend-tip span { display: flex; align-items: center; gap: 7px; padding: 2px 0; } .pf-trend-tip span i { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; } .pf-trend-tip span em { margin-left: auto; padding-left: 14px; font-style: normal; font-weight: 800; }
			.pf-scope { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 14px 2px 14px; font-size: 12px; color: var(--g-muted); } .pf-scope.on { padding: 8px 14px; border-radius: 12px; color: var(--g-text); background: color-mix(in srgb, var(--ph-acc, #6366f1) 10%, transparent); border: 1px solid color-mix(in srgb, var(--ph-acc, #6366f1) 30%, transparent); }
			.pf-scope-chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; cursor: pointer; color: var(--on-acc, #fff); background: var(--ph-acc, #6366f1); } .pf-scope-chip i { font-style: normal; font-size: 10px; opacity: .8; } .pf-scope-chip:hover { filter: brightness(1.1); }
			.pf-scope-clear { margin-left: auto; font-weight: 700; cursor: pointer; color: var(--ph-acc, #6366f1); } .pf-scope-clear:hover { text-decoration: underline; }
			.pf-table tbody tr.selected td { background: color-mix(in srgb, var(--ph-acc, #6366f1) 13%, transparent); } .pf-table tbody tr.selected td:first-child { box-shadow: inset 4px 0 0 var(--ph-acc, #6366f1); }
			.pf-open { color: var(--g-text); text-decoration: none; } .pf-open:hover b { color: var(--ph-acc, #6366f1); text-decoration: underline; }
			.pf-projects .hub-search { position: relative; } .pf-suggest { display: none; position: absolute; left: 0; right: 0; top: calc(100% + 6px); max-height: 320px; overflow-y: auto; z-index: 60; padding: 6px; border-radius: 14px; background: #ffffff; border: 1px solid var(--g-border); box-shadow: 0 16px 38px rgba(0, 0, 0, .28); } html[data-theme="dark"] .pf-suggest { background: #1f2233; } .pf-suggest.open { display: block; }
			.pf-sug-head { padding: 6px 10px 8px; font-size: 10.5px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--g-muted); }
			.pf-sug { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 10px; cursor: pointer; font-size: 13px; color: var(--g-text); } .pf-sug:hover { background: color-mix(in srgb, var(--ph-acc, #6366f1) 10%, transparent); } .pf-sug.on { background: color-mix(in srgb, var(--ph-acc, #6366f1) 16%, transparent); }
			.pf-sug b { font-weight: 700; } .pf-sug .pf-ident { margin-left: 0; } .pf-sug .pf-health, .pf-sug small { margin-left: auto; font-size: 11px; color: var(--g-muted); } .pf-sug .pf-health { color: var(--tone); }
			.pf-sug-check { width: 16px; height: 16px; flex: 0 0 auto; border-radius: 5px; border: 1.5px solid color-mix(in srgb, var(--g-text) 35%, transparent); position: relative; } .pf-sug.on .pf-sug-check { background: var(--ph-acc, #6366f1); border-color: var(--ph-acc, #6366f1); }
			.pf-sug.on .pf-sug-check::after { content: ""; position: absolute; left: 4.5px; top: 1.5px; width: 4px; height: 8px; border: solid var(--on-acc, #fff); border-width: 0 2px 2px 0; transform: rotate(45deg); }
			.pf-sug-empty { padding: 12px 10px; font-size: 12.5px; color: var(--g-muted); } .pf-sug-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 4px; padding: 10px 10px 4px; border-top: 1px solid var(--g-border); } .pf-sug-clear { font-size: 12px; font-weight: 700; cursor: pointer; color: var(--ph-acc, #6366f1); } .pf-sug-clear:hover { text-decoration: underline; }
			.pf-cstack { display: grid; grid-template-columns: minmax(90px, 150px) 34px minmax(60px, 1fr) auto; gap: 10px; align-items: center; margin-bottom: 8px; font-size: 12px; cursor: pointer; } .pf-cstack:hover > span:first-child { color: var(--ph-acc); }
			.pf-cstack > span:first-child { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .pf-cstack > b { color: var(--g-text); }
			.pf-cbar { display: flex; height: 10px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 8%, transparent); overflow: hidden; } .pf-cbar i { display: block; height: 100%; }
			.pf-counts { display: inline-flex; gap: 4px; } .pf-counts em { min-width: 26px; padding: 1px 7px; border-radius: 999px; font-style: normal; font-size: 11px; font-weight: 800; text-align: center; color: #fff; } .pf-counts em.zero { opacity: .3; } .pf-counts em.seg-yellow { color: #1f2937; }
			.pf-btk { display: grid; gap: 9px; } .pf-btk > div { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto 38px; gap: 8px; align-items: center; font-size: 12.5px; color: var(--g-text); } .pf-btk i { width: 10px; height: 10px; border-radius: 3px; } .pf-btk b { font-weight: 800; } .pf-btk small { color: var(--g-muted); text-align: right; }
			.pf-tree { position: relative; height: 200px; border-radius: 12px; overflow: hidden; background: color-mix(in srgb, var(--g-text) 6%, transparent); }
			.pf-tile { position: absolute; padding: 1.5px; transition: opacity .15s; } .pf-tile.dim { opacity: .35; }
			.pf-tile-in { position: relative; display: flex; flex-direction: column; justify-content: flex-start; gap: 1px; height: 100%; padding: 7px 9px 9px; border-radius: 8px; overflow: hidden; color: #fff; cursor: default;
				background: linear-gradient(145deg, var(--c), color-mix(in srgb, var(--c) 72%, #000)); }
			.pf-tile-in span { font-size: 11.5px; font-weight: 700; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; opacity: .95; } .pf-tile-in b { font-size: 15px; font-weight: 800; line-height: 1.15; } .pf-tile-in small { font-size: 10.5px; opacity: .85; }
			.pf-tile-bill { position: absolute; left: 0; right: 0; bottom: 0; height: 4px; background: linear-gradient(90deg, #34d399 var(--g), #fbbf24 var(--g)); }
			.pf-tkt { margin-bottom: 8px; } .pf-tk-donut .ph3-donut > div { pointer-events: none; } .pf .pf-tk-donut .ph3-donut circle { cursor: pointer; } .pf .pf-tkt-note { margin: 12px 0 0; } .pf-tkt-tools { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; margin: 4px 0 14px; } .pf-tkt-dates { display: inline-flex; align-items: center; gap: 8px; color: var(--g-muted); } .pf-tkt-dates input { height: 32px; width: 150px; border-radius: 10px; padding: 0 10px; background: var(--g-glass-strong); border: 1px solid var(--g-border); color: var(--g-text); }
			.pf-ttable { width: 100%; border-collapse: separate; border-spacing: 0; margin: 0; } .pf-ttable th, .pf-ttable td { text-align: left !important; padding: 11px 12px; vertical-align: middle; border-top: 0; }
			.pf-ttable th { font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--g-muted); border-bottom: 1px solid var(--g-border); } .pf-ttable td { border-bottom: 1px solid color-mix(in srgb, var(--g-text) 7%, transparent); font-size: 13px; color: var(--g-text); }
			.pf-ttable th:first-child, .pf-ttable td:first-child { width: 30%; } .pf-hrs { font-weight: 700; font-variant-numeric: tabular-nums; } .pf-hrs small { font-weight: 500; color: var(--g-muted); } .pf-ttable tbody tr:hover td { background: color-mix(in srgb, var(--ph-acc, #6366f1) 6%, transparent); }
			.pf-ttable tfoot td { border-top: 2px solid var(--g-border); border-bottom: 0; background: color-mix(in srgb, var(--g-text) 4%, transparent); font-size: 13.5px; }
			.pf-tkn { display: inline-block; min-width: 44px; padding: 3px 12px; border-radius: 999px; font-size: 13px; font-weight: 800; text-align: center; color: #fff; } .pf-tkn.zero { opacity: .35; }
			.pf-tk-created { background: #3b82f6; } .pf-tk-closed { background: #10b981; } .pf-tk-prog { background: #f59e0b; color: #1f2937; } .pf-tk-client { background: #8b5cf6; }
			.pf-btk-note { margin: 12px 0 0; } .pf .pf-cat-note { margin: 10px 0 0; } .pf .ph3-donut circle { cursor: default; } .pf .ph3-donut circle:hover { stroke-width: 16; }
			.pf-bill-key { display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 0 0 4px; font-size: 11.5px; color: var(--g-muted); } .pf-bill-key span { display: inline-flex; align-items: center; gap: 6px; } .pf-bill-key i { width: 9px; height: 9px; border-radius: 3px; } .pf-bill-key u { width: 16px; height: 0; border-top: 2px solid var(--ph-acc, #6366f1); }
			.pf-bill-wrap { position: relative; } .pt-y2 { font-size: 11px; fill: var(--g-muted); text-anchor: start; } .pb-bar { transform-box: fill-box; transform-origin: bottom; animation: tk-rise .7s cubic-bezier(.2, .8, .2, 1) both; animation-delay: var(--d); }
			.pb-line { fill: none; stroke: var(--ph-acc, #6366f1); stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 1; stroke-dashoffset: 1; animation: pt-draw 1.1s ease forwards .3s; } .pb-dot { fill: var(--ph-acc, #6366f1); stroke: #fff; stroke-width: 1; } .pb-hit { cursor: crosshair; }
			.pf-link, .pf-click, .pf-counts em[data-go], .pf-tile[data-go], .pf-btk > div[data-go], .pf-tkn[data-go], .pf-hrs [data-go], .pt-end[data-go], .pf-ds[data-go] { cursor: pointer; }
			.pf-link:hover, .pf-hrs [data-go]:hover { color: var(--ph-acc, #6366f1); text-decoration: underline; } .pf-counts em[data-go]:hover, .pf-tkn[data-go]:hover { filter: brightness(1.12); transform: translateY(-1px); } .pf-btk > div[data-go]:hover { background: color-mix(in srgb, var(--g-text) 7%, transparent); border-radius: 8px; }
			.pf-card-nums .pf-click:hover { background: color-mix(in srgb, var(--ph-acc, #6366f1) 14%, transparent); } .pt-end[data-go]:hover { text-decoration: underline; }
			.pf-note-btn { display: inline-flex; align-items: center; gap: 4px; padding: 1px 9px; border-radius: 999px; font-size: 11px; font-weight: 700; cursor: pointer; color: var(--g-muted); background: color-mix(in srgb, var(--g-text) 7%, transparent); } .pf-note-btn:hover { color: var(--ph-acc, #6366f1); background: color-mix(in srgb, var(--ph-acc, #6366f1) 14%, transparent); }
			.pf-card-foot { display: flex; align-items: center; gap: 10px; min-width: 0; } .pf-card-foot .pf-note-add { flex: 0 0 auto; padding: 4px 11px; font-size: 11.5px; } .pf-card-last { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11.5px; color: var(--g-muted); } .pf-card-last b { color: var(--g-text); font-weight: 700; }
			.pf-notes-cell { min-width: 230px; max-width: 320px; } .pf-nt-del { cursor: pointer; color: #dc2626; } .pf-nt-del:hover { text-decoration: underline; }
			.pf-nt-list { max-height: 260px; overflow-y: auto; margin-bottom: 12px; display: grid; gap: 8px; } .pf-nt { padding: 9px 12px; border-radius: 10px; background: var(--control-bg, rgba(127, 127, 127, .10)); } .pf-nt-h { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 3px; font-size: 12px; } .pf-nt-h span { color: var(--text-muted, #888); } .pf-nt-t { font-size: 13px; white-space: pre-wrap; }
			.pf-applied { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; padding: 10px 16px; margin: 0 0 14px; border-left: 5px solid var(--ph-acc, #6366f1); } .pf-applied-lead { font-size: 12px; font-weight: 800; color: var(--g-text); }
			.pf-applied-n { font-size: 12px; color: var(--g-muted); } .pf-applied-clear { margin-left: auto; }
			/* My Work */
			.mw .ph3-gauges { grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr)); } .mw .hub-tiles { margin-bottom: 22px; } .mw .hub-row { margin-bottom: 22px; }
			.mw-hello { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; margin: 2px 0 20px; } .mw-hello h4 { margin: 0 0 4px; font-size: 24px; font-weight: 800; letter-spacing: -.01em; color: var(--g-text); }
			.mw-hello span { font-size: 13px; color: var(--g-muted); } .mw-hello .mw-date { font-size: 12.5px; font-weight: 600; white-space: nowrap; }
			.mw-clear { display: grid; gap: 3px; padding: 6px 2px; } .mw-clear b { font-size: 14px; color: #059669; } .mw-clear span { font-size: 12.5px; color: var(--g-muted); }
			.mw .hub-group > summary { display: flex; align-items: center; gap: 10px; } .mw .hub-group > summary .hub-viewall { margin-left: auto; font-size: 12px; }
			@media (max-width: 1100px) { .mw .ph3-gauges { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
			.pf-health.pf-none { --tone: #94a3b8; }
			.pf .ph2-grid { margin-bottom: 22px; } .pf-projects { margin-bottom: 22px; }
			/* project picker */
			.pk-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
			.pk-stat { display: grid; gap: 2px; padding: 14px 18px; border-radius: var(--radius); background: var(--g-glass-strong); border: 1px solid var(--g-border); box-shadow: var(--n-raised); border-left: 4px solid var(--g-muted); }
			.pk-stat b { font-size: 28px; font-weight: 800; line-height: 1.1; color: var(--g-text); } .pk-stat span { font-size: 12px; color: var(--g-muted); }
			.pk-stat.pk-acc { border-left-color: var(--ph-acc); } .pk-stat.pk-bad { border-left-color: #ef4444; } .pk-stat.pk-bad b { color: #ef4444; }
			.pk-toolbar { display: flex; flex-wrap: wrap; gap: 12px 16px; align-items: center; margin-bottom: 18px; }
			.pk-search { flex: 1 1 260px; max-width: 420px; } .pk-search input { height: 38px; border-radius: 999px; padding-left: 16px; background: var(--g-glass-strong); border: 1px solid var(--g-border); color: var(--g-text); }
			.pk-chips { display: flex; gap: 8px; } .pk-chip { padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; color: var(--g-muted); background: var(--g-glass-strong); border: 1px solid var(--g-border); }
			.pk-chip:hover { color: var(--g-text); } .pk-chip.active { color: var(--on-acc, #fff); background: var(--ph-acc); border-color: transparent; }
			.pk-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }
			.pk-card { display: grid; gap: 14px; padding: 18px 20px; cursor: pointer; transition: transform .15s ease, box-shadow .15s ease; margin: 0; }
			.pk-card:hover, .pk-card:focus-visible { transform: translateY(-3px); outline: none; box-shadow: var(--n-raised), 0 10px 26px color-mix(in srgb, var(--ph-acc) 18%, transparent); }
			.pk-top { display: grid; grid-template-columns: 52px minmax(0, 1fr) auto; gap: 14px; align-items: center; }
			.pk-ring { position: relative; width: 52px; height: 52px; } .pk-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
			.pk-ring circle { fill: none; stroke-width: 4.5; stroke-linecap: round; } .pk-ring-bg { stroke: color-mix(in srgb, var(--g-text) 9%, transparent); }
			.pk-ring-fg { stroke: #10b981; stroke-dasharray: var(--p) 100; animation: al-sweep 1s ease-out both; }
			.pk-ring b { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; color: var(--g-text); } .pk-ring b small { font-size: 8px; color: var(--g-muted); margin-left: 1px; }
			.pk-name { min-width: 0; } .pk-name > b { display: block; font-size: 15px; font-weight: 800; color: var(--g-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
			.pk-name small { display: flex; align-items: center; gap: 8px; margin-top: 2px; font-size: 11px; color: var(--g-muted); }
			.pk-ident { padding: 1px 8px; border-radius: 6px; font-size: 10.5px; font-weight: 700; letter-spacing: .04em; background: color-mix(in srgb, var(--ph-acc) 14%, transparent); color: var(--ph-acc); } .pk-ident.pk-warn { background: color-mix(in srgb, #f59e0b 16%, transparent); color: #d97706; }
			.pk-days { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 7%, transparent); color: var(--g-muted); white-space: nowrap; }
			.pk-days.pk-soon { background: color-mix(in srgb, #f59e0b 16%, transparent); color: #d97706; } .pk-days.pk-late { background: color-mix(in srgb, #ef4444 14%, transparent); color: #dc2626; }
			.pk-split { display: flex; gap: 3px; height: 8px; } .pk-split i { border-radius: 4px; min-width: 0; animation: ph2-grow .9s ease-out both; } .pk-split i:empty { display: block; }
			.pk-closed { background: #10b981; } .pk-open { background: var(--ph-acc); } .pk-over { background: #ef4444; } .pk-split.pk-empty { background: color-mix(in srgb, var(--g-text) 7%, transparent); border-radius: 999px; }
			.pk-nums { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
			.pk-nums > div { display: grid; gap: 1px; padding: 8px 10px; border-radius: 10px; background: color-mix(in srgb, var(--g-text) 4%, transparent); }
			.pk-nums b { font-size: 17px; font-weight: 800; color: var(--g-text); line-height: 1.1; } .pk-nums span { font-size: 10.5px; color: var(--g-muted); } .pk-nums .pk-bad b { color: #ef4444; }
			.pk-sprint { display: grid; grid-template-columns: minmax(0, auto) minmax(0, 1fr) auto; gap: 10px; align-items: center; font-size: 11.5px; color: var(--g-text); }
			.pk-sprint > span { max-width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .pk-sprint > b { font-size: 11px; color: var(--g-muted); }
			.pk-track { height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 8%, transparent); overflow: hidden; } .pk-track i { display: block; height: 100%; width: var(--w); background: var(--ph-acc); border-radius: 999px; animation: ph2-grow .9s ease-out both; }
			.pk-sprint.pk-nosprint { display: block; color: var(--g-muted); }
			@media (max-width: 900px) { .pk-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
			/* tickets created vs resolved vs closed */
			.fl-body { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 22px; align-items: center; }
			.fl-stats { display: grid; gap: 6px; } .fl-stat { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: baseline; column-gap: 10px; padding: 6px 12px; border-radius: 10px; background: color-mix(in srgb, var(--g-text) 4%, transparent); }
			.fl-stat[data-go] { cursor: pointer; } .fl-stat[data-go]:hover { background: color-mix(in srgb, var(--g-text) 8%, transparent); }
			.fl-stat span { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: var(--g-muted); } .fl-stat span i { width: 9px; height: 9px; border-radius: 3px; }
			.fl-stat b { font-size: 18px; font-weight: 800; color: var(--g-text); } .fl-stat small { grid-column: 1 / -1; font-size: 10.5px; color: var(--g-muted); }
			.fl-chart { min-width: 0; } .fl-svg { width: 100%; height: auto; max-height: 200px; overflow: visible; }
			.fl-grid { stroke: color-mix(in srgb, var(--g-text) 7%, transparent); stroke-width: 1; } .fl-axis { stroke: color-mix(in srgb, var(--g-text) 18%, transparent); }
			.fl-ytext { font-size: 10px; fill: var(--g-muted); text-anchor: end; } .fl-xtext { font-size: 10.5px; fill: var(--g-muted); text-anchor: middle; }
			.fl-hit { fill: transparent; cursor: pointer; } .fl-week:hover .fl-hit { fill: color-mix(in srgb, var(--g-text) 5%, transparent); }
			.fl-bar { cursor: pointer; } .fl-bar rect { transform-box: fill-box; transform-origin: bottom; animation: tk-rise .8s cubic-bezier(.2, .8, .2, 1) both; animation-delay: var(--d); }
			.fl-bar:hover rect { filter: brightness(1.12); } .fl-v { font-size: 9.5px; font-weight: 700; fill: var(--g-text); text-anchor: middle; opacity: 0; transition: opacity .15s; } .fl-week:hover .fl-v { opacity: 1; }
			.fl-legend { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 16px; margin-top: 4px; font-size: 11.5px; color: var(--g-muted); }
			.fl-legend span { display: inline-flex; align-items: center; gap: 6px; } .fl-legend i { width: 10px; height: 10px; border-radius: 3px; } .fl-legend small { margin-left: auto; font-size: 10.5px; }
			@media (max-width: 900px) { .fl-body { grid-template-columns: 1fr; } }
			/* allocation & utilisation */
			.al .al-sub { display: flex; align-items: baseline; gap: 10px; font-size: 12px; font-weight: 700; color: var(--g-text); margin: 0 0 10px; }
			.al .al-sub span { font-weight: 500; font-size: 11px; color: var(--g-muted); display: inline-flex; align-items: center; gap: 6px; }
			.al-top { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 22px; align-items: stretch; margin-bottom: 20px; }
			.al-top > div { border-radius: calc(var(--radius) * .7); padding: 14px 16px; background: color-mix(in srgb, var(--g-text) 3.5%, transparent); border: 1px solid color-mix(in srgb, var(--g-text) 7%, transparent); }
			.al-gauge { position: relative; display: grid; justify-items: center; align-content: center; gap: 6px; }
			.al-gauge svg { width: 100%; max-width: 200px; overflow: visible; }
			.al-gauge path { fill: none; stroke-linecap: round; } .al-zone { stroke-width: 3; opacity: .55; } .al-track { stroke: color-mix(in srgb, var(--g-text) 9%, transparent); stroke-width: 14; }
			.al-value { stroke-width: 14; stroke-dasharray: var(--p) 100; animation: al-sweep 1.2s cubic-bezier(.2, .8, .2, 1) both; }
			@keyframes al-sweep { from { stroke-dasharray: 0 100; } }
			.al-tick { stroke: var(--g-text); stroke-width: 2; opacity: .55; stroke-linecap: round; }
			.al-gauge-num { position: absolute; top: 44%; display: grid; justify-items: center; } .al-gauge-num b { font-size: 34px; font-weight: 800; line-height: 1; color: var(--g-text); } .al-gauge-num b small { font-size: 15px; color: var(--g-muted); }
			.al-gauge-num span { font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--g-muted); margin-top: 3px; }
			.al-gauge .ph2-chip { margin-top: 2px; }
			.al-stats { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; align-content: center; }
			.al-stat { display: grid; gap: 3px; align-content: start; min-width: 0; } .al-stat > span { font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--g-muted); }
			.al-stat b { font-size: 22px; font-weight: 800; color: var(--g-text); line-height: 1.1; } .al-stat b small { font-size: 12px; font-weight: 600; color: var(--g-muted); } .al-stat > small { font-size: 11px; color: var(--g-muted); }
			.al-mix, .al-budget { grid-column: span 2; } .al-budget { grid-column: auto; }
			.al-mixbar { display: flex; gap: 3px; height: 10px; } .al-mixbar i { border-radius: 4px; min-width: 6px; }
			.al-mixkeys { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 11px; color: var(--g-muted); } .al-mixkeys em, .al-cap-keys em { font-style: normal; display: inline-flex; align-items: center; gap: 5px; }
			.al-mixkeys i, .al-cap-keys i { width: 8px; height: 8px; border-radius: 3px; }
			.al-line { height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 9%, transparent); overflow: hidden; } .al-line i { display: block; height: 100%; width: var(--w); background: var(--ph-acc); border-radius: 999px; animation: ph2-grow .9s ease-out both; }
			.al-former { margin-top: 10px; font-size: 11.5px; color: var(--g-muted); }
			.al-hint { margin: 0 0 14px; padding: 10px 14px; border-radius: 10px; font-size: 12.5px; background: color-mix(in srgb, #f59e0b 10%, transparent); color: var(--g-text); }
			.al-cap { margin-top: 20px; padding-top: 16px; border-top: 1px solid color-mix(in srgb, var(--g-text) 8%, transparent); }
			.al-cap-keys { display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 11px; color: var(--g-muted); margin-bottom: 10px; }
			.al-cap-row { display: grid; grid-template-columns: minmax(120px, 180px) minmax(0, 1fr) 46px 110px 200px; gap: 12px; align-items: center; justify-items: start; padding: 6px 0; font-size: 12.5px; }
			.al-cap-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
			.al-cap-bar { position: relative; display: flex; gap: 2px; justify-self: stretch; height: 14px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 6%, transparent); }
			.al-cap-bar i { height: 100%; border-radius: 4px; animation: ph2-grow .9s ease-out both; } .al-cap-bar i:first-child { border-radius: 999px 4px 4px 999px; }
			.al-cap-bar em { position: absolute; top: -4px; bottom: -4px; width: 2px; border-radius: 2px; background: var(--g-text); opacity: .5; }
			.al-cap-over { box-shadow: 0 0 0 2px color-mix(in srgb, #ef4444 45%, transparent); } .al-cap-row small { font-size: 11px; color: var(--g-muted); } .al-cap-row > span:last-child { display: flex; gap: 6px; }
			.pf-cap h6 { display: flex; align-items: baseline; gap: 10px; } .pf-cap h6 .hub-viewall { margin-left: auto; } .pf-cap-note { font-size: 11px; font-weight: 500; color: var(--g-muted); letter-spacing: 0; }
			.pf-cap-sum { display: flex; flex-wrap: wrap; gap: 12px 36px; margin: 4px 0 14px; } .pf-cap-sum > div { display: grid; gap: 2px; }
			.pf-cap-sum span { font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--g-muted); } .pf-cap-sum b { font-size: 22px; font-weight: 800; color: var(--g-text); } .pf-cap-sum b small { font-size: 12px; color: var(--g-muted); }
			.pf-cap-row { cursor: pointer; } .pf-cap-row:hover .al-cap-name { color: var(--acc); } .pf-cap .ph2-bad { color: #dc2626 !important; }
			.pf-cap .al-cap-row { grid-template-columns: minmax(130px, 200px) minmax(0, 1fr) 50px 120px 230px; }
			.pf-cap-mark { width: 2px !important; height: 12px !important; border-radius: 2px; background: var(--g-text); opacity: .5; }
			@media (max-width: 1000px) { .al-top { grid-template-columns: 1fr; } .al-cap-row { grid-template-columns: 1fr 1fr; } }
			.ph3-tk-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; } .ph3-tk-head b { font-size: 30px; font-weight: 800; line-height: 1; color: var(--g-text); }
			.ph3-tk-head span { font-size: 12px; color: var(--g-muted); } .ph3-tk-head em { margin-left: auto; font-style: normal; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: color-mix(in srgb, #10b981 15%, transparent); color: #059669; }
			html[data-theme="dark"] .ph3-tk-head em { color: #34d399; }
			.ph3-pipe { display: flex; gap: 3px; height: 14px; margin-bottom: 14px; } .ph3-pipe i { flex: var(--v) 1 0; min-width: 6px; border-radius: 4px; background: var(--c); cursor: pointer; transition: filter .15s; } .ph3-pipe i:hover { filter: brightness(1.12); }
			.ph3-tk-row { display: grid; grid-template-columns: 10px minmax(0, 1fr) 30px 38px 34%; gap: 10px; align-items: center; justify-items: start; font-size: 12.5px; padding: 5px 0; cursor: pointer; }
			.ph3-tk-row > i { width: 10px; height: 10px; border-radius: 3px; background: var(--c); } .ph3-tk-row small { color: var(--g-muted); } .ph3-tk-row:hover span { color: var(--ph-acc); }
			.ph3-tk-row > div { justify-self: stretch; height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 8%, transparent); overflow: hidden; }
			.ph3-tk-row > div em { display: block; height: 100%; width: var(--w); border-radius: 999px; background: var(--c); animation: ph2-grow .9s ease-out both; }
			.ph3-donut-wrap { display: grid; grid-template-columns: 140px minmax(0, 1fr); gap: 24px; align-items: center; justify-items: start; }
			.ph3-donut { position: relative; width: 140px; height: 140px; } .ph3-donut svg { width: 100%; height: 100%; transform: rotate(-90deg); }
			.ph3-donut circle { fill: none; stroke-width: 16; cursor: pointer; animation: ph2-up .6s ease-out both; } .ph3-donut circle:hover { stroke-width: 19; }
			.ph3-donut > div { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; } .ph3-donut b { font-size: 24px; font-weight: 800; color: var(--g-text); line-height: 1; } .ph3-donut small { font-size: 11px; color: var(--g-muted); }
			.ph3-keys { display: grid; gap: 7px; font-size: 12px; } .ph3-keys span { display: grid; grid-template-columns: 10px 96px auto; gap: 8px; align-items: center; justify-items: start; cursor: pointer; } .ph3-keys span:hover { color: var(--ph-acc); }
			.ph3-keys i { width: 10px; height: 10px; border-radius: 3px; } .ph3-keys b { color: var(--g-text); } .ph3-keys-3 span { grid-template-columns: 10px 90px auto; row-gap: 1px; } .ph3-keys-3 em { grid-column: 2 / span 2; } .ph3-keys em { font-style: normal; font-size: 11px; color: var(--g-muted); }
			.ph3 .hub-row-3 .ph3-donut-wrap { grid-template-columns: 120px minmax(0, 1fr); gap: 16px; } .ph3 .hub-row-3 .ph3-donut { width: 120px; height: 120px; }
			.ph3 .ph2-rel[data-go] { cursor: pointer; } .ph3 .hub-stack { grid-template-columns: 130px 44px minmax(0, 1fr); } .ph3 .hub-bar { grid-template-columns: 130px 44px minmax(0, 1fr); }
			.ph3 .hub-stack b, .ph3 .hub-bar b { order: 2; text-align: left; } .ph3 .hub-stack > div, .ph3 .hub-bar > div { order: 3; } .ph3 .legend-dataset-text { font-size: 11px !important; font-weight: 500 !important; }
			.ph3-person { display: grid; grid-template-columns: 30px 110px 28px minmax(0, 1fr); gap: 10px; align-items: center; justify-items: start; margin-bottom: 9px; font-size: 12px; cursor: pointer; }
			.ph3-pname { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .ph3-person b { order: 3; text-align: left; } .ph3-person .ph3-pbar { order: 4; justify-self: stretch; } .ph3-person:hover .ph3-pname { color: var(--ph-acc); }
			.ph3-pbar { display: flex; height: 10px; border-radius: 999px; background: var(--g-border); overflow: hidden; }
			.ph3-pbar i { display: block; height: 100%; width: var(--w); animation: ph2-grow .9s ease-out both; } .ph3-pbar-ok { background: #3b82f6; } .ph3-pbar-bad { background: #ef4444; } .ph3-pbar-warn { background: #f59e0b; }
			/* risks card: exposure bar, full-width matrix, top risks */
			.rk { display: flex; flex-direction: column; } .rk-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
			.rk-head b { font-size: 30px; font-weight: 800; line-height: 1; color: var(--g-text); } .rk-head > span { font-size: 12px; color: var(--g-muted); }
			.rk-head em { margin-left: auto; font-style: normal; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: color-mix(in srgb, #ef4444 13%, transparent); color: #dc2626; cursor: pointer; }
			html[data-theme="dark"] .rk-head em { color: #fca5a5; }
			.rk-bar { display: flex; gap: 3px; height: 12px; margin-bottom: 10px; } .rk-bar i { border-radius: 4px; min-width: 8px; cursor: pointer; } .rk-bar i:hover { filter: brightness(1.1); }
			.rk-bar .rk-none { flex: 1; background: color-mix(in srgb, var(--g-text) 8%, transparent); }
			.rk-keys { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; margin-bottom: 14px; }
			.rk-keys span { display: grid; grid-template-columns: 8px minmax(0, 1fr); column-gap: 6px; align-items: center; font-size: 11px; color: var(--g-muted); cursor: pointer; padding: 6px 8px; border-radius: 8px; background: color-mix(in srgb, var(--g-text) 4%, transparent); }
			.rk-keys span i { width: 8px; height: 8px; border-radius: 3px; } .rk-keys span b { grid-column: 2; font-size: 16px; font-weight: 800; color: var(--g-text); line-height: 1.1; }
			.rk-keys .rk-zero { opacity: .55; } .rk-keys span:hover { background: color-mix(in srgb, var(--g-text) 8%, transparent); }
			.rk-matrix { display: grid; grid-template-columns: 14px minmax(0, 1fr); grid-template-rows: auto auto; column-gap: 4px; }
			.rk-y { grid-row: 1; writing-mode: vertical-rl; transform: rotate(180deg); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--g-muted); text-align: center; }
			.rk-x { grid-column: 2; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--g-muted); text-align: center; margin-top: 4px; }
			.rk .ph3-heat { margin: 0; max-width: none; } .rk .hub-heat { max-width: none; gap: 4px; } .rk .hub-heat-cell { aspect-ratio: auto; height: 32px; border-radius: 7px; font-size: 13px; }
			.rk-top { margin-top: 14px; padding-top: 10px; border-top: 1px solid color-mix(in srgb, var(--g-text) 8%, transparent); display: grid; }
			.rk-item { display: grid; grid-template-columns: 8px minmax(0, 1fr) 26px 70px; gap: 10px; align-items: center; padding: 6px 0; color: var(--g-text) !important; text-decoration: none !important; font-size: 12.5px; }
			.rk-item > i { width: 8px; height: 8px; border-radius: 50%; } .rk-item > span { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
			.rk-item > span small { display: block; font-size: 10.5px; color: var(--g-muted); overflow: hidden; text-overflow: ellipsis; } .rk-item:hover > span { color: var(--ph-acc); }
			.rk-item > b { font-size: 13px; font-weight: 800; } .rk-item > small { font-size: 11px; color: var(--g-muted); }
			.rk-item > em { font-style: normal; font-size: 10.5px; font-weight: 700; color: #dc2626; } html[data-theme="dark"] .rk-item > em { color: #fca5a5; }
			.ph3-heat { margin: 12px 0 0; max-width: 250px; } .ph3-heat .hub-heat { max-width: none; } .ph3-heat .hub-sub { display: none; }
			.ph3-road { position: relative; height: 120px; margin: 6px 12px 0; }
			.ph3-road-line { position: absolute; left: 0; right: 0; top: 56px; height: 4px; border-radius: 999px; background: var(--g-border); }
			.ph3-today { position: absolute; top: 40px; width: 2px; height: 36px; background: #ef4444; } .ph3-today span { position: absolute; top: 38px; left: -14px; font-style: normal; font-size: 10px; font-weight: 700; color: #ef4444; }
			.ph3-mile { position: absolute; top: 48px; transform: translateX(-50%); color: inherit !important; text-decoration: none !important; animation: ph2-up .5s ease-out both; }
			.ph3-mile i { display: block; width: 20px; height: 20px; border-radius: 50%; border: 4px solid var(--g-glass-strong, #fff); background: #3b82f6; box-shadow: 0 0 0 2px #3b82f6; }
			.ph3-mile span { position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%); text-align: center; font-size: 11px; color: var(--g-muted); white-space: nowrap; }
			.ph3-mile span b { display: block; font-size: 12px; color: var(--g-text); } .ph3-mile.ph3-low span { bottom: auto; top: 30px; }
			.ph3-ok i { background: #10b981; box-shadow: 0 0 0 2px #10b981; } .ph3-warn i { background: #f59e0b; box-shadow: 0 0 0 2px #f59e0b; } .ph3-bad i { background: #ef4444; box-shadow: 0 0 0 2px #ef4444; }
			.ph3-role { display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: 10px; align-items: center; padding: 7px 0; border-top: 1px solid var(--g-border); } .ph3-role:first-of-type { border-top: 0; }
			.ph3-role-name { font-size: 12px; color: var(--g-muted); } .ph3-faces { display: flex; flex-wrap: wrap; gap: 6px; }
			@media (max-width: 1100px) { .ph3 .ph3-gauges, .pf .ph3-gauges { grid-template-columns: repeat(2, minmax(0, 1fr)); } .ph3 .ph3-grid-wide { grid-template-columns: 1fr; } }
			/* Project Health report (hx): a client-ready report look, independent of the hub theme. Navy + teal, amber/red only for problems. */
			.auri-hub .hx { --ph-acc: #7c3aed; --ph-acc-soft: rgba(124, 58, 237, .08); --ph-bad: #e11d48; --ph-warn: #ea580c; --ph-ok: #8b5cf6; --hx-ink: var(--g-text); --hx-muted: var(--g-muted); --hx-line: color-mix(in srgb, var(--g-text) 10%, transparent); --hx-card: var(--g-glass-strong); --hx-navy: #1e3a8a; --hx-teal: #0d9488;
				margin: -6px; padding: 6px; color: var(--hx-ink); font-feature-settings: "tnum" 1; }
			.hx .hx-hero { position: relative; overflow: hidden; border-radius: var(--radius); padding: 28px 32px 24px; margin-bottom: 22px; color: var(--hx-ink);
				background-image: radial-gradient(700px 260px at 100% 0%, rgba(124, 58, 237, .12), transparent 60%), radial-gradient(520px 220px at 0% 100%, rgba(251, 146, 60, .08), transparent 60%); }
			.hx .hx-hero-top { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; }
			.hx .hx-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: #7c3aed; }
			.hx .hx-hero h1 { margin: 6px 0 6px; font-size: 28px; font-weight: 800; letter-spacing: -.02em; color: var(--hx-ink); }
			.hx .hx-meta { display: flex; gap: 10px; align-items: center; font-size: 12px; color: var(--hx-muted); }
			.hx .hx-ident { padding: 2px 9px; border-radius: 6px; background: rgba(124, 58, 237, .10); color: #6d28d9; font-weight: 700; font-size: 11px; letter-spacing: .05em; }
			.hx .hx-dates { text-align: right; font-size: 12px; color: var(--hx-muted); display: grid; gap: 4px; } .hx .hx-dates b { font-size: 15px; color: var(--hx-ink); }
			.hx .hx-hero-body { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 32px; align-items: center; margin-top: 22px; }
			.hx .hx-score { position: relative; display: grid; justify-items: center; }
			.hx .hx-score svg { width: 230px; height: auto; overflow: visible; }
			.hx .hx-arc-bg, .hx .hx-arc { fill: none; stroke-width: 16; stroke-linecap: round; } .hx .hx-arc-bg { stroke: color-mix(in srgb, var(--g-text) 10%, transparent); }
			.hx .hx-arc { stroke: #22c55e; animation: hx-arc 1.2s ease-out both; } @keyframes hx-arc { from { stroke-dasharray: 0 100; } }
			.hx .hx-amber .hx-arc { stroke: #f59e0b; } .hx .hx-red .hx-arc { stroke: #f43f5e; } .hx .hx-none .hx-arc { stroke: #94a3b8; }
			.hx .hx-score > div { position: absolute; top: 48px; display: grid; justify-items: center; } .hx .hx-score > div b { font-size: 46px; font-weight: 800; color: var(--hx-ink); line-height: 1; }
			.hx .hx-score > div span { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--hx-muted); margin-top: 4px; }
			.hx .hx-level { margin-top: 8px; font-style: normal; font-weight: 700; font-size: 13px; padding: 4px 14px; border-radius: 999px; background: rgba(34, 197, 94, .12); color: #15803d; }
			.hx .hx-amber .hx-level { background: rgba(245, 158, 11, .14); color: #b45309; } .hx .hx-red .hx-level { background: rgba(244, 63, 94, .12); color: #be123c; } .hx .hx-none .hx-level { background: #f1f5f9; color: #475569; }
			.hx .hx-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
			.hx .hx-metric { padding: 16px 18px; border-radius: 14px; background: color-mix(in srgb, var(--g-text) 4%, transparent); border: 1px solid var(--hx-line); cursor: pointer; transition: background .15s, transform .15s, box-shadow .15s; }
			.hx .hx-metric:hover { background: color-mix(in srgb, #7c3aed 10%, transparent); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(124, 58, 237, .10); }
			.hx .hx-metric span { display: block; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--hx-muted); }
			.hx .hx-metric b { display: block; margin: 6px 0 10px; font-size: 32px; font-weight: 800; color: var(--hx-ink); line-height: 1; } .hx .hx-metric b small { font-size: 16px; color: var(--hx-muted); margin-left: 2px; }
			.hx .hx-meter { height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--g-text) 10%, transparent); overflow: hidden; } .hx .hx-meter i { display: block; height: 100%; width: var(--w); background: #7c3aed; border-radius: 999px; animation: ph2-grow 1s ease-out both; }
			.hx .hx-metric-bad .hx-meter i { background: #e11d48; } .hx .hx-metric em { display: block; margin-top: 8px; font-style: normal; font-size: 11.5px; color: var(--hx-muted); }
			.hx .hx-hero-foot { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 24px; margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--hx-line); }
			.hx .hx-reasons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 18px; align-content: start; }
			.hx .hx-reason { display: grid; grid-template-columns: 4px minmax(0, 1fr) auto; gap: 10px; align-items: center; font-size: 12.5px; color: var(--hx-ink); padding: 6px 0; }
			.hx .hx-reason i { align-self: stretch; border-radius: 4px; background: #a78bfa; } .hx .hx-reason.hx-red i { background: #e11d48; } .hx .hx-reason.hx-amber i { background: #fb923c; } .hx .hx-reason.hx-info i { background: #a78bfa; }
			.hx .hx-reason b { font-size: 11px; color: var(--hx-muted); } .hx .hx-reason[data-go] { cursor: pointer; } .hx .hx-reason[data-go]:hover span { color: #6d28d9; text-decoration: underline; }
			.hx .hx-working { font-size: 12px; color: var(--hx-muted); display: grid; gap: 6px; align-content: start; } .hx .hx-working b { color: var(--hx-ink); font-size: 12px; }
			.hx .hx-working span { font-size: 14px; font-weight: 700; color: var(--hx-ink); font-variant-numeric: tabular-nums; } .hx .hx-working small { font-size: 11.5px; line-height: 1.5; color: var(--hx-muted); } .hx .hx-working a { color: #7c3aed !important; }
			.hx .hx-section { margin-top: 26px; } .hx .hx-section-head { display: flex; align-items: center; gap: 12px; margin: 0 0 14px; }
			.hx .hx-section-head span { font-size: 12px; font-weight: 800; color: #7c3aed; letter-spacing: .06em; }
			.hx .hx-section-head h3 { margin: 0; font-size: 15px; font-weight: 800; letter-spacing: -.01em; color: var(--hx-ink); }
			.hx .hx-section-head::after { content: ""; flex: 1; height: 1px; background: var(--hx-line); }
			.hx .hub-panel h6 { font-size: 13px; font-weight: 700; color: var(--hx-ink); letter-spacing: 0; }
			.hx .hub-row { margin-bottom: 18px; } .hx .hub-row:last-child { margin-bottom: 0; }
			.hx .seg-blue { background: #7c3aed !important; } .hx .seg-orange { background: #fb923c !important; } .hx .seg-green { background: #c4b5fd !important; } .hx .seg-red { background: #e11d48 !important; }
			.hx .hub-bar i { background: #7c3aed !important; }
			.hx .hub-stack > div, .hx .hub-bar > div { height: 8px !important; border: 0 !important; box-shadow: none !important; background: color-mix(in srgb, var(--g-text) 8%, transparent) !important; }
			.hx .hub-meter { height: 18px; border: 0; box-shadow: none; background: color-mix(in srgb, var(--g-text) 8%, transparent); } .hx .hub-meter i { line-height: 18px; font-size: 10.5px; } .hx .hub-meter i.seg-green { color: #5b21b6 !important; }
			.hx .hx-tiles .hub-tile { --acc: #7c3aed; } .hx .hx-tiles .hub-tile.hub-orange { --acc: #ea580c; }
			.hx .hub-panel a { color: #6d28d9; font-weight: 600; } .hx .hub-panel a:hover { color: #4c1d95; text-decoration: underline; }
			.hx .ph3-donut circle { stroke-width: 15; }
			.hx .hub-chart, .hx .frappe-chart { background: transparent !important; box-shadow: none !important; }
			.hx .legend-dataset-text { font-size: 11px !important; font-weight: 500 !important; }
			.hx .hub-stack { grid-template-columns: 130px 44px minmax(0, 1fr); } .hx .hub-bar { grid-template-columns: 130px 44px minmax(0, 1fr); }
			.hx .hub-stack b, .hx .hub-bar b { order: 2; text-align: left; } .hx .hub-stack > div, .hx .hub-bar > div { order: 3; }
			.hx .ph3-keys-3 span { grid-template-columns: 10px 90px auto; row-gap: 1px; } .hx .ph3-keys-3 em { grid-column: 2 / span 2; font-style: normal; font-size: 11px; color: var(--hx-muted); }
			.hx .hub-row-3 .ph3-donut-wrap { grid-template-columns: 120px minmax(0, 1fr); gap: 16px; } .hx .hub-row-3 .ph3-donut { width: 120px; height: 120px; }
			html[data-theme="dark"] .hx .hx-eyebrow, html[data-theme="dark"] .hx .hx-section-head span { color: #a78bfa; }
			html[data-theme="dark"] .hx .hx-ident { background: rgba(167, 139, 250, .16); color: #c4b5fd; }
			html[data-theme="dark"] .hx .hx-meter { background: rgba(255, 255, 255, .08); } html[data-theme="dark"] .hx .hx-meter i { background: #a78bfa; } html[data-theme="dark"] .hx .hx-metric-bad .hx-meter i { background: #fb7185; }
			html[data-theme="dark"] .hx .hx-level { background: rgba(34, 197, 94, .16); color: #86efac; } html[data-theme="dark"] .hx .hx-amber .hx-level { background: rgba(245, 158, 11, .18); color: #fcd34d; }
			html[data-theme="dark"] .hx .hx-red .hx-level { background: rgba(244, 63, 94, .18); color: #fda4af; } html[data-theme="dark"] .hx .hx-none .hx-level { background: rgba(148, 163, 184, .2); color: #e2e8f0; }
			html[data-theme="dark"] .hx .hx-reason { color: #cbd5e1; } html[data-theme="dark"] .hx .hx-reason[data-go]:hover span { color: #c4b5fd; }
			html[data-theme="dark"] .hx .hx-working a, html[data-theme="dark"] .hx .hub-panel a { color: #c4b5fd !important; } html[data-theme="dark"] .hx .hub-panel a:hover { color: #ddd6fe !important; }
			html[data-theme="dark"] .hx .seg-blue, html[data-theme="dark"] .hx .hub-bar i { background: #8b5cf6 !important; } html[data-theme="dark"] .hx .seg-green { background: #5b4b8a !important; }
			html[data-theme="dark"] .hx .hub-meter i.seg-green { color: #ede9fe !important; }
			/* compact: the report is read at a glance, so tighter spacing and flatter charts */
			.hx .hx-hero { padding: 18px 24px 14px; margin-bottom: 14px; } .hx .hx-hero h1 { font-size: 22px; margin: 4px 0 3px; }
			.hx .hx-hero-body { grid-template-columns: 190px minmax(0, 1fr); gap: 22px; margin-top: 10px; }
			.hx .hx-score svg { width: 170px; } .hx .hx-score > div { top: 34px; } .hx .hx-score > div b { font-size: 36px; } .hx .hx-score > div span { font-size: 10px; margin-top: 2px; }
			.hx .hx-level { margin-top: 4px; padding: 3px 12px; font-size: 12px; text-align: center; }
			.hx .hx-metrics { gap: 10px; } .hx .hx-metric { padding: 10px 14px; } .hx .hx-metric b { font-size: 26px; margin: 3px 0 7px; } .hx .hx-metric b small { font-size: 14px; } .hx .hx-metric em { margin-top: 5px; font-size: 11px; }
			.hx .hx-hero-foot { margin-top: 10px; padding-top: 10px; gap: 20px; } .hx .hx-reasons { gap: 0 18px; } .hx .hx-reason { padding: 3px 0; font-size: 12px; } .hx .hx-working { gap: 3px; } .hx .hx-working span { font-size: 13px; } .hx .hx-working small { line-height: 1.4; }
			.hx .hx-tiles { gap: 12px; margin-bottom: 0; } .hx .hx-tiles .hub-tile { padding: 10px 16px; } .hx .hx-tiles .hub-tile b { font-size: 24px; }
			.hx .hx-section { margin-top: 14px; } .hx .hx-section-head { margin: 0 0 8px; }
			.hx .hub-panel { padding: 12px 16px; } .hx .hub-panel h6 { margin: 0 0 8px; } .hx .hub-row { margin-bottom: 12px; }
			.hx .hub-stack, .hx .hub-bar { margin-bottom: 4px; } .hx .hub-meter { margin-bottom: 8px; }
			.hx .hub-row-3 .ph3-donut-wrap { grid-template-columns: 96px minmax(0, 1fr); } .hx .hub-row-3 .ph3-donut { width: 96px; height: 96px; }
			.hx .ph2-row { padding: 6px 0; }
			/* less to read: the long score explanation folds away and the matrix note is a tooltip */
			.hx .hx-foot-fold { display: block; margin-top: 8px; padding-top: 8px; } .hx .hx-why summary { cursor: pointer; list-style: none; width: fit-content; } .hx .hx-why summary::-webkit-details-marker { display: none; }
			.hx .hx-why-btn { display: inline-flex; align-items: center; gap: 6px; padding: 4px 13px; border-radius: 999px; font-size: 11.5px; font-weight: 600; color: var(--hx-muted); border: 1px solid var(--hx-line); background: color-mix(in srgb, var(--hx-ink) 3%, transparent); }
			.hx .hx-why summary:hover .hx-why-btn, .hx .hx-why[open] .hx-why-btn { color: var(--hx-ink); border-color: color-mix(in srgb, var(--ph-acc) 45%, transparent); background: color-mix(in srgb, var(--ph-acc) 10%, transparent); }
			.hx .hx-why-body { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 8px 20px; margin-top: 10px; align-items: start; } .hx .hx-why-body:not(:has(.hx-reasons)) { grid-template-columns: 1fr; }
			.hx .hx-why-score { grid-column: 1 / -1; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; padding-bottom: 6px; border-bottom: 1px solid var(--hx-line); }
			.hx .hx-why-score b { font-size: 12px; color: var(--hx-ink); } .hx .hx-why .hx-formula { font-size: 14px; font-weight: 700; color: var(--hx-ink); font-variant-numeric: tabular-nums; }
			.hx .hub-heat + .hub-sub { display: none; }
			.hx .hx-nostatus .hx-hero-body { grid-template-columns: 1fr; }
			@media (max-width: 1100px) { .hx .hx-hero-body, .hx .hx-hero-foot, .hx .hx-why-body { grid-template-columns: 1fr; } .hx .hx-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .hx .hx-reasons { grid-template-columns: 1fr; } }
			.hub-meter { display: flex; height: 22px; border-radius: 999px; overflow: hidden; box-shadow: var(--n-inset); margin-bottom: 12px; border: 1px solid var(--g-border); }
			.hub-meter i, .hub-stack i { display: block; font-style: normal; font-size: 11px; font-weight: 700; color: #fff; text-align: center; line-height: 22px; min-width: 0; }
			.seg-blue { background: #3b82f6; } .seg-green { background: #10b981; } .seg-orange { background: #f59e0b; } .seg-red { background: #ef4444; } .seg-yellow { background: #eab308; }
			.hub-legend { display: flex; gap: 16px; font-size: 11px; color: var(--g-muted); margin-bottom: 8px; }
			.hub-legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 5px; }
			.hub-stack { display: grid; grid-template-columns: 150px 1fr 44px; align-items: center; gap: 10px; font-size: 12px; margin-bottom: 8px; }
			.hub-stack > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
			.hub-stack > div { display: flex; height: 12px; border-radius: 999px; overflow: hidden; box-shadow: var(--n-inset); border: 1px solid var(--g-border); }
			.hub-stack > div i { height: 100%; line-height: 12px; } .hub-stack b { text-align: right; }
			.hub-badge { font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--g-glass-strong); border: 1px solid var(--g-border); }
			.hub-risk-late { color: #ef4444; } .hub-risk-risk { color: #f59e0b; } .hub-risk-ok { color: #10b981; }

			/* soft UI effects: every variant keeps the raised neumorphic base and adds its own surface effect */
			.auri-hub[data-hub-theme="soft-convex"] :is(.hub-tile, .hub-card, .hub-panel, .hub-status) {
				background: linear-gradient(145deg, color-mix(in srgb, var(--g-glass) 72%, #fff), color-mix(in srgb, var(--g-glass) 86%, #000)); }
			/* dark mode: a much smaller lift, otherwise the white highlight washes the text out */
			html[data-theme="dark"] .auri-hub[data-hub-theme="soft-convex"] :is(.hub-tile, .hub-card, .hub-panel, .hub-status) {
				background: linear-gradient(145deg, color-mix(in srgb, var(--g-glass) 92%, #fff), color-mix(in srgb, var(--g-glass) 90%, #000)); }
			html[data-theme="dark"] .auri-hub[data-hub-theme="soft-pearl"] :is(.hub-tile, .hub-card, .hub-panel, .hub-status) {
				background: linear-gradient(160deg, color-mix(in srgb, var(--g-glass) 93%, #fff) 0%, var(--g-glass) 62%); }
			.auri-hub[data-hub-theme="soft-pressed"] :is(.hub-card, .hub-panel, .hub-status) { box-shadow: var(--n-inset); }
			.auri-hub[data-hub-theme="soft-pressed"] .hub-panel .hub-tile, .auri-hub[data-hub-theme="soft-pressed"] .hub-table { box-shadow: var(--n-raised); }
			.auri-hub[data-hub-theme="soft-glow"] .hub-tile { box-shadow: var(--n-raised), 0 0 26px color-mix(in srgb, var(--acc) 32%, transparent); }
			.auri-hub[data-hub-theme="soft-glow"] .hub-tile b { text-shadow: 0 0 16px color-mix(in srgb, var(--acc) 60%, transparent); }
			.auri-hub[data-hub-theme="soft-glow"] .hub-status { box-shadow: var(--n-raised), 0 0 30px color-mix(in srgb, var(--lvl) 30%, transparent); }
			html[data-theme="dark"] .auri-hub[data-hub-theme="soft-glow"] :is(.hub-card, .hub-panel) { box-shadow: var(--n-raised), 0 0 0 1px var(--g-border), 0 0 28px color-mix(in srgb, var(--acc) 14%, transparent); }
			.auri-hub[data-hub-theme="soft-glow"] .hub-title h4 { text-shadow: 0 0 18px color-mix(in srgb, var(--acc) 40%, transparent); }
			.auri-hub[data-hub-theme="soft-pearl"] :is(.hub-tile, .hub-card, .hub-panel, .hub-status) {
				background: linear-gradient(160deg, color-mix(in srgb, var(--g-glass) 35%, #fff) 0%, var(--g-glass) 62%);
				box-shadow: var(--n-raised), inset 0 1px 0 var(--n-light), inset 0 -1px 0 rgba(0, 0, 0, .05); }

			/* flat: no shadows or gradients, solid coloured tiles */
			.auri-hub[data-hub-theme="flat-solid"] .hub-tile { box-shadow: none; background: var(--acc); border-color: transparent; }
			.auri-hub[data-hub-theme="flat-solid"] .hub-tile::before { display: none; }
			.auri-hub[data-hub-theme="flat-solid"] .hub-card:hover { transform: none; border-color: var(--acc); }
			.auri-hub[data-hub-theme="flat-solid"] .hub-tile *, .auri-hub[data-hub-theme="flat-solid"] .hub-tile b { color: #fff !important; }
			.auri-hub[data-hub-theme="flat-solid"] .hub-status { border-radius: var(--radius); }


			/* shared by Portfolio, My Work, Quality and Status Report */
			.hub-reason.hub-info i { background: #3b82f6; }
			/* risk register */
			.hub-rb { display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 11px; font-weight: 700; }
			.hub-rb-critical { color: #ef4444; background: rgba(239, 68, 68, .14); } .hub-rb-high { color: #f97316; background: rgba(249, 115, 22, .14); }
			.hub-rb-medium { color: #ca8a04; background: rgba(234, 179, 8, .16); } .hub-rb-low { color: #10b981; background: rgba(16, 185, 129, .14); }
			.hub-risk-levels { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
			.hub-risk-levels .hub-rb b { font-size: 14px; margin-right: 2px; }
			.hub-heat { display: grid; grid-template-columns: 22px repeat(5, minmax(0, 1fr)); gap: 5px; max-width: 360px; }
			.hub-heat-axis { font-size: 11px; color: var(--g-muted); text-align: center; align-self: center; }
			.hub-heat-cell { aspect-ratio: 1.25; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; color: #fff; opacity: .28; }
			.hub-heat-cell.has { opacity: 1; }
			.auri-hub [data-go] { cursor: pointer; } .auri-hub .hub-stack[data-go]:hover, .auri-hub .hub-rb[data-go]:hover { filter: brightness(.95); outline: 1px solid var(--g-border); border-radius: 6px; } .auri-hub .hub-heat-cell[data-go]:hover { outline: 2px solid var(--g-text); }
			.hub-heat-critical { background: #ef4444; } .hub-heat-high { background: #f97316; } .hub-heat-medium { background: #eab308; } .hub-heat-low { background: #10b981; }
			.auri-hub { --on-acc: #ffffff; } html[data-theme="dark"] .auri-hub { --on-acc: #0b1020; }
			.hub-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 14px; }
			.hub-chip { font-size: 12px; font-weight: 600; padding: 5px 14px; border-radius: 999px; cursor: pointer; user-select: none;
				background: var(--g-glass-strong); border: 1px solid var(--g-border); box-shadow: var(--n-soft); color: var(--g-text); }
			.hub-chip.active { background: var(--acc); color: var(--on-acc, #fff); border-color: transparent; box-shadow: none; }
			.hub-toolbar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 14px; }
			.hub-toolbar .hub-search { margin: 0; flex: 1 1 260px; }
			.hub-table.sortable th { cursor: pointer; white-space: nowrap; } .hub-table.sortable th.sorted::after { content: " \u25BE"; }
			.hub-table.sortable th.sorted.asc::after { content: " \u25B4"; }
			.hub-table td.num, .hub-table th.num { text-align: right; }
			.hub-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 7px; background: #9ca3af; vertical-align: middle; }
			.hub-dot.red { background: #ef4444; } .hub-dot.amber { background: #f59e0b; } .hub-dot.green { background: #10b981; }
			.hub-clickrow { cursor: pointer; }
			.hub-badge-warn { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; } .hub-badge-bad { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
			.hub-sub { color: var(--g-muted); font-size: 12px; }
			.hub-group summary { cursor: pointer; font-weight: 700; padding: 6px 0; } .hub-group { margin-bottom: 10px; }
			.hub-btn { font-size: 11px; padding: 2px 10px; border-radius: 999px; border: 1px solid var(--g-border); background: var(--g-glass-strong); color: var(--g-text); cursor: pointer; }
			.hub-btn:hover { background: var(--acc); color: var(--on-acc, #fff); }
			.hub-frame { width: 100%; min-height: 900px; border: 0; border-radius: calc(var(--radius) * .7); background: #f3f4f6; }
			.hub-mini { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; font-size: 12px; }
			.hub-mini .progress { flex: 1; }
			.hub-list-row { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; padding: 6px 0; border-bottom: 1px solid var(--g-border); }
			@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) { .hub-card, .hub-panel { background: var(--g-glass-strong); } }
	</style>`).appendTo("head");
};
})();
