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
		const refresh = () => this.refresh();
		this.project_field = page.add_field({ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", reqd: 1, change: () => this.on_project_change() });
		this.period_field = page.add_field({ fieldname: "period", label: __("Period"), fieldtype: "Select", options: Object.entries(SR_PERIODS).map(([k, v]) => ({ value: k, label: __(v) })), default: "7", change: () => this.on_period_change() });
		this.from_field = page.add_field({ fieldname: "from_date", label: __("From"), fieldtype: "Date", change: refresh });
		this.to_field = page.add_field({ fieldname: "to_date", label: __("To"), fieldtype: "Date", change: refresh });
		this.note_field = page.add_field({ fieldname: "note", label: __("Note to client"), fieldtype: "Data", change: refresh });
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
		(last ? Promise.resolve(last) : frappe.xcall("auri_pms.tracking.api.get_hub_projects").then((rows) => (rows[0] ? rows[0].name : ""))).then((name) => {
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
		this.apply_period();
		this.refresh();
	}

	on_project_change() {
		this.recipients = null;
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
				frappe.xcall("auri_pms.tracking.api.get_status_report_html", args),
				frappe.xcall("auri_pms.tracking.api.get_status_report_history", { project: args.project }),
			])
				.then(([preview, history]) => this.render(preview, history))
				.catch(() => this.$body.html(`<div class="text-muted p-4">${__("This report is not available (check the project and the dates).")}</div>`));
		}, 250);
	}

	render(preview, history) {
		this.preview = preview;
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
					<div class="hub-panel"><h6>${__("Recently sent")}</h6>${past}</div>
					<div class="hub-panel"><h6>${__("Automatic schedule")}</h6><div class="text-muted small">${__("Set Report Recipients and Send Weekly On and/or Send Monthly On Day (use both for a weekly and a monthly report) in the Auri PMS tab of the Project to email this report automatically.")}</div></div>
				</div>
			</div>`);
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
		this.page.add_inner_button(__("Download PDF"), () => {
			const a = this.args();
			window.open(`/api/method/auri_pms.tracking.api.status_report_pdf?${$.param(a)}`);
		});
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub", this.project_field.get_value()));
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
					.xcall("auri_pms.tracking.api.email_status_report", { ...args, recipients: values.recipients, subject: values.subject })
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
