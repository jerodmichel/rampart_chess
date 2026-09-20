// Shared "who's signed in + what needs my attention" header widget -
// notification bell (friend requests, challenges) and an account avatar
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

    async function renderNotifications() {
        let incomingFriends = [];
        let incomingChallenges = [];
        try {
            [incomingFriends, incomingChallenges] = await Promise.all([
                api.incomingFriendRequests(), api.incomingChallenges(),
            ]);
        } catch (e) {
            return; // background poll - transient failure just retries next tick
        }

        const total = incomingFriends.length + incomingChallenges.length;
        notifBadge.hidden = total === 0;
        notifBadge.textContent = String(total);

        notifDropdown.innerHTML = '';
        if (total === 0) {
            const empty = document.createElement('p');
            empty.textContent = 'No new notifications.';
            notifDropdown.appendChild(empty);
        }
        for (const r of incomingFriends) {
            const row = document.createElement('a');
            row.className = 'notifRow';
            row.href = 'messages.html';
            row.textContent = `${r.from_username} sent you a friend request`;
            notifDropdown.appendChild(row);
        }
        for (const c of incomingChallenges) {
            const row = document.createElement('a');
            row.className = 'notifRow';
            row.href = 'index.html';
            const yourColor = c.challenger_color === 'white' ? 'black' : 'white';
            row.textContent = `${c.from_username} challenged you to a game (you'd play ${yourColor})`;
            notifDropdown.appendChild(row);
        }
        if (!notifDropdown.hidden) keepOnScreen(notifDropdown);
    }

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
}
