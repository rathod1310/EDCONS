// Added by edcons_foundry: start shop-floor logs from a Work Order
frappe.ui.form.on("Work Order", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || ["Completed", "Stopped", "Closed"].includes(frm.doc.status)) return;
		frm.add_custom_button(__("Production Entry"), () => {
			frappe.call({ method: "edcons_foundry.api.make_next",
				args: { source_doctype: "Work Order", source_name: frm.doc.name, target_doctype: "Production Entry" } })
				.then((r) => { const d = frappe.model.sync(r.message)[0]; frappe.set_route("Form", d.doctype, d.name); });
		}, __("Foundry"));
		if (frm.doc.foundry_heats) {
			frm.doc.foundry_heats.split(",").map((h) => h.trim()).filter(Boolean).forEach((h) => {
				frm.add_custom_button(__("Trace {0}", [h]), () => frappe.set_route("heat-trace", h), __("Foundry"));
			});
		}
	},
});
