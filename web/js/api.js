// Thin wrapper around the server/ FastAPI backend. No game logic lives
// here - every function is a direct call to one endpoint in server/app.py.

// Real-device testing (via the rampart-test Cloudflare Tunnel) serves the
// page itself from test.rampartchess.com, where "localhost:8080" would mean
// the TEST DEVICE's own loopback, not the dev machine actually running the
// API - auto-detecting this hostname and pointing at the tunnel's separate
// API subdomain avoids needing every test page to carry a manual
// window.RAMPART_API_BASE override just for this one case.
const BASE_URL = window.RAMPART_API_BASE || (
    window.location.hostname === 'test.rampartchess.com'
        ? 'https://test-api.rampartchess.com'
        : (window.location.hostname === 'rampartchess.com' || window.location.hostname === 'www.rampartchess.com')
            ? 'https://api.rampartchess.com'
            : 'http://localhost:8080'
);

// -- Android local engine (offline vs-AI play) ---------------------------
// When running as the packaged native app, a vs-AI game is played
// entirely on-device by a real embedded copy of the Python engine (see
// android_app/mobile_bridge.py + RampartEnginePlugin.java) instead of over
// the network - this is what lets "Play vs Computer" work with no
// connectivity at all. Only the specific per-game calls below ever check
// localGameAiColor; every human-vs-human/social call is untouched and
// always goes over the real network as before.
const isNativeApp = () => !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
const localGameAiColor = new Map(); // gameId -> ai_color, set when a local game is created

async function localCall(pluginMethod, args, path) {
    const body = await window.Capacitor.Plugins.RampartEngine[pluginMethod](args);
    if (body.error) throw new Error(`${path} failed (${body.status}): ${body.error}`);
    return body;
}

// test-api.rampartchess.com is deliberately NOT behind Cloudflare Access
// (unlike test.rampartchess.com) - it's a JSON API with nothing for a
// search engine to meaningfully index, every sensitive endpoint already
// requires a real Firebase auth token regardless, and gating it behind
// Access broke CORS preflight (Access intercepted the browser's OPTIONS
// preflight request and rejected it before this server's own CORSMiddleware
// ever got a chance to handle it). The one residual concern (someone
// finding this subdomain and viewing its API schema) is closed server-side
// instead - see server/app.py's docs_url=None.

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

// Bounds both the token wait and the fetch itself. Without this, a stalled
// token refresh or a dropped connection (seen in practice between two
// machines on flaky wifi) leaves the returned promise neither resolved nor
// rejected forever - callers like pollActiveGame's 3s loop already have a
// "transient failure, retry next tick" catch, but that catch is unreachable
// if the promise never settles at all. 10s is generous for a same-LAN
// dev server round trip while still being far shorter than a human's
// patience for "did my move go through".
const REQUEST_TIMEOUT_MS = 10000;

function withTimeout(promise, ms, message) {
    let timeoutId;
    const timeout = new Promise((_, reject) => {
        timeoutId = setTimeout(() => reject(new Error(message)), ms);
    });
    return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
}

