import { api, setTokenProvider, apiErrorDetail } from './api.js';
import { getIdToken, onAuthChange, uploadAvatar, getAvatarUrl, auth, logOut, reauthenticateWithPassword } from './firebase.js';
import { drawIdenticon } from './identicon.js';
import { initNavMenu } from './nav.js';
import { COUNTRIES, flagEmoji } from './countries.js';
import { aiOpponentName } from './constants.js';
import { EXTINCT_STATES, flagNode, stateName } from './extinctStates.js';
import { BADGE_CATEGORIES } from './badges.js';
import { attachTapLabel } from './taplabel.js';
import { openReportDialog, confirmAndBlock } from './moderation-ui.js';

setTokenProvider(getIdToken);
initNavMenu();

const signedOutMessage = document.getElementById('signedOutMessage');
const profileContent = document.getElementById('profileContent');
const avatarImg = document.getElementById('avatarImg');
const avatarCanvas = document.getElementById('avatarCanvas');
const avatarEditBtn = document.getElementById('avatarEditBtn');
const avatarFileInput = document.getElementById('avatarFileInput');
const profileUsername = document.getElementById('profileUsername');
const profileRating = document.getElementById('profileRating');
const bioDisplay = document.getElementById('bioDisplay');
const bioText = document.getElementById('bioText');
const bioEditBtn = document.getElementById('bioEditBtn');
const bioEditor = document.getElementById('bioEditor');
const bioTextarea = document.getElementById('bioTextarea');
const bioSaveBtn = document.getElementById('bioSaveBtn');
const bioCancelBtn = document.getElementById('bioCancelBtn');
const gamesLedger = document.getElementById('gamesLedger');
const badgesGrid = document.getElementById('badgesGrid');
const countryRow = document.getElementById('countryRow');
const countryLabel = document.getElementById('countryLabel');
const countryEditBtn = document.getElementById('countryEditBtn');
const countryEditor = document.getElementById('countryEditor');
const countrySelect = document.getElementById('countrySelect');
const extinctStateSelect = document.getElementById('extinctStateSelect');
const countrySaveBtn = document.getElementById('countrySaveBtn');
const countryCancelBtn = document.getElementById('countryCancelBtn');
const profileFriendsSection = document.getElementById('profileFriendsSection');
const profileFriendsList = document.getElementById('profileFriendsList');
const playerSearchInput = document.getElementById('playerSearchInput');
const playerSearchBtn = document.getElementById('playerSearchBtn');
const addFriendRow = document.getElementById('addFriendRow');
const messageFriendBtn = document.getElementById('messageFriendBtn');
const addFriendBtn = document.getElementById('addFriendBtn');
const removeFriendBtn = document.getElementById('removeFriendBtn');
const reportBtn = document.getElementById('reportBtn');
const blockBtn = document.getElementById('blockBtn');
const unblockBtn = document.getElementById('unblockBtn');
const blockedSection = document.getElementById('blockedSection');
const blockedList = document.getElementById('blockedList');
const acceptIncomingFriendBtn = document.getElementById('acceptIncomingFriendBtn');
const declineIncomingFriendBtn = document.getElementById('declineIncomingFriendBtn');
const addFriendStatus = document.getElementById('addFriendStatus');

const dangerZone = document.getElementById('dangerZone');
const deleteAccountOpenBtn = document.getElementById('deleteAccountOpenBtn');
const deleteAccountPanel = document.getElementById('deleteAccountPanel');
const deleteConfirmUsername = document.getElementById('deleteConfirmUsername');
const deletePassword = document.getElementById('deletePassword');
const deleteAccountConfirmBtn = document.getElementById('deleteAccountConfirmBtn');
const deleteAccountCancelBtn = document.getElementById('deleteAccountCancelBtn');
const deleteAccountStatus = document.getElementById('deleteAccountStatus');

