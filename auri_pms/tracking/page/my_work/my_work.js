// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

/* global auri_pms */
// My Work: my open tickets by due date, what blocks me, my hours this week and my sprints.
let ui; // shared UI kit (auri_hub.bundle.js)

frappe.pages["my-work"].on_page_load = function (wrapper) {
	frappe.require("auri_hub.bundle.js", () => {
		ui = auri_pms.ui;
		wrapper.my_work = new MyWork(wrapper);
		wrapper.my_work.load();
	});
};

frappe.pages["my-work"].on_page_show = function (wrapper) {
	if (wrapper.my_work) wrapper.my_work.load();
};

const MW_GROUPS = [
	["overdue", "Overdue", true],
	["today", "Due today", true],
	["week", "Due this week", true],
	["later", "Later", false],
	["no_due", "No due date", false],
];

class MyWork {
	constructor(wrapper) {
		const { page, $body } = ui.initPage(wrapper, "My Work");
		this.page = page;
		this.$body = $body;
	}

	load() {
		this.page.clear_inner_toolbar();
		this.page.clear_menu();
		ui.applyTheme(this.$body);
		this.page.add_inner_button(__("Refresh"), () => this.load());
		this.page.add_inner_button(__("Project Hub"), () => frappe.set_route("project-hub"));
		ui.addThemeMenu(this.page, () => this.load());
		this.$body.html(`<div class="text-muted p-4">${__("Loading...")}</div>`);
		frappe.xcall("auri_pms.tracking.api.get_my_work").then((data) => {
			this.data = data;
			this.render();
		});
	}

