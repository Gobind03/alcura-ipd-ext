frappe.pages["nurse-station-queue"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Nurse Station Queue"),
		single_column: true,
	});
	page.main.addClass("frappe-card");
	new NurseStationQueue({ page });
};

class NurseStationQueue {
	constructor({ page }) {
		this.page = page;
		this.$container = $('<div class="nurse-queue-container"></div>').appendTo(page.main);
		this._setup_filters();
		this.refresh();
		this._start_auto_refresh();
		frappe.realtime.on("ipd_order_notification", () => this.refresh());
		frappe.realtime.on("ipd_sla_breach", () => this.refresh());
	}

	_setup_filters() {
		this.ward_filter = this.page.add_field({
			fieldtype: "Link", fieldname: "ward", label: __("Ward"),
			options: "Hospital Ward", change: () => this.refresh(),
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
			status: this.status_filter?.get_value() || undefined,
		};

		frappe.call({
			method: "alcura_ipd_ext.api.department_queue.get_nurse_station_queue",
			args,
			callback: (r) => {
				this._render(r.message || []);
			},
		});
	}

	_render(orders) {
		if (!orders.length) {
			this.$container.html(
				`<div class="text-muted text-center" style="padding:40px;">${__("No pending orders for this ward.")}</div>`
			);
			return;
		}

		// Group by patient
		const grouped = {};
		for (const o of orders) {
			const key = o.patient;
			if (!grouped[key]) {
				grouped[key] = { patient: o.patient, patient_name: o.patient_name, bed: o.bed, ward: o.ward, orders: [] };
			}
			grouped[key].orders.push(o);
		}

		let html = `
			<div class="queue-summary" style="padding:8px 12px;background:var(--bg-light-gray);border-bottom:1px solid var(--border-color);">
				<strong>${orders.length}</strong> ${__("order(s) for")} <strong>${Object.keys(grouped).length}</strong> ${__("patient(s)")}
			</div>
		`;

		for (const key of Object.keys(grouped)) {
			const group = grouped[key];
			const patient_header = `
				<div style="padding:8px 12px;background:var(--bg-light-gray);border:1px solid var(--border-color);margin-top:8px;">
					<strong>${frappe.utils.escape_html(group.patient_name || group.patient)}</strong>
					${group.bed ? ` | ${__("Bed")}: ${group.bed}` : ""}
					${group.ward ? ` | ${__("Ward")}: ${group.ward}` : ""}
				</div>
			`;

			const rows = group.orders.map((o) => this._build_row(o)).join("");
			html += `${patient_header}
				<table class="table table-bordered table-sm" style="margin:0;">
					<thead><tr>
						<th>${__("Type")}</th>
						<th>${__("Detail")}</th>
						<th>${__("Urgency")}</th>
						<th>${__("Status")}</th>
						<th>${__("Elapsed")}</th>
						<th>${__("SLA")}</th>
						<th>${__("Actions")}</th>
					</tr></thead>
					<tbody>${rows}</tbody>
				</table>
			`;
		}

		this.$container.html(html);

		this.$container.find(".btn-queue-action").on("click", function () {
			const order = $(this).data("order");
			const action = $(this).data("action");
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.transition_order",
				args: { order, new_status: action },
				callback() {
					frappe.show_alert({ message: __("Order updated."), indicator: "green" });
				},
			});
		});
	}

	_build_row(o) {
		const type_icons = { Medication: "pill", "Lab Test": "flask", Radiology: "image", Procedure: "activity" };
		const detail = o.medication_name || o.lab_test_name || o.procedure_name || "";
		const sla_pill = `<span class="indicator-pill ${o.sla_color || "grey"}">${
			o.sla_remaining_minutes != null ? Math.round(o.sla_remaining_minutes) + " min" : "-"
		}</span>`;
		const urgency_cls = { Emergency: "red", STAT: "red", Urgent: "orange", Routine: "blue" }[o.urgency] || "grey";

		let actions = `<a href="/app/ipd-clinical-order/${o.name}" class="btn btn-xs btn-default">${__("Open")}</a>`;
		if (o.status === "Ordered") {
			actions += ` <button class="btn btn-xs btn-primary btn-queue-action" data-order="${o.name}" data-action="Acknowledged">${__("Ack")}</button>`;
		}

		return `<tr class="${o.is_sla_breached ? "bg-light-red" : ""}">
			<td><span class="indicator-pill ${urgency_cls}">${o.order_type}</span></td>
			<td><strong>${frappe.utils.escape_html(detail)}</strong></td>
			<td><span class="indicator-pill ${urgency_cls}">${o.urgency}</span></td>
			<td>${o.status}</td>
			<td>${Math.round(o.elapsed_minutes || 0)} min</td>
			<td>${sla_pill}</td>
			<td>${actions}</td>
		</tr>`;
	}

	_start_auto_refresh() {
		this._refresh_interval = setInterval(() => this.refresh(), 30000);
	}

	destroy() {
		if (this._refresh_interval) clearInterval(this._refresh_interval);
	}
}