deleteAccountOpenBtn.addEventListener('click', () => {
    deleteAccountPanel.hidden = false;
    deleteAccountOpenBtn.hidden = true;
});
deleteAccountCancelBtn.addEventListener('click', () => {
    deleteAccountPanel.hidden = true;
    deleteAccountOpenBtn.hidden = false;
    deleteConfirmUsername.value = '';
    deletePassword.value = '';
    deleteAccountStatus.textContent = '';
});
deleteAccountConfirmBtn.addEventListener('click', async () => {
    const typed = deleteConfirmUsername.value.trim();
    if (typed.toLowerCase() !== myProfile.username.toLowerCase()) {
        deleteAccountStatus.textContent = 'The username you typed does not match.';
        return;
    }
    if (!deletePassword.value) {
        deleteAccountStatus.textContent = 'Enter your password to continue.';
        return;
    }
    deleteAccountConfirmBtn.disabled = true;
    deleteAccountStatus.textContent = 'Deleting...';
    try {
        await reauthenticateWithPassword(deletePassword.value);
    } catch (e) {
        deleteAccountStatus.textContent = 'Incorrect password.';
        deleteAccountConfirmBtn.disabled = false;
        return;
    }
    try {
        await api.deleteAccount(typed);
    } catch (e) {
        deleteAccountStatus.textContent = apiErrorDetail(e) || 'Could not delete the account. Nothing was lost - try again.';
        deleteAccountConfirmBtn.disabled = false;
        return;
    }
    try { await logOut(); } catch (_) { /* the auth user is already gone server-side */ }
    window.location.replace('index.html');
});

addFriendBtn.addEventListener('click', async () => {
    addFriendBtn.disabled = true;
    try {
        const result = await api.sendFriendRequest(myProfile.username);
        addFriendStatus.textContent = result.status === 'accepted' ? 'You are now friends!' : 'Friend request sent!';
        addFriendBtn.hidden = true;
    } catch (e) {
        addFriendStatus.textContent = apiErrorDetail(e);
        addFriendBtn.disabled = false;
    }
});

removeFriendBtn.addEventListener('click', async () => {
    if (!confirm(`Remove ${myProfile.username} from your friends?`)) return;
    removeFriendBtn.disabled = true;
    try {
        await api.removeFriend(myProfile.username);
        await refreshFriendStatus(); // back to "Send Friend Request"
    } catch (e) {
        addFriendStatus.textContent = apiErrorDetail(e);
    } finally {
        removeFriendBtn.disabled = false;
    }
});

reportBtn.addEventListener('click', async () => {
    const { blocked } = await openReportDialog({ targetUsername: myProfile.username, kind: 'profile' });
    if (blocked) await refreshFriendStatus();
});

blockBtn.addEventListener('click', async () => {
    blockBtn.disabled = true;
    try {
        if (await confirmAndBlock(myProfile.username)) await refreshFriendStatus();
    } catch (e) {
        addFriendStatus.textContent = apiErrorDetail(e);
    } finally {
        blockBtn.disabled = false;
    }
});

unblockBtn.addEventListener('click', async () => {
    unblockBtn.disabled = true;
    try {
        await api.unblockPlayer(myProfile.username);
        await refreshFriendStatus();
    } catch (e) {
        addFriendStatus.textContent = apiErrorDetail(e);
    } finally {
        unblockBtn.disabled = false;
    }
});

let incomingRequestFromViewedPlayer = null; // set by refreshFriendStatus - the request_id, if this player has sent YOU one

acceptIncomingFriendBtn.addEventListener('click', async () => {
    acceptIncomingFriendBtn.disabled = true;
    declineIncomingFriendBtn.disabled = true;
    try {
        await api.acceptFriendRequest(incomingRequestFromViewedPlayer);
        acceptIncomingFriendBtn.hidden = true;
        declineIncomingFriendBtn.hidden = true;
        addFriendStatus.textContent = 'You are now friends!';
    } catch (e) {
        addFriendStatus.textContent = e.message;
        acceptIncomingFriendBtn.disabled = false;
        declineIncomingFriendBtn.disabled = false;
    }
});

