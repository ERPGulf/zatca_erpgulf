frappe.pages['zatca-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Zatca Dashboard (ErpGulf)',
        single_column: true
    });
    new test(page);
};

test = class test {
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
                    fieldname: "preview",
                },
               {
                    label: __("Malik"),
                    fieldname: "malik",
                    fieldtype: "HTML",
                },
               {
                    label: __("Zatca Charts"),
                    fieldname: "zatca_charts",
                    fieldtype: "HTML",
                },
               {
                    label: __("Zatca List"),
                    fieldname: "zatca_list",
                    fieldtype: "HTML",
                },

            ],
            body: this.page.body,
        });

        this.form.make();
    }

render_list() {
    // Insert dynamic content container
    this.form.get_field("zatca_list").html('<div id="dynamicContent"></div>');

    // Fetch and render the content after receiving data
    this.createList();  // Now calling the correct function to create list after dynamic content is set
}

createList() {
    // Example data structure - you should update it based on your actual API response
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            'doctype': 'Sales Invoice',  // Your Doctype to fetch data from
            'fields': ['name', 'posting_date', 'customer_name', 'grand_total', 'custom_zatca_status'],
            'filters': {
            'custom_zatca_status': 'Cleared', // Example filter: only fetch invoices with 'Paid' status
        },
        },
        callback: (response) => {
            // Pass the data to create the table content
            if (response.message && response.message.length > 0) {
                this.createContent(response.message);
            } else {
                // Handle case if no data is returned
                document.getElementById("dynamicContent").innerHTML = "<p>No data available</p>";
            }
        }
    });
}

createContent(data) {
    var container = document.getElementById("dynamicContent");

    // Create the table element
    var table = document.createElement('table');
    table.setAttribute('class', 'table table-bordered table-hover');

    // Create the caption
    var caption = document.createElement('caption');
    caption.setAttribute('class', 'text-center');
    caption.innerHTML = "Sales Invoice List";
    table.appendChild(caption);

    // Create the thead element
    var thead = document.createElement('thead');
    thead.setAttribute('class', 'table-info');
    var theadRow = document.createElement('tr');
    thead.appendChild(theadRow);

    // Header cells
    var headers = ['Inv.Number', 'Date', 'Supplier', 'Amount', 'Zatca Status'];
    headers.forEach(header => {
        var th = document.createElement('th');
        th.innerHTML = header;
        theadRow.appendChild(th);
    });

    // Create the tbody element
    var tbody = document.createElement('tbody');

    // Fill rows with dynamic data
    data.forEach(rowData => {
        var row = document.createElement('tr');
        var keys = Object.keys(rowData);

        keys.forEach(key => {
            var cell = document.createElement('td');

            if (key === 'grand_total') {
                // Format grand total to 2 decimal places
                var amount = parseFloat(rowData[key]).toFixed(2);
                cell.textContent = amount.toLocaleString();
            } else if (key === 'custom_zatca_status') {
                // Create a badge for status
                var badge = document.createElement('span');
                badge.setAttribute('class', rowData[key] === 'CLEARED' ? 'badge badge-success' : 'badge badge-danger');
                badge.textContent = rowData[key];
                cell.appendChild(badge);
            } else if (key === 'name') {
                // Create a link for the invoice
                var link = document.createElement('a');
                link.href = `/app/sales-invoice/${rowData[key]}`;
                link.target = '_blank';
                link.textContent = rowData[key];
                cell.appendChild(link);
            } else {
                cell.textContent = rowData[key];
            }

            row.appendChild(cell);
        });

        tbody.appendChild(row);
    });

    // Append the table elements
    table.appendChild(thead);
    table.appendChild(tbody);

    // Append the table to the container
    container.appendChild(table);
}


    create_card(title, count) {
        return `
        <div class="number-card" style="flex: 1 1 22%; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); min-width: 100px;">
            <h4 style="font-weight: bold; color: #495057;">${title}</h4>
            <div class="count" style="font-size: 32px; font-weight: bold; color: #007bff; margin-top: 10px;">${count}</div>
        </div>`;
    }

    render_cards() {
        const statuses = ['Reported', 'Cleared', 'Cleared With Warning', 'Failed','Not Submitted'];
        console.log('i am in');

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

    render_charts() {
        let zatca_chart_content = `
            <canvas id="myChart" style="flex: 1; max-width: 100%; height: 250px; box-sizing: border-box; border-radius: 8px; border: 1px solid #ddd; background-color: #fff; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); padding: 20px; margin-right: 10px;">
            </canvas>
        `;

        this.form.get_field("zatca_charts").html(zatca_chart_content);

        if (typeof Chart === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
            document.head.appendChild(script);

            script.onload = () => {
                fetch_monthly_zatca_status("myChart", "Monthly ZATCA Status Count");
            };

            script.onerror = (error) => {
                console.error("Error loading Chart.js:", error);
            };
        } else {
            fetch_monthly_zatca_status("myChart", "Monthly ZATCA Status Count");
        }

        function fetch_monthly_zatca_status(chartId, label, chartType = 'bar') {
            const monthlyStatusCount = {};

            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Sales Invoice",
                    fields: ["posting_date", "custom_zatca_status"],
                    filters: {
                        docstatus: 1,
                    },
                    limit_page_length: 5000  
                },
                callback: function(response) {
                    console.log(response);  // Debug the response data
                    if (response.message) {
                        response.message.forEach(invoice => {
                            const month = new Date(invoice.posting_date).getMonth();
                            const status = invoice.custom_zatca_status;

                            if (!monthlyStatusCount[status]) {
                                monthlyStatusCount[status] = Array(12).fill(0);
                            }
                            
                            monthlyStatusCount[status][month] += 1;
                        });

                        render_chart(chartId, monthlyStatusCount, label, chartType);
                    } else {
                        console.log("No records found.");
                    }
                }
            });
        }

        function render_chart(chartId, monthlyStatusCount, label, chartType = 'bar') {
            const ctx = document.getElementById(chartId).getContext('2d');

            const labels = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

            const datasets = Object.keys(monthlyStatusCount).map((status, index) => {
                const colors = [
                    'rgba(255, 99, 132, 0.2)', 'rgba(54, 162, 235, 0.2)', 'rgba(255, 206, 86, 0.2)', 
                    'rgba(75, 192, 192, 0.2)', 'rgba(153, 102, 255, 0.2)', 'rgba(255, 159, 64, 0.2)', 
                    'rgba(100, 199, 132, 0.2)', 'rgba(200, 162, 235, 0.2)', 'rgba(255, 200, 100, 0.2)', 
                    'rgba(75, 200, 255, 0.2)', 'rgba(153, 200, 200, 0.2)', 'rgba(255, 100, 200, 0.2)'
                ];

                return {
                    label: `${status} - ${label}`,
                    data: monthlyStatusCount[status],
                    backgroundColor: colors[index % colors.length],
                    borderColor: colors[index % colors.length].replace("0.2", "1"),
                    borderWidth: 1
                };
            });

            new Chart(ctx, {
                type: chartType,
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            stacked: true,
                        },
                        y: {
                            stacked: true
                        }
                    }
                }
            });
        }
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
};
