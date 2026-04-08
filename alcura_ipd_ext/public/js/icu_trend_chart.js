/**
 * ICU Trend Chart — reusable charting component for bedside observation trends.
 *
 * Uses frappe.Chart (frappe-charts) to render line charts with critical range
 * bands and missed-observation markers. Can be embedded in IPD Bedside Chart
 * form, ICU Dashboard workspace, or any custom page.
 *
 * Usage:
 *   const chart = new alcura_ipd_ext.ICUTrendChart({
 *     wrapper: document.getElementById("chart-area"),
 *     bedside_chart: "BSC-00042",
 *     parameter_name: "Temperature",
 *     from_datetime: "2026-04-01 00:00:00",
 *     to_datetime: "2026-04-08 23:59:59",
 *     critical_low: 35.5,
 *     critical_high: 39.5,
 *   });
 *   chart.render();
 */

frappe.provide("alcura_ipd_ext");

alcura_ipd_ext.ICUTrendChart = class ICUTrendChart {
	constructor(opts) {
		this.wrapper = opts.wrapper;
		this.bedside_chart = opts.bedside_chart;
		this.parameter_name = opts.parameter_name;
		this.from_datetime = opts.from_datetime || null;
		this.to_datetime = opts.to_datetime || null;
		this.critical_low = opts.critical_low || null;
		this.critical_high = opts.critical_high || null;
		this.height = opts.height || 250;
		this.chart_instance = null;
	}

	async render() {
		const data = await this._fetch_trend();
		if (!data || !data.length) {
			this.wrapper.innerHTML = `<p class="text-muted text-center">
				${__("No observations recorded for")} ${this.parameter_name}
			</p>`;
			return;
		}

		const labels = data.map((d) =>
			frappe.datetime.str_to_user(d.datetime)
		);
		const values = data.map((d) => d.value);

		const datasets = [
			{
				name: this.parameter_name,
				values: values,
			},
		];

		if (this.critical_low) {
			datasets.push({
				name: __("Critical Low"),
				values: new Array(values.length).fill(this.critical_low),
			});
		}
		if (this.critical_high) {
			datasets.push({
				name: __("Critical High"),
				values: new Array(values.length).fill(this.critical_high),
			});
		}

		this.chart_instance = new frappe.Chart(this.wrapper, {
			type: "line",
			height: this.height,
			data: {
				labels: labels,
				datasets: datasets,
			},
			lineOptions: {
				hideDots: 0,
				regionFill: 0,
			},
			tooltipOptions: {
				formatTooltipY: (d) =>
					d != null ? d.toFixed(1) : "--",
			},
			colors: this._get_colors(),
		});
	}

	async refresh(opts) {
		if (opts) {
			Object.assign(this, opts);
		}
		await this.render();
	}

	_get_colors() {
		const colors = ["#4299e1"];
		if (this.critical_low) colors.push("#e53e3e");
		if (this.critical_high) colors.push("#e53e3e");
		return colors;
	}

	async _fetch_trend() {
		const resp = await frappe.call({
			method: "alcura_ipd_ext.api.charting.get_observation_trend",
			args: {
				bedside_chart: this.bedside_chart,
				parameter_name: this.parameter_name,
				from_datetime: this.from_datetime,
				to_datetime: this.to_datetime,
			},
		});
		return resp.message || [];
	}
};

/**
 * Multi-parameter overlay trend chart.
 */
alcura_ipd_ext.ICUMultiTrendChart = class ICUMultiTrendChart {
	constructor(opts) {
		this.wrapper = opts.wrapper;
		this.bedside_chart = opts.bedside_chart;
		this.parameter_names = opts.parameter_names || [];
		this.from_datetime = opts.from_datetime || null;
		this.to_datetime = opts.to_datetime || null;
		this.height = opts.height || 300;
		this.chart_instance = null;
	}

	async render() {
		const data = await this._fetch_trends();
		if (!data || !Object.keys(data).length) {
			this.wrapper.innerHTML = `<p class="text-muted text-center">
				${__("No observations recorded")}
			</p>`;
			return;
		}

		const all_times = new Set();
		for (const param_data of Object.values(data)) {
			for (const point of param_data) {
				all_times.add(point.datetime);
			}
		}
		const sorted_times = Array.from(all_times).sort();
		const labels = sorted_times.map((t) => frappe.datetime.str_to_user(t));

		const datasets = [];
		for (const [param_name, points] of Object.entries(data)) {
			const time_map = {};
			for (const p of points) {
				time_map[p.datetime] = p.value;
			}
			datasets.push({
				name: param_name,
				values: sorted_times.map((t) =>
					time_map[t] !== undefined ? time_map[t] : null
				),
			});
		}

		this.chart_instance = new frappe.Chart(this.wrapper, {
			type: "line",
			height: this.height,
			data: { labels, datasets },
			lineOptions: { hideDots: 0, regionFill: 0 },
			tooltipOptions: {
				formatTooltipY: (d) =>
					d != null ? d.toFixed(1) : "--",
			},
		});
	}

	async _fetch_trends() {
		const resp = await frappe.call({
			method: "alcura_ipd_ext.api.charting.get_multi_parameter_trend",
			args: {
				bedside_chart: this.bedside_chart,
				parameter_names: JSON.stringify(this.parameter_names),
				from_datetime: this.from_datetime,
				to_datetime: this.to_datetime,
			},
		});
		return resp.message || {};
	}
};

/**
 * Observation schedule grid showing expected vs actual entries.
 */
alcura_ipd_ext.ObservationScheduleGrid = class ObservationScheduleGrid {
	constructor(opts) {
		this.wrapper = opts.wrapper;
		this.bedside_chart = opts.bedside_chart;
		this.from_datetime = opts.from_datetime || null;
		this.to_datetime = opts.to_datetime || null;
	}

	async render() {
		const slots = await this._fetch_schedule();
		if (!slots || !slots.length) {
			this.wrapper.innerHTML = `<p class="text-muted text-center">
				${__("No schedule data available")}
			</p>`;
			return;
		}

		let html = '<div class="observation-schedule-grid">';
		html += '<table class="table table-sm table-bordered">';
		html += `<thead><tr>
			<th>${__("Expected")}</th>
			<th>${__("Recorded")}</th>
			<th>${__("Status")}</th>
		</tr></thead><tbody>`;

		for (const slot of slots) {
			const status_class = slot.is_missed
				? "text-danger font-weight-bold"
				: slot.is_future
				? "text-muted"
				: "text-success";
			const status_text = slot.is_missed
				? __("Missed")
				: slot.is_future
				? __("Upcoming")
				: __("Recorded");
			const actual = slot.actual_at
				? frappe.datetime.str_to_user(slot.actual_at)
				: "--";

			html += `<tr>
				<td>${frappe.datetime.str_to_user(slot.expected_at)}</td>
				<td>${actual}</td>
				<td class="${status_class}">${status_text}</td>
			</tr>`;
		}

		html += "</tbody></table></div>";
		this.wrapper.innerHTML = html;
	}

	async _fetch_schedule() {
		const resp = await frappe.call({
			method: "alcura_ipd_ext.api.charting.get_observation_schedule",
			args: {
				bedside_chart: this.bedside_chart,
				from_datetime: this.from_datetime,
				to_datetime: this.to_datetime,
			},
		});
		return resp.message || [];
	}
};
