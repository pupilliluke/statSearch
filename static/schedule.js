// Set max date to today and default to today on page load
document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('date');
    const today = new Date().toISOString().split('T')[0];
    dateInput.max = today;
    dateInput.value = today;

    // Auto-load today's schedule
    loadSchedule(today);
});

// Form submission handler
document.getElementById('scheduleForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const date = document.getElementById('date').value || new Date().toISOString().split('T')[0];
    loadSchedule(date);
});

async function loadSchedule(date) {
    const submitBtn = document.querySelector('.search-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');

    // Show loading state
    submitBtn.disabled = true;
    btnText.textContent = 'Loading...';
    loader.classList.remove('hidden');

    // Hide previous results and errors
    document.getElementById('scheduleResults').classList.add('hidden');
    document.getElementById('error').classList.add('hidden');

    try {
        const response = await fetch(`/api/schedule?date=${date}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch schedule');
        }

        if (data.success) {
            displaySchedule(data);
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
    } catch (error) {
        displayError(error.message);
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        btnText.textContent = 'Load Schedule';
        loader.classList.add('hidden');
    }
}

function displaySchedule(data) {
    const resultsSection = document.getElementById('scheduleResults');
    const gamesList = document.getElementById('gamesList');
    const noGames = document.getElementById('noGames');

    // Update metadata
    document.getElementById('scheduleDate').textContent = `📅 ${formatDate(data.date)}`;
    document.getElementById('scheduleCount').textContent = `🏀 ${data.count} game${data.count !== 1 ? 's' : ''}`;

    // Clear previous results
    gamesList.innerHTML = '';

    if (data.games && data.games.length > 0) {
        // Display each game
        data.games.forEach(game => {
            const gameCard = createGameCard(game);
            gamesList.appendChild(gameCard);
        });

        noGames.classList.add('hidden');
    } else {
        noGames.classList.remove('hidden');
    }

    resultsSection.classList.remove('hidden');
}

function createGameCard(game) {
    const card = document.createElement('div');
    card.className = 'game-card';
    card.dataset.gameId = game.id;

    const statusClass = game.state === 'post' ? 'final' : game.state === 'in' ? 'live' : 'scheduled';
    const statusText = game.status;

    // Format game time
    let timeDisplay = '';
    if (game.state === 'pre') {
        const gameDate = new Date(game.date);
        timeDisplay = gameDate.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: '2-digit',
            timeZoneName: 'short'
        });
    }

    card.innerHTML = `
        <div class="game-status ${statusClass}">
            ${game.state === 'in' ? '🔴 ' : ''}${statusText}
            ${timeDisplay ? `<span class="game-time"> · ${timeDisplay}</span>` : ''}
        </div>
        <div class="game-matchup">
            <div class="team ${game.state === 'post' && parseInt(game.away.score) > parseInt(game.home.score) ? 'winner' : ''}">
                <img src="${game.away.logo}" alt="${game.away.abbreviation}" class="team-logo" onerror="this.style.display='none'">
                <div class="team-info">
                    <div class="team-name">${game.away.name}</div>
                    <div class="team-record">${game.away.record || ''}</div>
                </div>
                <div class="team-score">${game.state !== 'pre' ? game.away.score : ''}</div>
            </div>
            <div class="matchup-divider">@</div>
            <div class="team ${game.state === 'post' && parseInt(game.home.score) > parseInt(game.away.score) ? 'winner' : ''}">
                <img src="${game.home.logo}" alt="${game.home.abbreviation}" class="team-logo" onerror="this.style.display='none'">
                <div class="team-info">
                    <div class="team-name">${game.home.name}</div>
                    <div class="team-record">${game.home.record || ''}</div>
                </div>
                <div class="team-score">${game.state !== 'pre' ? game.home.score : ''}</div>
            </div>
        </div>
        <button class="view-boxscore-btn" onclick="viewBoxScore('${game.id}')" ${game.state === 'pre' ? 'disabled' : ''}>
            📊 View Box Score
        </button>
    `;

    return card;
}

async function viewBoxScore(espnGameId) {
    const dateInput = document.getElementById('date');
    const date = dateInput.value || new Date().toISOString().split('T')[0];

    // Show loading
    const gameCard = document.querySelector(`[data-game-id="${espnGameId}"]`);
    const btn = gameCard.querySelector('.view-boxscore-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ Loading...';
    btn.disabled = true;

    try {
        // Fetch all box scores for the date (ESPN ID ≠ NBA API ID)
        const response = await fetch(`/api/boxscore?date=${date}`);
        const data = await response.json();

        if (data.success && data.boxscores && data.boxscores.length > 0) {
            // Get team abbreviations from game card
            const teamAbbrevs = getTeamAbbreviationsFromCard(espnGameId);
            const gameBoxscores = filterBoxscoresByTeams(data.boxscores, teamAbbrevs);

            if (gameBoxscores.length > 0) {
                displayBoxScore(gameBoxscores, espnGameId);
            } else {
                // Fallback: show all if can't match
                displayBoxScore(data.boxscores, espnGameId);
            }
        } else {
            alert(`No box score data available yet.\nSource: ${data.source || 'none'}\nErrors: ${data.errors?.join(', ') || 'No data'}`);
        }
    } catch (error) {
        alert(`Error loading box score: ${error.message}`);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function getTeamAbbreviationsFromCard(gameId) {
    const gameCard = document.querySelector(`[data-game-id="${gameId}"]`);
    if (!gameCard) return [];

    // Look for team names in the card
    const teamElements = gameCard.querySelectorAll('.team-name');
    const teamNames = Array.from(teamElements).map(el => el.textContent.trim());

    // Extract likely abbreviations (usually first 3 letters or common abbreviations)
    return teamNames;
}

function filterBoxscoresByTeams(boxscores, teamNames) {
    if (!teamNames || teamNames.length === 0) return boxscores;

    // Get all unique team abbreviations from boxscores
    const boxscoreTeams = [...new Set(boxscores.map(b => b.team))];

    // If only 2 teams in boxscores and we're looking for a specific game, perfect match
    if (boxscoreTeams.length === 2 && teamNames.length === 2) {
        return boxscores;
    }

    // Otherwise try to match by team name/abbreviation
    const relevantBoxscores = boxscores.filter(b => {
        return teamNames.some(name => {
            // Match if team name contains abbreviation or vice versa
            const nameLower = name.toLowerCase();
            const teamLower = b.team.toLowerCase();
            return nameLower.includes(teamLower) ||
                   teamLower.includes(nameLower) ||
                   name.includes(b.team) ||
                   b.team.includes(name.substring(0, 3));
        });
    });

    return relevantBoxscores.length > 0 ? relevantBoxscores : boxscores;
}

function displayBoxScore(boxscores, gameId) {
    // Hide schedule, show boxscore
    document.getElementById('scheduleResults').classList.add('hidden');
    const boxscoreSection = document.getElementById('boxscoreSection');
    const boxscoreContent = document.getElementById('boxscoreContent');

    // Group by team
    const teams = {};
    boxscores.forEach(player => {
        if (!teams[player.team]) {
            teams[player.team] = [];
        }
        teams[player.team].push(player);
    });

    // Sort players by minutes played (desc)
    Object.keys(teams).forEach(team => {
        teams[team].sort((a, b) => {
            const minA = parseMinutes(a.min);
            const minB = parseMinutes(b.min);
            return minB - minA;
        });
    });

    // Calculate team totals
    const teamTotals = {};
    Object.keys(teams).forEach(team => {
        teamTotals[team] = {
            pts: teams[team].reduce((sum, p) => sum + p.pts, 0),
            reb: teams[team].reduce((sum, p) => sum + p.reb, 0),
            ast: teams[team].reduce((sum, p) => sum + p.ast, 0),
            stl: teams[team].reduce((sum, p) => sum + p.stl, 0),
            blk: teams[team].reduce((sum, p) => sum + p.blk, 0)
        };
    });

    // ESPN-style box score
    boxscoreContent.innerHTML = `
        ${Object.keys(teams).map(team => `
            <div class="espn-team-section">
                <div class="espn-team-header">
                    <h3>${team}</h3>
                    <div class="team-total-score">${teamTotals[team].pts}</div>
                </div>
                <div class="espn-table-wrapper">
                    <table class="espn-boxscore-table">
                        <thead>
                            <tr>
                                <th class="player-col">PLAYER</th>
                                <th>MIN</th>
                                <th>FG</th>
                                <th>3PT</th>
                                <th>FT</th>
                                <th>REB</th>
                                <th>AST</th>
                                <th>BLK</th>
                                <th>STL</th>
                                <th>PTS</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${teams[team].map((player, idx) => `
                                <tr class="${idx % 2 === 0 ? 'even-row' : 'odd-row'}">
                                    <td class="player-col"><strong>${player.player}</strong></td>
                                    <td>${player.min || '0:00'}</td>
                                    <td>-</td>
                                    <td>-</td>
                                    <td>-</td>
                                    <td>${player.reb}</td>
                                    <td>${player.ast}</td>
                                    <td>${player.blk || 0}</td>
                                    <td>${player.stl || 0}</td>
                                    <td><strong>${player.pts}</strong></td>
                                </tr>
                            `).join('')}
                            <tr class="totals-row">
                                <td class="player-col"><strong>TOTALS</strong></td>
                                <td>-</td>
                                <td>-</td>
                                <td>-</td>
                                <td>-</td>
                                <td><strong>${teamTotals[team].reb}</strong></td>
                                <td><strong>${teamTotals[team].ast}</strong></td>
                                <td><strong>${teamTotals[team].blk}</strong></td>
                                <td><strong>${teamTotals[team].stl}</strong></td>
                                <td><strong>${teamTotals[team].pts}</strong></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `).join('')}
        <div class="boxscore-footer">
            Data source: ${boxscores[0]?.source || 'Unknown'}
        </div>
    `;

    boxscoreSection.classList.remove('hidden');

    // Scroll to boxscore
    boxscoreSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeBoxScore() {
    document.getElementById('boxscoreSection').classList.add('hidden');
    document.getElementById('scheduleResults').classList.remove('hidden');
    document.querySelector('.search-section').scrollIntoView({ behavior: 'smooth' });
}

function parseMinutes(minStr) {
    if (!minStr || minStr === '0:00') return 0;
    const parts = minStr.split(':');
    return parseInt(parts[0]) || 0;
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
