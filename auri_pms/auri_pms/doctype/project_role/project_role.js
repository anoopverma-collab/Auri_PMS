// Copyright (c) 2026, Anoop Verma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project Role", {
	setup(frm) {
		// The rules table lists every Work Item field: only Can Edit is changed, rows are not added or removed.
		frm.set_df_property("field_rules", "cannot_add_rows", true);
		frm.set_df_property("field_rules", "cannot_delete_rows", true);
	},

	refresh(frm) {
		frm.fields_dict.field_rules.grid.wrapper.find(".grid-add-row, .grid-remove-rows").hide();
	},
});
