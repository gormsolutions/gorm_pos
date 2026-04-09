// frappe.pages['server-monitor'].on_page_load = function(wrapper) {
// 	var page = frappe.ui.make_app_page({
// 		parent: wrapper,
// 		title: 'Server Monitor',
// 		single_column: true
// 	});
// }apps/gormsolutions_mobile_app////server_monitor.py

frappe.pages['server-monitor'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: '✨ Server & MariaDB Disk Monitor',
        single_column: true
    });

    frappe.call({
        method: "gormsolutions_mobile_app.custom_api.maridb.server_monitor.get_disk_usage",
        callback: function (r) {
            const data = r.message;
            const disk = data.disk || {};
            const mariadb = data.mariadb || [];

            const mariadbRows = mariadb.map(db => `
                <tr class="border-t hover:bg-gray-50 transition">
                    <td class="p-3 font-medium text-gray-700">${db.database_name}</td>
                    <td class="p-3 text-purple-700">${db.data_size_mb.toFixed(2)} MB</td>
                    <td class="p-3 text-indigo-700">${db.index_size_mb.toFixed(2)} MB</td>
                    <td class="p-3 text-blue-700 font-semibold">${db.total_size_mb.toFixed(2)} MB</td>
                </tr>
            `).join("");

            $(wrapper).html(`
                <div class="flex justify-center items-center min-h-[85vh]">
                    <div class="max-w-5xl w-full space-y-10 p-8 bg-gradient-to-br from-white to-blue-50 rounded-xl shadow-2xl border border-gray-200">
                        
                        <!-- Server Disk Usage -->
                        <div class="bg-white rounded-2xl shadow-lg p-6">
                            <h2 class="text-3xl font-bold text-blue-700 mb-6">🖥️ Server Disk Usage</h2>
                            <table class="w-full text-left border-collapse text-lg">
                                <thead>
                                    <tr class="bg-blue-100 text-blue-900">
                                        <th class="p-3">Total</th>
                                        <th class="p-3">Used</th>
                                        <th class="p-3">Free</th>
                                        <th class="p-3">Used %</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr class="border-t">
                                        <td class="p-3">${disk.total.toFixed(2)} GB</td>
                                        <td class="p-3 text-red-600 font-semibold">${disk.used.toFixed(2)} GB</td>
                                        <td class="p-3 text-green-600 font-semibold">${disk.free.toFixed(2)} GB</td>
                                        <td class="p-3 font-semibold">${disk.percent_used.toFixed(2)}%</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <!-- MariaDB Disk Usage -->
                        <div class="bg-white rounded-2xl shadow-lg p-6">
                            <h2 class="text-3xl font-bold text-blue-700 mb-6">🛢️ MariaDB Disk Usage</h2>
                            <table class="w-full text-left border-collapse text-lg">
                                <thead>
                                    <tr class="bg-blue-100 text-blue-900">
                                        <th class="p-3">Database</th>
                                        <th class="p-3">Data Size (MB)</th>
                                        <th class="p-3">Index Size (MB)</th>
                                        <th class="p-3">Total DB Size (MB)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${mariadbRows}
                                </tbody>
                            </table>
                        </div>

                    </div>
                </div>
            `);
        }
    });
};
