import { api } from './api.js';
import { RANKS, SUITS, DECK_SUIT } from './constants.js';
import { drawBoard, colRowFromPoint, BOARD_WIDTH, BOARD_HEIGHT } from './render.js';

const canvas = document.getElementById('boardCanvas');
const ctx = canvas.getContext('2d');
canvas.width = BOARD_WIDTH;
canvas.height = BOARD_HEIGHT;

const statusLine = document.getElementById('statusLine');
const gameArea = document.getElementById('gameArea');
const aiColorSelect = document.getElementById('aiColorSelect');
const aiDifficultySelect = document.getElementById('aiDifficultySelect');
const newGameBtn = document.getElementById('newGameBtn');

const blackDeckEl = document.getElementById('blackDeck');
const whiteDeckEl = document.getElementById('whiteDeck');
const blackGraveEl = document.getElementById('blackGrave');
const whiteGraveEl = document.getElementById('whiteGrave');
const strikeListEl = document.getElementById('strikeList');
const raiseRaiderListEl = document.getElementById('raiseRaiderList');
const raiseQueenListEl = document.getElementById('raiseQueenList');
const historyListEl = document.getElementById('historyList');

let gameId = null;
let state = null;
let selected = null;
let legalDestinations = [];
let lastMoveSquares = [];
let castHighlight = null;
let busy = false;

// ---- notation parsing (display only - the server already applied the
// move; this just figures out which squares to highlight) ----------------

function parseSquareToken(token) {
    const m = token.match(/^(\d+)([a-f])/);
    if (!m) return null;
    const col = parseInt(m[1], 10) - 1;
    const row = 5 - (m[2].charCodeAt(0) - 'a'.charCodeAt(0));
    return [col, row];
}

function parseLastMoveSquares(notation) {
    if (!notation) return [];
    if (notation.includes('/')) {
        // compound move (infiltration capture + queen auto-spawn) - the
        // spawn is the final action, so that's what gets highlighted,
        // matching the desktop client's reconstruct_at_move fix.
        const spawnPart = notation.split('/')[1];
        const target = spawnPart.split('@')[1];
        const sq = target ? parseSquareToken(target) : null;
        return sq ? [sq] : [];
    }
    if (notation.includes('++') || notation.includes('--')) {
        const targetPart = notation.split('@')[1].split('(')[0];
        const sq = parseSquareToken(targetPart);
        return sq ? [sq] : [];
    }
    if (notation.includes('>')) {
        const [srcStr, dstStr] = notation.slice(1).split('>');
        const src = parseSquareToken(srcStr);
        const dst = parseSquareToken(dstStr);
        return [src, dst].filter(Boolean);
    }
    return [];
}

// ---- small display helpers ----------------------------------------------

