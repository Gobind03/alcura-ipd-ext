frappe.pages["lab-queue"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Lab Queue"),
		single_column: true,
	});
	page.main.addClass("frappe-card");
	page.lab_queue = new LabQueue({ page });
};

class LabQueue {
	constructor({ page }) {
		this.page = page;
		this.$container = $('<div class="lab-queue-container"></div>').appendTo(page.main);
		this._setup_filters();
		this.refresh();
		this._start_auto_refresh();
		frappe.realtime.on("ipd_order_notification", () => this.refresh());
		frappe.realtime.on("lab_sample_collected", () => this.refresh());
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
			method: "alcura_ipd_ext.api.department_queue.get_lab_queue",
			args,
			callback: (r) => {
				const orders = r.message || [];
				this._enrich_with_samples(orders);
			},
		});
	}

	_enrich_with_samples(orders) {
		if (!orders.length) {
			this._render(orders, {});
			return;
		}

		const order_names = orders.map((o) => o.name);
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "IPD Lab Sample",
				filters: { clinical_order: ["in", order_names] },
				fields: [
					"name", "clinical_order", "status", "collection_status",
					"barcode", "is_critical_result", "critical_result_acknowledged_by",
				],
				limit_page_length: 500,
			},
			callback: (r) => {
				const sample_map = {};
				for (const s of r.message || []) {
					if (!sample_map[s.clinical_order]) sample_map[s.clinical_order] = [];
					sample_map[s.clinical_order].push(s);
				}
				this._render(orders, sample_map);
			},
		});
	}

	_render(orders, sample_map) {
		if (!orders.length) {
			this.$container.html(
				`<div class="text-muted text-center" style="padding:40px;">${__("No pending lab orders.")}</div>`
			);
			return;
		}

		const rows = orders.map((o) => this._build_row(o, sample_map[o.name] || [])).join("");
		this.$container.html(`
			<div class="queue-summary" style="padding:8px 12px;background:var(--bg-light-gray);border-bottom:1px solid var(--border-color);">
				<strong>${orders.length}</strong> ${__("order(s)")}
			</div>
			<table class="table table-bordered table-hover table-sm" style="margin:0;">
				<thead><tr>
					<th>${__("Order")}</th>
					<th>${__("Patient")}</th>
					<th>${__("Lab Test")}</th>
					<th>${__("Sample")}</th>
					<th>${__("Sample Status")}</th>
					<th>${__("Urgency")}</th>
					<th>${__("Status")}</th>
					<th>${__("Elapsed")}</th>
					<th>${__("SLA")}</th>
					<th>${__("Actions")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>
		`);

		this._bind_actions();
	}

	_build_row(o, samples) {
		const sla_pill = `<span class="indicator-pill ${o.sla_color || "grey"}">${
			o.sla_remaining_minutes != null ? Math.round(o.sla_remaining_minutes) + " min" : "-"
		}</span>`;

		const urgency_cls = { Emergency: "red", STAT: "red", Urgent: "orange", Routine: "blue" }[o.urgency] || "grey";
		const fasting = o.is_fasting_required ? `<span class="indicator-pill orange">${__("Fasting")}</span>` : "";

		// Latest sample info
		const latest = samples.length ? samples[samples.length - 1] : null;
		const sample_status = latest ? latest.status : "No Sample";
		const sample_cls = {
			Pending: "grey", Collected: "blue", "In Transit": "orange",
			Received: "green", Processing: "green", Completed: "green", Rejected: "red",
		}[sample_status] || "grey";
		const barcode_display = latest?.barcode ? `<small class="text-muted">${latest.barcode}</small>` : "";
		const critical = latest?.is_critical_result
			? (latest.critical_result_acknowledged_by
				? `<span class="indicator-pill green">${__("Crit. Ack")}</span>`
				: `<span class="indicator-pill red">${__("CRITICAL")}</span>`)
			: "";

		let actions = "";
		if (o.status === "Ordered") {
			actions = `<button class="btn btn-xs btn-primary btn-ack" data-order="${o.name}">${__("Acknowledge")}</button>`;
		}

		if (latest && latest.status === "Pending") {
			actions += ` <button class="btn btn-xs btn-default btn-collect" data-sample="${latest.name}">${__("Collect")}</button>`;
		}
		if (latest && latest.status === "Collected") {
			actions += ` <button class="btn btn-xs btn-default btn-handoff" data-sample="${latest.name}">${__("Hand Off")}</button>`;
		}
		if (latest && (latest.status === "Collected" || latest.status === "In Transit")) {
			actions += ` <button class="btn btn-xs btn-default btn-receive" data-sample="${latest.name}">${__("Receive")}</button>`;
		}
		if (o.status === "In Progress") {
			actions += ` <button class="btn btn-xs btn-success btn-complete" data-order="${o.name}">${__("Result Published")}</button>`;
		}
		if (latest?.is_critical_result && !latest?.critical_result_acknowledged_by) {
			actions += ` <button class="btn btn-xs btn-danger btn-crit-ack" data-sample="${latest.name}">${__("Ack Critical")}</button>`;
		}

		return `<tr class="${latest?.is_critical_result && !latest?.critical_result_acknowledged_by ? "bg-light-red" : ""}">
			<td><a href="/app/ipd-clinical-order/${o.name}">${o.name}</a></td>
			<td>${frappe.utils.escape_html(o.patient_name || o.patient)}</td>
			<td><strong>${frappe.utils.escape_html(o.lab_test_name || "")}</strong></td>
			<td>${frappe.utils.escape_html(o.sample_type || "")} ${fasting} ${barcode_display}</td>
			<td><span class="indicator-pill ${sample_cls}">${sample_status}</span> ${critical}</td>
			<td><span class="indicator-pill ${urgency_cls}">${o.urgency}</span></td>
			<td>${o.status}</td>
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

		this.$container.find(".btn-collect").on("click", function () {
			const sample = $(this).data("sample");
			const d = new frappe.ui.Dialog({
				title: __("Record Sample Collection"),
				fields: [
					{ fieldtype: "Data", fieldname: "collection_site", label: __("Collection Site") },
					{ fieldtype: "Small Text", fieldname: "notes", label: __("Notes") },
				],
				primary_action_label: __("Collect"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "alcura_ipd_ext.api.lab_sample.record_collection",
						args: { sample_name: sample, collection_site: values.collection_site || "", notes: values.notes || "" },
						freeze: true,
						callback() {
							frappe.show_alert({ message: __("Sample collected."), indicator: "green" });
							self.refresh();
						},
					});
				},
			});
			d.show();
		});

		this.$container.find(".btn-handoff").on("click", function () {
			const sample = $(this).data("sample");
			const d = new frappe.ui.Dialog({
				title: __("Hand Off Sample"),
				fields: [
					{
						fieldtype: "Select", fieldname: "transport_mode", label: __("Transport Mode"),
						options: "\nManual\nPneumatic Tube\nRunner",
					},
				],
				primary_action_label: __("Hand Off"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "alcura_ipd_ext.api.lab_sample.record_handoff",
						args: { sample_name: sample, transport_mode: values.transport_mode || "Manual" },
						freeze: true,
						callback() {
							frappe.show_alert({ message: __("Sample handed off."), indicator: "green" });
							self.refresh();
						},
					});
				},
			});
			d.show();
		});

		this.$container.find(".btn-receive").on("click", function () {
			const sample = $(this).data("sample");
			const d = new frappe.ui.Dialog({
				title: __("Receive Sample in Lab"),
				fields: [
					{
						fieldtype: "Select", fieldname: "sample_condition", label: __("Sample Condition"),
						options: "Acceptable\nHemolyzed\nClotted\nInsufficient\nContaminated", reqd: 1,
					},
				],
				primary_action_label: __("Receive"),
				primary_action(values) {
					d.hide();
					frappe.call({
						method: "alcura_ipd_ext.api.lab_sample.record_receipt",
						args: { sample_name: sample, sample_condition: values.sample_condition },
						freeze: true,
						callback(r) {
							const msg = r.message?.needs_recollection
								? __("Sample received — recollection needed.")
								: __("Sample received.");
							frappe.show_alert({ message: msg, indicator: "green" });
							self.refresh();
						},
					});
				},
			});
			d.show();
		});

		this.$container.find(".btn-complete").on("click", function () {
			const order = $(this).data("order");
			frappe.call({
				method: "alcura_ipd_ext.api.clinical_order.record_milestone",
				args: { order, milestone: "Result Published" },
				callback() {
					frappe.call({
						method: "alcura_ipd_ext.api.clinical_order.transition_order",
						args: { order, new_status: "Completed" },
						callback() {
							frappe.show_alert({ message: __("Result published. Order completed."), indicator: "green" });
							self.refresh();
						},
					});
				},
			});
		});

		this.$container.find(".btn-crit-ack").on("click", function () {
			const sample = $(this).data("sample");
			frappe.call({
				method: "alcura_ipd_ext.api.lab_sample.acknowledge_critical_result",
				args: { sample_name: sample },
				freeze: true,
				callback() {
					frappe.show_alert({ message: __("Critical result acknowledged."), indicator: "green" });
					self.refresh();
				},
			});
		});
	}

	_start_auto_refresh() {
		this._refresh_interval = setInterval(() => this.refresh(), 30000);
	}

	destroy() {
		if (this._refresh_interval) clearInterval(this._refresh_interval);
	}
}
