frappe.ui.form.on("Furnace Heat", {
	setup(frm) {
		frm.set_query("furnace", () => ({ filters: { is_active: 1 } }));
	},
	refresh(frm) {
		edcons_foundry.setup(frm);
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Test Certificate"), () => frm.print_doc ? frm.print_doc() : frappe.set_route("print", frm.doctype, frm.doc.name), __("View"));
		}
		if (frm.doc.kwh_per_tonne && frm.doc.docstatus < 2) {
			frappe.db.get_single_value("Foundry Settings", "kwh_target").then((t) => {
				if (t && frm.doc.kwh_per_tonne > t) {
					frm.dashboard.add_comment(__("kWh per tonne {0} is above the target {1}", [format_number(frm.doc.kwh_per_tonne, null, 0), t]), "orange", true);
				}
			});
		}
	},
	furnace(frm) {
		if (!frm.doc.furnace) return;
		frappe.db.get_value("Furnace", frm.doc.furnace, ["current_lining_no", "heats_on_lining"]).then(({ message: f }) => {
			frm.set_value("lining_no", f.current_lining_no);
			frm.set_value("lining_heat_no", (f.heats_on_lining || 0) + 1);
		});
	},
	kwh_start: (frm) => frm.trigger("calc"),
	kwh_end: (frm) => frm.trigger("calc"),
	liquid_metal_kg: (frm) => frm.trigger("calc"),
	c_pct: (frm) => frm.trigger("calc"),
	si_pct: (frm) => frm.trigger("calc"),
	p_pct: (frm) => frm.trigger("calc"),
	coke_kg: (frm) => frm.trigger("calc"),
	calc(frm) {
		let total = 0, cost = 0, ret = 0, coke = 0;
		(frm.doc.charge || []).forEach((r) => {
			if (r.charge_type === "Coke") { coke += flt(r.qty_kg); return; }
			total += flt(r.qty_kg); cost += flt(r.amount);
			if (r.charge_type === "Return Metal") ret += flt(r.qty_kg);
		});
		frm.set_value("total_charge_kg", total);
		frm.set_value("return_metal_kg", ret);
		frm.set_value("charge_cost", cost);
		frm.set_value("cost_per_kg", total ? cost / total : 0);
		const kwh = frm.doc.kwh_end ? flt(frm.doc.kwh_end) - flt(frm.doc.kwh_start) : 0;
		frm.set_value("kwh_consumed", kwh);
		const metal = flt(frm.doc.liquid_metal_kg) || total;
		frm.set_value("kwh_per_tonne", metal && kwh ? kwh / (metal / 1000) : 0);
		frm.set_value("ce_pct", frm.doc.c_pct ? flt(frm.doc.c_pct) + (flt(frm.doc.si_pct) + flt(frm.doc.p_pct)) / 3 : 0);
		coke = flt(frm.doc.coke_kg) || coke;
		frm.set_value("coke_ratio", coke ? total / coke : 0);
	},
});

frappe.ui.form.on("Heat Charge Item", {
	qty_kg(frm, cdt, cdn) { frappe.ui.form.trigger(cdt, cdn, "rate"); },
	rate(frm, cdt, cdn) {
		const r = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "amount", flt(r.qty_kg) * flt(r.rate));
		frm.trigger("calc");
	},
	charge_type: (frm) => frm.trigger("calc"),
	charge_remove: (frm) => frm.trigger("calc"),
});
