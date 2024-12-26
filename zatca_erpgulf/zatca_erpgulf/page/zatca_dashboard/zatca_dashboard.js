frappe.pages['zatca-dashboard'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Zatca Dashboard (ErpGulf)',
        single_column: true
    });
    new ZatcaDashboard(page);
};

class ZatcaDashboard {
    constructor(page) {
        this.page = page;
        this.make_form();
        this.render_cards();
        this.render_charts();
        this.render_list();
    }

    make_form() {
        this.form = new frappe.ui.FieldGroup({
            fields: [{
                fieldtype: "HTML",
                fieldname: "preview"
            },
            {
                label: __("Malik"),
                fieldname: "malik",
                fieldtype: "HTML"
            },
            {
                label: __("Zatca Charts"),
                fieldname: "zatca_charts",
                fieldtype: "HTML"
            },
            {
                label: __("Current Month Zatca Status"),
                fieldname: "current_month_zatca_chart",
                fieldtype: "HTML"
            },
            {
                label: __("Zatca List"),
                fieldname: "zatca_list",
                fieldtype: "HTML"
            }
            ],
            body: this.page.body,
        });
        this.form.make();
    }

    render_charts() {
        let charts_container = `
<div style="display: flex; justify-content: space-between;  box-sizing: border-box;">
	<div style="width: 49%;background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);" >   
	
	<canvas id="currentMonthChart" style="flex: 1; height: 250px;"></canvas>
	</div>
<div style="width: 49% ;background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);" > <canvas id="monthlyChart" style="flex: 1; height: 250px; margin-right: 10px;"></canvas> </div>
</div>

        `;

        this.form.get_field("zatca_charts").html(charts_container);
        if (typeof Chart === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
            document.head.appendChild(script);

            script.onload = () => {
                this.fetch_monthly_zatca_status("monthlyChart", "Monthly ZATCA Status Count", "bar");
                this.fetch_current_month_zatca_status("currentMonthChart", "Current Month ZATCA Status Count", "pie");
            };

            script.onerror = (error) => {
                console.error("Error loading Chart.js:", error);
            };
        } else {
            this.fetch_monthly_zatca_status("monthlyChart", "Monthly ZATCA Status Count", "bar");
            this.fetch_current_month_zatca_status("currentMonthChart", "Current Month ZATCA Status Count", "pie");
        }



    }