declineIncomingFriendBtn.addEventListener('click', async () => {
    acceptIncomingFriendBtn.disabled = true;
    declineIncomingFriendBtn.disabled = true;
    try {
        await api.declineFriendRequest(incomingRequestFromViewedPlayer);
        acceptIncomingFriendBtn.hidden = true;
        declineIncomingFriendBtn.hidden = true;
        addFriendBtn.hidden = false;
        addFriendBtn.disabled = false;
        addFriendStatus.textContent = 'Declined.';
    } catch (e) {
        addFriendStatus.textContent = e.message;
        acceptIncomingFriendBtn.disabled = false;
        declineIncomingFriendBtn.disabled = false;
    }
});

// Figures out the REAL relationship with the viewed player - already
// friends, a request already pending in either direction, or neither -
// rather than always showing a fresh "Send Friend Request" button with no
// memory of what's already happened (the bug the user hit: revisiting a
// profile after sending a request just showed the button again).
async function refreshFriendStatus() {
    addFriendBtn.hidden = false;
    addFriendBtn.disabled = false;
    acceptIncomingFriendBtn.hidden = true;
    declineIncomingFriendBtn.hidden = true;
    messageFriendBtn.hidden = true;
    removeFriendBtn.hidden = true;
    reportBtn.hidden = false;
    blockBtn.hidden = false;
    unblockBtn.hidden = true;
    addFriendStatus.textContent = '';
    incomingRequestFromViewedPlayer = null;

    const [currentFriends, incoming, outgoing, blocked] = await Promise.all([
        api.friends(), api.incomingFriendRequests(), api.outgoingFriendRequests(), api.blocks(),
    ]);

    // Blocked: nothing to do here except offer to undo it (the server
    // refuses every friend request/challenge/message in either direction).
    if (blocked.some((b) => b.username === myProfile.username)) {
        addFriendBtn.hidden = true;
        blockBtn.hidden = true;
        unblockBtn.hidden = false;
        addFriendStatus.textContent = 'You have blocked this player';
        return;
    }

    if (currentFriends.some((f) => f.username === myProfile.username)) {
        addFriendBtn.hidden = true;
        addFriendStatus.textContent = 'You are friends';
        // DMs are friends-only server-side (server/messages.py), so this
        // link only ever appears once that's actually true.
        messageFriendBtn.href = `messages.html?user=${encodeURIComponent(myProfile.username)}`;
        messageFriendBtn.hidden = false;
        removeFriendBtn.hidden = false;
        return;
    }

    const theirRequestToMe = incoming.find((r) => r.from_username === myProfile.username);
    if (theirRequestToMe) {
        addFriendBtn.hidden = true;
        acceptIncomingFriendBtn.hidden = false;
        declineIncomingFriendBtn.hidden = false;
        incomingRequestFromViewedPlayer = theirRequestToMe.request_id;
        addFriendStatus.textContent = `${myProfile.username} has sent you a friend request`;
        return;
    }

    const myRequestToThem = outgoing.find((r) => r.to_username === myProfile.username && r.status === 'pending');
    if (myRequestToThem) {
        addFriendBtn.hidden = true;
        addFriendStatus.textContent = 'Friend request pending';
    }
}

let myProfile = null; // whichever profile is currently ON SCREEN - your own, or someone else's (see isOwnProfile)
let isOwnProfile = true; // false when viewing another player's profile via ?user=

playerSearchBtn.addEventListener('click', () => {
    const username = playerSearchInput.value.trim();
    if (username) window.location.href = `profile.html?user=${encodeURIComponent(username)}`;
});
playerSearchInput.addEventListener('keydown', (evt) => {
    if (evt.key === 'Enter') playerSearchBtn.click();
});

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

