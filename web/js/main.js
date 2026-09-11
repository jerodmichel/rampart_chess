import { api, setTokenProvider } from './api.js';
import { signUpWithEmail, logInWithEmail, logOut, onAuthChange, getIdToken } from './firebase.js';
import { initNavMenu, setupDropdown } from './nav.js';
import {
    CARD_VAL, CARD_SQUARES, ROWS,
    DECK_SUIT_INDEX, boardCardSuitIndex, boardCardRankIndex,
} from './constants.js';
import {
    drawScreen, colRowFromPoint, buttonAt, deckCardAt, isPlayableSquare,
    DESIGN_WIDTH, DESIGN_HEIGHT, THEME_PRESETS, setTheme, PIECE_SET_NAMES, setPieceSet,
    triggerLightning, isLightningActive, startHourglass, stopHourglass, isHourglassActive,
    setFlipped, isFlipped,
} from './render.js';

// Every api.js request fetches a live token right before sending, rather
// than this code caching one - see api.js's setTokenProvider for why.
setTokenProvider(getIdToken);

initNavMenu();
setupDropdown(document.getElementById('displaySettingsBtn'), document.getElementById('displaySettingsDropdown'));

const canvas = document.getElementById('boardCanvas');
const ctx = canvas.getContext('2d');
canvas.width = DESIGN_WIDTH;
canvas.height = DESIGN_HEIGHT;

const statusLine = document.getElementById('statusLine');
const aiColorSelect = document.getElementById('aiColorSelect');
const aiDifficultySelect = document.getElementById('aiDifficultySelect');
const newGameBtn = document.getElementById('newGameBtn');
const themeSelect = document.getElementById('themeSelect');
const pieceSetSelect = document.getElementById('pieceSetSelect');
const historyPrevBtn = document.getElementById('historyPrevBtn');
const historyLiveBtn = document.getElementById('historyLiveBtn');
const historyNextBtn = document.getElementById('historyNextBtn');
const effectsToggle = document.getElementById('effectsToggle');
const flipBoardBtn = document.getElementById('flipBoardBtn');
const gameActions = document.getElementById('gameActions');
const resignBtn = document.getElementById('resignBtn');
const offerDrawBtn = document.getElementById('offerDrawBtn');
const acceptDrawBtn = document.getElementById('acceptDrawBtn');
const declineDrawBtn = document.getElementById('declineDrawBtn');
const clocksBar = document.getElementById('clocks');
const whiteClockEl = document.getElementById('whiteClock');
const blackClockEl = document.getElementById('blackClock');

// Thunder (sound) + lightning (animation) always fire together on desktop
// (every cast trigger site calls both one line apart - see effects.py/
// main.py), so one combined toggle covers both; the hourglass "AI thinking"
// indicator is left always-on since it's an informational cue, not an
// effect. Persisted in localStorage as a per-browser display preference.
let effectsEnabled = true;
try {
    const stored = localStorage.getItem('rampart.effectsEnabled');
    if (stored !== null) effectsEnabled = stored === 'true';
} catch (_) { /* localStorage unavailable */ }
effectsToggle.checked = effectsEnabled;
effectsToggle.addEventListener('change', () => {
    effectsEnabled = effectsToggle.checked;
    try { localStorage.setItem('rampart.effectsEnabled', String(effectsEnabled)); } catch (_) { /* ignore */ }
});

const strikeSound = new Audio('assets/sounds/thunder_strike.wav');
const raiseSound = new Audio('assets/sounds/thunder_raise.mp3');

function playCastSound(kind) {
    const audio = kind === 'strike' ? strikeSound : raiseSound;
    try {
        audio.currentTime = 0;
        audio.play().catch(() => {});
    } catch (_) { /* ignore */ }
}

// ---- accounts -------------------------------------------------------------
//
// The browser signs in directly with Firebase Auth (see firebase.js); a
// live ID token is forwarded to server/ on every request (see
// setTokenProvider above) so it can verify who's asking
// (server/firebase_auth.py's get_current_uid) rather than trusting a
// client-supplied uid. A username
// isn't part of Firebase Auth itself, so right after sign-up (or on login,
// if a previous sign-up never finished claiming one) this also calls
// POST /auth/register to claim one via server/accounts.py.

const authStatus = document.getElementById('authStatus');
const authEmail = document.getElementById('authEmail');
const authPassword = document.getElementById('authPassword');
const authUsername = document.getElementById('authUsername');
const signUpBtn = document.getElementById('signUpBtn');
const logInBtn = document.getElementById('logInBtn');
const logOutBtn = document.getElementById('logOutBtn');

let currentProfile = null; // {uid, username} once signed in AND registered

// True once Firebase Auth has a signed-in user but server/ has no username
// on file for them yet - either mid sign-up, or a sign-up that got
// interrupted before the username was claimed on a previous visit.
let pendingUsernameClaim = false;

