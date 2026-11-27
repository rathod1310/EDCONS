frappe.ui.form.on("Shot Blast Log", {
	refresh(frm) { edcons_foundry.setup(frm); },
	hour_meter_start: (frm) => frm.trigger("calc"),
	hour_meter_end: (frm) => frm.trigger("calc"),
	calc(frm) {
		const items = frm.doc.items || [];
		frm.set_value({
			total_nos: edcons_foundry.sum(items, "nos"),
			total_rejected_nos: edcons_foundry.sum(items, "rejected_nos"),
			total_kg: edcons_foundry.sum(items, "weight_kg"),
			running_hours: frm.doc.hour_meter_end ? flt(frm.doc.hour_meter_end) - flt(frm.doc.hour_meter_start) : 0,
		});
	},
});
frappe.ui.form.on("Shot Blast Item", {
	items_add(frm, cdt, cdn) { edcons_foundry.copy_previous_row(frm, cdt, cdn, ["heat"]); },
	nos: calc_row, std_weight: calc_row, rejected_nos: calc_row,
	items_remove: (frm) => frm.trigger("calc"),
});
function calc_row(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "weight_kg", cint(r.nos) * flt(r.std_weight));
	frm.trigger("calc");
}