function cap(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function squareLabel(col, row) {
    const letter = String.fromCharCode('a'.charCodeAt(0) + (5 - row));
    return `${col + 1}${letter}`;
}

function cardLabel(card) {
    return `${RANKS[card.rank]}${SUITS[card.suit]}`;
}

function isGameOver(s) {
    return Boolean(s.king_mated || s.king_stalemated);
}

function humanColor() {
    return state.ai_color === 'white' ? 'black' : 'white';
}

function computeStatus(s) {
    if (s.king_mated) {
        // _post_move only advances next_player when the game ISN'T over,
        // so next_player here is still the side that just delivered mate.
        return `${cap(s.next_player)} wins by checkmate!`;
    }
    if (s.king_stalemated) {
        return 'Draw (stalemate, repetition, or insufficient material).';
    }
    return `${cap(s.next_player)} to move.`;
}

function setStatus(text) {
    statusLine.textContent = text;
}

function setBusy(b) {
    busy = b;
    canvas.style.cursor = b ? 'wait' : 'pointer';
    document.querySelectorAll('.castList button, #newGameBtn').forEach((el) => {
        el.disabled = b;
    });
}

// ---- rendering ------------------------------------------------------------

function drawCanvas() {
    if (!state) return;
    drawBoard(ctx, state, { selected, legalDestinations, lastMoveSquares, castHighlight });
}

function renderDeck(container, deckArray, colorLabel) {
    container.innerHTML = '';
    const suit = DECK_SUIT[colorLabel];
    RANKS.forEach((rank, i) => {
        const used = deckArray[i];
        const div = document.createElement('div');
        div.className = 'deckCard' + (used ? ' used' : '');
        div.innerHTML = `<span>${rank}</span><span>${suit}</span>`;
        container.appendChild(div);
    });
}

function renderGrave(container, graveArray, colorLabel) {
    container.innerHTML = '';
    graveArray.forEach((name) => {
        if (!name) return;
        const img = document.createElement('img');
        img.src = `assets/misc/dead_${colorLabel}_${name}.png`;
        img.alt = `${colorLabel} ${name} in the graveyard`;
        container.appendChild(img);
    });
}

function renderCastList(container, moves, category) {
    container.innerHTML = '';
    moves.forEach((mv) => {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        const cardsStr = mv.cards.map(cardLabel).join(', ');
        btn.textContent = `${squareLabel(mv.to[0], mv.to[1])} — ${cardsStr}`;
        btn.addEventListener('click', () => onPickCastMove(category, mv.index));
        btn.addEventListener('mouseenter', () => {
            castHighlight = mv.to;
            drawCanvas();
        });
        btn.addEventListener('mouseleave', () => {
            castHighlight = null;
            drawCanvas();
        });
        li.appendChild(btn);
        container.appendChild(li);
    });
}

function clearCastLists() {
    strikeListEl.innerHTML = '';
    raiseRaiderListEl.innerHTML = '';
    raiseQueenListEl.innerHTML = '';
    castHighlight = null;
}

function renderHistory(history) {
    historyListEl.innerHTML = '';
    for (let i = 0; i < history.length; i += 2) {
        const li = document.createElement('li');
        const whiteMove = history[i] || '';
        const blackMove = history[i + 1] || '';
        li.textContent = blackMove ? `${whiteMove}   ${blackMove}` : whiteMove;
        historyListEl.appendChild(li);
    }
}

function renderAll() {
    drawCanvas();
    renderDeck(blackDeckEl, state.black_deck, 'black');
    renderDeck(whiteDeckEl, state.white_deck, 'white');
    renderGrave(blackGraveEl, state.black_grave, 'black');
    renderGrave(whiteGraveEl, state.white_grave, 'white');
    renderHistory(state.history);
    setStatus(computeStatus(state));
    if (isGameOver(state)) clearCastLists();
}

// ---- game flow --------------------------------------------------------

async function afterStateUpdate(notation) {
    if (notation !== undefined) lastMoveSquares = parseLastMoveSquares(notation);
    renderAll();
    if (isGameOver(state)) return;
    if (state.next_player === state.ai_color) {
        await triggerAiMove();
    } else {
        await refreshCastMoves();
    }
}

async function triggerAiMove() {
    setStatus(`${cap(state.ai_color)} (AI) is thinking...`);
    clearCastLists();
    setBusy(true);
    try {
        const result = await api.aiMove(gameId);
        state = result;
        await afterStateUpdate(result.notation);
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

async function refreshCastMoves() {
    if (isGameOver(state)) return;
    try {
        const moves = await api.castMoves(gameId);
        renderCastList(strikeListEl, moves.strike || [], 'strike');
        renderCastList(raiseRaiderListEl, moves.raise_raider || [], 'raise_raider');
        renderCastList(raiseQueenListEl, moves.raise_queen || [], 'raise_queen');
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    }
}

async function onPickCastMove(category, index) {
    setBusy(true);
    try {
        const result = await api.castMove(gameId, category, index);
        state = result;
        selected = null;
        legalDestinations = [];
        await afterStateUpdate(result.notation);
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

async function startNewGame() {
    const aiColor = aiColorSelect.value;
    const aiDifficulty = aiDifficultySelect.value;
    setBusy(true);
    setStatus('Starting new game...');
    try {
        state = await api.newGame(aiColor, aiDifficulty);
        gameId = state.id;
        selected = null;
        legalDestinations = [];
        lastMoveSquares = [];
        gameArea.hidden = false;
        await afterStateUpdate();
    } catch (e) {
        setStatus(`Error: ${e.message} (is the server running at the configured API base URL?)`);
    } finally {
        setBusy(false);
    }
}

// ---- input --------------------------------------------------------------

canvas.addEventListener('click', async (evt) => {
    if (busy || !state || isGameOver(state)) return;
    if (state.next_player === state.ai_color) return;

    const rect = canvas.getBoundingClientRect();
    const x = (evt.clientX - rect.left) * (canvas.width / rect.width);
    const y = (evt.clientY - rect.top) * (canvas.height / rect.height);
    const cr = colRowFromPoint(x, y);
    if (!cr) return;
    const { col, row } = cr;

    if (selected) {
        const isDest = legalDestinations.some(([c, r]) => c === col && r === row);
        if (isDest) {
            const from = selected;
            setBusy(true);
            try {
                const result = await api.move(gameId, from.col, from.row, col, row);
                state = result;
                selected = null;
                legalDestinations = [];
                await afterStateUpdate(result.notation);
            } catch (e) {
                setStatus(`Error: ${e.message}`);
            } finally {
                setBusy(false);
            }
            return;
        }
    }

    const piece = state.pieces.find((p) => p.col === col && p.row === row);
    if (piece && piece.color === humanColor()) {
        setBusy(true);
        try {
            const res = await api.legalMoves(gameId, col, row);
            selected = res.destinations.length ? { col, row } : null;
            legalDestinations = res.destinations;
            drawCanvas();
        } catch (e) {
            setStatus(`Error: ${e.message}`);
        } finally {
            setBusy(false);
        }
    } else {
        selected = null;
        legalDestinations = [];
        drawCanvas();
    }
});

newGameBtn.addEventListener('click', startNewGame);
