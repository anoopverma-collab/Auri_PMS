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
		dark: { bg: "linear-gradient(135deg,#151826 0%,#1b1633 50%,#10242b 100%)", b1: "rgba(99,102,241,.32)", b3: "rgba(20,184,166,.22)", glass: "rgba(34,39,56,.55)", strong: "rgba(42,48,70,.78)", border: "rgba(255,255,255,.09)", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.045)", nd: "rgba(0,0,0,.55)", acc: "#818cf8", bar: "linear-gradient(90deg,#6366f1,#ec4899)", blur: 18, d: 7, bm: 2.2, r: 22 },
	},
	soft: {
		label: "Soft UI (Neumorphism)",
		light: { bg: "#e4e8ef", b1: "transparent", b3: "transparent", glass: "#e4e8ef", strong: "#e9edf3", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(163,177,198,.75)", acc: "#4f46e5", bar: "linear-gradient(90deg,#4f46e5,#7c3aed)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#25282e", b1: "transparent", b3: "transparent", glass: "#25282e", strong: "#2b2f36", border: "transparent", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.06)", nd: "rgba(0,0,0,.6)", acc: "#818cf8", bar: "linear-gradient(90deg,#6366f1,#a78bfa)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-convex": {
		label: "Soft UI - Convex",
		light: { bg: "#e6e9ef", b1: "transparent", b3: "transparent", glass: "#e6e9ef", strong: "#e6e9ef", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(163,177,198,.75)", acc: "#4f46e5", bar: "linear-gradient(90deg,#4f46e5,#7c3aed)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#25282e", b1: "transparent", b3: "transparent", glass: "#25282e", strong: "#25282e", border: "transparent", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.07)", nd: "rgba(0,0,0,.6)", acc: "#818cf8", bar: "linear-gradient(90deg,#6366f1,#a78bfa)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-pressed": {
		label: "Soft UI - Pressed",
		light: { bg: "#e1e5ec", b1: "transparent", b3: "transparent", glass: "#e1e5ec", strong: "#e1e5ec", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(155,170,192,.8)", acc: "#0f766e", bar: "linear-gradient(90deg,#0f766e,#22c55e)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#22252b", b1: "transparent", b3: "transparent", glass: "#22252b", strong: "#22252b", border: "transparent", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.06)", nd: "rgba(0,0,0,.65)", acc: "#2dd4bf", bar: "linear-gradient(90deg,#14b8a6,#4ade80)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-glow": {
		label: "Soft UI - Glow",
		light: { bg: "#e7e8f2", b1: "transparent", b3: "transparent", glass: "#e7e8f2", strong: "#e7e8f2", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(165,170,200,.75)", acc: "#6366f1", bar: "linear-gradient(90deg,#6366f1,#ec4899)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#141824", b1: "transparent", b3: "transparent", glass: "#141824", strong: "#141824", border: "transparent", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(120,130,200,.09)", nd: "rgba(0,0,0,.7)", acc: "#818cf8", bar: "linear-gradient(90deg,#818cf8,#f472b6)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	"soft-pearl": {
		label: "Soft UI - Pearl",
		light: { bg: "#eceff4", b1: "transparent", b3: "transparent", glass: "#eceff4", strong: "#eceff4", border: "transparent", text: "#374151", muted: "#6b7280", nl: "#ffffff", nd: "rgba(170,182,203,.7)", acc: "#2563eb", bar: "linear-gradient(90deg,#2563eb,#06b6d4)", blur: 0, d: 8, bm: 2.2, r: 24 },
		dark: { bg: "#1c1f26", b1: "transparent", b3: "transparent", glass: "#1c1f26", strong: "#1c1f26", border: "transparent", text: "#e5e7eb", muted: "#9ca3af", nl: "rgba(255,255,255,.08)", nd: "rgba(0,0,0,.6)", acc: "#60a5fa", bar: "linear-gradient(90deg,#3b82f6,#22d3ee)", blur: 0, d: 8, bm: 2.2, r: 24 },
	},
	minimal: {
		label: "Minimal Clean",
		light: { bg: "#f7f7f8", b1: "transparent", b3: "transparent", glass: "#ffffff", strong: "#ffffff", border: "#e5e7eb", text: "#111827", muted: "#6b7280", nl: "rgba(255,255,255,0)", nd: "rgba(17,24,39,.10)", acc: "#2563eb", bar: "linear-gradient(90deg,#2563eb,#2563eb)", blur: 0, d: 1, bm: 3, r: 12 },
		dark: { bg: "#0b0b0c", b1: "transparent", b3: "transparent", glass: "#151517", strong: "#1b1b1e", border: "#2a2a2e", text: "#f3f4f6", muted: "#9ca3af", nl: "rgba(255,255,255,0)", nd: "rgba(0,0,0,.6)", acc: "#60a5fa", bar: "linear-gradient(90deg,#60a5fa,#60a5fa)", blur: 0, d: 1, bm: 3, r: 12 },
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
ui.tile = (value, label, cls, sub, route) =>
	`<div class="hub-tile ${cls || ""}" ${route ? `data-route='${route}'` : ""}><b>${value}</b><span>${label}</span>${sub ? `<em>${sub}</em>` : ""}</div>`;

ui.panel = (title, body, cls) => `<div class="hub-panel ${cls || ""}"><h6>${title}</h6>${body}</div>`;

ui.bar = (label, value, max, cls) =>
	`<div class="hub-bar"><span>${ui.esc(label)}</span><div><i class="${cls || ""}" style="width:${max ? (value / max) * 100 : 0}%"></i></div><b>${flt(value, 1)}</b></div>`;

// Stacked rows with full labels (charts truncate long names): rows are [label, value1, value2, ...], one value per segment.
ui.stack = (rows, names, classes) => {
	const sum = (r) => r.slice(1).reduce((a, b) => a + b, 0);
	const max = Math.max(1, ...rows.map(sum));
	const legend = `<div class="hub-legend">${names.map((n, i) => `<span><i class="${classes[i]}"></i>${n}</span>`).join("")}</div>`;
	return (
		legend +
		(rows.length
			? rows
					.map(
						(r) => `<div class="hub-stack"><span title="${ui.esc(r[0])}">${ui.esc(r[0])}</span><div>${r
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

ui.link = (doctype, name, label) => `<a href="/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}">${ui.esc(label || name)}</a>`;

ui.chart = ($root, selector, config) => {
	const el = $root.find(selector)[0];
	if (el) new frappe.Chart(el, { height: 230, ...config });
};

// Traffic-light banner: {level, label, score, reasons: [{level, text}]}
ui.statusBanner = (st, scoreLabel) =>
	`<div class="hub-status hub-${st.level}">
		<div class="hub-status-dial"><b>${st.score === null || st.score === undefined ? "-" : st.score}</b><span><strong style="font-weight:800;font-size:10px;color:inherit">${scoreLabel || __("health")}</strong></span></div>
		<div><h5>${ui.esc(st.label)}</h5><ul>${(st.reasons || []).map((r) => `<li class="hub-reason hub-${r.level}"><i></i>${ui.esc(r.text)}</li>`).join("")}</ul></div>
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
			.hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 22px; }
			.hub-card { padding: 18px 20px; cursor: pointer; transition: transform .18s ease; }
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
			.hub-tile[data-route] { cursor: pointer; } .hub-tile[data-route]:hover { transform: translateY(-2px); }
			.hub-tile[data-route]:active { transform: none; box-shadow: var(--n-inset); }
			.hub-blue { --acc: #3b82f6; } .hub-red { --acc: #ef4444; } .hub-purple { --acc: #8b5cf6; } .hub-orange { --acc: #f59e0b; }
			.hub-cyan { --acc: #06b6d4; } .hub-green { --acc: #10b981; } .hub-teal { --acc: #14b8a6; }
			.auri-hub[data-hub-theme="mono"] .hub-tile { --acc: var(--g-text); }
			.auri-hub[data-hub-theme="mono"] .hub-tile.hub-red b { text-decoration: underline; }

			.hub-cols { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 22px; }
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
			.hub-meter { display: flex; height: 22px; border-radius: 999px; overflow: hidden; box-shadow: var(--n-inset); margin-bottom: 12px; border: 1px solid var(--g-border); }
			.hub-meter i, .hub-stack i { display: block; font-style: normal; font-size: 11px; font-weight: 700; color: #fff; text-align: center; line-height: 22px; min-width: 0; }
			.seg-blue { background: #3b82f6; } .seg-green { background: #10b981; } .seg-orange { background: #f59e0b; }
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
			.auri-hub[data-hub-theme="soft-pressed"] :is(.hub-card, .hub-panel, .hub-status) { box-shadow: var(--n-inset); }
			.auri-hub[data-hub-theme="soft-pressed"] .hub-panel .hub-tile, .auri-hub[data-hub-theme="soft-pressed"] .hub-table { box-shadow: var(--n-raised); }
			.auri-hub[data-hub-theme="soft-glow"] .hub-tile { box-shadow: var(--n-raised), 0 0 26px color-mix(in srgb, var(--acc) 32%, transparent); }
			.auri-hub[data-hub-theme="soft-glow"] .hub-tile b { text-shadow: 0 0 16px color-mix(in srgb, var(--acc) 60%, transparent); }
			.auri-hub[data-hub-theme="soft-glow"] .hub-status { box-shadow: var(--n-raised), 0 0 30px color-mix(in srgb, var(--lvl) 30%, transparent); }
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
			.hub-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 14px; }
			.hub-chip { font-size: 12px; font-weight: 600; padding: 5px 14px; border-radius: 999px; cursor: pointer; user-select: none;
				background: var(--g-glass-strong); border: 1px solid var(--g-border); box-shadow: var(--n-soft); color: var(--g-text); }
			.hub-chip.active { background: var(--acc); color: #fff; border-color: transparent; box-shadow: none; }
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
			.hub-btn:hover { background: var(--acc); color: #fff; }
			.hub-frame { width: 100%; min-height: 900px; border: 0; border-radius: calc(var(--radius) * .7); background: #f3f4f6; }
			.hub-mini { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; font-size: 12px; }
			.hub-mini .progress { flex: 1; }
			.hub-list-row { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; padding: 6px 0; border-bottom: 1px solid var(--g-border); }
			@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) { .hub-card, .hub-panel { background: var(--g-glass-strong); } }
	</style>`).appendTo("head");
};
})();
