// Shared "who's signed in + what needs my attention" header widget -
// notification bell (friend requests, challenges) and an account avatar
// with a Profile/Sign Out dropdown - included on every page the same way
// nav.js's initNavMenu() already is. Lives to the left, next to the
// hamburger menu, per the user's explicit placement request.

import { api, setTokenProvider } from './api.js';
import { getIdToken, onAuthChange, logOut, getAvatarUrl } from './firebase.js';
import { drawIdenticon } from './identicon.js';
import { setupDropdown } from './nav.js';
import { flagNode } from './extinctStates.js';

setTokenProvider(getIdToken); // harmless if the page's own script already did this

const accountHeader = document.getElementById('accountHeader');
const notifBtn = document.getElementById('notifBtn');
const notifBadge = document.getElementById('notifBadge');
const notifDropdown = document.getElementById('notifDropdown');
const headerUserLabel = document.getElementById('headerUserLabel');
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

    async function initAccountHeader() {
        const token = await getIdToken();
        accountHeader.hidden = !token;
        if (!token) return;
        let profile;
        try {
            profile = await api.me();
        } catch (e) {
            accountHeader.hidden = true; // signed in but hasn't claimed a username yet
            return;
        }
        avatarMenuBtn.title = `${profile.username} (${profile.rating ?? 1200})`;
        headerUserLabel.textContent = '';
        const flag = flagNode(profile.country);
        if (flag) headerUserLabel.append(flag, ' ');
        headerUserLabel.append(`${profile.username} (${profile.rating ?? 1200})`);
        await loadAvatar(profile.uid);
        await renderNotifications();
    }

    onAuthChange(initAccountHeader);
    setInterval(() => { if (!accountHeader.hidden) renderNotifications(); }, 10000);
}
