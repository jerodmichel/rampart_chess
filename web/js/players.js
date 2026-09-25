// Players page: every account ranked by rating (server/players.py), with
// who's online, trophies, and a Challenge button that opens a small dialog
// instead of sending the player off to the Home page's challenge form.

import { api, apiErrorDetail, setTokenProvider } from './api.js';
import { getIdToken, onAuthChange, getAvatarUrl } from './firebase.js';
import { initNavMenu } from './nav.js';
import { drawIdenticon } from './identicon.js';
import { flagNode } from './extinctStates.js';
import { highestPerCategory } from './badges.js';
import { attachTapLabel } from './taplabel.js';

setTokenProvider(getIdToken);
initNavMenu();

const REFRESH_MS = 30000;

const summaryEl = document.getElementById('playersSummary');
const podiumEl = document.getElementById('podium');
const listEl = document.getElementById('playersList');
const emptyEl = document.getElementById('playersEmpty');
const searchInput = document.getElementById('playersSearch');
const filterBtns = [...document.querySelectorAll('.playersFilter')];
const friendsFilterBtn = document.querySelector('.playersFilter[data-filter="friends"]');
const signedOutNote = document.getElementById('playersSignedOutNote');

const dialog = document.getElementById('challengeDialog');
const dialogPlayer = document.getElementById('challengeDialogPlayer');
const dialogColor = document.getElementById('challengeDialogColor');
const dialogTime = document.getElementById('challengeDialogTime');
const dialogStatus = document.getElementById('challengeDialogStatus');
const dialogSend = document.getElementById('challengeDialogSend');
const dialogCancel = document.getElementById('challengeDialogCancel');

let players = [];
let signedIn = false;
let filter = 'all';
let loadFailed = false;
const avatarUrls = new Map(); // uid -> url | null, once resolved

// ---- data ----------------------------------------------------------------

async function load() {
    try {
        players = await api.players();
        loadFailed = false;
    } catch (e) {
        console.error('players load failed:', e);
        loadFailed = players.length === 0;
    }
    // Every visitor gets an anonymous Firebase session, so "has a token"
    // isn't "has an account" - the server marks the viewer's own row
    // only when they've claimed a username.
    signedIn = players.some((p) => p.is_me);
    signedOutNote.hidden = signedIn || loadFailed;
    friendsFilterBtn.hidden = !signedIn;
    if (!signedIn && filter === 'friends') filterBtns[0].click();
    render();
}

// ---- small builders --------------------------------------------------------

function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
}

function avatar(player, size) {
    const wrap = el('span', 'playerAvatar');
    wrap.style.setProperty('--avatar-size', `${size}px`);
    const img = el('img');
    img.alt = '';
    const canvas = el('canvas');
    canvas.width = canvas.height = size * 2; // crisp on high-DPI screens
    wrap.append(img, canvas);

    const show = (url) => {
        if (url) {
            img.src = url;
            img.hidden = false;
            canvas.hidden = true;
        } else {
            img.hidden = true;
            canvas.hidden = false;
            drawIdenticon(canvas, player.uid);
        }
    };
    if (avatarUrls.has(player.uid)) {
        show(avatarUrls.get(player.uid));
    } else {
        show(null);
        getAvatarUrl(player.uid).then((url) => {
            avatarUrls.set(player.uid, url);
            if (url) show(url);
        });
    }

    const dot = el('span', `statusDot ${player.online ? 'online' : 'offline'}`);
    dot.title = player.online ? 'Online' : 'Offline';
    wrap.appendChild(dot);
    return wrap;
}

function nameLine(player) {
    const line = el('span', 'playerNameLine');
    const link = el('a', 'playerName');
    link.href = `profile.html?user=${encodeURIComponent(player.username)}`;
    const flag = flagNode(player.country);
    if (flag) link.append(flag, ' ');
    link.append(player.username);
    line.appendChild(link);
    if (player.is_me) line.appendChild(el('span', 'playerTag me', 'You'));
    else if (player.is_friend) line.appendChild(el('span', 'playerTag friend', 'Friend'));
    return line;
}

