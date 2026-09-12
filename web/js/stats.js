import { api, setTokenProvider } from './api.js';
import { getIdToken, onAuthChange } from './firebase.js';
import { initNavMenu } from './nav.js';

setTokenProvider(getIdToken);
initNavMenu();

const playerSearchInput = document.getElementById('playerSearchInput');
const playerSearchBtn = document.getElementById('playerSearchBtn');
const signedOutMessage = document.getElementById('signedOutMessage');
const statsContent = document.getElementById('statsContent');
const statsUsername = document.getElementById('statsUsername');
const statCurrentRating = document.getElementById('statCurrentRating');
const statPeakRating = document.getElementById('statPeakRating');
const statRank = document.getElementById('statRank');
const statGamesPlayed = document.getElementById('statGamesPlayed');
const rangeButtons = document.querySelectorAll('.rangeBtn');
const chartContainer = document.getElementById('chartContainer');
const chartSvg = document.getElementById('ratingChart');
const chartTooltip = document.getElementById('chartTooltip');
const chartEmptyState = document.getElementById('chartEmptyState');
const tableViewToggle = document.getElementById('tableViewToggle');
const ratingTable = document.getElementById('ratingTable');
const ratingTableBody = document.getElementById('ratingTableBody');

let fullHistory = []; // the currently-loaded player's full rating_history, oldest first
let currentRange = 'all';

playerSearchBtn.addEventListener('click', () => {
    const username = playerSearchInput.value.trim();
    if (username) window.location.href = `stats.html?user=${encodeURIComponent(username)}`;
});
playerSearchInput.addEventListener('keydown', (evt) => {
    if (evt.key === 'Enter') playerSearchBtn.click();
});

for (const btn of rangeButtons) {
    btn.addEventListener('click', () => {
        for (const b of rangeButtons) b.classList.remove('active');
        btn.classList.add('active');
        currentRange = btn.dataset.range;
        renderChart();
    });
}

tableViewToggle.addEventListener('click', () => {
    const showing = !ratingTable.hidden;
    ratingTable.hidden = showing;
    tableViewToggle.textContent = showing ? 'View as table' : 'Hide table';
});

function showSignedOut(message) {
    signedOutMessage.textContent = message;
    signedOutMessage.hidden = false;
    statsContent.hidden = true;
}

