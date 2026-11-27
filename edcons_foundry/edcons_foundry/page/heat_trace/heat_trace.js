frappe.pages["heat-trace"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Heat Traceability"), single_column: true });
	page.add_inner_button(__("Shop Floor"), () => frappe.set_route("shop-floor"));
	const $body = $(`<div class="ef-hub"><div class="ef-search"></div><div class="ef-out"></div></div>`).appendTo(page.main);
	const ctl = frappe.ui.form.make_control({
		parent: $body.find(".ef-search"),
		df: { fieldtype: "Link", options: "Furnace Heat", label: __("Heat No."), change() { const v = ctl.get_value(); if (v) frappe.set_route("heat-trace", v); } },
		render_input: true,
	});
	wrapper.load = (heat) => {
		if (!heat) { $body.find(".ef-out").html(`<div class="ef-empty">${__("Choose a heat to see everything made from it.")}</div>`); return; }
		ctl.set_value(heat);
		frappe.call({ method: "edcons_foundry.api.trace_heat", args: { heat }, freeze: true })
			.then(({ message }) => render($body.find(".ef-out"), message));
	};
};
frappe.pages["heat-trace"].on_page_show = function (wrapper) {
	wrapper.load(frappe.get_route()[1]);
};

function render($out, d) {
	const h = d.heat, n = (v, p = 0) => format_number(v || 0, null, p), esc = frappe.utils.escape_html;
	const link = (dt, name) => (name ? `<a href="/app/${frappe.router.slug(dt)}/${encodeURIComponent(name)}">${esc(name)}</a>` : "");
	const kpi = (v, l) => `<div class="ef-kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
	const table = (rows, cols) => rows.length ? `<div class="ef-wrap"><table class="ef-table"><thead><tr>${cols.map((c) => `<th>${__(c[0])}</th>`).join("")}</tr></thead>
		<tbody>${rows.map((r) => `<tr>${cols.map((c) => `<td>${c[1](r)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
		: `<div class="ef-empty">${__("Nothing recorded yet.")}</div>`;
	const step = (title, body) => `<div class="ef-step"><h5>${__(title)}</h5>${body}</div>`;
	const doc = (dt) => (r) => link(dt, r.name) + (r.docstatus ? "" : ` <span class="indicator-pill orange">${__("Draft")}</span>`);
	const date = (r) => frappe.datetime.str_to_user(r.posting_date);

	$out.html(`
		<div class="ef-trace-head">
			${kpi(link("Furnace Heat", h.name), __("{0} · {1} shift · {2}", [frappe.datetime.str_to_user(h.posting_date), h.shift || "", h.furnace || ""]))}
			${kpi(esc(h.grade || "–"), __("Grade · CE {0}%", [n(h.ce_pct, 2)]))}
			${kpi(n(h.total_charge_kg) + " kg", __("Charge, {0} kWh/t", [n(h.kwh_per_tonne)]))}
			${kpi(n(h.poured_nos), __("Castings poured, {0} kg", [n(h.poured_kg)]))}
			${kpi(n(h.rejected_nos), __("Rejected, {0} kg", [n(h.rejected_kg)]))}
			${kpi(n(h.yield_pct, 1) + "%", __("Yield (good kg / charge)"))}
			${kpi(esc(h.chemistry_status || ""), __("Lab status"))}
		</div>
		${step("1 · Melt: chemistry", table([h], [["C %", (r) => r.c_pct], ["Si %", (r) => r.si_pct], ["Mn %", (r) => r.mn_pct], ["P %", (r) => r.p_pct],
			["S %", (r) => r.s_pct], ["Mg %", (r) => r.mg_pct], ["Tensile", (r) => r.tensile_mpa || ""], ["Elong. %", (r) => r.elongation_pct || ""], ["BHN", (r) => r.hardness_bhn || ""]]))}
		${step("3 · Mould & Pour", table(d.production, [["Entry", doc("Production Entry")], ["Date", date], ["Moulder", (r) => esc(r.moulder_name || "")],
			["Item", (r) => esc(r.item_name || r.item_code)], ["Work Order", (r) => link("Work Order", r.work_order)], ["Nos", (r) => r.nos], ["Rej", (r) => r.rejected_nos || 0], ["kg", (r) => n(r.weight_kg)]]))}
		${step("Work Orders and Job Cards", table(d.job_cards, [["Job Card", (r) => link("Job Card", r.name)], ["Work Order", (r) => link("Work Order", r.work_order)],
			["Operation", (r) => esc(r.operation)], ["Done", (r) => `${n(r.total_completed_qty)} / ${n(r.for_quantity)}`], ["Status", (r) => esc(r.status)]]))}
		${step("4 · Shot Blast", table(d.shot_blast, [["Log", doc("Shot Blast Log")], ["Date", date], ["Item", (r) => esc(r.item_code)], ["Nos", (r) => r.nos], ["Rej", (r) => r.rejected_nos || 0]]))}
		${step("5 · Finish", table(d.finishing, [["Log", doc("Finishing Log")], ["Date", date], ["Worker", (r) => esc(r.worker_name || "")], ["Process", (r) => esc(r.process || "")],
			["Item", (r) => esc(r.item_code)], ["Finished", (r) => r.finished_nos], ["Rej", (r) => r.rejected_nos || 0], ["Avg wt", (r) => n(r.actual_weight, 2)], ["Weight", (r) => esc(r.weight_flag || "")]]))}
		${step("6 · Inspect", table(d.inspection, [["Inspection", doc("Visual Inspection")], ["Date", date], ["Item", (r) => esc(r.item_code)], ["Checked", (r) => r.qty_checked], ["Rejected", (r) => r.total_rejected], ["OK", (r) => r.ok_qty]]))}
		${step("7 · Load Test", table(d.load_tests, [["Report", doc("Load Test Report")], ["Date", date], ["Item", (r) => esc(r.item_code)], ["Standard", (r) => esc(r.standard || "")],
			["Required kN", (r) => r.required_load_kn], ["Applied kN", (r) => r.applied_load_kn], ["Result", (r) => esc(r.result || "")]]))}
		${step("Rejections", table(d.rejections, [["Report", doc("Rejection Report")], ["Date", date], ["Stage", (r) => esc(r.stage)], ["Item", (r) => esc(r.item_code)], ["Reason", (r) => esc(r.reason || "")], ["Qty", (r) => r.qty_nos], ["kg", (r) => n(r.weight_kg)]]))}
		${step("8 · Dispatch", table(d.dispatch, [["Delivery Note", (r) => link("Delivery Note", r.name)], ["Date", date], ["Customer", (r) => esc(r.customer)], ["Item", (r) => esc(r.item_code)], ["Qty", (r) => r.qty]]))}
	`);
}