// ---- country (self-reported, like chess.com's flag - never geolocated) --

countrySelect.appendChild(new Option('No country set', ''));
for (const { code, name } of COUNTRIES) {
    countrySelect.appendChild(new Option(`${flagEmoji(code)} ${name}`, code));
}

// Extinct states have no Unicode flag glyph to put in the option text (see
// extinctStates.js) - the native <select> can't show an image inline, so
// these options are plain names; the chosen flag renders afterward via
// flagNode(), same as the regular country picker's label does.
extinctStateSelect.appendChild(new Option('No historical state set', ''));
for (const { code, name } of EXTINCT_STATES) {
    extinctStateSelect.appendChild(new Option(name, code));
}

// The two pickers are alternate sources for the one `country` field -
// choosing in one clears the other, so Save always has a single answer.
countrySelect.addEventListener('change', () => {
    if (countrySelect.value) extinctStateSelect.value = '';
});
extinctStateSelect.addEventListener('change', () => {
    if (extinctStateSelect.value) countrySelect.value = '';
});

function renderCountryLabel() {
    const name = stateName(myProfile.country);
    countryLabel.textContent = '';
    if (!name) {
        countryLabel.textContent = 'No country set';
        return;
    }
    const flag = flagNode(myProfile.country);
    if (flag) countryLabel.append(flag, ' ');
    countryLabel.append(name);
}

function renderProfileUsername() {
    profileUsername.textContent = '';
    const flag = flagNode(myProfile.country);
    if (flag) profileUsername.append(flag, ' ');
    profileUsername.append(myProfile.username);
}

countryEditBtn.addEventListener('click', () => {
    countrySelect.value = COUNTRIES.some((c) => c.code === myProfile.country) ? myProfile.country : '';
    extinctStateSelect.value = EXTINCT_STATES.some((s) => s.code === myProfile.country) ? myProfile.country : '';
    countryRow.hidden = true;
    countryEditor.hidden = false;
});

countryCancelBtn.addEventListener('click', () => {
    countryEditor.hidden = true;
    countryRow.hidden = false;
});