function renderAuthUI(message) {
    const signedIn = currentProfile !== null || pendingUsernameClaim;
    authEmail.hidden = signedIn;
    authPassword.hidden = signedIn;
    signUpBtn.hidden = signedIn;
    logInBtn.hidden = signedIn;
    logOutBtn.hidden = !signedIn;
    authUsername.hidden = !pendingUsernameClaim;
    challengePanel.hidden = currentProfile === null;

    if (message) {
        authStatus.textContent = message;
    } else if (currentProfile) {
        authStatus.textContent = `Signed in as ${currentProfile.username}`;
    } else if (pendingUsernameClaim) {
        authStatus.textContent = 'Choose a username to finish setting up your account:';
    } else {
        authStatus.textContent = '';
    }
}

// Firebase Auth errors carry a stable `.code` (e.g. "auth/weak-password");
// api.js's own errors (server/ validation, username taken, etc.) don't, but
// wrap the useful part in a "PATH failed (status): <detail>" string - strip
// that boilerplate down to just <detail> instead.
const FIREBASE_AUTH_ERRORS = {
    'auth/invalid-email': 'That doesn\'t look like a valid email address.',
    'auth/missing-password': 'Enter a password.',
    'auth/weak-password': 'Password must be at least 6 characters.',
    'auth/email-already-in-use': 'An account with that email already exists - try logging in instead.',
    'auth/user-not-found': 'Email or password is incorrect.',
    'auth/wrong-password': 'Email or password is incorrect.',
    'auth/invalid-credential': 'Email or password is incorrect.',
    'auth/too-many-requests': 'Too many attempts - please wait a moment and try again.',
};

function friendlyErrorMessage(e) {
    if (e.code && FIREBASE_AUTH_ERRORS[e.code]) return FIREBASE_AUTH_ERRORS[e.code];
    const match = e.message.match(/^\/\S+ failed \(\d+\): (.+)$/);
    return match ? match[1] : e.message;
}

async function refreshProfile() {
    // Only checking whether anyone's signed in at all here - api.js fetches
    // its own fresh token (via setTokenProvider below) on every request
    // rather than reusing whatever this returns.
    const token = await getIdToken();
    if (!token) {
        currentProfile = null;
        pendingUsernameClaim = false;
        renderAuthUI();
        return;
    }
    try {
        currentProfile = await api.me();
        pendingUsernameClaim = false;
    } catch (e) {
        currentProfile = null;
        pendingUsernameClaim = true;
    }
    renderAuthUI();
    if (currentProfile) refreshChallenges();
}

signUpBtn.addEventListener('click', async () => {
    if (!authEmail.value || !authPassword.value) {
        renderAuthUI('Enter an email and password.');
        return;
    }
    try {
        await signUpWithEmail(authEmail.value, authPassword.value);
        await refreshProfile();
    } catch (e) {
        renderAuthUI(friendlyErrorMessage(e));
    }
});

logInBtn.addEventListener('click', async () => {
    if (!authEmail.value || !authPassword.value) {
        renderAuthUI('Enter an email and password.');
        return;
    }
    try {
        await logInWithEmail(authEmail.value, authPassword.value);
        await refreshProfile();
    } catch (e) {
        renderAuthUI(friendlyErrorMessage(e));
    }
});

logOutBtn.addEventListener('click', async () => {
    await logOut();
    currentProfile = null;
    pendingUsernameClaim = false;
    renderAuthUI();
    incomingChallengesList.innerHTML = '';
    outgoingChallengesList.innerHTML = '';
});

authUsername.addEventListener('keydown', async (evt) => {
    if (evt.key !== 'Enter' || !pendingUsernameClaim) return;
    if (!authUsername.value) {
        renderAuthUI('Choose a username to finish setting up your account:');
        return;
    }
    try {
        currentProfile = await api.register(authUsername.value);
        pendingUsernameClaim = false;
        renderAuthUI();
    } catch (e) {
        renderAuthUI(friendlyErrorMessage(e));
    }
});

onAuthChange(refreshProfile);

// ---- challenges (match invites) --------------------------------------
//
// No realtime push yet (that's the next phase - porting io_src_dev's
// RTDB-based move sync to be server-relayed); for now both the challenge
// list and an active human-vs-human game's moves are kept in sync with the
// other player by simple polling (see the two setInterval calls at the
// bottom of this file).

const challengePanel = document.getElementById('challengePanel');
const challengeUsernameInput = document.getElementById('challengeUsername');
const challengeColorSelect = document.getElementById('challengeColorSelect');
const challengeTimeControlSelect = document.getElementById('challengeTimeControlSelect');
const sendChallengeBtn = document.getElementById('sendChallengeBtn');
const incomingChallengesList = document.getElementById('incomingChallenges');
const outgoingChallengesList = document.getElementById('outgoingChallenges');

