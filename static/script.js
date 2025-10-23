// Set max date to today on page load
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date');
    const today = new Date().toISOString().split('T')[0];
    dateInput.max = today;
});

// Form submission handler
document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const submitBtn = form.querySelector('.search-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');

    // Get form values
    const date = document.getElementById('date').value;
    const pts = document.getElementById('pts').value;
    const ast = document.getElementById('ast').value;
    const reb = document.getElementById('reb').value;
    const logic = document.getElementById('logic').value;

    // Build query parameters
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    if (pts) params.append('pts', pts);
    if (ast) params.append('ast', ast);
    if (reb) params.append('reb', reb);
    params.append('logic', logic);

    // Show loading state
    submitBtn.disabled = true;
    btnText.textContent = 'Searching...';
    loader.classList.remove('hidden');

    // Hide previous results and errors
    document.getElementById('results').classList.add('hidden');
    document.getElementById('error').classList.add('hidden');

    try {
        const response = await fetch(`/api/stats?${params.toString()}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch stats');
        }

        if (data.success) {
            displayResults(data);
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
    } catch (error) {
        displayError(error.message);
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        btnText.textContent = 'Search Stats';
        loader.classList.add('hidden');
    }
});

function displayResults(data) {
    const resultsSection = document.getElementById('results');
    const resultsBody = document.getElementById('resultsBody');
    const noResults = document.getElementById('noResults');

    // Update metadata
    document.getElementById('resultsDate').textContent = `📅 ${formatDate(data.date)}`;
    document.getElementById('resultsSource').textContent = `🔌 Source: ${data.source || 'N/A'}`;
    document.getElementById('resultsCount').textContent = `👥 ${data.count} player${data.count !== 1 ? 's' : ''}`;

    // Display filters
    displayFilters(data.filters);

    // Clear previous results
    resultsBody.innerHTML = '';

    if (data.players && data.players.length > 0) {
        // Sort players by PTS, then AST, then REB (descending)
        const sortedPlayers = [...data.players].sort((a, b) => {
            if (b.PTS !== a.PTS) return b.PTS - a.PTS;
            if (b.AST !== a.AST) return b.AST - a.AST;
            return b.REB - a.REB;
        });

        // Populate table
        sortedPlayers.forEach(player => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${escapeHtml(player.Player)}</strong></td>
                <td>${escapeHtml(player.Team)}</td>
                <td class="stat-col">${player.PTS}</td>
                <td class="stat-col">${player.REB}</td>
                <td class="stat-col">${player.AST}</td>
            `;
            resultsBody.appendChild(row);
        });

        noResults.classList.add('hidden');
    } else {
        noResults.classList.remove('hidden');
    }

    resultsSection.classList.remove('hidden');
}

function displayFilters(filters) {
    const filtersDisplay = document.getElementById('resultsFilters');
    const applied = [];

    if (filters.pts !== null) applied.push(`${filters.pts}+ PTS`);
    if (filters.ast !== null) applied.push(`${filters.ast}+ AST`);
    if (filters.reb !== null) applied.push(`${filters.reb}+ REB`);

    if (applied.length === 0) {
        applied.push('20+ PTS', '5+ AST', '7+ REB (defaults)');
        filtersDisplay.textContent = `📊 Filters (ANY): ${applied.join(', ')}`;
    } else {
        const logicText = filters.logic.toUpperCase();
        filtersDisplay.textContent = `📊 Filters (${logicText}): ${applied.join(', ')}`;
    }
}

function displayError(message) {
    const errorBox = document.getElementById('error');
    errorBox.textContent = `❌ Error: ${message}`;
    errorBox.classList.remove('hidden');
}

function formatDate(dateStr) {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