function formatShortDate(ms) {
    return new Date(ms).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatFullDate(ms) {
    return new Date(ms).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

// ---- rating timeline chart ----------------------------------------------
//
// Plain hand-rolled SVG, matching this project's no-build-step/no-library
// approach elsewhere (see project-rampart-browser-port memory) rather than
// pulling in a charting library for one line chart.

const NS = 'http://www.w3.org/2000/svg';
const CHART_W = 640;
const CHART_H = 260;
const MARGIN = { left: 46, right: 12, top: 12, bottom: 30 };
const PLOT_W = CHART_W - MARGIN.left - MARGIN.right;
const PLOT_H = CHART_H - MARGIN.top - MARGIN.bottom;

function svgEl(tag, attrs) {
    const el = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    return el;
}

function filterHistory(range) {
    if (range === 'all') return fullHistory;
    const now = Date.now();
    const windowMs = range === '30d' ? 30 * 24 * 60 * 60 * 1000 : 182 * 24 * 60 * 60 * 1000;
    return fullHistory.filter((e) => (e.timestamp || 0) >= now - windowMs);
}

function renderTable(data) {
    ratingTableBody.innerHTML = '';
    for (const entry of data) {
        const row = document.createElement('tr');
        const dateCell = document.createElement('td');
        dateCell.textContent = formatFullDate(entry.timestamp);
        const ratingCell = document.createElement('td');
        ratingCell.textContent = String(entry.rating);
        row.append(dateCell, ratingCell);
        ratingTableBody.appendChild(row);
    }
}

function renderChart() {
    const data = filterHistory(currentRange);
    chartSvg.innerHTML = '';
    renderTable(data);

    if (data.length === 0) {
        chartEmptyState.hidden = false;
        chartSvg.hidden = true;
        chartTooltip.hidden = true;
        return;
    }
    chartEmptyState.hidden = true;
    chartSvg.hidden = false;

    const ratingsArr = data.map((d) => d.rating);
    let minR = Math.min(...ratingsArr);
    let maxR = Math.max(...ratingsArr);
    if (minR === maxR) {
        minR -= 50;
        maxR += 50;
    }
    const pad = (maxR - minR) * 0.15;
    minR = Math.floor((minR - pad) / 50) * 50;
    maxR = Math.ceil((maxR + pad) / 50) * 50;

    const xAt = (i) => MARGIN.left + (data.length <= 1 ? PLOT_W / 2 : (i / (data.length - 1)) * PLOT_W);
    const yAt = (r) => MARGIN.top + PLOT_H - ((r - minR) / (maxR - minR)) * PLOT_H;

    // gridlines + y-axis labels (min / mid / max) - recessive, hairline
    for (const frac of [0, 0.5, 1]) {
        const r = Math.round((minR + frac * (maxR - minR)) / 5) * 5;
        const y = yAt(r);
        chartSvg.appendChild(svgEl('line', {
            x1: MARGIN.left, x2: CHART_W - MARGIN.right, y1: y, y2: y, class: 'chartGridline',
        }));
        const label = svgEl('text', { x: MARGIN.left - 8, y: y + 4, class: 'chartAxisLabel', 'text-anchor': 'end' });
        label.textContent = String(r);
        chartSvg.appendChild(label);
    }

    // x-axis date labels - first/middle/last only, never one per point
    const xTickIndices = data.length === 1 ? [0] : [...new Set([0, Math.floor((data.length - 1) / 2), data.length - 1])];
    for (const i of xTickIndices) {
        const anchor = i === 0 ? 'start' : (i === data.length - 1 ? 'end' : 'middle');
        const label = svgEl('text', { x: xAt(i), y: CHART_H - 8, class: 'chartAxisLabel', 'text-anchor': anchor });
        label.textContent = formatShortDate(data[i].timestamp);
        chartSvg.appendChild(label);
    }

    if (data.length > 1) {
        const points = data.map((d, i) => `${xAt(i)},${yAt(d.rating)}`).join(' ');
        chartSvg.appendChild(svgEl('polyline', { points, fill: 'none', class: 'chartLine' }));
    }

    // end marker - surface-color ring so it stays legible where it meets the line
    const lastIdx = data.length - 1;
    const lastX = xAt(lastIdx);
    const lastY = yAt(data[lastIdx].rating);
    chartSvg.appendChild(svgEl('circle', { cx: lastX, cy: lastY, r: 6, class: 'chartMarkerRing' }));
    chartSvg.appendChild(svgEl('circle', { cx: lastX, cy: lastY, r: 4, class: 'chartMarkerDot' }));

    // direct label at the end - the value the story is about
    const endLabel = svgEl('text', {
        x: lastX - 10, y: lastY - 10, class: 'chartEndLabel',
        'text-anchor': lastX > CHART_W - 60 ? 'end' : 'start',
    });
    endLabel.textContent = String(data[lastIdx].rating);
    chartSvg.appendChild(endLabel);

    // hover layer: crosshair snaps to the nearest data point on X
    const crosshair = svgEl('line', {
        x1: 0, x2: 0, y1: MARGIN.top, y2: CHART_H - MARGIN.bottom, class: 'chartCrosshair', visibility: 'hidden',
    });
    const hoverDot = svgEl('circle', { r: 5, class: 'chartHoverDot', visibility: 'hidden' });
    const hitRect = svgEl('rect', { x: MARGIN.left, y: MARGIN.top, width: PLOT_W, height: PLOT_H, fill: 'transparent' });
    chartSvg.append(crosshair, hoverDot, hitRect);

    function showTooltipAt(nearest) {
        const x = xAt(nearest);
        const y = yAt(data[nearest].rating);
        crosshair.setAttribute('x1', x);
        crosshair.setAttribute('x2', x);
        crosshair.setAttribute('visibility', 'visible');
        hoverDot.setAttribute('cx', x);
        hoverDot.setAttribute('cy', y);
        hoverDot.setAttribute('visibility', 'visible');

        chartTooltip.innerHTML = '';
        const valueEl = document.createElement('div');
        valueEl.className = 'chartTooltipValue';
        valueEl.textContent = String(data[nearest].rating);
        const dateEl = document.createElement('div');
        dateEl.className = 'chartTooltipDate';
        dateEl.textContent = formatFullDate(data[nearest].timestamp);
        chartTooltip.append(valueEl, dateEl);
        chartTooltip.hidden = false;
        chartTooltip.style.left = `${(x / CHART_W) * 100}%`;
        chartTooltip.style.top = `${(y / CHART_H) * 100}%`;
    }

    hitRect.addEventListener('pointermove', (evt) => {
        const bounds = chartSvg.getBoundingClientRect();
        const px = ((evt.clientX - bounds.left) / bounds.width) * CHART_W;
        let nearest = 0;
        let nearestDist = Infinity;
        for (let i = 0; i < data.length; i++) {
            const dist = Math.abs(xAt(i) - px);
            if (dist < nearestDist) {
                nearestDist = dist;
                nearest = i;
            }
        }
        showTooltipAt(nearest);
    });
    hitRect.addEventListener('pointerleave', () => {
        crosshair.setAttribute('visibility', 'hidden');
        hoverDot.setAttribute('visibility', 'hidden');
        chartTooltip.hidden = true;
    });
}

// ---- page load ------------------------------------------------------------

async function loadStats() {
    const viewedUsername = new URLSearchParams(window.location.search).get('user');
    let username = viewedUsername;

    if (!username) {
        const token = await getIdToken();
        if (!token) {
            showSignedOut('Please sign in on the Home page first, or search for a player above.');
            return;
        }
        try {
            username = (await api.me()).username;
        } catch (e) {
            showSignedOut('Please finish creating your account on the Home page first.');
            return;
        }
    }

    let profile;
    let rank;
    try {
        [profile, rank] = await Promise.all([api.playerProfile(username), api.playerRank(username)]);
    } catch (e) {
        showSignedOut(`No player named "${username}".`);
        return;
    }

    signedOutMessage.hidden = true;
    statsContent.hidden = false;

    statsUsername.textContent = profile.username;
    statCurrentRating.textContent = profile.rating ?? 1200;
    statPeakRating.textContent = profile.peak_rating ?? profile.rating ?? 1200;
    statGamesPlayed.textContent = profile.games_played ?? 0;
    statRank.textContent = rank.rank
        ? `#${rank.rank} of ${rank.total} (Top ${rank.top_percentile}%)`
        : 'Unranked';

    try {
        fullHistory = await api.playerRatingHistory(profile.username);
    } catch (e) {
        fullHistory = [];
    }
    renderChart();
}

onAuthChange(loadStats);
