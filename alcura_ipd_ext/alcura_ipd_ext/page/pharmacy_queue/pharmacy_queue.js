frappe.pages["pharmacy-queue"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Pharmacy Queue"),
		single_column: true,
	});
	page.main.addClass("frappe-card");
	page.pharmacy_queue = new PharmacyQueue({ page });
};

class PharmacyQueue {
	constructor({ page }) {
		this.page = page;
		this.$container = $('<div class="pharmacy-queue-container"></div>').appendTo(page.main);
		this._setup_filters();
		this._refresh_interval = null;
		this.refresh();
		this._start_auto_refresh();
		frappe.realtime.on("ipd_order_notification", () => this.refresh());
		frappe.realtime.on("ipd_substitution_requested", () => this.refresh());
	}

	_setup_filters() {
		this.ward_filter = this.page.add_field({
			fieldtype: "Link", fieldname: "ward", label: __("Ward"),
			options: "Hospital Ward", change: () => this.refresh(),
		});
		this.urgency_filter = this.page.add_field({
			fieldtype: "Select", fieldname: "urgency", label: __("Urgency"),
			options: "\nRoutine\nUrgent\nSTAT\nEmergency", change: () => this.refresh(),
		});
		this.status_filter = this.page.add_field({
			fieldtype: "Select", fieldname: "status", label: __("Status"),
			options: "\nOrdered\nAcknowledged\nIn Progress", change: () => this.refresh(),
		});
		this.page.add_inner_button(__("Refresh"), () => this.refresh());
	}

	refresh() {
		const args = {
			ward: this.ward_filter?.get_value() || undefined,
			urgency: this.urgency_filter?.get_value() || undefined,
			status: this.status_filter?.get_value() || undefined,
		};

		frappe.call({
			method: "alcura_ipd_ext.api.department_queue.get_pharmacy_queue",
			args,
			callback: (r) => {
				this._render(r.message || []);
			},
		});
	}

	_render(orders) {
		if (!orders.length) {
			this.$container.html(
				`<div class="text-muted text-center" style="padding:40px;">${__("No pending medication orders.")}</div>`
			);
			return;
		}

		const rows = orders.map((o) => this._build_row(o)).join("");
		this.$container.html(`
			<div class="queue-summary" style="padding:8px 12px;background:var(--bg-light-gray);border-bottom:1px solid var(--border-color);">
				<strong>${orders.length}</strong> ${__("order(s)")}
			</div>
			<table class="table table-bordered table-hover table-sm" style="margin:0;">
				<thead><tr>
					<th>${__("Order")}</th>
					<th>${__("Patient")}</th>
					<th>${__("Medication")}</th>
					<th>${__("Dose / Route")}</th>
					<th>${__("Urgency")}</th>
					<th>${__("Status")}</th>
					<th>${__("Dispense")}</th>
					<th>${__("Elapsed")}</th>
					<th>${__("SLA")}</th>
					<th>${__("Actions")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>
		`);

		this._bind_actions();
	}

	_build_row(o) {
		const sla_pill = `<span class="indicator-pill ${o.sla_color || "grey"}">${
			o.sla_remaining_minutes != null ? Math.round(o.sla_remaining_minutes) + " min" : "-"
		}</span>`;

		const urgency_cls = { Emergency: "red", STAT: "red", Urgent: "orange", Routine: "blue" }[o.urgency] || "grey";
		const dispense_status = o.dispense_status || "Pending";
		const dispense_cls = {
			Pending: "grey",
			"Partially Dispensed": "orange",
			"Fully Dispensed": "green",
		}[dispense_status] || "grey";

		const subst = o.substitution_status === "Requested"
			? `<span class="indicator-pill yellow">${__("Subst. Pending")}</span> `
			: "";

		let actions = "";
		if (o.status === "Ordered") {
			actions = `<button class="btn btn-xs btn-primary btn-ack" data-order="${o.name}">${__("Acknowledge")}</button>`;
		} else if (o.status === "Acknowledged" || o.status === "In Progress") {
			actions = `
				<button class="btn btn-xs btn-default btn-stock" data-order="${o.name}" data-item="${o.medication_item || ""}">${__("Check Stock")}</button>
				<button class="btn btn-xs btn-success btn-dispense" data-order="${o.name}">${__("Dispense")}</button>
			`;
			if (o.substitution_status !== "Requested") {
				actions += ` <button class="btn btn-xs btn-warning btn-substitute" data-order="${o.name}">${__("Substitute")}</button>`;
			}
		}

		return `<tr>
			<td><a href="/app/ipd-clinical-order/${o.name}">${o.name}</a></td>
			<td>${frappe.utils.escape_html(o.patient_name || o.patient)}</td>
			<td><strong>${frappe.utils.escape_html(o.medication_name || "")}</strong></td>
			<td>${frappe.utils.escape_html(o.dose || "")} ${frappe.utils.escape_html(o.route || "")}</td>
			<td><span class="indicator-pill ${urgency_cls}">${o.urgency}</span>${o.is_stat ? ' <span class="indicator-pill red">STAT</span>' : ""}</td>
			<td>${o.status}</td>
			<td>${subst}<span class="indicator-pill ${dispense_cls}">${dispense_status}</span></td>
			<td>${Math.round(o.elapsed_minutes || 0)} min</td>
			<td>${sla_pill}</td>
			<td>${actions}</td>
		</tr>`;
	}

