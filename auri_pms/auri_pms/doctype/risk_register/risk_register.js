// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

const RISK_COLORS = { Critical: "red", High: "orange", Medium: "yellow", Low: "green" };

frappe.ui.form.on("Risk Register", {
	refresh(frm) {
		frm.trigger("load_radar");
		frm.trigger("render_guide");
		if (frm.is_new()) return;
		const level = frm.doc.risk_level;
		// set_headline appends a block on every call, and refresh runs more than once after a save.
		frm.dashboard.clear_headline();
		if (level) frm.dashboard.set_headline(`<span class="indicator-pill ${RISK_COLORS[level] || "gray"}">${__(level)} · ${__("score")} ${frm.doc.risk_score}</span>`);
		if (frm.doc.status !== "Closed" && frm.perm[0].write) {
			frm.add_custom_button(__("Close Risk"), () => frm.events.close_risk(frm)).addClass("btn-primary");
		}
		frm.add_custom_button(__("Project Health"), () => frappe.set_route("project-hub", frm.doc.project, "health"), __("View"));
	},
	project: (frm) => frm.trigger("load_radar"),
	probability: (frm) => frm.trigger("preview_score"),
	impact: (frm) => frm.trigger("preview_score"),
	// The 5 x 5 matrix: score = probability x impact, coloured by the PMS Settings thresholds; this risk's cell is outlined.
	render_guide(frm) {
		const limits = frappe.boot.auri_pms_risk_thresholds || { medium: 5, high: 10, critical: 15 };
		const level = (score) => (score >= limits.critical ? "critical" : score >= limits.high ? "high" : score >= limits.medium ? "medium" : "low");
		const options = (name) => (frm.fields_dict[name].df.options || "").split("\n").filter(Boolean);
		const value = (label) => cint((label || "0").split(" ")[0]);
		const probabilities = options("probability");
		const impacts = options("impact");
		const [p, i] = [value(frm.doc.probability), value(frm.doc.impact)];
		const rows = [...probabilities].reverse().map((plabel) => {
			const pv = value(plabel);
			const cells = impacts.map((ilabel) => {
				const iv = value(ilabel);
				const here = pv === p && iv === i ? " auri-risk-here" : "";
				return `<td class="auri-risk-${level(pv * iv)}${here}">${pv * iv}</td>`;
			});
			return `<tr><th>${frappe.utils.escape_html(__(plabel))}</th>${cells.join("")}</tr>`;
		});
		const head = impacts.map((label) => `<th>${frappe.utils.escape_html(__(label))}</th>`).join("");
		const legend = [
			["low", __("Low"), `1 - ${limits.medium - 1}`],
			["medium", __("Medium"), `${limits.medium} - ${limits.high - 1}`],
			["high", __("High"), `${limits.high} - ${limits.critical - 1}`],
			["critical", __("Critical"), `${limits.critical} - 25`],
		]
			.map(([key, label, range]) => `<span class="auri-chip"><span class="auri-risk-dot auri-risk-${key}"></span>${label} ${range}</span>`)
			.join("");
		frm.fields_dict.scoring_guide.$wrapper.html(
			`<div class="auri-risk-matrix">
				<p class="text-muted small">${__("Risk Score = Probability x Impact (1 to 25). The level comes from the thresholds in PMS Settings (Risk & Health). Rows: probability. Columns: impact.")}</p>
				<table class="table table-bordered table-sm"><thead><tr><th></th>${head}</tr></thead><tbody>${rows.join("")}</tbody></table>
				<div class="auri-chips">${legend}</div>
				${radar_html(frm, limits)}
			</div>`
		);
	},
	close_risk(frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Close Risk {0}", [frm.doc.name]),
			fields: [
				{ fieldname: "closed_on", fieldtype: "Date", label: __("Closed On"), reqd: 1, default: frappe.datetime.get_today(), max_date: frappe.datetime.get_today() },
				{ fieldname: "closing_remark", fieldtype: "Small Text", label: __("Closing Remark"), reqd: 1 },
			],
			primary_action_label: __("Close Risk"),
			primary_action(values) {
				dialog.hide();
				frm.set_value({ status: "Closed", closed_on: values.closed_on, closing_remark: values.closing_remark }).then(() => frm.save());
			},
		});
		dialog.show();
	},
	load_radar(frm) {
		if (!frm.doc.project) {
			frm._radar_rows = [];
			return frm.trigger("render_guide");
		}
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Risk Register",
				filters: { project: frm.doc.project, status: ["in", ["Identified", "Mitigating", "Monitoring"]] },
				fields: ["name", "title", "risk_score", "risk_level"],
				order_by: "risk_score desc",
				limit_page_length: 12,
			},
			callback: (r) => {
				frm._radar_rows = r.message || [];
				frm.trigger("render_guide");
			},
		});
	},
	preview_score(frm) {
		frm.trigger("render_guide");
		const value = (s) => cint((s || "0").split(" ")[0]);
		const score = value(frm.doc.probability) * value(frm.doc.impact);
		frm.set_value("risk_score", score);
		const limits = frappe.boot.auri_pms_risk_thresholds || { medium: 5, high: 10, critical: 15 };
		frm.set_value("risk_level", score >= limits.critical ? "Critical" : score >= limits.high ? "High" : score >= limits.medium ? "Medium" : score ? "Low" : "");
	},
});