countrySaveBtn.addEventListener('click', async () => {
    countrySaveBtn.disabled = true;
    try {
        myProfile = await api.updateCountry(extinctStateSelect.value || countrySelect.value);
        renderCountryLabel();
        renderProfileUsername();
        countryEditor.hidden = true;
        countryRow.hidden = false;
    } catch (e) {
        alert(`Couldn't save country: ${e.message}`);
    } finally {
        countrySaveBtn.disabled = false;
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

// Raw stored keys (server/challenges.py TIME_CONTROLS) -> short display
// labels. .ledgerTimeControl below reserves enough width for the longest
// of these ("1 day/move") so AI games (no time control at all) still line
// up with human games under any of the three current options.
const TIME_CONTROL_LABELS = {
    '30min': '30 min',
    '1hour': '1 hour',
    '1day_per_move': '1 day/move',
};

function formatTimeControl(tc) {
    return tc ? (TIME_CONTROL_LABELS[tc] || tc) : '';
}

// `earned` is the {badge_id: {unlocked_at}} map api.playerBadges() returns.
// Shows every phase-1 badge, grouped the same way the design was pitched -
// earned ones full-color with an unlock date, unearned ones dimmed with a
// lock, so the whole roster is visible as something to work toward even on
// a fresh account. Most icons are still plain emoji placeholders (see
// badges.js); a few now have real image art instead, rendered as an <img>
// below rather than emoji text.
function renderBadges(earned) {
    badgesGrid.innerHTML = '';
    for (const category of BADGE_CATEGORIES) {
        const section = document.createElement('div');
        section.className = 'badgeCategory';
        const heading = document.createElement('h4');
        heading.textContent = category.name;
        section.appendChild(heading);
        const sub = document.createElement('p');
        sub.className = 'badgeCategorySubtitle';
        sub.textContent = category.subtitle;
        section.appendChild(sub);

        const row = document.createElement('div');
        row.className = 'badgeRow';
        for (const badge of category.badges) {
            const unlock = earned[badge.id];
            const cell = document.createElement('div');
            cell.className = unlock ? 'badgeCell badgeEarned' : 'badgeCell badgeLocked';
            attachTapLabel(cell, unlock
                ? `${badge.name} - ${badge.description}`
                : `${badge.name} (locked) - ${badge.description}`);
            const icon = document.createElement('span');
            icon.className = 'badgeIcon';
            if (badge.image) {
                const img = document.createElement('img');
                img.src = badge.image;
                img.alt = '';
                icon.appendChild(img);
            } else {
                icon.textContent = badge.icon;
            }
            const name = document.createElement('span');
            name.className = 'badgeName';
            name.textContent = badge.name;
            cell.append(icon, name);
            row.appendChild(cell);
        }
        section.appendChild(row);
        badgesGrid.appendChild(section);
    }
}

function makeLedgerRow(g) {
    const mine = g.white_uid === myProfile.uid ? 'white' : 'black';
    // A vs-AI game has no account (hence no username) on the AI's
    // side at all - fall back to a "Computer (difficulty)" label
    // rather than an empty/uid-shaped name.
    const aiLabel = g.ai_difficulty ? `${aiOpponentName(g.ai_difficulty)} (${g.ai_difficulty})` : 'Computer';
    const opponentUsername = mine === 'white' ? g.black_username : g.white_username;
    const { text, cls } = resultLabel(g.result, mine);

    const row = document.createElement('div');
    row.className = 'ledgerRow';

    // Two SEPARATE links, not one row-wide anchor - the opponent's
    // name should open THEIR profile, while the rest of the row opens
    // the game itself. An AI opponent has no profile to link to.
    const opponent = document.createElement(opponentUsername ? 'a' : 'span');
    opponent.className = 'ledgerOpponent';
    opponent.textContent = `vs ${opponentUsername || aiLabel}`;
    if (opponentUsername) opponent.href = `profile.html?user=${encodeURIComponent(opponentUsername)}`;

    const gameLink = document.createElement('a');
    gameLink.className = 'ledgerGameLink';
    gameLink.href = `index.html?game=${encodeURIComponent(g.id)}`;

    const color = document.createElement('span');
    color.className = 'ledgerColor';
    color.textContent = mine === 'white' ? 'White' : 'Black';

    const resultEl = document.createElement('span');
    resultEl.className = `ledgerResult ${cls}`;
    resultEl.textContent = text;

    const timeControl = document.createElement('span');
    timeControl.className = 'ledgerTimeControl';
    timeControl.textContent = formatTimeControl(g.time_control);

    const date = document.createElement('span');
    date.className = 'ledgerDate';
    date.textContent = formatDate(g.updated_at);

    gameLink.append(color, resultEl, timeControl, date);
    row.append(opponent, gameLink);
    return row;
}

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

// Collapsed by default; the caller fills in `.body`. Used for both the
// year and (nested inside it) month sections below.
function makeLedgerSection(label, className) {
    const section = document.createElement('div');
    section.className = className;

    const toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'ledgerSectionToggle';
    toggleBtn.setAttribute('aria-expanded', 'false');
    const labelEl = document.createElement('span');
    labelEl.textContent = label;
    const arrow = document.createElement('span');
    arrow.className = 'ledgerSectionArrow';
    arrow.innerHTML = '&#9662;';
    toggleBtn.append(labelEl, arrow);

    const body = document.createElement('div');
    body.className = 'ledgerSectionBody';
    body.hidden = true;

    toggleBtn.addEventListener('click', () => {
        body.hidden = !body.hidden;
        toggleBtn.setAttribute('aria-expanded', String(!body.hidden));
    });

    section.append(toggleBtn, body);
    return { section, body };
}

// Beyond the most-recent RECENT_GAMES_SHOWN (always shown flat, expanded),
// older games get "filed" into collapsed year -> month sections so the
// ledger doesn't turn into an endless scroll once someone has played a
// lot of games. Only years/months that actually have a game get a section.
const RECENT_GAMES_SHOWN = 25;

function renderFiledGames(games) {
    const container = document.createElement('div');
    container.className = 'ledgerFiled';

    const years = new Map(); // year -> Map(month -> games[]), insertion order preserved
    for (const g of games) {
        const d = new Date(g.updated_at);
        const year = d.getFullYear();
        const month = d.getMonth();
        if (!years.has(year)) years.set(year, new Map());
        const months = years.get(year);
        if (!months.has(month)) months.set(month, []);
        months.get(month).push(g);
    }

    for (const [year, months] of years) {
        const yearSection = makeLedgerSection(String(year), 'ledgerYearSection');
        for (const [month, monthGames] of months) {
            const monthSection = makeLedgerSection(MONTH_NAMES[month], 'ledgerMonthSection');
            for (const g of monthGames) monthSection.body.appendChild(makeLedgerRow(g));
            yearSection.body.appendChild(monthSection.section);
        }
        container.appendChild(yearSection.section);
    }
    return container;
}

function renderLedger(games) {
    gamesLedger.innerHTML = '';
    if (games.length === 0) {
        const empty = document.createElement('p');
        empty.textContent = 'No games played yet.';
        gamesLedger.appendChild(empty);
        return;
    }
    // `games` arrives newest-first from the server.
    const recent = games.slice(0, RECENT_GAMES_SHOWN);
    const filed = games.slice(RECENT_GAMES_SHOWN);

    for (const g of recent) gamesLedger.appendChild(makeLedgerRow(g));
    if (filed.length > 0) gamesLedger.appendChild(renderFiledGames(filed));
}

function renderProfileFriends(friendsList) {
    profileFriendsList.innerHTML = '';
    if (friendsList.length === 0) {
        const empty = document.createElement('p');
        empty.textContent = 'No friends yet - find a player above and send a request.';
        profileFriendsList.appendChild(empty);
        return;
    }
    for (const f of friendsList) {
        const link = document.createElement('a');
        link.className = 'friendProfileLink';
        link.href = `profile.html?user=${encodeURIComponent(f.username)}`;
        link.textContent = f.username;
        profileFriendsList.appendChild(link);
    }
}

// ---- page load ------------------------------------------------------------

function showSignedOut(message) {
    signedOutMessage.textContent = message;
    signedOutMessage.hidden = false;
    profileContent.hidden = true;
}

async function loadProfile() {
    const viewedUsername = new URLSearchParams(window.location.search).get('user');

    if (viewedUsername) {
        // Public view of ANOTHER player - no sign-in required at all.
        isOwnProfile = false;
        try {
            myProfile = await api.playerProfile(viewedUsername);
        } catch (e) {
            showSignedOut(`No player named "${viewedUsername}".`);
            return;
        }
        // ...unless ?user= happens to name YOUR OWN account (e.g. searching
        // your own username) - redirect to the plain own-profile view rather
        // than rendering a broken "add yourself as a friend" state.
        if (auth.currentUser && auth.currentUser.uid === myProfile.uid) {
            window.location.replace('profile.html');
            return;
        }
    } else {
        isOwnProfile = true;
        const token = await getIdToken();
        if (!token) {
            showSignedOut('Please sign in on the Home page first, or search for a player above.');
            return;
        }
        try {
            myProfile = await api.me();
        } catch (e) {
            // signed in but never claimed a username - nothing to show here;
            // send them back to Home to finish that first.
            showSignedOut('Please finish creating your account on the Home page first.');
            return;
        }
    }

    signedOutMessage.hidden = true;
    profileContent.hidden = false;
    avatarEditBtn.hidden = !isOwnProfile;
    bioEditBtn.hidden = !isOwnProfile;

    // The flag itself shows for anyone viewing (via profileUsername below);
    // editing it only makes sense on your own profile.
    countryEditor.hidden = true;
    countryRow.hidden = !isOwnProfile;
    dangerZone.hidden = !isOwnProfile;
    if (isOwnProfile) renderCountryLabel();

    // Only makes sense on someone ELSE's profile, and only for a signed-in
    // viewer (an anonymous visitor has no account to send a request from).
    const viewerToken = await getIdToken();
    addFriendRow.hidden = isOwnProfile || !viewerToken;
    if (!addFriendRow.hidden) {
        try {
            await refreshFriendStatus();
        } catch (e) {
            // Not fatal - worst case the button shows and errors
            // informatively on click - but silent otherwise made this
            // exact failure mode (fetching friend status fails -> the
            // button wrongly shows for an already-added friend) invisible
            // to diagnose, so at least log it.
            console.error('refreshFriendStatus failed:', e);
        }
    }

    if (isOwnProfile) loadBlockedList();

    renderProfileUsername();
    // rating/games_played are absent only for an account registered before
    // ratings existed (accounts.register_username sets them for every new
    // one now) - falls back the same way ratings.py's own server-side
    // reads do, so an old account just shows the same starting point a
    // brand-new one would until its first rated game.
    const gamesPlayed = myProfile.games_played ?? 0;
    profileRating.textContent = `Rating: ${myProfile.rating ?? 1200} (${gamesPlayed} rated game${gamesPlayed === 1 ? '' : 's'})`;
    bioText.textContent = myProfile.bio || (isOwnProfile ? '(no bio yet)' : '(no bio)');
    await loadAvatar(myProfile.uid);

    try {
        renderLedger(isOwnProfile ? await api.myGames() : await api.playerGames(myProfile.username));
    } catch (e) {
        gamesLedger.textContent = `Error loading games: ${e.message}`;
    }

    try {
        renderBadges(await api.playerBadges(myProfile.username));
    } catch (e) {
        badgesGrid.textContent = `Error loading trophies: ${e.message}`;
    }

    // Private - only shown on your OWN profile, never on someone else's
    // public view (who you're friends with isn't public information here).
    profileFriendsSection.hidden = !isOwnProfile;
    if (isOwnProfile) {
        try {
            renderProfileFriends(await api.friends());
        } catch (e) {
            profileFriendsList.textContent = `Error loading friends: ${e.message}`;
        }
    }
}

// Own profile only: who you've blocked, with an Unblock button each. The
// whole section stays hidden while the list is empty.
async function loadBlockedList() {
    blockedSection.hidden = true;
    let blocked;
    try {
        blocked = await api.blocks();
    } catch (e) {
        console.error('loadBlockedList failed:', e);
        return;
    }
    blockedList.innerHTML = '';
    for (const b of blocked) {
        const row = document.createElement('div');
        row.className = 'friendRow';
        const name = document.createElement('a');
        name.href = `profile.html?user=${encodeURIComponent(b.username)}`;
        name.textContent = b.username;
        const unblock = document.createElement('button');
        unblock.textContent = 'Unblock';
        unblock.addEventListener('click', async () => {
            unblock.disabled = true;
            try {
                await api.unblockPlayer(b.username);
                await loadBlockedList();
            } catch (e) {
                unblock.disabled = false;
                alert(apiErrorDetail(e));
            }
        });
        row.append(name, unblock);
        blockedList.appendChild(row);
    }
    blockedSection.hidden = blocked.length === 0;
}

onAuthChange(loadProfile);
// onAuthChange alone wouldn't re-run this for a same-page navigation
// between two ?user=... profiles (no auth state actually changes) - the
// player-search box and every ledger opponent link do a real navigation
// (window.location.href / <a href>), so a plain load is enough there too.