	_bind_actions() {
		const self = this;

		this.$container.find(".btn-ack").on("click", function () {
			const order = $(this).data("order");
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.transition_order",
				args: { order, new_status: "Acknowledged" },
				callback() {
					frappe.show_alert({ message: __("Order acknowledged."), indicator: "green" });
					self.refresh();
				},
			});
		});

		this.$container.find(".btn-stock").on("click", function () {
			const item = $(this).data("item");
			if (!item) {
				frappe.msgprint(__("No medication item linked to this order."));
				return;
			}
			frappe.call({
				method: "alcura_ipd_ext.api.pharmacy.verify_stock",
				args: { item_code: item },
				callback(r) {
					const data = r.message || {};
					let wh_rows = "";
					for (const w of data.warehouses || []) {
						wh_rows += `<tr><td>${w.warehouse}</td><td>${w.actual_qty}</td><td>${w.available_qty}</td></tr>`;
					}
					frappe.msgprint({
						title: __("Stock for {0}", [item]),
						message: `
							<p><strong>${__("Total Available")}:</strong> ${data.available_qty || 0}</p>
							<table class="table table-sm table-bordered">
								<thead><tr><th>${__("Warehouse")}</th><th>${__("Actual")}</th><th>${__("Available")}</th></tr></thead>
								<tbody>${wh_rows || `<tr><td colspan="3" class="text-muted">${__("No stock found")}</td></tr>`}</tbody>
							</table>
						`,
						indicator: data.available_qty > 0 ? "green" : "red",
					});
				},
			});
		});

		this.$container.find(".btn-dispense").on("click", function () {
			const order = $(this).data("order");
			_show_dispense_dialog(order, self);
		});

		this.$container.find(".btn-substitute").on("click", function () {
			const order = $(this).data("order");
			_show_substitution_dialog(order, self);
		});
	}

	_start_auto_refresh() {
		this._refresh_interval = setInterval(() => this.refresh(), 30000);
	}

	destroy() {
		if (this._refresh_interval) clearInterval(this._refresh_interval);
	}
}

function _show_dispense_dialog(order, queue) {
	const d = new frappe.ui.Dialog({
		title: __("Dispense Medication"),
		fields: [
			{ fieldtype: "Float", fieldname: "dispensed_qty", label: __("Quantity"), reqd: 1 },
			{
				fieldtype: "Select", fieldname: "dispense_type", label: __("Dispense Type"),
				options: "Full\nPartial", default: "Full", reqd: 1,
			},
			{ fieldtype: "Data", fieldname: "batch_no", label: __("Batch No") },
			{ fieldtype: "Link", fieldname: "warehouse", label: __("Warehouse"), options: "Warehouse" },
			{ fieldtype: "Date", fieldname: "expiry_date", label: __("Expiry Date") },
			{ fieldtype: "Small Text", fieldname: "notes", label: __("Notes") },
		],
		primary_action_label: __("Dispense"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.pharmacy.dispense_medication",
				args: {
					order_name: order,
					dispensed_qty: values.dispensed_qty,
					dispense_type: values.dispense_type,
					batch_no: values.batch_no,
					warehouse: values.warehouse,
					expiry_date: values.expiry_date,
					notes: values.notes,
				},
				freeze: true,
				callback(r) {
					if (r.message) {
						frappe.show_alert({
							message: __("Dispensed successfully. Status: {0}", [r.message.dispense_status]),
							indicator: "green",
						});
						queue.refresh();
					}
				},
			});
		},
	});
	d.show();
}

function _show_substitution_dialog(order, queue) {
	const d = new frappe.ui.Dialog({
		title: __("Request Substitution"),
		fields: [
			{ fieldtype: "Link", fieldname: "substitute_item", label: __("Substitute Item"), options: "Item", reqd: 1 },
			{ fieldtype: "Small Text", fieldname: "reason", label: __("Reason"), reqd: 1 },
		],
		primary_action_label: __("Request"),
		primary_action(values) {
			d.hide();
			frappe.call({
				method: "alcura_ipd_ext.api.pharmacy.request_substitution",
				args: {
					order_name: order,
					substitute_item: values.substitute_item,
					reason: values.reason,
				},
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Substitution request sent to doctor."), indicator: "blue" });
					queue.refresh();
				},
			});
		},
	});
	d.show();
}