    fetch_monthly_zatca_status(chartId, label, chartType = 'bar') {
        const monthlyStatusCount = {};

        // Get the current year
        const currentYear = new Date().getFullYear();

        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Sales Invoice",
                fields: ["posting_date", "custom_zatca_status"],
                filters: {
                    docstatus: 1
                },
                limit_page_length: 5000,
            },
            callback: (response) => {
                if (response.message) {
                    response.message.forEach((invoice) => {
                        const postingDate = new Date(invoice.posting_date);
                        const invoiceYear = postingDate.getFullYear(); // Get the year of the invoice
                        const month = postingDate.getMonth(); // Get the month of the invoice
                        const status = invoice.custom_zatca_status;

                        // Check if the invoice is from the current year
                        if (invoiceYear === currentYear) {
                            if (!monthlyStatusCount[status]) {
                                monthlyStatusCount[status] = Array(12).fill(0);
                            }
                            monthlyStatusCount[status][month] += 1;
                        }
                    });

                    // Render the chart with the data for the current year
                    this.render_chart(chartId, monthlyStatusCount, label, chartType);
                }
            },
        });
    }

    fetch_current_month_zatca_status(chartId, label, chartType = 'pie') {
        const currentMonth = new Date().getMonth(); // Dynamically get the current month
        const monthlyStatusCount = {};
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Sales Invoice",
                fields: ["posting_date", "custom_zatca_status"],
                filters: {
                    docstatus: 1
                },
                limit_page_length: 5000,
            },
            callback: (response) => {
                if (response.message) {
                    response.message.forEach((invoice) => {
                        const invoiceMonth = new Date(invoice.posting_date).getMonth();
                        const status = invoice.custom_zatca_status;

                        if (invoiceMonth === currentMonth) {
                            monthlyStatusCount[status] = (monthlyStatusCount[status] || 0) + 1;
                        }
                    });
                    this.render_chart(chartId, monthlyStatusCount, label, chartType);
                }
            },
        });
    }

    render_chart(chartId, data, label, chartType) {
        const ctx = document.getElementById(chartId).getContext('2d');
        const labels = chartType === 'bar' ? ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'] :
            Object.keys(data);

        const datasets = Object.keys(data).map((status, index) => {
            const colors = [
                'rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)',
                'rgba(75, 192, 192, 0.2)', 'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)',
            ];
            return {
                label: status,
                data: chartType === 'bar' ? data[status] : [data[status]],
                backgroundColor: colors[index % colors.length],
                borderColor: colors[index % colors.length].replace("0.2", "1"),
                borderWidth: 1,

            };
        });

        new Chart(ctx, {
            type: chartType,
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: chartType === 'bar' ? {
                    x: {
                        stacked: true
                    },
                    y: {
                        stacked: true
                    },
                } : {},
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: label
                    }
                }
            },
        });
    }

    render_cards() {
        const statuses = ['Reported', 'Cleared', 'Cleared With Warning', 'Failed', 'Not Submitted'];

        function getCountForStatus(status) {
            return frappe.call({
                method: "frappe.client.get_count",
                args: {
                    doctype: "Sales Invoice",
                    filters: {
                        custom_zatca_status: status
                    }
                }
            });
        }

        const statusPromises = statuses.map(status => getCountForStatus(status));

        Promise.all(statusPromises).then((responses) => {
            let malikContent = `<div class="card-container" style="display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; margin-top: 20px;margin-bottom: 20px;">`;

            responses.forEach((response, index) => {
                const count = response.message || 0;
                malikContent += this.create_card(statuses[index], count);
            });

            malikContent += '</div>';
            this.form.get_field("malik").html(malikContent);
        });
    }

    create_card(title, count) {
        return `
	    <a href="/app/query-report/Zatca Status Report?&status=${title}" style="color: ">
        <div class="number-card" style="flex: 1 1 22%; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); min-width: 100px;">
            <h4 style="font-weight: bold; color: #495057;">
               ${title}
            </h4>            

            <div class="count" style="font-size: 32px; font-weight: bold; color: #007bff; margin-top: 10px;">${count}</div>
        </div> </a>

	
`;
    }

    render_list() {
        this.form.get_field("zatca_list").html('<div id="dynamicContent" style="background-color: #f8f9fa;margin-top:15px; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);" ></div>');
        this.createList();
    }

    createList() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                'doctype': 'Sales Invoice',
                'fields': ['name', 'posting_date', 'customer_name', 'grand_total', 'custom_zatca_status'],
                'filters': {
                    'custom_zatca_status': 'Not Submitted',
                    'docstatus': 1
                },
                order_by: "posting_date desc"
            },
            callback: (response) => {
                if (response.message && response.message.length > 0) {
                    this.createContent(response.message);
                } else {
                    document.getElementById("dynamicContent").innerHTML = "<p>No data available</p>";
                }
            }
        });
    }


    createContent(data) {
        var container = document.getElementById("dynamicContent");

        var table = document.createElement('table');
        table.setAttribute('class', 'table table-bordered table-hover');

        var caption = document.createElement('caption');
        caption.setAttribute('class', 'text-center');
        caption.innerHTML = "Sales Invoice List";
        table.appendChild(caption);

        var thead = document.createElement('thead');
        var headerRow = document.createElement('tr');
        ['Invoice', 'Customer', 'Date', 'Amount', 'ZATCA Status'].forEach((headerText) => {
            var th = document.createElement('th');
            th.innerHTML = headerText;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        var tbody = document.createElement('tbody');
        data.forEach((invoice) => {
            var row = document.createElement('tr');
            row.innerHTML = `
                <td><a href="/app/sales-invoice/${invoice.name}">${invoice.name}</a></td>
                <td style="text-align: left;">${invoice.customer_name}</td>
                <td  style="text-align: center;">${invoice.posting_date}</td>
                 <td style="text-align: right;">${invoice.grand_total.toFixed(2)}</td> <!-- Two decimal and right-aligned -->
                <td></td>`;
            tbody.appendChild(row);
            var statusCell = row.cells[4]; // This is the last cell (custom_zatca_status)
            var badge = document.createElement('span');
            badge.setAttribute('class', invoice.custom_zatca_status === 'CLEARED' ? 'badge badge-success' : 'badge badge-danger');
            badge.textContent = invoice.custom_zatca_status;
            statusCell.appendChild(badge);
        });

        table.appendChild(tbody);
        container.appendChild(table);
    }
    load_chartjs() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
}