// Radar of the project's open risks: one axis per risk, distance from the centre = score (1 to 25).
function radar_html(frm, limits) {
	const FILLS = { Low: "#10b981", Medium: "#eab308", High: "#f97316", Critical: "#ef4444" };
	const levelOf = (score) => (score >= limits.critical ? "Critical" : score >= limits.high ? "High" : score >= limits.medium ? "Medium" : score ? "Low" : "");
	const value = (label) => cint((label || "0").split(" ")[0]);
	const draft = value(frm.doc.probability) * value(frm.doc.impact);
	// This risk shows its unsaved score; the others come from the database.
	let rows = (frm._radar_rows || []).filter((r) => r.name !== frm.doc.name).map((r) => ({ ...r, score: cint(r.risk_score) }));
	if (draft) rows.push({ name: frm.doc.name, title: frm.doc.title, score: draft, current: true });
	rows = rows.sort((a, b) => b.score - a.score).slice(0, 12);
	const heading = `<h6 class="mt-4">${__("Open risks in this project")}</h6>`;
	if (rows.length < 3) {
		return `${heading}<p class="text-muted small">${__("The radar needs at least 3 open risks in the project.")}</p>`;
	}
	const [W, H, R] = [550, 400, 115];
	const [cx, cy] = [W / 2, H / 2];
	const n = rows.length;
	const point = (index, score) => {
		const angle = (index / n) * 2 * Math.PI - Math.PI / 2;
		const d = (Math.min(score, 25) / 25) * R;
		return [cx + d * Math.cos(angle), cy + d * Math.sin(angle), angle];
	};
	const ring = (score) => rows.map((_, k) => point(k, score).slice(0, 2).join(",")).join(" ");
	const rings = [limits.medium, limits.high, limits.critical, 25]
		.map((score) => {
			const [x, y] = point(0, score);
			return `<polygon points="${ring(score)}" fill="none" stroke="currentColor" stroke-opacity="0.18" ${score === 25 ? "" : 'stroke-dasharray="4 4"'}/>` +
				`<text x="${x + 6}" y="${y + 4}" font-size="11" fill="currentColor" fill-opacity="0.55">${score}</text>`;
		})
		.join("");
	const spokes = rows
		.map((r, k) => {
			const [x, y, angle] = point(k, 25);
			const [lx, ly] = [cx + (R + 18) * Math.cos(angle), cy + (R + 18) * Math.sin(angle)];
			const anchor = Math.abs(Math.cos(angle)) < 0.25 ? "middle" : Math.cos(angle) > 0 ? "start" : "end";
			const id = (r.name || __("This risk")).split("-").pop();
			const label = frappe.utils.escape_html(`${id} ${(r.title || "").length > 18 ? (r.title || "").slice(0, 17) + "…" : r.title || ""}`);
			return `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="currentColor" stroke-opacity="0.18"/>` +
				`<text x="${lx}" y="${ly}" text-anchor="${anchor}" dominant-baseline="middle" font-size="12" fill="currentColor" ${r.current ? 'font-weight="700"' : 'fill-opacity="0.8"'}>${label}</text>`;
		})
		.join("");
	const shape = rows.map((r, k) => point(k, r.score).slice(0, 2).join(",")).join(" ");
	const dots = rows
		.map((r, k) => {
			const [x, y] = point(k, r.score);
			const colour = FILLS[levelOf(r.score)];
			return `<circle cx="${x}" cy="${y}" r="${r.current ? 8 : 5}" fill="${colour}" stroke="${r.current ? "currentColor" : "#fff"}" stroke-width="${r.current ? 3 : 1.5}"><title>${frappe.utils.escape_html(`${r.name || ""} ${r.title || ""}: ${r.score}`)}</title></circle>`;
		})
		.join("");
	return `${heading}<svg viewBox="0 0 ${W} ${H}" style="display:block;width:100%;max-width:550px;height:auto;margin:0 auto;color:var(--text-color)" role="img" aria-label="${__("Radar of open risk scores")}">${rings}${spokes}<polygon points="${shape}" fill="#ef4444" fill-opacity="0.14" stroke="#ef4444" stroke-width="2"/>${dots}</svg>
		<p class="text-muted small">${__("One axis per open risk, farthest from the centre = highest score. Rings mark the Medium, High and Critical thresholds and the maximum of 25. The ringed dot is this risk.")}</p>`;
}