function renderChallenges(incoming, outgoing, gameStates = new Map()) {
    incomingChallengesList.innerHTML = '';
    for (const c of incoming) {
        const row = document.createElement('div');
        row.className = 'challengeRow';
        const yourColor = c.challenger_color === 'white' ? 'black' : 'white';
        const label = document.createElement('span');
        label.textContent = `${c.from_username} challenges you - you'd play ${yourColor}`;
        const acceptBtn = document.createElement('button');
        acceptBtn.textContent = 'Accept';
        acceptBtn.addEventListener('click', () => acceptChallenge(c.challenge_id));
        const declineBtn = document.createElement('button');
        declineBtn.textContent = 'Decline';
        declineBtn.addEventListener('click', () => declineChallengeById(c.challenge_id));
        const dismissBtn = document.createElement('button');
        dismissBtn.textContent = '✕';
        dismissBtn.title = 'Remove this challenge';
        dismissBtn.addEventListener('click', () => dismissChallengeById(c.challenge_id));
        row.append(label, acceptBtn, declineBtn, dismissBtn);
        incomingChallengesList.appendChild(row);
    }

    outgoingChallengesList.innerHTML = '';
    for (const c of outgoing) {
        const row = document.createElement('div');
        row.className = 'challengeRow';
        const label = document.createElement('span');
        label.textContent = `You challenged ${c.to_username} (${c.status})`;
        row.appendChild(label);
        if (c.status === 'accepted' && c.game_id) {
            const gameState = gameStates.get(c.game_id);
            const isOver = Boolean(gameState && gameState.result);
            const joinBtn = document.createElement('button');
            // Once the game has actually ended there's nothing left to
            // "join" - still let them open it (it already just displays
            // whatever state comes back, finished or not), but the label
            // shouldn't imply you're resuming a live game.
            joinBtn.textContent = isOver ? 'View Game' : 'Join Game';
            joinBtn.addEventListener('click', () => joinAcceptedGame(c.challenge_id, c.game_id));
            row.appendChild(joinBtn);
        }
        const dismissBtn = document.createElement('button');
        dismissBtn.textContent = '✕';
        dismissBtn.title = 'Remove this challenge';
        dismissBtn.addEventListener('click', () => dismissChallengeById(c.challenge_id));
        row.appendChild(dismissBtn);
        outgoingChallengesList.appendChild(row);
    }
}

async function refreshChallenges() {
    if (!currentProfile) return;
    try {
        const [incoming, outgoing] = await Promise.all([
            api.incomingChallenges(), api.outgoingChallenges(),
        ]);

        // For every accepted outgoing challenge, check its game's actual
        // status - dead (server restart orphaned it, self-heal by
        // dismissing, same as joinAcceptedGame's 404 handling) or finished
        // (still viewable, but "Join Game" shouldn't be offered as if
        // there's a live game to resume).
        const accepted = outgoing.filter((c) => c.status === 'accepted' && c.game_id);
        const gameStates = new Map(); // game_id -> state, or null once confirmed dead
        await Promise.all(accepted.map(async (c) => {
            try {
                gameStates.set(c.game_id, await api.getGame(c.game_id));
            } catch (e) {
                if (e.message.includes('failed (404)')) {
                    gameStates.set(c.game_id, null);
                    await api.dismissChallenge(c.challenge_id).catch(() => {});
                }
                // any other error (network hiccup) - leave unset, treated
                // as still-joinable this tick rather than risk a false dismiss
            }
        }));
        const stillRelevant = outgoing.filter((c) => (
            c.status !== 'accepted' || !c.game_id || gameStates.get(c.game_id) !== null
        ));

        renderChallenges(incoming, stillRelevant, gameStates);
    } catch (e) { /* background poll - a transient failure just retries next tick */ }
}

