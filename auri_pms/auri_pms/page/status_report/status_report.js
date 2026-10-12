// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

/* global auri_pms */
// Client status report: preview, email (with a saved log) and PDF for one project and period.
let ui; // shared UI kit (auri_hub.bundle.js)

frappe.pages["status-report"].on_page_load = function (wrapper) {
	frappe.require("auri_hub.bundle.js", () => {
		ui = auri_pms.ui;
		wrapper.status_report = new StatusReport(wrapper);
		wrapper.status_report.show(frappe.get_route()[1]);
	});
};

frappe.pages["status-report"].on_page_show = function (wrapper) {
	if (wrapper.status_report) wrapper.status_report.show(frappe.get_route()[1]);
};

const SR_PERIODS = { 7: "Last 7 days", 14: "Last 14 days", 30: "Last 30 days", custom: "Custom range" };

class StatusReport {
	constructor(wrapper) {
		const { page, $body } = ui.initPage(wrapper, "Client Status Report");
		this.page = page;
		this.$body = $body;
		this.excluded = new Set(); // tickets removed from this report only
		this.included = new Map(); // tickets added to this report only, with a note for the client
		this.sections = {}; // section switches changed for this report only
		this.order = []; // section order changed for this report only (empty: PMS Settings or the layout's own)
		const refresh = () => this.refresh();
		this.project_field = page.add_field({ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", reqd: 1, change: () => this.on_project_change() });
		this.period_field = page.add_field({ fieldname: "period", label: __("Period"), fieldtype: "Select", options: Object.entries(SR_PERIODS).map(([k, v]) => ({ value: k, label: __(v) })), default: "7", change: () => this.on_period_change() });
		this.from_field = page.add_field({ fieldname: "from_date", label: __("From"), fieldtype: "Date", change: refresh });
		this.to_field = page.add_field({ fieldname: "to_date", label: __("To"), fieldtype: "Date", change: refresh });
		this.note_field = page.add_field({ fieldname: "note", label: __("Note to client"), fieldtype: "Data", change: refresh });
		this.template_field = page.add_field({ fieldname: "template", label: __("Email Template"), fieldtype: "Link", options: "Email Template", get_query: () => ({ filters: { auri_pms_enabled: 1 } }), change: refresh });
		this.builtin_field = page.add_field({ fieldname: "builtin_layout", label: __("Built-in layout"), fieldtype: "Check", change: () => this.on_builtin_change() });
		this.period_field.set_value("7");
		this.apply_period();
	}

	show(project) {
		ui.showSidebar();
		this.page.clear_inner_toolbar();
		this.page.clear_primary_action();
		ui.applyTheme(this.$body);
		ui.addThemeMenu(this.page, () => this.show(this.project_field.get_value()));
		if (project && decodeURIComponent(project) !== this.project_field.get_value()) this.project_field.set_value(decodeURIComponent(project));
		else if (!this.project_field.get_value()) this.preselect_project();
		else this.refresh();
	}

	// Open with a project instead of a blank page: the last one used, else the first one the user can see.
	preselect_project() {
		let last = "";
		try {
			last = localStorage.getItem("auri_status_project") || "";
		} catch (e) {
			// storage can be blocked; fall back to the first project
		}
		(last ? Promise.resolve(last) : frappe.xcall("auri_pms.auri_pms.api.get_hub_projects").then((rows) => (rows[0] ? rows[0].name : ""))).then((name) => {
			if (name) this.project_field.set_value(name);
			else this.refresh();
		});
	}

	apply_period() {
		const key = this.period_field.get_value();
		const custom = key === "custom";
		[this.from_field, this.to_field].forEach((f) => f.$wrapper.toggle(custom));
		if (!custom) {
			this.from_field.set_value(frappe.datetime.add_days(frappe.datetime.get_today(), -cint(key || 7)));
			this.to_field.set_value(frappe.datetime.get_today());
		}
	}

	on_period_change() {
		this.excluded.clear();
		this.included.clear();
		this.apply_period();
		this.refresh();
	}

	on_builtin_change() {
		this.template_field.$wrapper.toggle(!cint(this.builtin_field.get_value()));
		this.refresh();
	}

	on_project_change() {
		this.recipients = null;
		this.excluded.clear();
		this.included.clear();
		this.sections = {};
		this.order = [];
		try {
			if (this.project_field.get_value()) localStorage.setItem("auri_status_project", this.project_field.get_value());
		} catch (e) {
			// storage can be blocked
		}
		this.refresh();
	}

	args() {
		return {
			project: this.project_field.get_value(),
			from_date: this.from_field.get_value(),
			to_date: this.to_field.get_value(),
			note: this.note_field.get_value() || "",
			exclude: JSON.stringify([...this.excluded]),
			include: JSON.stringify(Object.fromEntries(this.included)),
			sections: JSON.stringify(this.sections),
			order: JSON.stringify(this.order),
			template: cint(this.builtin_field.get_value()) ? "__builtin__" : this.template_field.get_value() || "",
		};
	}

	refresh() {
		const args = this.args();
		if (!args.project || !args.from_date || !args.to_date) {
			this.$body.html(`<div class="hub-title"><h4>${__("Client Status Report")}</h4><span class="text-muted">${__("Choose a project to preview its report.")}</span></div>`);
			return;
		}
		clearTimeout(this.timer);
		this.timer = setTimeout(() => {
			this.$body.html(`<div class="text-muted p-4">${__("Building the report...")}</div>`);
			Promise.all([
				frappe.xcall("auri_pms.auri_pms.api.get_status_report_html", args),
				frappe.xcall("auri_pms.auri_pms.api.get_status_report_history", { project: args.project }),
			])
				.then(([preview, history]) => this.render(preview, history))
				.catch(() => this.$body.html(`<div class="text-muted p-4">${__("This report is not available (check the project and the dates).")}</div>`));
		}, 250);
	}

	render(preview, history) {
		this.preview = preview;
		this.template_field.set_description(preview.default_template ? __("Empty uses {0} (PMS Settings)", [preview.default_template]) : __("Empty uses the built-in layout"));
		const esc = ui.esc;
		const past = history.length
			? history
					.map((h) => `<div class="hub-list-row"><span>${ui.link("Project Status Report", h.name, `${frappe.datetime.str_to_user(h.from_date)} - ${frappe.datetime.str_to_user(h.to_date)}`)}${cint(h.scheduled) ? ` <span class="hub-badge">${__("scheduled")}</span>` : ""}</span><span class="hub-sub">${esc(h.sent_to)}</span></div>`)
					.join("")
			: `<div class="text-muted small">${__("Nothing has been sent yet.")}</div>`;
		this.$body.html(`
			<div class="hub-title"><h4>${__("Client Status Report")}</h4><span class="text-muted">${__("Preview of the email and PDF")}</span></div>
			<div class="hub-cols">
				<div class="hub-col"><div class="hub-panel"><h6>${__("Preview")}</h6><iframe class="hub-frame" sandbox="allow-same-origin" title="${__("Report preview")}"></iframe></div></div>
				<div class="hub-col">
					${preview.status ? ui.statusBanner(preview.status) : ""}
					<div class="hub-panel"><h6>${__("Tickets in this report")}</h6>${this.tickets_panel(preview.tickets)}</div>
					<div class="hub-panel"><h6>${__("Recently sent")}</h6>${past}</div>
					<div class="hub-panel"><h6>${__("Automatic schedule")}</h6><div class="text-muted small">${__("Set Report Recipients and Send Weekly On and/or Send Monthly On Day (use both for a weekly and a monthly report) in the Auri PMS tab of the Project to email this report automatically.")}</div></div>
				</div>
			</div>`);
		this.$body.find("[data-exclude]").on("click", (e) => {
			this.excluded.add($(e.currentTarget).attr("data-exclude"));
			this.refresh();
		});
		this.$body.find("[data-unadd]").on("click", (e) => {
			this.included.delete($(e.currentTarget).attr("data-unadd"));
			this.refresh();
		});
		this.$body.find("[data-note]").on("change", (e) => {
			this.included.set($(e.currentTarget).attr("data-note"), $(e.currentTarget).val());
			this.refresh();
		});
		this.make_add_ticket_control();
		this.$body.find("[data-restore]").on("click", (e) => {
			this.excluded.delete($(e.currentTarget).attr("data-restore"));
			this.refresh();
		});
		const frame = this.$body.find("iframe")[0];
		frame.addEventListener("load", () => {
			try {
				frame.style.height = `${frame.contentDocument.documentElement.scrollHeight + 30}px`;
			} catch (e) {
				/* keep the default height */
			}
		});
		frame.srcdoc = preview.html;
		this.page.clear_primary_action();
		if (preview.can_send) this.page.set_primary_action(__("Email report"), () => this.email_dialog(), "mail");
		this.page.add_inner_button(__("Sections"), () => this.section_dialog());
		this.page.add_inner_button(__("Download PDF"), () => {
			const a = this.args();
			window.open(`/api/method/auri_pms.auri_pms.api.status_report_pdf?${$.param(a)}`);
		});
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub", this.project_field.get_value()));
	}

	// Remove a ticket from this send only; "Hide from Client Report" on the ticket removes it from every report.
	tickets_panel(tickets) {
		const esc = ui.esc;
		const rows = (tickets || [])
			.map((t) => `<div class="hub-list-row"><span>${ui.link("Work Item", t.name, t.name)} ${esc(t.subject)} <span class="hub-sub">${esc(t.section)}</span></span><a class="text-danger" data-exclude="${esc(t.name)}" title="${__("Remove from this report")}">&times;</a></div>`)
			.join("");
		const removed = [...this.excluded]
			.map((name) => `<div class="hub-list-row"><span class="text-muted">${esc(name)}</span><a data-restore="${esc(name)}">${__("Restore")}</a></div>`)
			.join("");
		const added = (this.preview.added || [])
			.map((t) => `<div class="hub-list-row"><span>${ui.link("Work Item", t.name, t.name)} ${esc(t.subject)} <span class="hub-sub">${__("Added")}</span><input class="form-control input-xs" style="margin-top:4px" data-note="${esc(t.name)}" placeholder="${__("Note for the client (optional)")}" maxlength="500" value="${esc(this.included.get(t.name) || "")}"></span><a class="text-danger" data-unadd="${esc(t.name)}" title="${__("Remove from this report")}">&times;</a></div>`)
			.join("");
		return `${rows || `<div class="text-muted small">${__("No tickets are listed in this report.")}</div>`}${added}${removed ? `<div class="hub-sub" style="margin-top:8px">${__("Removed from this report")}</div>${removed}` : ""}
			<div class="hub-sub" style="margin-top:10px">${__("Add a ticket")}</div><div class="hub-add-ticket"></div>`;
	}

	// Pick any ticket of the project (even a hidden one or one past the section limit) to list it in an extra section.
	make_add_ticket_control() {
		const project = this.project_field.get_value();
		const control = frappe.ui.form.make_control({
			parent: this.$body.find(".hub-add-ticket"),
			df: {
				fieldtype: "Link",
				options: "Work Item",
				fieldname: "add_ticket",
				placeholder: __("Search a ticket"),
				get_query: () => ({ filters: { project } }),
				change: () => {
					const name = control.get_value();
					if (!name) return;
					this.excluded.delete(name);
					this.included.set(name, this.included.get(name) || "");
					this.refresh();
				},
			},
			render_input: true,
		});
	}

	// Choose which sections the report lists and in what order (this report only).
	section_dialog() {
		const labels = { modules: __("Progress by module"), waiting: __("Waiting on client"), delivered: __("Delivered"), in_progress: __("In progress"), next_up: __("Coming up next"), extra: __("Additional tickets"), issues: __("Risks and issues"), plan: __("Plan (sprint and releases)"), risks: __("Risk register mitigation"), time: __("Time spent") };
		const figures = { created: __("New tickets count"), completion: __("Completion percentage") };
		const order = (this.preview.order || []).filter((k) => labels[k]);
		Object.keys(labels).forEach((k) => !order.includes(k) && order.push(k));
		const state = { ...(this.preview.sections || {}) };
		const dialog = new frappe.ui.Dialog({
			title: __("Sections in this report"),
			fields: [{ fieldtype: "HTML", fieldname: "list" }],
			primary_action_label: __("Apply"),
			primary_action: () => {
				this.order = order.slice();
				this.sections = { ...state };
				dialog.hide();
				this.refresh();
			},
		});
		const $box = dialog.fields_dict.list.$wrapper;
		const draw = () => {
			const rows = order
				.map((key, i) => `<div class="sr-row" draggable="true" data-index="${i}" style="display:flex;align-items:center;gap:8px;padding:5px 4px;border-bottom:1px solid var(--border-color);background:var(--control-bg, transparent)">
					<span class="text-muted" style="cursor:grab;user-select:none" title="${__("Drag to move")}">&#9776;</span>
					<span style="flex:1">${labels[key]}</span>
					<input type="checkbox" data-key="${key}" ${cint(state[key]) ? "checked" : ""}>
				</div>`)
				.join("");
			const extra = Object.entries(figures)
				.map(([key, label]) => `<div style="display:flex;align-items:center;gap:8px;padding:5px 4px;border-bottom:1px solid var(--border-color)"><span style="width:14px"></span><span style="flex:1">${label}</span><input type="checkbox" data-key="${key}" ${cint(state[key]) ? "checked" : ""}></div>`)
				.join("");
			$box.html(`<div class="text-muted small" style="margin-bottom:6px">${__("Tick the sections to include, then drag the rows to reorder them.")}</div>${rows}<div class="text-muted small" style="margin:14px 0 4px">${__("Summary figures")}</div>${extra}`);
			$box.find("input[data-key]").on("change", (e) => (state[$(e.currentTarget).attr("data-key")] = e.currentTarget.checked ? 1 : 0));
			const move = (from, to) => {
				if (from === to || to < 0 || to >= order.length) return;
				order.splice(to, 0, order.splice(from, 1)[0]);
				draw();
			};
			// drag a row onto another to put it there
			let dragged = null;
			$box.find(".sr-row")
				.on("dragstart", (e) => {
					dragged = cint($(e.currentTarget).attr("data-index"));
					e.originalEvent.dataTransfer.effectAllowed = "move";
					e.originalEvent.dataTransfer.setData("text/plain", String(dragged));
					$(e.currentTarget).css("opacity", 0.4);
				})
				.on("dragend", (e) => $(e.currentTarget).css("opacity", 1))
				.on("dragover", (e) => {
					e.preventDefault();
					$(e.currentTarget).css("box-shadow", "inset 0 2px 0 var(--primary)");
				})
				.on("dragleave", (e) => $(e.currentTarget).css("box-shadow", ""))
				.on("drop", (e) => {
					e.preventDefault();
					if (dragged !== null) move(dragged, cint($(e.currentTarget).attr("data-index")));
					dragged = null;
				});
		};
		draw();
		dialog.show();
	}

	email_dialog() {
		const args = this.args();
		const dialog = new frappe.ui.Dialog({
			title: __("Email status report"),
			fields: [
				{ fieldname: "recipients", label: __("Recipients"), fieldtype: "Small Text", reqd: 1, default: this.recipients || this.preview.recipients, description: __("Email addresses separated by commas or new lines") },
				{ fieldname: "subject", label: __("Subject"), fieldtype: "Data", reqd: 1, default: this.preview.subject },
			],
			primary_action_label: __("Send"),
			primary_action: (values) => {
				frappe
					.xcall("auri_pms.auri_pms.api.email_status_report", { ...args, recipients: values.recipients, subject: values.subject })
					.then((name) => {
						dialog.hide();
						this.recipients = values.recipients;
						frappe.show_alert({ message: __("Report queued for sending ({0})", [name]), indicator: "green" });
						this.refresh();
					});
			},
		});
		dialog.show();
	}
}
