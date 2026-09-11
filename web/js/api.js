// Thin wrapper around the server/ FastAPI backend. No game logic lives
// here - every function is a direct call to one endpoint in server/app.py.

const BASE_URL = window.RAMPART_API_BASE || 'http://localhost:8080';

// Registered once by main.js as firebase.js's getIdToken - called FRESH on
// every request rather than caching a token string, since a Firebase ID
// token expires after exactly 1 hour. Calling getIdToken() each time isn't
// wasteful: the SDK caches the underlying JWT itself and only actually
// refreshes it over the network when it's genuinely close to expiring, so
// this is what keeps a long-open tab from suddenly sending a stale token
// and getting 401s once the first-ever token happens to age out.
let tokenProvider = () => Promise.resolve(null);

export function setTokenProvider(fn) {
    tokenProvider = fn;
}

async function request(path, options) {
    const headers = { 'Content-Type': 'application/json' };
    const token = await tokenProvider();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}${path}`, {
        headers,
        ...options,
    });
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const body = await res.json();
            detail = body.detail || detail;
        } catch (_) { /* no JSON body */ }
        throw new Error(`${path} failed (${res.status}): ${detail}`);
    }
    return res.json();
}

export const api = {
    newGame(aiColor, aiDifficulty) {
        return request('/games', {
            method: 'POST',
            body: JSON.stringify({ ai_color: aiColor, ai_difficulty: aiDifficulty }),
        });
    },

    getGame(gameId) {
        return request(`/games/${gameId}`);
    },

    legalMoves(gameId, col, row) {
        return request(`/games/${gameId}/legal_moves?col=${col}&row=${row}`);
    },

    move(gameId, fromCol, fromRow, toCol, toRow) {
        return request(`/games/${gameId}/move`, {
            method: 'POST',
            body: JSON.stringify({ from_col: fromCol, from_row: fromRow, to_col: toCol, to_row: toRow }),
        });
    },

    // cards: [{rank, suit}], kind: 'strike' | 'raise' - see
    // GameSession.legal_cast_destinations_for_combo for why this exists
    // instead of matching against /cast_moves' single auto-found combo.
    castComboDestinations(gameId, cards, kind) {
        return request(`/games/${gameId}/cast_combo_destinations`, {
            method: 'POST',
            body: JSON.stringify({ cards, kind }),
        });
    },

    castComboMove(gameId, cards, kind, toCol, toRow) {
        return request(`/games/${gameId}/cast_combo_move`, {
            method: 'POST',
            body: JSON.stringify({ cards, kind, to_col: toCol, to_row: toRow }),
        });
    },

    aiMove(gameId) {
        return request(`/games/${gameId}/ai_move`, { method: 'POST' });
    },

    // Read-only snapshot of the position after `index` half-moves (0 = the
    // start, history.length = live) - never mutates the live game.
    historyAt(gameId, index) {
        return request(`/games/${gameId}/history/${index}`);
    },

    // -- accounts (all require a signed-in user - see setTokenProvider) --

    register(username) {
        return request('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username }),
        });
    },

    me() {
        return request('/auth/me');
    },

    updateBio(bio) {
        return request('/profile/bio', {
            method: 'POST',
            body: JSON.stringify({ bio }),
        });
    },

    myGames() {
        return request('/profile/games');
    },

    findUser(username) {
        return request(`/auth/users/${encodeURIComponent(username)}`);
    },

    // -- challenges (match invites) -----------------------------------

    createChallenge(toUsername, color = 'random', timeControl = '30min') {
        return request('/challenges', {
            method: 'POST',
            body: JSON.stringify({ to_username: toUsername, color, time_control: timeControl }),
        });
    },

    incomingChallenges() {
        return request('/challenges/incoming');
    },

    outgoingChallenges() {
        return request('/challenges/outgoing');
    },

    acceptChallenge(challengeId) {
        return request(`/challenges/${challengeId}/accept`, { method: 'POST' });
    },

    declineChallenge(challengeId) {
        return request(`/challenges/${challengeId}/decline`, { method: 'POST' });
    },

    // Removes a challenge record outright, in any status - for clutter
    // (an accepted challenge whose in-memory game is gone after a server
    // restart, or a pending one you're no longer interested in).
    dismissChallenge(challengeId) {
        return request(`/challenges/${challengeId}/dismiss`, { method: 'POST' });
    },

    // -- ending a game --------------------------------------------------

    resign(gameId) {
        return request(`/games/${gameId}/resign`, { method: 'POST' });
    },

    offerDraw(gameId) {
        return request(`/games/${gameId}/offer_draw`, { method: 'POST' });
    },

    respondDraw(gameId, accept) {
        return request(`/games/${gameId}/respond_draw`, {
            method: 'POST',
            body: JSON.stringify({ accept }),
        });
    },
};
