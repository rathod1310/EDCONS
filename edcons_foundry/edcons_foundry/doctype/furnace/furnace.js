frappe.ui.form.on("Furnace", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Start New Lining"), () => {
			frappe.confirm(__("Start lining {0}? The heat count on this lining goes back to 0.", [(frm.doc.current_lining_no || 0) + 1]), () => {
				frappe.call("edcons_foundry.api.start_new_lining", { furnace: frm.doc.name }).then(() => frm.reload_doc());
			});
		});
		frm.add_custom_button(__("New Heat"), () => frappe.new_doc("Furnace Heat", { furnace: frm.doc.name }));
	},
});
