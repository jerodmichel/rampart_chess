// Shared "who's signed in + what needs my attention" header widget -
// notification bell (friend requests, challenges, unread messages) and an account avatar
// with a Profile/Sign Out dropdown - included on every page the same way
// nav.js's initNavMenu() already is. Lives to the left, next to the
// hamburger menu, per the user's explicit placement request.

import { api, setTokenProvider } from './api.js';
import { getIdToken, onAuthChange, logOut, getAvatarUrl } from './firebase.js';
import { drawIdenticon } from './identicon.js';
import { setupDropdown, keepOnScreen } from './nav.js';
import { flagNode } from './extinctStates.js';
import { highestPerCategory } from './badges.js';
import { attachTapLabel } from './taplabel.js';
import { fetchChallenges, buildChallengeRows, CHALLENGES_CHANGED_EVENT, NOTIFICATIONS_SEEN_EVENT } from './challenges-ui.js';

setTokenProvider(getIdToken); // harmless if the page's own script already did this

const accountHeader = document.getElementById('accountHeader');
const notifBtn = document.getElementById('notifBtn');
const notifBadge = document.getElementById('notifBadge');
const notifDropdown = document.getElementById('notifDropdown');
const headerUserLabel = document.getElementById('headerUserLabel');
const headerRatingText = document.getElementById('headerRatingText');
const headerTrophyRow = document.getElementById('headerTrophyRow');
const avatarMenuBtn = document.getElementById('avatarMenuBtn');
const avatarMenuDropdown = document.getElementById('avatarMenuDropdown');
const headerAvatarImg = document.getElementById('headerAvatarImg');
const headerAvatarCanvas = document.getElementById('headerAvatarCanvas');
const headerLogOutBtn = document.getElementById('headerLogOutBtn');

