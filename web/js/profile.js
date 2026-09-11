import { api, setTokenProvider } from './api.js';
import { getIdToken, onAuthChange, uploadAvatar, getAvatarUrl } from './firebase.js';
import { drawIdenticon } from './identicon.js';
import { initNavMenu } from './nav.js';

setTokenProvider(getIdToken);
initNavMenu();

const signedOutMessage = document.getElementById('signedOutMessage');
const profileContent = document.getElementById('profileContent');
const avatarImg = document.getElementById('avatarImg');
const avatarCanvas = document.getElementById('avatarCanvas');
const avatarEditBtn = document.getElementById('avatarEditBtn');
const avatarFileInput = document.getElementById('avatarFileInput');
const profileUsername = document.getElementById('profileUsername');
const bioDisplay = document.getElementById('bioDisplay');
const bioText = document.getElementById('bioText');
const bioEditBtn = document.getElementById('bioEditBtn');
const bioEditor = document.getElementById('bioEditor');
const bioTextarea = document.getElementById('bioTextarea');
const bioSaveBtn = document.getElementById('bioSaveBtn');
const bioCancelBtn = document.getElementById('bioCancelBtn');
const gamesLedger = document.getElementById('gamesLedger');

let myProfile = null; // {uid, username, bio?, created_at}

// ---- avatar -----------------------------------------------------------
//
// No "has an avatar" flag is tracked anywhere in the Realtime Database -
// avatars/{uid} in Storage either exists or it doesn't, and that's the
// only source of truth. A 404 there just means "show the identicon."

async function loadAvatar(uid) {
    const url = await getAvatarUrl(uid);
    if (url) {
        avatarImg.src = url;
        avatarImg.hidden = false;
        avatarCanvas.hidden = true;
    } else {
        avatarImg.hidden = true;
        avatarCanvas.hidden = false;
        drawIdenticon(avatarCanvas, uid);
    }
}

// Center-crops to a square and downsizes before upload, so avatars stay
// small and visually consistent regardless of what someone picks.
function resizeImageToSquareJpeg(file, targetSize) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            const side = Math.min(img.width, img.height);
            const sx = (img.width - side) / 2;
            const sy = (img.height - side) / 2;
            const canvas = document.createElement('canvas');
            canvas.width = targetSize;
            canvas.height = targetSize;
            canvas.getContext('2d').drawImage(img, sx, sy, side, side, 0, 0, targetSize, targetSize);
            canvas.toBlob((blob) => {
                URL.revokeObjectURL(img.src);
                if (blob) resolve(blob); else reject(new Error('image processing failed'));
            }, 'image/jpeg', 0.85);
        };
        img.onerror = () => reject(new Error('could not read that image file'));
        img.src = URL.createObjectURL(file);
    });
}

avatarEditBtn.addEventListener('click', () => avatarFileInput.click());

avatarFileInput.addEventListener('change', async () => {
    const file = avatarFileInput.files[0];
    if (!file || !myProfile) return;
    if (file.size > 5 * 1024 * 1024) {
        alert('Please choose an image under 5MB.');
        avatarFileInput.value = '';
        return;
    }
    avatarEditBtn.disabled = true;
    try {
        const blob = await resizeImageToSquareJpeg(file, 128);
        await uploadAvatar(myProfile.uid, blob);
        await loadAvatar(myProfile.uid);
    } catch (e) {
        alert(`Couldn't upload avatar: ${e.message}`);
    } finally {
        avatarEditBtn.disabled = false;
        avatarFileInput.value = '';
    }
});

// ---- bio ----------------------------------------------------------------

bioEditBtn.addEventListener('click', () => {
    bioTextarea.value = myProfile.bio || '';
    bioDisplay.hidden = true;
    bioEditor.hidden = false;
    bioTextarea.focus();
});

bioCancelBtn.addEventListener('click', () => {
    bioEditor.hidden = true;
    bioDisplay.hidden = false;
});

bioSaveBtn.addEventListener('click', async () => {
    bioSaveBtn.disabled = true;
    try {
        myProfile = await api.updateBio(bioTextarea.value);
        bioText.textContent = myProfile.bio || '(no bio yet)';
        bioEditor.hidden = true;
        bioDisplay.hidden = false;
    } catch (e) {
        alert(`Couldn't save bio: ${e.message}`);
    } finally {
        bioSaveBtn.disabled = false;
    }
});

// ---- games ledger ---------------------------------------------------------

function formatDate(ms) {
    return ms ? new Date(ms).toLocaleDateString() : '';
}

function resultLabel(result, mine) {
    if (!result) return { text: 'In progress', cls: 'ledgerOngoing' };
    if (result.winner === null) return { text: 'Draw', cls: 'ledgerDraw' };
    return result.winner === mine
        ? { text: 'Win', cls: 'ledgerWin' }
        : { text: 'Loss', cls: 'ledgerLoss' };
}

function renderLedger(games) {
    gamesLedger.innerHTML = '';
    if (games.length === 0) {
        const empty = document.createElement('p');
        empty.textContent = 'No games played yet.';
        gamesLedger.appendChild(empty);
        return;
    }
    for (const g of games) {
        const mine = g.white_uid === myProfile.uid ? 'white' : 'black';
        // A vs-AI game has no account (hence no username) on the AI's
        // side at all - fall back to a "Computer (difficulty)" label
        // rather than an empty/uid-shaped name.
        const aiLabel = g.ai_difficulty ? `Computer (${g.ai_difficulty})` : 'Computer';
        const opponentUsername = mine === 'white'
            ? (g.black_username || aiLabel)
            : (g.white_username || aiLabel);
        const { text, cls } = resultLabel(g.result, mine);

        const row = document.createElement('a');
        row.className = 'ledgerRow';
        row.href = `index.html?game=${encodeURIComponent(g.id)}`;

        const opponent = document.createElement('span');
        opponent.className = 'ledgerOpponent';
        opponent.textContent = `vs ${opponentUsername}`;

        const color = document.createElement('span');
        color.className = 'ledgerColor';
        color.textContent = mine === 'white' ? 'White' : 'Black';

        const resultEl = document.createElement('span');
        resultEl.className = `ledgerResult ${cls}`;
        resultEl.textContent = text;

        const timeControl = document.createElement('span');
        timeControl.className = 'ledgerTimeControl';
        timeControl.textContent = g.time_control || '';

        const date = document.createElement('span');
        date.className = 'ledgerDate';
        date.textContent = formatDate(g.updated_at);

        row.append(opponent, color, resultEl, timeControl, date);
        gamesLedger.appendChild(row);
    }
}

// ---- page load ------------------------------------------------------------

async function loadProfile() {
    const token = await getIdToken();
    if (!token) {
        signedOutMessage.hidden = false;
        profileContent.hidden = true;
        return;
    }
    try {
        myProfile = await api.me();
    } catch (e) {
        // signed in but never claimed a username - nothing to show here;
        // send them back to Home to finish that first.
        signedOutMessage.hidden = false;
        profileContent.hidden = true;
        return;
    }
    signedOutMessage.hidden = true;
    profileContent.hidden = false;

    profileUsername.textContent = myProfile.username;
    bioText.textContent = myProfile.bio || '(no bio yet)';
    await loadAvatar(myProfile.uid);

    try {
        renderLedger(await api.myGames());
    } catch (e) {
        gamesLedger.textContent = `Error loading games: ${e.message}`;
    }
}

onAuthChange(loadProfile);
