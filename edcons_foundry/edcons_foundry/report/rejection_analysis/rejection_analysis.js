frappe.query_reports["Rejection Analysis"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1 },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "group_by", label: __("Group By"), fieldtype: "Select", options: "Reason\nStage\nItem\nMoulder\nHeat", default: "Reason", reqd: 1 },
		{ fieldname: "stage", label: __("Stage"), fieldtype: "Select", options: "\nMoulding\nPouring\nShot Blasting\nFinishing\nInspection\nCustomer Return" },
	],
};
