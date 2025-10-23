// Fantasy Basketball Dashboard JavaScript

document.addEventListener('DOMContentLoaded', () => {
    loadFantasyData();

    // Sync button handler
    document.getElementById('syncBtn').addEventListener('click', syncFantasyData);

    // Team select handler
    document.getElementById('teamSelect').addEventListener('change', handleTeamSelect);
});

async function syncFantasyData() {
    const btn = document.getElementById('syncBtn');
    const btnText = btn.querySelector('.btn-text');
    const loader = btn.querySelector('.loader');

    btn.disabled = true;
    btnText.textContent = '⏳ Syncing...';
    loader.classList.remove('hidden');

    try {
        const response = await fetch('/api/fantasy/sync', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            alert(`✅ Sync successful!\n\nTeams: ${data.teams_count}\nRosters: ${data.rosters_count}\nMatchups: ${data.matchups_count}`);
            loadFantasyData(); // Reload data
        } else {
            alert(`❌ Sync failed: ${data.errors?.join(', ')}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        btn.disabled = false;
        btnText.textContent = '🔄 Sync League Data';
        loader.classList.add('hidden');
    }
}

async function loadFantasyData() {
    console.log('🔄 Starting to load fantasy data...');
    showLoading();

    try {
        // Load teams and standings
        console.log('📊 Loading standings...');
        await loadStandings();
        console.log('✅ Standings loaded');

        // Load matchups
        console.log('🏀 Loading matchups...');
        await loadMatchups();
        console.log('✅ Matchups loaded');

    } catch (error) {
        console.error('❌ Error in loadFantasyData:', error);
        displayError(error.message);
    } finally {
        console.log('🏁 Hiding loading spinner...');
        hideLoading();
        console.log('✅ Fantasy data load complete');
    }
}

async function loadStandings() {
    try {
        const response = await fetch('/api/fantasy/teams');
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load teams');
        }

        const teams = data.teams;

        // Sort by wins descending
        teams.sort((a, b) => b.wins - a.wins);

        // Update count
        document.getElementById('teamCount').textContent = `${teams.length} teams`;

        // Populate standings table
        const tbody = document.getElementById('standingsBody');
        tbody.innerHTML = '';

        teams.forEach((team, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${index + 1}</strong></td>
                <td><strong>${team.team_name}</strong></td>
                <td>${team.owner || 'N/A'}</td>
                <td>${team.wins}-${team.losses}</td>
                <td>${team.points_for || 0}</td>
                <td>${team.points_against || 0}</td>
            `;
            tbody.appendChild(row);
        });

        // Populate team select dropdown
        const teamSelect = document.getElementById('teamSelect');
        teamSelect.innerHTML = '<option value="">Select a team...</option>';
        teams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.team_id;
            option.textContent = team.team_name;
            teamSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Error loading standings:', error);
    }
}

async function loadMatchups() {
    try {
        const response = await fetch('/api/fantasy/matchups');
        const data = await response.json();

        if (!data.success || !data.matchups || data.matchups.length === 0) {
            console.warn('No matchups available');
            // Hide matchups section if no data
            document.getElementById('matchups').style.display = 'none';
            return;
        }

        const matchups = data.matchups;

        // Update count
        document.getElementById('matchupCount').textContent = `${matchups.length} matchups`;

        // Populate matchups
        const matchupsList = document.getElementById('matchupsList');
        matchupsList.innerHTML = '';

        matchups.forEach(matchup => {
            const card = document.createElement('div');
            card.className = 'matchup-card';

            const homeWinning = matchup.home_score > matchup.away_score;
            const awayWinning = matchup.away_score > matchup.home_score;

            card.innerHTML = `
                <div class="matchup-teams">
                    <div class="matchup-team ${homeWinning ? 'winning' : ''}">
                        <div class="team-name">${matchup.home_team}</div>
                        <div class="team-score">${matchup.home_score.toFixed(1)}</div>
                    </div>
                    <div class="matchup-vs">VS</div>
                    <div class="matchup-team ${awayWinning ? 'winning' : ''}">
                        <div class="team-name">${matchup.away_team}</div>
                        <div class="team-score">${matchup.away_score.toFixed(1)}</div>
                    </div>
                </div>
            `;

            matchupsList.appendChild(card);
        });

    } catch (error) {
        console.error('Error loading matchups:', error);
    }
}

