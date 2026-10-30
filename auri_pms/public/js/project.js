// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

// Auri PMS tab UX on the ERPNext Project form. Rules are enforced on the server.
frappe.ui.form.on("Project", {
	setup(frm) {
		frm.set_query("parent_project", () => ({ filters: { name: ["!=", frm.doc.name] } }));
		frm.set_query("user", "tracker_members", () => ({ filters: { enabled: 1 } }));
		// enabled_trackers is a Table MultiSelect (no grid): the query goes on the field itself.
		frm.set_query("enabled_trackers", () => ({ filters: { is_active: 1 } }));
		frm.set_query("enabled_statuses", () => ({ filters: { is_active: 1 } }));
	},
	refresh(frm) {
		frm._pms_was_enabled = cint(frm.doc.pms_enabled);
		// The identifier is fixed once saved (set-only-once rule R-02).
		if (frm.doc.tracker_identifier && !frm.is_new()) {
			frm.set_df_property("tracker_identifier", "read_only", 1);
		}
		if (frm.doc.pms_enabled && !frm.is_new()) {
			frm.add_custom_button(__("Project Hub"), () => frappe.set_route("project-hub", frm.doc.name));
		}
	},
	pms_enabled(frm) {
		// Switching Auri PMS on selects every active Ticket Type by default (the server does the same on save).
		if (!frm.doc.pms_enabled || (frm.doc.enabled_trackers || []).length) return;
		frappe.db.get_list("Ticket Type", { filters: { is_active: 1 }, pluck: "name", limit: 0 }).then((names) => {
			names.forEach((name) => frm.add_child("enabled_trackers", { tracker: name }));
			frm.refresh_field("enabled_trackers");
		});
		frappe.db.get_list("Work Item Status", { filters: { is_active: 1 }, pluck: "name", limit: 0 }).then((names) => {
			if ((frm.doc.enabled_statuses || []).length) return;
			names.forEach((name) => frm.add_child("enabled_statuses", { status: name }));
			frm.refresh_field("enabled_statuses");
		});
	},
	before_save(frm) {
		// Switching Auri PMS off hides the project; with records on it, ask first (the server needs the confirmation).
		if (frm.doc.pms_enabled || frm.is_new() || !frm._pms_was_enabled || frm._pms_disable_confirmed) {
			frm._pms_disable_confirmed = false;
			return;
		}
		frappe.validated = false;
		frappe
			.xcall("auri_pms.auri_pms.project_hooks.get_record_counts", { project: frm.doc.name })
			.then((counts) => {
				if (!counts.some((row) => row.total)) {
					frm._pms_disable_confirmed = true;
					return frm.save();
				}
				const rows = counts
					.map(
						(row) =>
							`<tr><td>${frappe.utils.escape_html(row.label)}</td>` +
							`<td class="text-right">${row.open ?? "-"}</td>` +
							`<td class="text-right">${row.total}</td></tr>`
					)
					.join("");
				frappe.confirm(
					`<p>${__("This project still has Auri PMS records. Disabling Auri PMS hides the project from the Auri PMS dashboard and screens. The records are kept and come back if you enable it again.")}</p>` +
						`<table class="table table-bordered table-sm"><thead><tr><th>${__("Doctype")}</th>` +
						`<th class="text-right">${__("Open")}</th><th class="text-right">${__("Total")}</th></tr></thead>` +
						`<tbody>${rows}</tbody></table>` +
						`<p>${__("Do you want to disable Auri PMS?")}</p>`,
					() =>
						frappe
							.xcall("auri_pms.auri_pms.project_hooks.confirm_disable", { project: frm.doc.name })
							.then(() => {
								frm._pms_disable_confirmed = true;
								return frm.save();
							}),
					() => frm.set_value("pms_enabled", 1)
				);
			});
	},
	tracker_identifier(frm) {
		if (frm.doc.tracker_identifier) {
			frm.set_value("tracker_identifier", frm.doc.tracker_identifier.toUpperCase().trim());
		}
	},
});

frappe.ui.form.on("Project Member", {
	project_role(frm, cdt, cdn) {
		// Show what the chosen Project Role allows (the server refreshes this on save).
		const row = locals[cdt][cdn];
		if (!row.project_role) return frappe.model.set_value(cdt, cdn, "role_permissions", "");
		frappe
			.xcall("auri_pms.auri_pms.project_hooks.get_role_permissions", { project_role: row.project_role })
			.then((text) => frappe.model.set_value(cdt, cdn, "role_permissions", text));
	},
});