async function acceptChallenge(challengeId) {
    setBusy(true);
    try {
        loadGame(await api.acceptChallenge(challengeId));
        await afterStateUpdate();
        await refreshChallenges();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

async function declineChallengeById(challengeId) {
    try {
        await api.declineChallenge(challengeId);
        await refreshChallenges();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    }
}

async function dismissChallengeById(challengeId) {
    try {
        await api.dismissChallenge(challengeId);
        await refreshChallenges();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    }
}

async function joinAcceptedGame(challengeId, joinGameId) {
    setBusy(true);
    try {
        loadGame(await api.getGame(joinGameId));
        await afterStateUpdate();
    } catch (e) {
        // server/'s game storage is in-memory only, so a server restart
        // during testing orphans every live game - self-heal by removing
        // the now-pointless challenge record rather than leaving a Join
        // Game button that 404s forever.
        if (e.message.includes('failed (404)')) {
            setStatus('That game no longer exists - removing it from your challenges.');
            await api.dismissChallenge(challengeId).catch(() => {});
            await refreshChallenges();
        } else {
            setStatus(`Error: ${e.message}`);
        }
    } finally {
        setBusy(false);
    }
}

sendChallengeBtn.addEventListener('click', async () => {
    if (!challengeUsernameInput.value) return;
    try {
        await api.createChallenge(
            challengeUsernameInput.value, challengeColorSelect.value, challengeTimeControlSelect.value);
        challengeUsernameInput.value = '';
        await refreshChallenges();
    } catch (e) {
        setStatus(friendlyErrorMessage(e));
    }
});

// Matches board.py's notation convention: "++" prefixes every Raise-family
// cast (raise, raise-from-grave, raise-queen), "--" every Strike. The free
// queen placement on jack-house infiltration is a plain move (no cards, no
// cast prefix - see feedback-check-rulebook-not-just-code) so it never
// triggers thunder/lightning, which is correct: desktop doesn't either.
function castKindFromNotation(notation) {
    if (!notation) return null;
    if (notation.startsWith('++')) return 'raise';
    if (notation.startsWith('--')) return 'strike';
    return null;
}

THEME_PRESETS.forEach((theme, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = theme.name;
    themeSelect.appendChild(opt);
});
PIECE_SET_NAMES.forEach(({ key, label }) => {
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = label;
    pieceSetSelect.appendChild(opt);
});
themeSelect.addEventListener('change', () => {
    setTheme(Number(themeSelect.value));
    drawCanvas();
});
pieceSetSelect.addEventListener('change', () => {
    setPieceSet(pieceSetSelect.value);
    drawCanvas();
});
flipBoardBtn.addEventListener('click', () => {
    setFlipped(!isFlipped());
    drawCanvas();
});

// Preload the custom button font so the very first canvas draw doesn't
// silently fall back to the default serif before it's ready.
document.fonts.load('600 20px "Cinzel Web"').catch(() => {});

let gameId = null;
let state = null;
let selected = null;
let legalDestinations = [];
let lastMoveSquares = [];
let aiThinking = false;
let busy = false;
let hoverSquare = null;
let hoverButton = null;
let hoverDeckCard = null;

// History-viewer state. viewIndex/viewState are null while live; browsing
// is strictly read-only (no casting/moving) and never touches `state`,
// which always stays the true live position - see GameSession.state_at.
let viewIndex = null;
let viewState = null;

// Casting state - mirrors clicker.py's clicked_cards/clicked_btn.
let clickedCards = []; // {source:'deck', color, rank} | {source:'board', col, row, rank}
let committedButton = null; // 'strike' | 'raise' | null
let castDestinations = []; // [{col, row, category, index}] once committed
let transientMessage = null; // e.g. "No eligible raider to strike."

function squaresEqual(a, b) {
    if (!a && !b) return true;
    if (!a || !b) return false;
    return a.col === b.col && a.row === b.row;
}

function deckCardsEqual(a, b) {
    if (!a && !b) return true;
    if (!a || !b) return false;
    return a.color === b.color && a.rank === b.rank;
}

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

// ---- history viewer -------------------------------------------------------

function isBrowsingHistory() {
    return viewState !== null;
}

function activeState() {
    return viewState || state;
}

function historyLastMoveSquares(idx) {
    if (!state || idx <= 0) return [];
    return parseLastMoveSquares(state.history[idx - 1]);
}

function updateHistoryButtons() {
    if (!state) {
        historyPrevBtn.disabled = true;
        historyNextBtn.disabled = true;
        historyLiveBtn.disabled = true;
        return;
    }
    const total = state.history.length;
    const currentIndex = viewIndex === null ? total : viewIndex;
    historyPrevBtn.disabled = busy || currentIndex <= 0;
    historyNextBtn.disabled = busy || currentIndex >= total;
    historyLiveBtn.disabled = busy || viewIndex === null;
}

async function goToHistory(index) {
    if (!state) return;
    const total = state.history.length;
    const clamped = Math.max(0, Math.min(index, total));
    if (clamped >= total) {
        goLive();
        return;
    }
    setBusy(true);
    try {
        viewState = await api.historyAt(gameId, clamped);
        viewIndex = clamped;
        drawCanvas();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

function goLive() {
    viewState = null;
    viewIndex = null;
    drawCanvas();
}

// ---- small display helpers ----------------------------------------------

function cap(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function isGameOver(s) {
    // s.result (server/game_session.py's unified summary) now covers
    // checkmate/stalemate too, not just resignation/draw - king_mated/
    // king_stalemated are kept in the response for anything that still
    // reads them directly, but this is the one place that should reflect
    // every way a game can end.
    return Boolean(s.result);
}

function humanColor() {
    if (state.ai_color) return state.ai_color === 'white' ? 'black' : 'white';
    // human-vs-human game (see challenges.py): "my" color is whichever
    // side server/ assigned my uid to, not inferred from an AI opponent.
    if (currentProfile) {
        if (state.white_uid === currentProfile.uid) return 'white';
        if (state.black_uid === currentProfile.uid) return 'black';
    }
    return null;
}

// Matches _enemy_jack_house_occupied(color) in board.py: COLOR can start
// casting once their own piece has infiltrated the enemy's jack house.
function jackHouseSquare(color) {
    return color === 'white' ? { col: 4, row: 0 } : { col: 5, row: 5 };
}

function jackHouseOccupiedBy(s, color) {
    const sq = jackHouseSquare(color);
    const piece = s.pieces.find((p) => p.col === sq.col && p.row === sq.row);
    return Boolean(piece && piece.color === color);
}

// Blackjack-style sum with ace flexibility, matching clicker.py's
// has_sum_21 (ace counts as 1, or the whole hand as 11 instead of 21 if an
// ace is present).
function handSum21(cards) {
    let total = 0;
    let hasAce = false;
    for (const c of cards) {
        total += CARD_VAL[c.rank];
        if (c.rank === 0) hasAce = true;
    }
    return total === 21 || (hasAce && total === 11);
}

// Matches board.py's board-card click gating: a card square, not a house
// row, carrying one of the current human player's own raiders.
function isBoardCardSquare(col, row) {
    if (row === 0 || row === ROWS - 1) return false;
    if (!CARD_SQUARES.has(`${col},${row}`)) return false;
    const piece = state.pieces.find((p) => p.col === col && p.row === row);
    // NB: the server's piece entries use "piece" for the type string (e.g.
    // {col, row, piece: 'raider', color}), not "name".
    return Boolean(piece && piece.piece === 'raider' && piece.color === humanColor());
}

function toggleClickedCard(card) {
    transientMessage = null;
    if (committedButton) {
        committedButton = null;
        castDestinations = [];
    }
    const idx = clickedCards.findIndex((c) => c.source === card.source &&
        c.color === card.color && c.rank === card.rank &&
        c.col === card.col && c.row === card.row);
    if (idx >= 0) {
        clickedCards.splice(idx, 1);
    } else if (clickedCards.length < 3) {
        clickedCards.push(card);
    }
    drawCanvas();
}

function cancelCasting() {
    clickedCards = [];
    committedButton = null;
    castDestinations = [];
    transientMessage = null;
    drawCanvas();
}

// ---- turning "the cards I clicked" into what the server's combo-aware
// endpoints expect ({rank, suit} using the server's own raw suit indices,
// not the display symbols) ----------------------------------------------

function toCardSpec(card) {
    if (card.source === 'deck') {
        return { rank: card.rank, suit: DECK_SUIT_INDEX[card.color] };
    }
    return { rank: card.rank, suit: boardCardSuitIndex(card.col, card.row) };
}

async function commitCastButton(button) {
    const boardCardCount = clickedCards.filter((c) => c.source === 'board').length;
    if (button === 'strike' && boardCardCount < 2) return; // has_2_raider_cards
    if (button === 'raise' && boardCardCount < 1) return; // has_board_card
    if (!handSum21(clickedCards)) return;

    setBusy(true);
    try {
        const cardSpecs = clickedCards.map(toCardSpec);
        const destinations = await api.castComboDestinations(gameId, cardSpecs, button);
        const squares = [];
        for (const category of ['strike', 'raise_raider', 'raise_queen']) {
            for (const mv of destinations[category] || []) {
                squares.push({ col: mv.to[0], row: mv.to[1], category });
            }
        }
        if (squares.length === 0) {
            committedButton = null;
            castDestinations = [];
            transientMessage = button === 'strike'
                ? 'No eligible raider to strike.'
                : 'No eligible square to raise on.';
        } else {
            committedButton = button;
            castDestinations = squares;
            transientMessage = null;
        }
        drawCanvas();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

function computeStatus(s) {
    if (isBrowsingHistory()) {
        return `Viewing move ${viewIndex} of ${state.history.length}.`;
    }
    if (s.result) {
        const { winner, reason } = s.result;
        switch (reason) {
            case 'checkmate': return `${cap(winner)} wins by checkmate!`;
            case 'resignation': return `${cap(winner === 'white' ? 'black' : 'white')} resigned - ${cap(winner)} wins!`;
            case 'draw_agreement': return 'Draw by agreement.';
            case 'timeout': return `${cap(winner === 'white' ? 'black' : 'white')} ran out of time - ${cap(winner)} wins!`;
            case 'stalemate': default: return 'Draw (stalemate, repetition, or insufficient material).';
        }
    }
    if (s.draw_offered_by && s.draw_offered_by !== humanColor()) {
        return `${cap(s.draw_offered_by)} has offered a draw.`;
    }
    if (aiThinking) {
        return `${cap(s.next_player)} (AI) is thinking...`;
    }
    if (transientMessage) {
        return transientMessage;
    }
    if (committedButton === 'strike') {
        return 'Choose a raider to send to the grave.';
    }
    if (committedButton === 'raise') {
        const hasQueen = castDestinations.some((d) => d.category === 'raise_queen');
        return hasQueen
            ? 'Choose a tile where you want to place the queen.'
            : 'Choose a tile where you want to place a raider.';
    }
    if (s.next_player === humanColor() && jackHouseOccupiedBy(s, s.next_player)) {
        if (clickedCards.length === 0) {
            return 'To begin casting, click on a card in your deck.';
        }
        if (handSum21(clickedCards)) {
            return 'Click one of the "strike" or "raise" buttons.';
        }
        return 'Choose cards from your deck and from the board that sum to 21.';
    }
    return `${cap(s.next_player)} to move.`;
}

// ---- canvas <-> page coordinate conversion (canvas is CSS-scaled) --------

function pageToCanvas(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: (evt.clientX - rect.left) * scaleX,
        y: (evt.clientY - rect.top) * scaleY,
    };
}

// ---- rendering ------------------------------------------------------------

function drawCanvas() {
    const s = activeState();
    if (!s) return;
    const browsing = isBrowsingHistory();
    drawScreen(ctx, s, {
        selected: browsing ? null : selected,
        legalDestinations: browsing ? [] : legalDestinations,
        lastMoveSquares: browsing ? historyLastMoveSquares(viewIndex) : lastMoveSquares,
        committedButton: browsing ? null : committedButton,
        castDestinations: browsing ? [] : castDestinations,
        hoverSquare: browsing ? null : hoverSquare,
        hoverButton: browsing ? null : hoverButton,
        hoverDeckCard: browsing ? null : hoverDeckCard,
        clickedCards: browsing ? [] : clickedCards,
        aiThinking: !browsing && aiThinking,
        promptText: computeStatus(s),
    });
}

// Lightning/hourglass animate off wall-clock time (see render.js), so they
// need their own redraw loop independent of the click/hover-driven
// drawCanvas() calls above; idles (no rAF churn) whenever neither is active.
let animationLoopRunning = false;

function animationTick() {
    if (isLightningActive() || isHourglassActive()) {
        drawCanvas();
        requestAnimationFrame(animationTick);
    } else {
        animationLoopRunning = false;
    }
}

function ensureAnimationLoop() {
    if (animationLoopRunning) return;
    animationLoopRunning = true;
    requestAnimationFrame(animationTick);
}

function setStatus(text) {
    statusLine.textContent = text;
}

function setBusy(b) {
    busy = b;
    canvas.style.cursor = b ? 'wait' : 'pointer';
    newGameBtn.disabled = b;
    updateHistoryButtons();
}

// Resign is always available (either participant, any time, regardless of
// whose turn it is); Offer Draw only makes sense between two real human
// opponents - there's no one for the AI to negotiate with.
function updateGameActionButtons() {
    if (!state || isBrowsingHistory() || isGameOver(state) || !humanColor()) {
        gameActions.hidden = true;
        return;
    }
    gameActions.hidden = false;

    const isHumanVsHuman = state.ai_color === null;
    const mine = humanColor();
    const incomingOffer = isHumanVsHuman && state.draw_offered_by && state.draw_offered_by !== mine;
    const myOwnPendingOffer = isHumanVsHuman && state.draw_offered_by === mine;

    offerDrawBtn.hidden = !isHumanVsHuman || incomingOffer;
    offerDrawBtn.disabled = myOwnPendingOffer;
    offerDrawBtn.textContent = myOwnPendingOffer ? 'Draw Offered...' : 'Offer Draw';

    acceptDrawBtn.hidden = !incomingOffer;
    declineDrawBtn.hidden = !incomingOffer;
}

// ---- clocks -----------------------------------------------------------
//
// Plain numeric display for now - a placeholder for the alchemical-
// hourglass look planned for these later (see render.js's Hourglass_effect
// port, which was built for the "AI thinking" indicator but is the obvious
// starting point once that design is ready). Server is the sole time
// authority (game_session.py); this only interpolates smoothly BETWEEN
// syncs so the countdown doesn't visibly jump once per poll - see
// clockSyncedAt, set fresh every time renderAll() processes a new state.

let clockSyncedAt = null;

function formatClock(ms) {
    if (ms == null) return '--:--';
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return hours > 0 ? `${hours}:${minutes}:${seconds}` : `${minutes}:${seconds}`;
}

function updateClocks() {
    if (!state || !state.time_control) {
        clocksBar.hidden = true;
        return;
    }
    clocksBar.hidden = false;
    // Frozen (no live interpolation) while over or while browsing a past
    // position - state itself is still the live game either way, so this
    // just stops the display from ticking rather than changing what it reads.
    const frozen = isBrowsingHistory() || isGameOver(state) || clockSyncedAt === null;
    const elapsedSinceSync = frozen ? 0 : Date.now() - clockSyncedAt;
    let whiteMs = state.white_time_ms;
    let blackMs = state.black_time_ms;
    if (!frozen) {
        if (state.next_player === 'white') whiteMs = Math.max(0, whiteMs - elapsedSinceSync);
        else blackMs = Math.max(0, blackMs - elapsedSinceSync);
    }
    whiteClockEl.textContent = `White: ${formatClock(whiteMs)}`;
    blackClockEl.textContent = `Black: ${formatClock(blackMs)}`;
    whiteClockEl.classList.toggle('clockActive', !frozen && state.next_player === 'white');
    blackClockEl.classList.toggle('clockActive', !frozen && state.next_player === 'black');
}

function renderAll() {
    clockSyncedAt = Date.now(); // state.*_time_ms above is only ever fresh right here
    drawCanvas();
    updateHistoryButtons();
    updateGameActionButtons();
    updateClocks();
    setStatus(gameId ? '' : 'Start a new game to begin.');
}

// ---- game flow --------------------------------------------------------

async function afterStateUpdate(notation, casterColor) {
    if (notation !== undefined) lastMoveSquares = parseLastMoveSquares(notation);
    const castKind = castKindFromNotation(notation);
    if (castKind && casterColor && effectsEnabled) {
        triggerLightning(casterColor);
        playCastSound(castKind);
        ensureAnimationLoop();
    }
    clickedCards = [];
    committedButton = null;
    castDestinations = [];
    transientMessage = null;
    viewState = null;
    viewIndex = null;
    renderAll();
    if (isGameOver(state)) return;
    if (state.next_player === state.ai_color) {
        await triggerAiMove();
    }
}

async function triggerAiMove() {
    aiThinking = true;
    startHourglass();
    ensureAnimationLoop();
    setBusy(true);
    drawCanvas();
    try {
        const result = await api.aiMove(gameId);
        state = result;
        aiThinking = false;
        stopHourglass();
        await afterStateUpdate(result.notation, state.ai_color);
    } catch (e) {
        aiThinking = false;
        stopHourglass();
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

// Shared by startNewGame and joining a game via an accepted challenge -
// resets every piece of local UI/casting/history-view state to match a
// freshly-fetched game object before afterStateUpdate() takes over.
function loadGame(newState) {
    state = newState;
    gameId = state.id;
    selected = null;
    legalDestinations = [];
    lastMoveSquares = [];
    viewState = null;
    viewIndex = null;
    cancelCasting();
    // orient the board toward whoever's actually looking at it (chess.com/
    // lichess convention) - humanColor() already resolves correctly for
    // both an AI opponent and a real human-vs-human game. A player can
    // still flip away from this via the Flip Board button afterward.
    setFlipped(humanColor() === 'black');
}

async function startNewGame() {
    const aiColor = aiColorSelect.value;
    const aiDifficulty = aiDifficultySelect.value;
    setBusy(true);
    setStatus('Starting new game...');
    try {
        loadGame(await api.newGame(aiColor, aiDifficulty));
        await afterStateUpdate();
    } catch (e) {
        setStatus(`Error: ${e.message} (is the server running at the configured API base URL?)`);
    } finally {
        setBusy(false);
    }
}

// ---- input --------------------------------------------------------------

canvas.addEventListener('mousemove', (evt) => {
    if (!state || isBrowsingHistory()) return;
    const { x, y } = pageToCanvas(evt);
    const newHoverButton = buttonAt(x, y);
    let newHoverSquare = newHoverButton ? null : colRowFromPoint(x, y);
    if (newHoverSquare && !isPlayableSquare(newHoverSquare.col, newHoverSquare.row)) {
        newHoverSquare = null;
    }
    const newHoverDeckCard = (newHoverButton || newHoverSquare) ? null : deckCardAt(x, y);

    if (newHoverButton !== hoverButton || !squaresEqual(newHoverSquare, hoverSquare) ||
        !deckCardsEqual(newHoverDeckCard, hoverDeckCard)) {
        hoverButton = newHoverButton;
        hoverSquare = newHoverSquare;
        hoverDeckCard = newHoverDeckCard;
        drawCanvas();
    }
});

canvas.addEventListener('mouseleave', () => {
    if (hoverButton || hoverSquare || hoverDeckCard) {
        hoverButton = null;
        hoverSquare = null;
        hoverDeckCard = null;
        drawCanvas();
    }
});

canvas.addEventListener('click', async (evt) => {
    if (!state || isBrowsingHistory()) return;
    const { x, y } = pageToCanvas(evt);

    // 1. STRIKE/RAISE button
    const button = buttonAt(x, y);
    if (button) {
        if (busy || isGameOver(state) || state.next_player !== humanColor()) return;
        if (committedButton === button) {
            cancelCasting();
        } else {
            await commitCastButton(button);
        }
        return;
    }

    // 2. deck card - always the way a combo selection begins
    const deckCard = deckCardAt(x, y);
    if (deckCard) {
        if (busy || isGameOver(state) || state.next_player !== humanColor()) return;
        if (deckCard.color !== humanColor()) return; // not your deck
        const deckArray = deckCard.color === 'black' ? state.black_deck : state.white_deck;
        if (deckArray[deckCard.rank]) return; // already used
        if (!jackHouseOccupiedBy(state, deckCard.color)) return; // not eligible to cast yet
        toggleClickedCard({ source: 'deck', color: deckCard.color, rank: deckCard.rank });
        return;
    }

    if (busy || isGameOver(state) || state.next_player !== humanColor()) return;

    const cr = colRowFromPoint(x, y);
    if (!cr) return;
    const { col, row } = cr;

    // 3. board card - only ever completes a combo already started with a
    // deck card, matching the desktop client exactly.
    if (clickedCards.length > 0 && isBoardCardSquare(col, row)) {
        toggleClickedCard({
            source: 'board', col, row, rank: boardCardRankIndex(col, row),
        });
        return;
    }

    // 4. committed to a cast - a highlighted destination executes it,
    // anything else while committed is a no-op (matches the desktop
    // client: once clicked_btn is set, board clicks only mean "choose a
    // destination").
    if (committedButton) {
        const dest = castDestinations.find((d) => d.col === col && d.row === row);
        if (dest) {
            setBusy(true);
            try {
                const cardSpecs = clickedCards.map(toCardSpec);
                const result = await api.castComboMove(gameId, cardSpecs, committedButton, col, row);
                state = result;
                cancelCasting();
                await afterStateUpdate(result.notation, humanColor());
            } catch (e) {
                setStatus(`Error: ${e.message}`);
            } finally {
                setBusy(false);
            }
        }
        return;
    }

    // 5. normal piece move/select - only reachable with no cards selected
    if (clickedCards.length > 0) return;

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

historyPrevBtn.addEventListener('click', () => {
    if (!state || busy) return;
    const currentIndex = viewIndex === null ? state.history.length : viewIndex;
    goToHistory(currentIndex - 1);
});
historyNextBtn.addEventListener('click', () => {
    if (!state || busy) return;
    const currentIndex = viewIndex === null ? state.history.length : viewIndex;
    goToHistory(currentIndex + 1);
});
historyLiveBtn.addEventListener('click', () => {
    if (!state || busy) return;
    goLive();
});

updateHistoryButtons();

// ---- ending a game (resign / draw) ---------------------------------------

resignBtn.addEventListener('click', async () => {
    if (!state || busy) return;
    if (!confirm('Are you sure you want to resign?')) return;
    setBusy(true);
    try {
        state = await api.resign(gameId);
        cancelCasting();
        renderAll();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
});

offerDrawBtn.addEventListener('click', async () => {
    if (!state || busy || offerDrawBtn.disabled) return;
    setBusy(true);
    try {
        state = await api.offerDraw(gameId);
        renderAll();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
});

async function respondToDraw(accept) {
    if (!state || busy) return;
    setBusy(true);
    try {
        state = await api.respondDraw(gameId, accept);
        cancelCasting();
        renderAll();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}
acceptDrawBtn.addEventListener('click', () => respondToDraw(true));
declineDrawBtn.addEventListener('click', () => respondToDraw(false));

// ---- polling bridge for human-vs-human games -----------------------------
//
// Placeholder for real push-based sync (io_src_dev's move protocol, ported
// to be server-relayed - see project-rampart-browser-port memory note).
// Only ever touches human-vs-human games (ai_color === null); an AI game
// already updates its own local `state` synchronously after every move, so
// there's nothing for this to catch there.

async function pollActiveGame() {
    if (!gameId || !state || busy || isBrowsingHistory()) return;
    if (state.ai_color !== null || isGameOver(state)) return;
    // Snapshot gameId - the request below can take a moment, and if the
    // user accepts/joins a *different* game while it's in flight, this
    // response describes a game that's no longer the active one at all.
    const pollingGameId = gameId;
    let fresh;
    try {
        fresh = await api.getGame(pollingGameId);
    } catch (e) {
        return; // transient - next tick retries
    }
    // Re-check everything after the await, not just before it - loadGame()
    // (new game / accepted challenge / joined game) may have run while this
    // request was in flight, and a stale response must never clobber it.
    if (gameId !== pollingGameId || !state || busy || isBrowsingHistory()) return;

    const hasNewMove = fresh.history.length > state.history.length;
    // Resignation/draw-agreement never append to history, so they'd
    // otherwise never be noticed here at all.
    const hasNewResult = Boolean(fresh.result) && !state.result;
    const hasNewDrawOffer = fresh.draw_offered_by !== state.draw_offered_by;
    if (!hasNewMove && !hasNewResult && !hasNewDrawOffer) return;

    const newNotation = hasNewMove ? fresh.history[fresh.history.length - 1] : undefined;
    const moverColor = state.next_player; // whoever's turn it was before this catch-up
    state = fresh;
    await afterStateUpdate(newNotation, moverColor);
}

setInterval(() => { if (currentProfile) refreshChallenges(); }, 5000);
setInterval(pollActiveGame, 3000);
setInterval(updateClocks, 250); // smooth countdown between the poll's 3s syncs

// ---- opening a game linked from the Profile page's ledger ----------------

(async function loadGameFromUrl() {
    const gameId = new URLSearchParams(window.location.search).get('game');
    if (!gameId) return;
    setBusy(true);
    try {
        loadGame(await api.getGame(gameId));
        await afterStateUpdate();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
})();
