frappe.listview_settings["Production Entry"] = {
	add_fields: ["docstatus"],
	onload(listview) {
		listview.page.add_inner_button(__("Shop Floor"), () => frappe.set_route("shop-floor"));
	},
};
