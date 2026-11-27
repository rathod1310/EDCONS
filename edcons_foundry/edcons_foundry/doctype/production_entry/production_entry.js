frappe.ui.form.on("Production Entry", {
	refresh(frm) {
		edcons_foundry.setup(frm, { tables: ["pouring"] });
		if (frm.doc.docstatus === 1 && frm.doc.total_rejected_nos && !frm.doc.rejection_report) {
			frm.add_custom_button(__("Rejection Report"), () =>
				frappe.new_doc("Rejection Report", { stage: "Moulding", reference_doctype: frm.doctype, reference_name: frm.doc.name, produced_nos: frm.doc.total_nos }),
				__("Next step"));
		}
	},
	calc(frm) {
		let nos = 0, kg = 0, rej = 0;
		const heats = [];
		(frm.doc.items || []).forEach((r) => {
			nos += cint(r.nos); kg += flt(r.weight_kg); rej += cint(r.rejected_nos);
			if (r.heat && !heats.includes(r.heat)) heats.push(r.heat);
		});
		frm.set_value({ total_nos: nos, total_weight_kg: kg, total_rejected_nos: rej, total_good_nos: nos - rej, heats: heats.join(", ") });
	},
});

frappe.ui.form.on("Production Entry Item", {
	items_add(frm, cdt, cdn) {
		edcons_foundry.copy_previous_row(frm, cdt, cdn, ["heat", "moulder", "moulding_type", "customer"]);
	},
	nos(frm, cdt, cdn) { row_calc(frm, cdt, cdn); },
	rejected_nos(frm, cdt, cdn) { row_calc(frm, cdt, cdn); },
	book_weight(frm, cdt, cdn) { row_calc(frm, cdt, cdn); },
	item_code(frm, cdt, cdn) {
		const r = locals[cdt][cdn];
		if (r.item_code && !r.work_order) {
			frappe.db.get_list("Work Order", {
				filters: { production_item: r.item_code, docstatus: 1, status: ["in", ["Not Started", "In Process"]] },
				fields: ["name"], order_by: "planned_start_date asc", limit: 2,
			}).then((wos) => { if (wos.length === 1) frappe.model.set_value(cdt, cdn, "work_order", wos[0].name); });
		}
	},
	items_remove: (frm) => frm.trigger("calc"),
});

function row_calc(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	if (cint(r.rejected_nos) > cint(r.nos)) {
		frappe.show_alert({ message: __("Rejected is more than cast in row {0}", [r.idx]), indicator: "red" });
	}
	frappe.model.set_value(cdt, cdn, "weight_kg", cint(r.nos) * flt(r.book_weight));
	frappe.model.set_value(cdt, cdn, "good_nos", cint(r.nos) - cint(r.rejected_nos));
	frm.trigger("calc");
}

frappe.ui.form.on("Pouring Record", {
	pouring_add(frm, cdt, cdn) {
		const first = (frm.doc.items || []).find((r) => r.heat);
		if (first) frappe.model.set_value(cdt, cdn, "heat", first.heat);
	},
	pouring_time_sec: velocity,
	good_casting_wt: velocity,
});
function velocity(frm, cdt, cdn) {
	const r = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "pouring_velocity", flt(r.pouring_time_sec) ? flt(r.good_casting_wt) / flt(r.pouring_time_sec) : 0);
}