async function handleTeamSelect(e) {
    const teamId = e.target.value;

    if (!teamId) {
        document.getElementById('rosterContent').classList.add('hidden');
        return;
    }

    try {
        const response = await fetch('/api/fantasy/rosters');
        const data = await response.json();

        if (!data.success) {
            throw new Error('Failed to load rosters');
        }

        // Filter roster for selected team
        const teamRoster = data.rosters.filter(p => p.team_id == teamId);

        // Sort by avg_points descending
        teamRoster.sort((a, b) => (b.avg_points || 0) - (a.avg_points || 0));

        // Calculate totals
        let totalAvgPoints = 0;
        let totalPoints = 0;

        // Populate roster table
        const tbody = document.getElementById('rosterBody');
        tbody.innerHTML = '';

        teamRoster.forEach(player => {
            const row = document.createElement('tr');

            const statusText = player.injured ? (player.injuryStatus || 'Out') : 'Active';
            const avgPts = player.avg_points || 0;
            const totPts = player.total_points || 0;

            totalAvgPoints += avgPts;
            totalPoints += totPts;

            row.innerHTML = `
                <td><strong><a href="#" class="player-link" data-player="${player.player_name}">${player.player_name}</a></strong></td>
                <td>${player.position || 'N/A'}</td>
                <td>${player.pro_team || 'N/A'}</td>
                <td>${avgPts.toFixed(1)}</td>
                <td>${totPts.toFixed(1)}</td>
                <td>${statusText}</td>
            `;

            if (player.injured) {
                row.classList.add('injured-row');
            }

            tbody.appendChild(row);
        });

        // Add totals row
        const totalRow = document.createElement('tr');
        totalRow.style.fontWeight = 'bold';
        totalRow.style.backgroundColor = 'var(--gray-100)';
        totalRow.style.borderTop = '2px solid var(--gray-300)';
        totalRow.innerHTML = `
            <td colspan="3" style="text-align: right;"><strong>TEAM TOTAL:</strong></td>
            <td><strong>${totalAvgPoints.toFixed(1)}</strong></td>
            <td><strong>${totalPoints.toFixed(1)}</strong></td>
            <td></td>
        `;
        tbody.appendChild(totalRow);

        document.getElementById('rosterContent').classList.remove('hidden');

        // Add click handlers to player links
        document.querySelectorAll('.player-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const playerName = e.target.dataset.player;
                viewPlayerStats(playerName);
            });
        });

    } catch (error) {
        displayError(error.message);
    }
}

async function viewPlayerStats(playerName) {
    try {
        showLoading();
        const response = await fetch(`/api/player/${encodeURIComponent(playerName)}?limit=10`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error);
        }

        // Create modal or section to display player stats
        displayPlayerStatsModal(data);

    } catch (error) {
        displayError(error.message);
    } finally {
        hideLoading();
    }
}