async function request(path, options) {
    const headers = { 'Content-Type': 'application/json' };
    const token = await withTimeout(
        tokenProvider(),
        REQUEST_TIMEOUT_MS,
        'timed out waiting for auth token',
    );
    if (token) headers.Authorization = `Bearer ${token}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    let res;
    try {
        res = await fetch(`${BASE_URL}${path}`, {
            headers,
            ...options,
            signal: controller.signal,
        });
    } catch (e) {
        if (e.name === 'AbortError') throw new Error(`${path} timed out`);
        throw e;
    } finally {
        clearTimeout(timeoutId);
    }
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

// The above wraps every failure in a "PATH failed (status): <detail>"
// string - callers that show e.message directly to the user (profile.js,
// messages.js) want just <detail> instead of that request-shape boilerplate.
// Lives here, not duplicated per-caller, since it's this module's own error
// format being unwrapped.
export function apiErrorDetail(e) {
    const match = e.message.match(/^\/\S+ failed \(\d+\): (.+)$/);
    return match ? match[1] : e.message;
}

export const api = {
    async newGame(aiColor, aiDifficulty) {
        if (isNativeApp()) {
            const body = await localCall('newGame', { aiColor, aiDifficulty }, '/games');
            localGameAiColor.set(body.id, aiColor);
            return body;
        }
        return request('/games', {
            method: 'POST',
            body: JSON.stringify({ ai_color: aiColor, ai_difficulty: aiDifficulty }),
        });
    },

    getGame(gameId) {
        if (localGameAiColor.has(gameId)) return localCall('getGame', { gameId }, `/games/${gameId}`);
        return request(`/games/${gameId}`);
    },

    legalMoves(gameId, col, row) {
        if (localGameAiColor.has(gameId)) {
            return localCall('legalMoves', { gameId, col, row }, `/games/${gameId}/legal_moves`);
        }
        return request(`/games/${gameId}/legal_moves?col=${col}&row=${row}`);
    },

    // queenCol/queenRow are only needed when this move sends a raider into
    // the enemy queen's house while the mover's own queen is dead (see
    // main.js's pendingQueenMove) - omitted for every other move.
    move(gameId, fromCol, fromRow, toCol, toRow, queenCol, queenRow) {
        if (localGameAiColor.has(gameId)) {
            return localCall('move', {
                gameId, fromCol, fromRow, toCol, toRow,
                queenCol: queenCol ?? null, queenRow: queenRow ?? null,
            }, `/games/${gameId}/move`);
        }
        return request(`/games/${gameId}/move`, {
            method: 'POST',
            body: JSON.stringify({
                from_col: fromCol, from_row: fromRow, to_col: toCol, to_row: toRow,
                queen_col: queenCol ?? null, queen_row: queenRow ?? null,
            }),
        });
    },

    // cards: [{rank, suit}], kind: 'strike' | 'raise' - see
    // GameSession.legal_cast_destinations_for_combo for why this exists
    // instead of matching against /cast_moves' single auto-found combo.
    castComboDestinations(gameId, cards, kind) {
        if (localGameAiColor.has(gameId)) {
            return localCall('castComboDestinations',
                { gameId, cardsJson: JSON.stringify(cards), kind }, `/games/${gameId}/cast_combo_destinations`);
        }
        return request(`/games/${gameId}/cast_combo_destinations`, {
            method: 'POST',
            body: JSON.stringify({ cards, kind }),
        });
    },

    castComboMove(gameId, cards, kind, toCol, toRow) {
        if (localGameAiColor.has(gameId)) {
            return localCall('castComboMove',
                { gameId, cardsJson: JSON.stringify(cards), kind, toCol, toRow }, `/games/${gameId}/cast_combo_move`);
        }
        return request(`/games/${gameId}/cast_combo_move`, {
            method: 'POST',
            body: JSON.stringify({ cards, kind, to_col: toCol, to_row: toRow }),
        });
    },

    aiMove(gameId) {
        if (localGameAiColor.has(gameId)) return localCall('aiMove', { gameId }, `/games/${gameId}/ai_move`);
        return request(`/games/${gameId}/ai_move`, { method: 'POST' });
    },

    // Read-only snapshot of the position after `index` half-moves (0 = the
    // start, history.length = live) - never mutates the live game.
    historyAt(gameId, index) {
        if (localGameAiColor.has(gameId)) {
            return localCall('historyAt', { gameId, index }, `/games/${gameId}/history/${index}`);
        }
        return request(`/games/${gameId}/history/${index}`);
    },

    // The human-readable "Moves" list (server/game_session.py's
    // display_history) - separate from getGame()/historyAt() since it's
    // only needed while the Moves panel is actually open, not on every
    // poll tick.
    moves(gameId) {
        if (localGameAiColor.has(gameId)) return localCall('moves', { gameId }, `/games/${gameId}/moves`);
        return request(`/games/${gameId}/moves`);
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

    updateCountry(country) {
        return request('/profile/country', {
            method: 'POST',
            body: JSON.stringify({ country }),
        });
    },

    myGames() {
        return request('/profile/games');
    },

    findUser(username) {
        return request(`/auth/users/${encodeURIComponent(username)}`);
    },

    // -- public player profiles (viewing someone ELSE's stats/history) --

    playerProfile(username) {
        return request(`/players/${encodeURIComponent(username)}`);
    },

    playerGames(username) {
        return request(`/players/${encodeURIComponent(username)}/games`);
    },

    playerRatingHistory(username) {
        return request(`/players/${encodeURIComponent(username)}/rating_history`);
    },

    playerRank(username) {
        return request(`/players/${encodeURIComponent(username)}/rank`);
    },

    playerBadges(username) {
        return request(`/players/${encodeURIComponent(username)}/badges`);
    },

    // -- spectating -------------------------------------------------------

    liveGames() {
        return request('/games/live');
    },

    // -- friends ------------------------------------------------------------

    sendFriendRequest(username) {
        return request('/friends/request', {
            method: 'POST',
            body: JSON.stringify({ to_username: username }),
        });
    },

    incomingFriendRequests() {
        return request('/friends/incoming');
    },

    outgoingFriendRequests() {
        return request('/friends/outgoing');
    },

    acceptFriendRequest(requestId) {
        return request(`/friends/${requestId}/accept`, { method: 'POST' });
    },

    declineFriendRequest(requestId) {
        return request(`/friends/${requestId}/decline`, { method: 'POST' });
    },

    dismissFriendRequest(requestId) {
        return request(`/friends/${requestId}/dismiss`, { method: 'POST' });
    },

    friends() {
        return request('/friends');
    },

    removeFriend(username) {
        return request(`/friends/${encodeURIComponent(username)}/remove`, { method: 'POST' });
    },

    // -- direct messages (friends only) -------------------------------------

    sendDirectMessage(username, text) {
        return request(`/messages/${encodeURIComponent(username)}`, {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
    },

    directMessages(username) {
        return request(`/messages/${encodeURIComponent(username)}`);
    },

    inbox() {
        return request('/messages');
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
        if (localGameAiColor.has(gameId)) {
            const aiColor = localGameAiColor.get(gameId);
            const color = aiColor === 'white' ? 'black' : 'white'; // the human is always the non-AI side locally
            return localCall('resign', { gameId, color }, `/games/${gameId}/resign`);
        }
        return request(`/games/${gameId}/resign`, { method: 'POST' });
    },

    // Only valid with zero moves played - disposes of the game instead of
    // recording a loss (see server/app.py's /abort).
    abort(gameId) {
        if (localGameAiColor.has(gameId)) {
            return localCall('abort', { gameId }, `/games/${gameId}/abort`).then(body => {
                localGameAiColor.delete(gameId);
                return body;
            });
        }
        return request(`/games/${gameId}/abort`, { method: 'POST' });
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

    // -- chat (human-vs-human games only) --------------------------------

    sendChatMessage(gameId, text) {
        return request(`/games/${gameId}/chat`, {
            method: 'POST',
            body: JSON.stringify({ text }),
        });
    },

    chatMessages(gameId) {
        return request(`/games/${gameId}/chat`);
    },
};
