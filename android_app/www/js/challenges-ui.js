// Challenge rows shared by the Play vs Human panel (main.js) and the header
// bell's dropdown (header.js), so the two show the exact same lines and
// buttons and can't drift apart. Acting in either place fires
// CHALLENGES_CHANGED_EVENT so both refresh at once.

import { api } from './api.js';

export const CHALLENGES_CHANGED_EVENT = 'rampart:challengesChanged';
// Fired after something was marked seen, so the bell recounts right away.
export const NOTIFICATIONS_SEEN_EVENT = 'rampart:notificationsSeen';

// How long an accepted challenge keeps showing the challenger's Join Game row.
const ACCEPTED_CHALLENGE_VISIBLE_MS = 24 * 60 * 60 * 1000;

// What Accept/Join Game do with the game. Default (every page but the home
// page): go to the home page with that game open. main.js replaces it to
// load the game onto the board in place.
let openGame = (game) => {
    window.location.href = `index.html?game=${encodeURIComponent(game.id)}`;
};
export function setChallengeGameOpener(fn) {
    openGame = fn;
}

// The bell's dropdown would otherwise stay open over the game just opened.
function goToGame(game) {
    const bell = document.getElementById('notifDropdown');
    if (bell) bell.hidden = true;
    return openGame(game);
}

function announceChange() {
    window.dispatchEvent(new Event(CHALLENGES_CHANGED_EVENT));
}

// {incoming, outgoing, gameStates} - outgoing already filtered to what
// should show: pending ones, and accepted ones until 24h after acceptance
// (declined/expired just disappear). Older records have no accepted_at -
// fall back to created_at.
export async function fetchChallenges() {
    const [incoming, outgoing] = await Promise.all([
        api.incomingChallenges(), api.outgoingChallenges(),
    ]);
    const now = Date.now();
    const recentAccepted = outgoing.filter((c) => (
        c.status === 'accepted' && c.game_id &&
        now - (c.accepted_at || c.created_at || 0) < ACCEPTED_CHALLENGE_VISIBLE_MS
    ));

    // For every accepted outgoing challenge, check its game's actual
    // status - dead (server restart orphaned it, self-heal by dismissing,
    // same as joining's 404 handling) or finished (still viewable, but
    // "Join Game" shouldn't be offered as if there's a live game to resume).
    const gameStates = new Map(); // game_id -> state, or null once confirmed dead
    await Promise.all(recentAccepted.map(async (c) => {
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
    const visibleOutgoing = outgoing.filter((c) => (
        c.status === 'pending' || (recentAccepted.includes(c) && gameStates.get(c.game_id) !== null)
    ));
    return { incoming, outgoing: visibleOutgoing, gameStates };
}

function button(text, onClick, title) {
    const btn = document.createElement('button');
    btn.textContent = text;
    if (title) btn.title = title;
    btn.addEventListener('click', onClick);
    return btn;
}

// `onError(message)` shows a failure wherever the caller shows status text.
// Returns {incoming: [rows], outgoing: [rows]}.
export function buildChallengeRows({ incoming, outgoing, gameStates }, onError) {
    const act = (fn) => async () => {
        try {
            await fn();
        } catch (e) {
            onError(`Error: ${e.message}`);
        }
        announceChange();
    };
    const dismissBtn = (c) => button('✕', act(() => api.dismissChallenge(c.challenge_id)), 'Remove this challenge');

    const incomingRows = incoming.map((c) => {
        const row = document.createElement('div');
        row.className = 'challengeRow';
        const yourColor = c.challenger_color === 'white' ? 'black' : 'white';
        const label = document.createElement('span');
        label.textContent = `${c.from_username} challenges you - you'd play ${yourColor}`;
        row.append(
            label,
            button('Accept', act(async () => goToGame(await api.acceptChallenge(c.challenge_id)))),
            button('Decline', act(() => api.declineChallenge(c.challenge_id))),
            dismissBtn(c),
        );
        return row;
    });

    const outgoingRows = outgoing.map((c) => {
        const row = document.createElement('div');
        row.className = 'challengeRow';
        const label = document.createElement('span');
        label.textContent = `You challenged ${c.to_username} (${c.status})`;
        row.appendChild(label);
        if (c.status === 'accepted' && c.game_id) {
            const gameState = gameStates.get(c.game_id);
            // Once the game has actually ended there's nothing left to
            // "join" - still let them open it, but the label shouldn't
            // imply you're resuming a live game.
            const isOver = Boolean(gameState && gameState.result);
            row.appendChild(button(isOver ? 'View Game' : 'Join Game', act(async () => {
                try {
                    goToGame(await api.getGame(c.game_id));
                } catch (e) {
                    // The game is gone (server restart) - remove the
                    // now-pointless challenge rather than leave a Join
                    // Game button that 404s forever.
                    if (!e.message.includes('failed (404)')) throw e;
                    onError('That game no longer exists - removing it from your challenges.');
                    await api.dismissChallenge(c.challenge_id).catch(() => {});
                }
            })));
        }
        row.appendChild(dismissBtn(c));
        return row;
    });

    return { incoming: incomingRows, outgoing: outgoingRows };
}