function trophyRow(player) {
    const row = el('span', 'playersTrophies');
    const top = highestPerCategory(player.badges || {});
    for (const badge of top) {
        const icon = badge.image ? el('img', 'playersTrophyIcon') : el('span', 'playersTrophyIcon', badge.icon);
        if (badge.image) {
            icon.src = badge.image;
            icon.alt = badge.name;
        }
        attachTapLabel(icon, badge.name);
        row.appendChild(icon);
    }
    const total = Object.keys(player.badges || {}).length;
    if (total > top.length) {
        const more = el('span', 'playersTrophyMore', `+${total - top.length}`);
        attachTapLabel(more, `${total} trophies in all`);
        row.appendChild(more);
    }
    return row;
}

function gamesText(player) {
    return `${player.games_played} game${player.games_played === 1 ? '' : 's'}`;
}

function joinedText(player) {
    if (!player.created_at) return 'new player';
    const when = new Date(player.created_at).toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
    return `joined ${when}`;
}

function statusText(player) {
    if (player.playing_game_id) return 'Playing now';
    return player.online ? 'Online' : 'Offline';
}

function actions(player) {
    const box = el('div', 'playerActions');
    if (player.playing_game_id && !player.is_me) {
        const watch = el('a', 'watchBtn', 'Watch');
        watch.href = `index.html?game=${encodeURIComponent(player.playing_game_id)}`;
        box.appendChild(watch);
    }
    if (player.can_challenge) {
        const btn = el('button', 'challengeBtn', 'Challenge');
        btn.addEventListener('click', () => openChallenge(player));
        box.appendChild(btn);
    } else if (signedIn && !player.is_me && player.friends_only && !player.is_friend) {
        box.appendChild(el('span', 'friendsOnlyNote', 'Friends only'));
    }
    return box;
}

function ratingBlock(player) {
    const block = el('div', 'playerRating');
    block.appendChild(el('span', 'ratingValue', String(player.rating)));
    let sub;
    if (!player.rank) sub = joinedText(player);
    else if (player.peak_rating > player.rating) sub = `peak ${player.peak_rating}`;
    else sub = gamesText(player);
    block.appendChild(el('span', 'ratingSub', sub));
    return block;
}

// ---- podium (top three, only for the unfiltered view) ----------------------

const MEDALS = ['gold', 'silver', 'bronze'];

function podiumCard(player) {
    const medal = MEDALS[player.rank - 1];
    const card = el('li', `podiumCard ${medal}`);
    card.appendChild(el('span', 'podiumRank', String(player.rank)));
    card.appendChild(avatar(player, 72));
    card.appendChild(nameLine(player));
    card.appendChild(trophyRow(player));
    const rating = el('div', 'podiumRating');
    rating.appendChild(el('span', 'ratingValue', String(player.rating)));
    const live = player.playing_game_id || player.online;
    rating.appendChild(el('span', `ratingSub${live ? ' live' : ''}`, live ? statusText(player) : gamesText(player)));
    card.appendChild(rating);
    card.appendChild(actions(player));
    return card;
}

// ---- list rows ---------------------------------------------------------------

function playerRow(player) {
    const row = el('li', 'playerRow');
    if (player.is_me) row.classList.add('isMe');
    row.appendChild(el('span', 'playerRank', player.rank ? String(player.rank) : '\u2013'));
    row.appendChild(avatar(player, 44));
    const info = el('div', 'playerInfo');
    info.appendChild(nameLine(player));
    const meta = el('div', 'playerMeta');
    meta.appendChild(el('span', `playerStatus ${player.playing_game_id ? 'playing' : (player.online ? 'online' : '')}`, statusText(player)));
    meta.appendChild(trophyRow(player));
    info.appendChild(meta);
    row.appendChild(info);
    row.appendChild(ratingBlock(player));
    row.appendChild(actions(player));
    return row;
}

// ---- render ----------------------------------------------------------------