function displayPlayerStatsModal(data) {
    const player = data.player;
    const games = data.games;

    // Calculate season averages
    let avgPts = 0, avgReb = 0, avgAst = 0, avgStl = 0, avgBlk = 0, avgMin = 0, avgFg = 0, avg3p = 0;
    if (games.length > 0) {
        avgPts = (games.reduce((sum, g) => sum + (g.PTS || 0), 0) / games.length).toFixed(1);
        avgReb = (games.reduce((sum, g) => sum + (g.REB || 0), 0) / games.length).toFixed(1);
        avgAst = (games.reduce((sum, g) => sum + (g.AST || 0), 0) / games.length).toFixed(1);
        avgStl = (games.reduce((sum, g) => sum + (g.STL || 0), 0) / games.length).toFixed(1);
        avgBlk = (games.reduce((sum, g) => sum + (g.BLK || 0), 0) / games.length).toFixed(1);
        avgMin = (games.reduce((sum, g) => sum + (parseFloat(g.MIN) || 0), 0) / games.length).toFixed(1);
        avgFg = (games.reduce((sum, g) => sum + ((g.FG_PCT || 0) * 100), 0) / games.length).toFixed(1);
        avg3p = (games.reduce((sum, g) => sum + ((g.FG3_PCT || 0) * 100), 0) / games.length).toFixed(1);
    }

    // Remove existing modal if any
    const existingModal = document.querySelector('.player-modal-overlay');
    if (existingModal) {
        existingModal.remove();
    }

    // Create modal overlay
    const modal = document.createElement('div');
    modal.className = 'player-modal-overlay';
    modal.innerHTML = `
        <div class="player-modal">
            <div class="player-modal-header">
                <h2>${player.name}</h2>
                <button class="close-modal">&times;</button>
            </div>
            <div class="player-modal-body">
                <div class="player-stats-summary">
                    <h3>Season Averages (Last ${games.length} Games)</h3>
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-value">${avgPts}</div>
                            <div class="stat-label">PTS</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${avgReb}</div>
                            <div class="stat-label">REB</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${avgAst}</div>
                            <div class="stat-label">AST</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${avgStl}</div>
                            <div class="stat-label">STL</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${avgBlk}</div>
                            <div class="stat-label">BLK</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${avgMin}</div>
                            <div class="stat-label">MIN</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${avgFg}%</div>
                            <div class="stat-label">FG%</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">${avg3p}%</div>
                            <div class="stat-label">3P%</div>
                        </div>
                    </div>
                </div>
                <h3>Recent Games</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Matchup</th>
                                <th>MIN</th>
                                <th>PTS</th>
                                <th>REB</th>
                                <th>AST</th>
                                <th>STL</th>
                                <th>BLK</th>
                                <th>FG%</th>
                                <th>3P%</th>
                            </tr>
                        </thead>
                        <tbody id="playerGamesBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Populate table
    const tbody = modal.querySelector('#playerGamesBody');
    games.forEach(game => {
        const row = document.createElement('tr');
        const fgPct = game.FG_PCT ? (game.FG_PCT * 100).toFixed(1) : '0.0';
        const fg3Pct = game.FG3_PCT ? (game.FG3_PCT * 100).toFixed(1) : '0.0';

        row.innerHTML = `
            <td>${game.GAME_DATE}</td>
            <td>${game.MATCHUP}</td>
            <td>${game.MIN || 0}</td>
            <td><strong>${game.PTS || 0}</strong></td>
            <td>${game.REB || 0}</td>
            <td>${game.AST || 0}</td>
            <td>${game.STL || 0}</td>
            <td>${game.BLK || 0}</td>
            <td>${fgPct}%</td>
            <td>${fg3Pct}%</td>
        `;
        tbody.appendChild(row);
    });

    // Close button handler
    modal.querySelector('.close-modal').addEventListener('click', () => {
        modal.remove();
    });

    // Click outside to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

function showLoading() {
    console.log('⏳ Showing loading spinner');
    const loadingEl = document.getElementById('loading');
    if (loadingEl) {
        loadingEl.classList.remove('hidden');
        console.log('✅ Loading spinner shown');
    } else {
        console.error('❌ Loading element not found!');
    }
}

function hideLoading() {
    console.log('🔚 Hiding loading spinner');
    const loadingEl = document.getElementById('loading');
    if (loadingEl) {
        loadingEl.classList.add('hidden');
        console.log('✅ Loading spinner hidden');
    } else {
        console.error('❌ Loading element not found!');
    }
}

function displayError(message) {
    const errorBox = document.getElementById('error');
    errorBox.textContent = `❌ Error: ${message}`;
    errorBox.classList.remove('hidden');

    setTimeout(() => {
        errorBox.classList.add('hidden');
    }, 5000);
}
