function refreshDashboard() {
    if (window.location.pathname !== '/') return;

    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            if (data.error) return;

            // Update Stats
            document.querySelector('#stat-total').textContent = data.stats.total;
            document.querySelector('#stat-passed').textContent = data.stats.passed;
            document.querySelector('#stat-failed').textContent = data.stats.failed;
            document.querySelector('#stat-rejected').textContent = data.stats.rejected;
            document.querySelector('#stat-rate').textContent = data.stats.rate + '%';

            // Update Table
            const tbody = document.querySelector('#contracts-table tbody');
            if (!tbody) return;

            // Keep header row
            const headerHtml = tbody.querySelector('tr:first-child').outerHTML;
            let rowsHtml = headerHtml;

            data.active_contracts.forEach(c => {
                const dateSplit = c.created_at.substring(0, 16).replace('T', ' ');
                rowsHtml += `
                <tr>
                    <td><strong>${c.description}</strong><br><small>${c.task}</small></td>
                    <td><span class="badge" data-bg="${c.status}">${c.status.toUpperCase()}</span></td>
                    <td>${dateSplit}</td>
                    <td><a href="/contract/${c.id}">View Details</a></td>
                </tr>`;
            });
            tbody.innerHTML = rowsHtml;
        })
        .catch(err => console.error("Error fetching dashboard data:", err));
}

// Check every 10 seconds
setInterval(refreshDashboard, 10000);