	log_time(name, subject) {
		frappe.prompt(
			[
				{ fieldname: "hours", label: __("Hours"), fieldtype: "Float", reqd: 1 },
				{ fieldname: "activity_type", label: __("Activity"), fieldtype: "Link", options: "Activity Type", reqd: 1 },
				{ fieldname: "is_billable", label: __("Billable"), fieldtype: "Check", default: 1 },
				{ fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
				{ fieldname: "comment", label: __("Comment"), fieldtype: "Small Text" },
			],
			(values) =>
				frappe.xcall("auri_pms.tracking.api.log_time", { work_item: name, ...values }).then(() => {
					frappe.show_alert({ message: __("Time logged on {0}", [name]), indicator: "green" });
					this.load();
				}),
			__("Log time: {0}", [subject.length > 60 ? `${subject.slice(0, 57)}...` : subject]),
			__("Log")
		);
	}

	ticket_table(rows) {
		const esc = ui.esc;
		return `<table class="table table-sm hub-table"><thead><tr><th>${__("Ticket")}</th><th>${__("Summary")}</th><th>${__("Status")}</th><th>${__("Priority")}</th><th>${__("Due")}</th><th></th></tr></thead><tbody>${rows
			.map((i) => {
				const badges = [
					i.blocked_by.length ? `<span class="hub-badge hub-badge-bad" title="${esc(i.blocked_by.join(", "))}">${__("Blocked")}</span>` : "",
					cint(i.dependent_on_client) ? `<span class="hub-badge hub-badge-warn" title="${esc(i.client_dependency_note || "")}">${__("Waiting on client")}</span>` : "",
				].join(" ");
				return `<tr><td style="white-space:nowrap">${ui.link("Work Item", i.name)}</td>
					<td>${esc(i.subject)} ${badges}<div class="hub-sub">${esc(i.project_label)}${i.module ? ` · ${esc(i.module)}` : ""}</div></td><td>${esc(__(i.status))}</td><td>${esc(__(i.priority))}</td>
					<td class="${i.days_overdue ? "text-danger" : ""}" style="white-space:nowrap">${i.due_date ? frappe.datetime.str_to_user(i.due_date) : ""}${i.days_overdue ? `<div class="hub-sub">${__("{0} days late", [i.days_overdue])}</div>` : ""}</td>
					<td><button class="hub-btn" data-log="${esc(i.name)}" data-subject="${esc(i.subject)}">${__("Log time")}</button></td></tr>`;
			})
			.join("")}</tbody></table>`;
	}

	render() {
		const d = this.data;
		const t = d.tiles;
		const { tile, panel } = ui;
		const groups = MW_GROUPS.filter(([key]) => d.groups[key].length)
			.map(
				([key, label, open]) =>
					`<details class="hub-group" ${open ? "open" : ""}><summary>${__(label)} (${d.groups[key].length})</summary>${this.ticket_table(d.groups[key])}</details>`
			)
			.join("");
		const sprints = d.sprints.length
			? d.sprints
					.map(
						(s) => `<div class="hub-mini"><span>${ui.link("Sprint", s.name, s.label)}</span><div class="progress"><div class="progress-bar" style="width:${s.percent}%"></div></div><span>${__("{0} days left", [s.days_left])}</span></div>
						<div class="hub-sub" style="margin:-4px 0 8px">${__("My tickets: {0} of {1} closed", [s.mine_closed, s.mine_total])}</div>`
					)
					.join("")
			: `<div class="text-muted small">${__("No active sprint with your tickets.")}</div>`;
		const raised = d.raised.length
			? d.raised.map((r) => `<div class="hub-list-row"><span>${ui.link("Work Item", r.name)} ${ui.esc(r.subject)}</span><span class="hub-sub">${ui.esc(r.assignee_name)}</span></div>`).join("")
			: `<div class="text-muted small">${__("Nothing you raised is waiting on someone else.")}</div>`;
		const mine_waiting = Object.values(d.groups).flat().filter((i) => cint(i.dependent_on_client));
		const waiting = mine_waiting.length
			? ui.table(mine_waiting, [__("Ticket"), __("Summary"), __("What we need"), __("Waiting")], (i) =>
				`<tr><td style="white-space:nowrap">${ui.link("Work Item", i.name)}</td><td>${ui.esc(i.subject)}</td><td>${ui.esc(i.client_dependency_note || "")}</td><td style="white-space:nowrap">${i.client_dependency_since ? ui.days(frappe.datetime.get_diff(d.today, i.client_dependency_since)) : ""}</td></tr>`)
			: `<div class="text-muted small">${__("None of your tickets is waiting on the client.")}</div>`;
		const missing = d.hours.missing_days.length ? `<div class="hub-badge hub-badge-warn" style="display:inline-block;margin-top:8px">${__("No hours logged on {0}", [d.hours.missing_days.join(", ")])}</div>` : "";
		this.$body.html(`
			<div class="hub-title"><h4>${__("My Work")}</h4><span class="text-muted">${ui.esc(frappe.user.full_name())} · ${frappe.datetime.str_to_user(d.today)}</span></div>
			<div class="hub-tiles">
				${tile(t.open, __("Open tickets"), "hub-blue")}
				${tile(t.overdue, __("Overdue"), t.overdue ? "hub-red" : "hub-teal")}
				${tile(t.today, __("Due today"), "hub-orange")}
				${tile(t.week, __("Due this week"), "hub-purple")}
				${tile(t.client_waiting, __("Waiting on client"), "hub-cyan")}
				${tile(t.blocked, __("Blocked"), t.blocked ? "hub-red" : "hub-teal")}
				${tile(t.hours_week, __("Hours this week"), "hub-green", __("{0}% of {1} h", [t.capacity_pct, t.capacity]))}
				${tile(t.closed_28d, __("Closed (28 days)"), "hub-teal")}
			</div>
			<div class="hub-cols">
				<div class="hub-col">${panel(__("My tickets"), groups || `<div class="text-muted small">${__("Nothing is assigned to you right now.")}</div>`)}</div>
				<div class="hub-col">
					${panel(__("Hours this week"), `<div class="hub-chart" id="mw-hours"></div>${missing}`)}
					${panel(`${__("Risks I own")} (${d.risks.length})`, d.risks.length ? ui.riskTable(d.risks, true) : `<div class="text-muted small">${__("You do not own any open risks.")}</div>`)}
					${panel(`${__("Waiting on the client")} (${mine_waiting.length})`, waiting)}
					${panel(__("My active sprints"), sprints)}
					${panel(__("I raised, others are working on"), raised)}
					${panel(__("Tickets I closed (last 4 weeks)"), `<div class="hub-chart" id="mw-closed"></div>`)}
				</div>
			</div>`);
		this.$body.find("[data-log]").on("click", (e) => this.log_time($(e.currentTarget).data("log"), $(e.currentTarget).data("subject")));
		const palette = ui.PALETTE;
		ui.chart(this.$body, "#mw-hours", { type: "bar", height: 200, data: { labels: d.hours.days, datasets: [{ name: __("Billable"), values: d.hours.billable }, { name: __("Non-billable"), values: d.hours.non_billable }] }, colors: [palette.green, palette.orange], barOptions: { stacked: 1, spaceRatio: 0.4 } });
		ui.chart(this.$body, "#mw-closed", { type: "bar", height: 160, data: { labels: [__("3 weeks ago"), __("2 weeks ago"), __("Last week"), __("This week")], datasets: [{ name: __("Closed"), values: d.closed_weekly }] }, colors: [palette.purple], barOptions: { spaceRatio: 0.5 } });
	}
}