if (accountHeader) {
    setupDropdown(notifBtn, notifDropdown);
    setupDropdown(avatarMenuBtn, avatarMenuDropdown);

    headerLogOutBtn.addEventListener('click', async () => {
        await logOut();
        window.location.href = 'index.html';
    });

    // The number counts notifications newer than when they were last seen
    // (server-stored, so it syncs across devices): opening this dropdown
    // sees everything; challenges also count as seen once the Play vs Human
    // panel has shown them. The rows stay listed until dealt with.
    let lastData = null;
    let lastError = '';

    function unseenCount({ incomingFriends, challenges, unreadThreads, seen }) {
        const seenChallenges = Math.max(seen.all, seen.challenges);
        return incomingFriends.filter((r) => (r.created_at || 0) > seen.all).length +
            challenges.incoming.filter((c) => (c.created_at || 0) > seenChallenges).length +
            challenges.outgoing.filter((c) => (
                c.status === 'accepted' && (c.accepted_at || c.created_at || 0) > seenChallenges
            )).length +
            unreadThreads.filter((t) => (t.last_timestamp || 0) > seen.all).length;
    }

    function updateBadge() {
        const total = lastData ? unseenCount(lastData) : 0;
        notifBadge.hidden = total === 0;
        notifBadge.textContent = String(total);
    }

    async function renderNotifications() {
        let incomingFriends = [];
        let challenges;
        let unreadThreads = [];
        let seen;
        try {
            [incomingFriends, challenges, seen] = await Promise.all([
                api.incomingFriendRequests(), fetchChallenges(), api.notificationsSeen(),
            ]);
        } catch (e) {
            return; // background poll - transient failure just retries next tick
        }
        // Separate try: the bell must keep working for requests/challenges
        // even if the inbox call hiccups (or an older server lacks `unread`).
        try {
            unreadThreads = (await api.inbox()).filter((t) => t.unread);
        } catch (e) { /* no message alerts this tick */ }

        lastData = { incomingFriends, challenges, unreadThreads, seen };
        updateBadge();

        // Same rows and buttons as the Play vs Human panel (challenges-ui.js).
        // (No re-render here - the action's own change event re-renders.)
        const challengeRows = buildChallengeRows(challenges, (message) => { lastError = message; });
        const children = [];
        if (lastError) {
            const err = document.createElement('p');
            err.textContent = lastError;
            children.push(err);
        }
        for (const r of incomingFriends) {
            const row = document.createElement('a');
            row.className = 'notifRow';
            row.href = 'messages.html';
            row.textContent = `${r.from_username} sent you a friend request`;
            children.push(row);
        }
        children.push(...challengeRows.incoming, ...challengeRows.outgoing);
        for (const t of unreadThreads) {
            const row = document.createElement('a');
            row.className = 'notifRow';
            // messages.html?user=X opens that conversation directly.
            row.href = `messages.html?user=${encodeURIComponent(t.other_username)}`;
            row.textContent = `New message from ${t.other_username}`;
            children.push(row);
        }
        if (children.length === 0) {
            const empty = document.createElement('p');
            empty.textContent = 'No new notifications.';
            children.push(empty);
        }
        notifDropdown.replaceChildren(...children);
        if (!notifDropdown.hidden) keepOnScreen(notifDropdown);
    }

    // Opening the dropdown sees everything in it.
    notifBtn.addEventListener('click', async () => {
        lastError = ''; // an old error goes once the dropdown is reopened
        if (notifDropdown.hidden || !lastData) return;
        try {
            lastData.seen = await api.markNotificationsSeen('all');
            updateBadge();
        } catch (e) { /* stays counted; retried next open */ }
    });
    window.addEventListener(CHALLENGES_CHANGED_EVENT, () => renderNotifications());
    window.addEventListener(NOTIFICATIONS_SEEN_EVENT, () => renderNotifications());

    async function loadAvatar(uid) {
        const url = await getAvatarUrl(uid);
        if (url) {
            headerAvatarImg.src = url;
            headerAvatarImg.hidden = false;
            headerAvatarCanvas.hidden = true;
        } else {
            headerAvatarImg.hidden = true;
            headerAvatarCanvas.hidden = false;
            drawIdenticon(headerAvatarCanvas, uid);
        }
    }

    async function initAccountHeader(retried) {
        const token = await getIdToken();
        accountHeader.hidden = !token;
        if (!token) return;
        let profile;
        try {
            profile = await api.me();
        } catch (e) {
            // Only a 404 means "signed in but hasn't claimed a username
            // yet" - anything else is a transient failure, so retry once
            // before giving up rather than hiding the header for good.
            if (!/\(404\)/.test(e.message) && !retried) {
                setTimeout(() => initAccountHeader(true), 2000);
            }
            accountHeader.hidden = true;
            return;
        }
        avatarMenuBtn.title = `${profile.username} (${profile.rating ?? 1200})`;
        headerUserLabel.textContent = '';
        const flag = flagNode(profile.country);
        if (flag) headerUserLabel.append(flag, ' ');
        headerUserLabel.append(profile.username);
        // Its own element (not just appended text) rather than part of
        // headerUserLabel - on mobile this moves down to sit alongside
        // the trophy row (see #headerMetaRow in index.html/style.css)
        // instead of getting truncated away along with a long username.
        headerRatingText.textContent = `(${profile.rating ?? 1200})`;
        window.dispatchEvent(new Event('rampart:headerReady'));
        await loadAvatar(profile.uid);
        await renderNotifications();
        await renderHeaderTrophies(profile.username);
    }

    // One icon per category (whichever badge in it was earned most
    // recently - see badges.js's highestPerCategory), in the top nav's
    // account area right next to your own name - purely decorative, so a
    // lookup failure just means no trophy row, never a broken header.
    async function renderHeaderTrophies(username) {
        headerTrophyRow.innerHTML = '';
        try {
            const earned = await api.playerBadges(username);
            for (const badge of highestPerCategory(earned)) {
                const iconEl = badge.image ? document.createElement('img') : document.createElement('span');
                iconEl.className = 'playerTrophyIcon';
                attachTapLabel(iconEl, badge.name);
                if (badge.image) {
                    iconEl.src = badge.image;
                    iconEl.alt = badge.name;
                } else {
                    iconEl.textContent = badge.icon;
                }
                headerTrophyRow.appendChild(iconEl);
            }
        } catch (e) { /* decorative only - see comment above */ }
    }

    onAuthChange(() => initAccountHeader());
    // Fired by main.js right after a fresh sign-up finishes claiming a
    // username - that doesn't touch Firebase Auth itself, so onAuthChange
    // alone never re-fires and this widget would otherwise stay hidden
    // until something else (e.g. a page refresh) re-triggered it.
    window.addEventListener('rampart:profileClaimed', () => initAccountHeader());
    setInterval(() => { if (!accountHeader.hidden) renderNotifications(); }, 10000);

    // "Online" on the Players page: a ping every minute while a signed-in
    // player has any page open and visible (server/players.py counts anyone
    // heard from in the last 2.5 minutes). Skipped for a backgrounded tab.
    const pingPresence = () => {
        if (!accountHeader.hidden && !document.hidden) api.presencePing().catch(() => {});
    };
    setInterval(pingPresence, 60000);
    document.addEventListener('visibilitychange', pingPresence);
    window.addEventListener('rampart:headerReady', pingPresence);
}