function filtered() {
    const q = searchInput.value.trim().toLowerCase();
    return players.filter((p) => {
        if (filter === 'online' && !p.online) return false;
        if (filter === 'friends' && !p.is_friend && !p.is_me) return false;
        return !q || p.username.toLowerCase().includes(q);
    });
}

function render() {
    const onlineCount = players.filter((p) => p.online).length;
    summaryEl.textContent = '';
    if (players.length) {
        summaryEl.append(`${players.length} player${players.length === 1 ? '' : 's'}`);
        const online = el('span', 'summaryOnline');
        online.append(el('span', onlineCount ? 'statusDot online pulse' : 'statusDot'), `${onlineCount} online now`);
        summaryEl.append(' · ', online);
    }

    const rows = filtered();
    const unfiltered = filter === 'all' && !searchInput.value.trim();
    const podiumPlayers = unfiltered ? rows.filter((p) => p.rank && p.rank <= 3) : [];
    podiumEl.replaceChildren(...podiumPlayers.map(podiumCard));
    podiumEl.hidden = podiumPlayers.length === 0;
    const listItems = [];
    let dividerShown = false;
    for (const p of rows) {
        if (podiumPlayers.includes(p)) continue;
        if (!p.rank && !dividerShown) {
            dividerShown = true;
            const divider = el('li', 'playersDivider');
            divider.append(el('span', '', 'New players'), el('small', '', 'ranked after their first rated game'));
            listItems.push(divider);
        }
        listItems.push(playerRow(p));
    }
    listEl.replaceChildren(...listItems);

    emptyEl.hidden = rows.length > 0;
    if (loadFailed) emptyEl.textContent = "Couldn't load players - check your connection and try again.";
    else if (filter === 'online') emptyEl.textContent = 'Nobody else is online right now.';
    else if (filter === 'friends') emptyEl.textContent = 'No friends yet - add some from their profile pages.';
    else emptyEl.textContent = 'No players match that search.';
}

for (const btn of filterBtns) {
    btn.addEventListener('click', () => {
        filter = btn.dataset.filter;
        for (const b of filterBtns) {
            b.classList.toggle('active', b === btn);
            b.setAttribute('aria-selected', String(b === btn));
        }
        render();
    });
}
searchInput.addEventListener('input', render);

// ---- challenge dialog --------------------------------------------------------

let challengeTarget = null;

function openChallenge(player) {
    challengeTarget = player;
    dialogPlayer.replaceChildren(avatar(player, 40), nameLine(player), el('span', 'dialogRating', String(player.rating)));
    dialogStatus.textContent = '';
    dialogStatus.className = '';
    dialogSend.hidden = false;
    dialogSend.disabled = false;
    dialogCancel.textContent = 'Cancel';
    dialog.showModal();
}

dialogCancel.addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (evt) => {
    if (evt.target === dialog) dialog.close(); // backdrop click
});

dialogSend.addEventListener('click', async () => {
    if (!challengeTarget) return;
    dialogSend.disabled = true;
    dialogStatus.className = '';
    dialogStatus.textContent = 'Sending...';
    try {
        await api.createChallenge(challengeTarget.username, dialogColor.value, dialogTime.value);
        dialogStatus.className = 'ok';
        dialogStatus.textContent = '';
        dialogStatus.append(`Challenge sent to ${challengeTarget.username}. `);
        const link = el('a', '', 'Go to your challenges');
        link.href = 'index.html?open=human';
        dialogStatus.append(link, ' - the game starts there once they accept.');
        dialogSend.hidden = true;
        dialogCancel.textContent = 'Done';
    } catch (e) {
        dialogStatus.className = 'error';
        dialogStatus.textContent = apiErrorDetail(e);
        dialogSend.disabled = false;
    }
});

// ---- boot --------------------------------------------------------------------

onAuthChange(() => load());
window.addEventListener('rampart:profileClaimed', load);
setInterval(() => { if (!document.hidden) load(); }, REFRESH_MS);
document.addEventListener('visibilitychange', () => { if (!document.hidden) load(); });
