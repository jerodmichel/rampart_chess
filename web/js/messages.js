import { api, setTokenProvider } from './api.js';
import { getIdToken, onAuthChange } from './firebase.js';
import { initNavMenu } from './nav.js';

setTokenProvider(getIdToken);
initNavMenu();

const signedOutMessage = document.getElementById('signedOutMessage');
const messagesPage = document.getElementById('messagesPage');
const addFriendInput = document.getElementById('addFriendInput');
const addFriendBtn = document.getElementById('addFriendBtn');
const addFriendStatus = document.getElementById('addFriendStatus');
const incomingFriendRequestsList = document.getElementById('incomingFriendRequests');
const outgoingFriendRequestsList = document.getElementById('outgoingFriendRequests');
const friendsList = document.getElementById('friendsList');
const threadHeader = document.getElementById('threadHeader');
const threadMessages = document.getElementById('threadMessages');
const threadInputRow = document.getElementById('threadInputRow');
const threadInput = document.getElementById('threadInput');
const threadSendBtn = document.getElementById('threadSendBtn');

let signedIn = false;
let currentFriends = []; // last-fetched friends list, kept so openThread can re-highlight without a refetch
let activeFriend = null; // username of the friend whose thread is open, or null
let activeThreadMessages = [];

function formatTimestamp(ms) {
    if (!ms) return '';
    return new Date(ms).toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    });
}

// ---- friend requests + friends list --------------------------------------

function renderFriendRequests(incoming, outgoing) {
    incomingFriendRequestsList.innerHTML = '';
    for (const r of incoming) {
        const row = document.createElement('div');
        row.className = 'requestRow';
        const label = document.createElement('span');
        label.textContent = `${r.from_username} has sent you a friend request`;
        const acceptBtn = document.createElement('button');
        acceptBtn.textContent = 'Accept';
        acceptBtn.addEventListener('click', () => respondToFriendRequest(r.request_id, true));
        const declineBtn = document.createElement('button');
        declineBtn.textContent = 'Decline';
        declineBtn.addEventListener('click', () => respondToFriendRequest(r.request_id, false));
        row.append(label, acceptBtn, declineBtn);
        incomingFriendRequestsList.appendChild(row);
    }

    outgoingFriendRequestsList.innerHTML = '';
    for (const r of outgoing) {
        if (r.status === 'accepted') continue; // now just a friend - no lingering row needed
        const row = document.createElement('div');
        row.className = 'requestRow';
        const label = document.createElement('span');
        label.textContent = `Request to ${r.to_username} (${r.status})`;
        const dismissBtn = document.createElement('button');
        dismissBtn.textContent = '✕';
        dismissBtn.title = 'Remove this request';
        dismissBtn.addEventListener('click', () => dismissFriendRequest(r.request_id));
        row.append(label, dismissBtn);
        outgoingFriendRequestsList.appendChild(row);
    }
}

function renderFriends(friends) {
    friendsList.innerHTML = '';
    if (friends.length === 0) {
        const empty = document.createElement('p');
        empty.textContent = 'No friends yet - add one above.';
        friendsList.appendChild(empty);
        return;
    }
    for (const f of friends) {
        const row = document.createElement('div');
        row.className = 'friendRow';
        if (f.username === activeFriend) row.classList.add('active');
        const name = document.createElement('span');
        name.textContent = f.username;
        name.addEventListener('click', () => openThread(f.username));
        const profileLink = document.createElement('a');
        profileLink.href = `profile.html?user=${encodeURIComponent(f.username)}`;
        profileLink.textContent = 'Profile';
        profileLink.className = 'friendProfileLink';
        const removeBtn = document.createElement('button');
        removeBtn.textContent = 'Remove';
        removeBtn.addEventListener('click', () => removeFriend(f.username));
        row.append(name, profileLink, removeBtn);
        friendsList.appendChild(row);
    }
}

async function refreshFriends() {
    if (!signedIn) return;
    try {
        const [incoming, outgoing, friends] = await Promise.all([
            api.incomingFriendRequests(), api.outgoingFriendRequests(), api.friends(),
        ]);
        renderFriendRequests(incoming, outgoing);
        currentFriends = friends;
        renderFriends(currentFriends);
    } catch (e) { /* background poll - a transient failure just retries next tick */ }
}

addFriendBtn.addEventListener('click', async () => {
    const username = addFriendInput.value.trim();
    if (!username) return;
    try {
        await api.sendFriendRequest(username);
        addFriendInput.value = '';
        addFriendStatus.textContent = '';
        await refreshFriends();
    } catch (e) {
        addFriendStatus.textContent = e.message;
    }
});
addFriendInput.addEventListener('keydown', (evt) => {
    if (evt.key === 'Enter') addFriendBtn.click();
});

async function respondToFriendRequest(requestId, accept) {
    try {
        await (accept ? api.acceptFriendRequest(requestId) : api.declineFriendRequest(requestId));
        await refreshFriends();
    } catch (e) {
        addFriendStatus.textContent = e.message;
    }
}

async function dismissFriendRequest(requestId) {
    try {
        await api.dismissFriendRequest(requestId);
        await refreshFriends();
    } catch (e) {
        addFriendStatus.textContent = e.message;
    }
}

async function removeFriend(username) {
    try {
        await api.removeFriend(username);
        if (activeFriend === username) closeThread();
        await refreshFriends();
    } catch (e) {
        addFriendStatus.textContent = e.message;
    }
}

// ---- thread (one open conversation at a time) ----------------------------

function renderThreadMessages() {
    threadMessages.innerHTML = '';
    for (const m of activeThreadMessages) {
        const row = document.createElement('div');
        row.className = 'threadMsg';
        const meta = document.createElement('div');
        meta.className = 'threadMsgMeta';
        meta.textContent = formatTimestamp(m.timestamp);
        const text = document.createElement('div');
        text.className = 'threadMsgText';
        text.textContent = m.text;
        row.append(text, meta);
        threadMessages.appendChild(row);
    }
    threadMessages.scrollTop = threadMessages.scrollHeight;
}

async function openThread(username) {
    activeFriend = username;
    threadHeader.textContent = username;
    threadInputRow.hidden = false;
    renderFriends(currentFriends); // re-render to highlight the active row
    try {
        activeThreadMessages = await api.directMessages(username);
    } catch (e) {
        activeThreadMessages = [];
    }
    renderThreadMessages();
}

function closeThread() {
    activeFriend = null;
    activeThreadMessages = [];
    threadHeader.textContent = 'Select a friend to start messaging';
    threadInputRow.hidden = true;
    threadMessages.innerHTML = '';
}

async function sendThreadMessage() {
    const text = threadInput.value.trim();
    if (!text || !activeFriend) return;
    threadInput.value = '';
    try {
        activeThreadMessages.push(await api.sendDirectMessage(activeFriend, text));
        renderThreadMessages();
    } catch (e) {
        addFriendStatus.textContent = e.message;
    }
}

threadSendBtn.addEventListener('click', sendThreadMessage);
threadInput.addEventListener('keydown', (evt) => {
    if (evt.key === 'Enter') sendThreadMessage();
});

async function pollActiveThread() {
    if (!activeFriend) return;
    const pollingFriend = activeFriend;
    let fresh;
    try {
        fresh = await api.directMessages(pollingFriend);
    } catch (e) {
        return;
    }
    if (activeFriend !== pollingFriend) return; // switched threads while this was in flight
    if (fresh.length === activeThreadMessages.length) return;
    activeThreadMessages = fresh;
    renderThreadMessages();
}

// ---- page load --------------------------------------------------------

async function loadMessagesPage() {
    const token = await getIdToken();
    signedIn = Boolean(token);
    signedOutMessage.hidden = signedIn;
    messagesPage.hidden = !signedIn;
    if (signedIn) await refreshFriends();
}

onAuthChange(loadMessagesPage);
setInterval(refreshFriends, 5000);
setInterval(pollActiveThread, 3000);
