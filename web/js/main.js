import { api, setTokenProvider } from './api.js';
import { flagNode } from './extinctStates.js';
import { highestPerCategory } from './badges.js';
import { attachTapLabel } from './taplabel.js';
import { aiOpponentName, aiOpponentAvatar } from './constants.js';
import {
    signUpWithEmail, logInWithEmail, onAuthChange, getIdToken, getAvatarUrl,
    isEmailVerified, reloadCurrentUser, resetPassword,
} from './firebase.js';
import { drawIdenticon } from './identicon.js';
import { initNavMenu, setupDropdown, keepOnScreen } from './nav.js';
import { enterMobileFullscreen, exitMobileFullscreen, onLayoutModeChange, isMobileBoardActive, isFakeFullscreenActive } from './mobile.js';
import {
    computeCellSize, boardSize, drawBoardMobile, colRowFromPointMobile, cellRect,
    triggerLightningMobile, isLightningActiveMobile,
} from './render-mobile.js';
import { renderMobilePanels, setDeckCardTapHandler } from './mobile-panels.js';
import {
    CARD_VAL, CARD_SQUARES, ROWS, COLS,
    DECK_SUIT_INDEX, boardCardSuitIndex, boardCardRankIndex,
} from './constants.js';
import {
    drawScreen, colRowFromPoint, buttonAt, deckCardAt, isPlayableSquare,
    DESIGN_WIDTH, DESIGN_HEIGHT, THEME_PRESETS, setTheme, PIECE_SET_NAMES, setPieceSet,
    triggerLightning, isLightningActive, startHourglass, stopHourglass, isHourglassActive,
    setFlipped, isFlipped,
} from './render.js';

// Every api.js request fetches a live token right before sending, rather
// than this code caching one - see api.js's setTokenProvider for why.
setTokenProvider(getIdToken);

initNavMenu();
setupDropdown(document.getElementById('displaySettingsBtn'), document.getElementById('displaySettingsDropdown'));

// On touch devices, Display Settings moves into the hamburger menu instead
// of sitting in #belowBoard - that row is already tight with Flip/Resign/
// history arrows on a narrow screen, and unlike those, Display Settings
// isn't something a player needs mid-move. Reparenting the existing node
// (rather than building a second one) keeps the setupDropdown wiring above
// working unchanged - it's keyed to these same element IDs regardless of
// which parent they end up under.
//
// (Mobile #navMenu/#displaySettings reparenting now lives in nav.js's
// initNavMenu(), called above, so it applies on every page - not just
// this one.)

const canvas = document.getElementById('boardCanvas');
const ctx = canvas.getContext('2d');
// Declared up here (rather than with the rest of the game-UI elements
// further down) because syncMobileCanvasResolution() below needs to size
// these to match the board's own width - moved early enough that they're
// already initialized by the time that function's body actually runs.
const clocksBar = document.getElementById('clocks');
const playerNamesBar = document.getElementById('playerNames');
const mobileBoardRow = document.getElementById('mobileBoardRow');

// Match the canvas's backing-store resolution to its actual on-page (CSS)
// size times the screen's pixel density, instead of a fixed DESIGN_WIDTH/
// DESIGN_HEIGHT. style.css controls the real displayed size responsively
// (#boardCanvas is width:100%/height:auto with an aspect-ratio, inside
// #boardWrap's width:1000px;max-width:100%) - a naive fix that hardcoded
// canvas.style.width/height to DESIGN_WIDTH/DESIGN_HEIGHT px (tried
// first, reverted) fought that: inline style always beats a stylesheet
// rule, so the canvas stopped shrinking to fit a narrower window at all.
// This instead reads the CSS-computed box size fresh (getBoundingClientRect)
// and only sets the backing store (canvas.width/height attributes) and the
// draw-context scale from it - never canvas.style.width/height - so
// style.css keeps sole ownership of the responsive/visible size, exactly
// as before this whole change.
//
// Every draw call in render.js still just uses DESIGN_WIDTH/DESIGN_HEIGHT
// logical coordinates - ctx.setTransform() is what maps those onto
// whatever the current backing-store resolution actually is.
//
// pageToCanvas() below (the mouse/touch hit-testing helper) had to be
// updated for this: it used to derive its scale factor from
// canvas.width/rect.width, which worked when canvas.width == DESIGN_WIDTH,
// but now that canvas.width is a devicePixelRatio-scaled physical pixel
// count, that formula silently mapped clicks into the wrong (backing-
// store) coordinate space instead of the logical DESIGN_WIDTH/
// DESIGN_HEIGHT one every hit-test helper actually works in - breaking
// every click on any screen with devicePixelRatio != 1. Fixed to scale
// against DESIGN_WIDTH/DESIGN_HEIGHT directly instead.
function syncCanvasResolution() {
    // Clears any inline pixel size (and the deck-panel-alignment offset
    // below) syncMobileCanvasResolution() may have set the last time
    // mobile board mode was active, so style.css's own width:100%/
    // aspect-ratio rule regains sole ownership here, exactly as before
    // mobile mode existed.
    canvas.style.width = '';
    canvas.style.height = '';
    canvas.style.position = '';
    canvas.style.top = '';
    playerNamesBar.style.width = '';
    playerNamesBar.style.position = '';
    playerNamesBar.style.top = '';
    clocksBar.style.width = '';
    clocksBar.style.position = '';
    clocksBar.style.top = '';
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const targetWidth = Math.round(rect.width * dpr);
    const targetHeight = Math.round(rect.height * dpr);
    if (canvas.width === targetWidth && canvas.height === targetHeight) {
        return false;  // unchanged - skip the backing-store reset (it clears the canvas)
    }
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    // Setting canvas.width/height (even to a same-valued no-op elsewhere)
    // resets the whole 2D context state - transform, imageSmoothingQuality,
    // everything - back to defaults, so both must be re-applied every time
    // this branch runs, not just once at startup.
    // targetWidth/DESIGN_WIDTH == targetHeight/DESIGN_HEIGHT (the CSS
    // aspect-ratio keeps the box proportional to the design size), so one
    // scale factor covers both axes.
    const scale = targetWidth / DESIGN_WIDTH;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.imageSmoothingQuality = 'high';
    return true;
}

// The mobile square-cell board (render-mobile.js) has no fixed aspect ratio
// to hand off to CSS the way desktop's DESIGN_WIDTH/DESIGN_HEIGHT box does -
// its whole point is filling whatever space is actually available, which
// depends on the live viewport, not a stylesheet rule. So this sets
// canvas.style.width/height directly (in real CSS px, not %) rather than
// deferring to style.css, unlike syncCanvasResolution() above.
let mobileCell = 0;

function syncMobileCanvasResolution() {
    // Reset any downward offset a previous call may have applied (see
    // bottom of this function) before measuring - otherwise
    // spaceAboveCanvas below would be measuring a position that already
    // includes last call's own adjustment, feeding into itself.
    canvas.style.top = '';
    playerNamesBar.style.top = '';
    clocksBar.style.top = '';

    // How much vertical space player-names/clocks (still their own row
    // above the canvas at this stage - see the approved mobile plan's later
    // phases for folding them into the board itself) already take up,
    // measured before this function changes the canvas's own size, so it
    // isn't measuring something that depends on the very thing being
    // computed.
    //
    // Scroll-independent on purpose: #boardWrap is a scroll container in
    // fullscreen (belowBoard/chat/moves sit under the board), and
    // getBoundingClientRect().top shrinks by however far it's scrolled -
    // a re-sync while scrolled then saw extra room above the board and
    // ballooned it. Adding scrollTop back gives the unscrolled distance.
    const spaceAboveCanvas = canvas.getBoundingClientRect().top +
        (document.getElementById('boardWrap')?.scrollTop || 0);
    const availableWidth = window.innerWidth;
    const availableHeight = Math.max(100, window.innerHeight - spaceAboveCanvas);
    const cell = computeCellSize(availableWidth, availableHeight);
    const { width, height } = boardSize(cell);
    const dpr = window.devicePixelRatio || 1;
    const targetWidth = Math.round(width * dpr);
    const targetHeight = Math.round(height * dpr);

    mobileCell = cell;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    // Matches the names/clock bars to the board's own width rather than
    // the full screen - #boardWrap:fullscreen's align-items:center already
    // shrinks these to content width by default, which pulled both names
    // together near the middle; style.css's own width:100% (used for
    // #belowBoard/#chatPanel/etc.) would swing too far the other way here,
    // stretching them across the *whole* screen including the side panels,
    // not just above the board itself where they visually belong.
    playerNamesBar.style.width = `${width}px`;
    clocksBar.style.width = `${width}px`;

    // The deck/grave side panels (the canvas's siblings in #mobileBoardRow)
    // size themselves from their own content (13 stacked deck cards), which
    // can end up taller than the canvas's own height computed above -
    // #mobileBoardRow's align-items:stretch only stretches items with an
    // auto cross-size, and the canvas has an explicit one (set just above),
    // so it doesn't grow to match a taller row; it was instead left sitting
    // at the row's top with unused space below it (device-dependent - only
    // shows up when the real screen's proportions don't happen to make
    // these two heights already match). Shifting the canvas - and the
    // names/clocks bars above it, as one unit - down by that same gap via
    // position:relative (not a size or flow change) closes it without
    // moving the side panels at all, and without disturbing next call's
    // spaceAboveCanvas measurement above (already reset before this runs).
    const rowHeight = mobileBoardRow ? mobileBoardRow.getBoundingClientRect().height : 0;
    const gap = Math.max(0, rowHeight - height - 10);
    canvas.style.position = 'relative';
    canvas.style.top = `${gap}px`;
    playerNamesBar.style.position = 'relative';
    playerNamesBar.style.top = `${gap}px`;
    clocksBar.style.position = 'relative';
    clocksBar.style.top = `${gap}px`;

    if (canvas.width === targetWidth && canvas.height === targetHeight) {
        return false;
    }
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingQuality = 'high';
    return true;
}

function syncActiveCanvasResolution() {
    return isMobileBoardActive() ? syncMobileCanvasResolution() : syncCanvasResolution();
}
syncActiveCanvasResolution();

// Re-sync (and repaint - changing canvas.width/height clears it) whenever
// the canvas's actual CSS box size changes: a window resize, but also
// anything else layout-driven (zoom, orientation change, a sidebar
// appearing) that ResizeObserver catches and a plain 'resize' listener
// wouldn't.
new ResizeObserver(() => {
    if (syncActiveCanvasResolution()) drawCanvas();
}).observe(canvas);

// The mobile fullscreen button/exit button/rotate hint themselves are pure
// CSS (see style.css's #boardWrap:fullscreen rules) - this just drives the
// actual Fullscreen/Orientation-Lock API calls behind them.
const mobileFullscreenBtn = document.getElementById('mobileFullscreenBtn');
const mobileExitFullscreenBtn = document.getElementById('mobileExitFullscreenBtn');
const boardWrap = document.getElementById('boardWrap');
mobileFullscreenBtn.addEventListener('click', () => {
    enterMobileFullscreen(boardWrap).catch(() => {});
});
mobileExitFullscreenBtn.addEventListener('click', () => {
    exitMobileFullscreen().catch(() => {});
});
onLayoutModeChange(() => {
    if (syncActiveCanvasResolution()) drawCanvas();
});

const statusLine = document.getElementById('statusLine');
const statusLineTextEl = document.getElementById('statusLineText');
const statusLineChatFlash = document.getElementById('statusLineChatFlash');
const aiColorSelect = document.getElementById('aiColorSelect');
const aiDifficultySelect = document.getElementById('aiDifficultySelect');
const newGameBtn = document.getElementById('newGameBtn');
const themeSelect = document.getElementById('themeSelect');
const pieceSetSelect = document.getElementById('pieceSetSelect');
const historyPrevBtn = document.getElementById('historyPrevBtn');
const historyFirstBtn = document.getElementById('historyFirstBtn');
const historyLastBtn = document.getElementById('historyLastBtn');
const historyNextBtn = document.getElementById('historyNextBtn');
const effectsToggle = document.getElementById('effectsToggle');
const flipBoardBtn = document.getElementById('flipBoardBtn');
const gameActions = document.getElementById('gameActions');
const quickActions = document.getElementById('quickActions');
const abortBtn = document.getElementById('abortBtn');
const resignBtn = document.getElementById('resignBtn');
const offerDrawBtn = document.getElementById('offerDrawBtn');
const acceptDrawBtn = document.getElementById('acceptDrawBtn');
const declineDrawBtn = document.getElementById('declineDrawBtn');
const whiteClockEl = document.getElementById('whiteClock');
const blackClockEl = document.getElementById('blackClock');
const whitePlayerSlot = document.getElementById('whitePlayerSlot');
const blackPlayerSlot = document.getElementById('blackPlayerSlot');
const chatPanel = document.getElementById('chatPanel');
const chatMessagesEl = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSendBtn = document.getElementById('chatSendBtn');
const movesPanel = document.getElementById('movesPanel');
const movesToggleBtn = document.getElementById('movesToggleBtn');
const movesToggleArrow = document.getElementById('movesToggleArrow');
const movesListEl = document.getElementById('movesList');

// Thunder (sound) + lightning (animation) always fire together on desktop
// (every cast trigger site calls both one line apart - see effects.py/
// main.py), so one combined toggle covers both; the hourglass "AI thinking"
// indicator is left always-on since it's an informational cue, not an
// effect. Persisted in localStorage as a per-browser display preference.
let effectsEnabled = true;
try {
    const stored = localStorage.getItem('rampart.effectsEnabled');
    if (stored !== null) effectsEnabled = stored === 'true';
} catch (_) { /* localStorage unavailable */ }
effectsToggle.checked = effectsEnabled;
effectsToggle.addEventListener('change', () => {
    effectsEnabled = effectsToggle.checked;
    try { localStorage.setItem('rampart.effectsEnabled', String(effectsEnabled)); } catch (_) { /* ignore */ }
});

const strikeSound = new Audio('assets/sounds/thunder_strike.wav');
const raiseSound = new Audio('assets/sounds/thunder_raise.mp3');
// Matches game.py's play_sound(captured) - the plain move/capture click,
// independent of (and gated by the same effectsEnabled toggle as) the
// cast thunder above.
const moveSound = new Audio('assets/sounds/move.wav');
const captureSound = new Audio('assets/sounds/capture.wav');
// A new chat message needs to get your attention even while #chatPanel is
// scrolled out of view - see flashChatIndicator() below and the
// .chatFlashIcon rules in style.css. Same effectsEnabled gate as every
// other sound above.
const chatSound = new Audio('assets/sounds/chat.wav');

function playCastSound(kind) {
    const audio = kind === 'strike' ? strikeSound : raiseSound;
    try {
        audio.currentTime = 0;
        audio.play().catch(() => {});
    } catch (_) { /* ignore */ }
}

function playMoveSound(captured) {
    const audio = captured ? captureSound : moveSound;
    try {
        audio.currentTime = 0;
        audio.play().catch(() => {});
    } catch (_) { /* ignore */ }
}

// ---- accounts -------------------------------------------------------------
//
// The browser signs in directly with Firebase Auth (see firebase.js); a
// live ID token is forwarded to server/ on every request (see
// setTokenProvider above) so it can verify who's asking
// (server/firebase_auth.py's get_current_uid) rather than trusting a
// client-supplied uid. A username
// isn't part of Firebase Auth itself, so right after sign-up (or on login,
// if a previous sign-up never finished claiming one) this also calls
// POST /auth/register to claim one via server/accounts.py.

const authPanel = document.getElementById('authPanel');
const authStatus = document.getElementById('authStatus');
const authEmail = document.getElementById('authEmail');
const authPassword = document.getElementById('authPassword');
const authUsername = document.getElementById('authUsername');
const claimUsernameBtn = document.getElementById('claimUsernameBtn');
const signUpBtn = document.getElementById('signUpBtn');
const logInBtn = document.getElementById('logInBtn');
const forgotPasswordBtn = document.getElementById('forgotPasswordBtn');
const verifyEmailBanner = document.getElementById('verifyEmailBanner');
const resendVerificationBtn = document.getElementById('resendVerificationBtn');

let currentProfile = null; // {uid, username} once signed in AND registered

// True once Firebase Auth has a signed-in user but server/ has no username
// on file for them yet - either mid sign-up, or a sign-up that got
// interrupted before the username was claimed on a previous visit.
let pendingUsernameClaim = false;

function renderAuthUI(message) {
    const signedIn = currentProfile !== null || pendingUsernameClaim;
    // Once fully signed in (a real username claimed), the whole sign-in
    // form is redundant - the header's avatar/notifications widget
    // (header.js) covers "who's signed in" and Sign Out now. Still shown
    // during pendingUsernameClaim, since that step still needs authUsername.
    authPanel.hidden = currentProfile !== null;
    authEmail.hidden = signedIn;
    authPassword.hidden = signedIn;
    signUpBtn.hidden = signedIn;
    logInBtn.hidden = signedIn;
    forgotPasswordBtn.hidden = signedIn;
    authUsername.hidden = !pendingUsernameClaim;
    claimUsernameBtn.hidden = !pendingUsernameClaim;
    challengePanel.hidden = currentProfile === null;

    // Soft nudge only - nothing server-side is gated on this (see
    // firebase.js's verifyEmailWithCode comment), just a reminder banner.
    verifyEmailBanner.hidden = !signedIn || isEmailVerified();

    if (message) {
        authStatus.textContent = message;
    } else if (pendingUsernameClaim) {
        authStatus.textContent = 'Choose a username to finish setting up your account:';
    } else {
        authStatus.textContent = '';
    }
}

// Firebase Auth errors carry a stable `.code` (e.g. "auth/weak-password");
// api.js's own errors (server/ validation, username taken, etc.) don't, but
// wrap the useful part in a "PATH failed (status): <detail>" string - strip
// that boilerplate down to just <detail> instead.
const FIREBASE_AUTH_ERRORS = {
    'auth/invalid-email': 'That doesn\'t look like a valid email address.',
    'auth/missing-password': 'Enter a password.',
    'auth/weak-password': 'Password must be at least 6 characters.',
    'auth/email-already-in-use': 'An account with that email already exists - try logging in instead.',
    'auth/user-not-found': 'Email or password is incorrect.',
    'auth/wrong-password': 'Email or password is incorrect.',
    'auth/invalid-credential': 'Email or password is incorrect.',
    'auth/too-many-requests': 'Too many attempts - please wait a moment and try again.',
};

function friendlyErrorMessage(e) {
    if (e.code && FIREBASE_AUTH_ERRORS[e.code]) return FIREBASE_AUTH_ERRORS[e.code];
    const match = e.message.match(/^\/\S+ failed \(\d+\): (.+)$/);
    return match ? match[1] : e.message;
}

async function refreshProfile() {
    // Only checking whether anyone's signed in at all here - api.js fetches
    // its own fresh token (via setTokenProvider below) on every request
    // rather than reusing whatever this returns.
    const token = await getIdToken();
    if (!token) {
        currentProfile = null;
        pendingUsernameClaim = false;
        renderAuthUI();
        return;
    }
    try {
        currentProfile = await api.me();
        pendingUsernameClaim = false;
    } catch (e) {
        currentProfile = null;
        // ONLY a 404 ("no account registered") means "signed in but hasn't
        // claimed a username" - anything else (timeout, network failure,
        // 5xx, expired token) says nothing about whether a username
        // exists, and treating it as "no username" is what kept dropping
        // already-registered users onto the choose-a-username screen.
        pendingUsernameClaim = /\(404\)/.test(e.message);
        if (!pendingUsernameClaim) {
            renderAuthUI(`Couldn't load your account (${friendlyErrorMessage(e)}). Click Log In to try again.`);
            return;
        }
    }
    renderAuthUI();
    if (currentProfile) refreshChallenges();
}

// The verification link opens in its OWN tab (verify.html), so this tab's
// cached emailVerified flag never changes on its own - re-read it from
// Firebase when the player comes back to this tab (and slowly while it
// stays open), so the banner clears without a manual refresh.
async function recheckEmailVerified() {
    if (verifyEmailBanner.hidden) return;
    if (await reloadCurrentUser()) verifyEmailBanner.hidden = true;
}
document.addEventListener('visibilitychange', () => { if (!document.hidden) recheckEmailVerified(); });
window.addEventListener('focus', recheckEmailVerified);
setInterval(() => { if (!document.hidden) recheckEmailVerified(); }, 30000);

signUpBtn.addEventListener('click', async () => {
    if (!authEmail.value || !authPassword.value) {
        renderAuthUI('Enter an email and password.');
        return;
    }
    try {
        await signUpWithEmail(authEmail.value, authPassword.value);
        api.sendVerificationEmail().catch(() => {}); // best-effort - the resend button covers a failure here
        await refreshProfile();
    } catch (e) {
        renderAuthUI(friendlyErrorMessage(e));
    }
});

forgotPasswordBtn.addEventListener('click', async () => {
    if (!authEmail.value) {
        renderAuthUI('Enter your email above first, then click "Forgot password?" again.');
        return;
    }
    try {
        await resetPassword(authEmail.value);
        renderAuthUI('Password reset email sent, if that address has an account.');
    } catch (e) {
        renderAuthUI(friendlyErrorMessage(e));
    }
});

resendVerificationBtn.addEventListener('click', async () => {
    resendVerificationBtn.disabled = true;
    try {
        await api.sendVerificationEmail();
        resendVerificationBtn.textContent = 'Sent!';
    } catch (e) {
        resendVerificationBtn.textContent = 'Resend email';
        setStatus(`Error: ${e.message}`);
    } finally {
        setTimeout(() => {
            resendVerificationBtn.disabled = false;
            resendVerificationBtn.textContent = 'Resend email';
        }, 5000);
    }
});

logInBtn.addEventListener('click', async () => {
    if (!authEmail.value || !authPassword.value) {
        renderAuthUI('Enter an email and password.');
        return;
    }
    try {
        await logInWithEmail(authEmail.value, authPassword.value);
        await refreshProfile();
    } catch (e) {
        renderAuthUI(friendlyErrorMessage(e));
    }
});

// Enter in either field logs in (not Sign Up - a plain login is the far
// more common return-key expectation, and this is the same form both
// buttons share, so Enter has to pick one).
function loginOnEnter(evt) {
    if (evt.key === 'Enter') logInBtn.click();
}
authEmail.addEventListener('keydown', loginOnEnter);
authPassword.addEventListener('keydown', loginOnEnter);

// Sign Out itself now lives in the header's avatar dropdown (header.js) -
// it does a full navigation to index.html, so there's no in-place state
// to reset here.

// Shared by both the Enter key and claimUsernameBtn - on mobile there's no
// guarantee the on-screen keyboard's return key even fires a 'keydown'
// Enter (and it wasn't obviously discoverable as the way to submit even
// when it does), so a real button is required, not just a nicety.
async function claimUsername() {
    if (!pendingUsernameClaim) return;
    if (!authUsername.value) {
        renderAuthUI('Choose a username to finish setting up your account:');
        return;
    }
    try {
        currentProfile = await api.register(authUsername.value);
        pendingUsernameClaim = false;
        renderAuthUI();
        // header.js's account widget only re-fills itself on Firebase auth
        // state changes (onAuthChange) - claiming a username here doesn't
        // touch Firebase Auth at all, so without this it stayed hidden/
        // stale until something else (e.g. a page refresh) re-fired that.
        window.dispatchEvent(new CustomEvent('rampart:profileClaimed'));
    } catch (e) {
        renderAuthUI(friendlyErrorMessage(e));
    }
}

authUsername.addEventListener('keydown', (evt) => {
    if (evt.key === 'Enter') claimUsername();
});
claimUsernameBtn.addEventListener('click', claimUsername);

// One-time corrective re-check, not a delay - loadGameFromUrl further down
// still fires its own api.getGame()/loadGame() immediately as before,
// completely untouched, so a game still loads and renders exactly as
// quickly as it did before this existed. The only thing added here is a
// follow-up: humanColor() (used by loadGame() to decide which way to
// flip the board, and by updateChatPanel()/updateMovesPanel()/
// updateGameActionButtons() to decide whether to show those side panels
// at all) needs currentProfile, which Firebase's async session restore
// doesn't guarantee is ready by the time that immediate call runs - a
// player reopening a game link (e.g. from the Profile ledger) could see
// it come back unflipped, and/or with chat/moves/resign-draw stuck
// hidden until the next real game-state change forces a fresh
// renderAll(). Re-running renderAll() on EVERY onAuthChange firing (not
// just the first) is always safe/idempotent for the panels - they're
// pure functions of server state + humanColor(), nothing to protect. A
// single "fires once" guard here was tried first and wasn't enough on a
// real phone: Firebase can call onAuthChange more than once during
// startup (e.g. once before its persisted-session check resolves), and
// on a device where that happens BEFORE the deep-linked game finishes
// loading, the old one-shot guard burned its only correction on a still-
// null state and never got to re-fire once the real profile/game were
// both actually ready - reproduced this way on a real phone even though
// the equivalent race apparently resolves fine, by luck of timing, on
// desktop. The board flip is the only piece that genuinely needs one-time
// protection (so a later auth event can't undo a manual Flip Board
// click) - tracked directly by a real click on that button instead of a
// fragile "first callback wins" assumption.
let userFlippedManually = false;
onAuthChange(async () => {
    await refreshProfile();
    if (state) {
        if (humanColor() && !userFlippedManually) setFlipped(humanColor() === 'black');
        renderAll();
    }
});

// ---- challenges (match invites) --------------------------------------
//
// No realtime push yet (that's the next phase - porting io_src_dev's
// RTDB-based move sync to be server-relayed); for now both the challenge
// list and an active human-vs-human game's moves are kept in sync with the
// other player by simple polling (see the two setInterval calls at the
// bottom of this file).

const challengePanel = document.getElementById('challengePanel');
const challengeUsernameInput = document.getElementById('challengeUsername');
const challengeColorSelect = document.getElementById('challengeColorSelect');
const challengeTimeControlSelect = document.getElementById('challengeTimeControlSelect');
const sendChallengeBtn = document.getElementById('sendChallengeBtn');
challengeUsernameInput.addEventListener('keydown', (evt) => {
    if (evt.key === 'Enter') sendChallengeBtn.click();
});
const incomingChallengesList = document.getElementById('incomingChallenges');
const outgoingChallengesList = document.getElementById('outgoingChallenges');

function renderChallenges(incoming, outgoing, gameStates = new Map()) {
    incomingChallengesList.innerHTML = '';
    for (const c of incoming) {
        const row = document.createElement('div');
        row.className = 'challengeRow';
        const yourColor = c.challenger_color === 'white' ? 'black' : 'white';
        const label = document.createElement('span');
        label.textContent = `${c.from_username} challenges you - you'd play ${yourColor}`;
        const acceptBtn = document.createElement('button');
        acceptBtn.textContent = 'Accept';
        acceptBtn.addEventListener('click', () => acceptChallenge(c.challenge_id));
        const declineBtn = document.createElement('button');
        declineBtn.textContent = 'Decline';
        declineBtn.addEventListener('click', () => declineChallengeById(c.challenge_id));
        const dismissBtn = document.createElement('button');
        dismissBtn.textContent = '✕';
        dismissBtn.title = 'Remove this challenge';
        dismissBtn.addEventListener('click', () => dismissChallengeById(c.challenge_id));
        row.append(label, acceptBtn, declineBtn, dismissBtn);
        incomingChallengesList.appendChild(row);
    }

    outgoingChallengesList.innerHTML = '';
    for (const c of outgoing) {
        const row = document.createElement('div');
        row.className = 'challengeRow';
        const label = document.createElement('span');
        label.textContent = `You challenged ${c.to_username} (${c.status})`;
        row.appendChild(label);
        if (c.status === 'accepted' && c.game_id) {
            const gameState = gameStates.get(c.game_id);
            const isOver = Boolean(gameState && gameState.result);
            const joinBtn = document.createElement('button');
            // Once the game has actually ended there's nothing left to
            // "join" - still let them open it (it already just displays
            // whatever state comes back, finished or not), but the label
            // shouldn't imply you're resuming a live game.
            joinBtn.textContent = isOver ? 'View Game' : 'Join Game';
            joinBtn.addEventListener('click', () => joinAcceptedGame(c.challenge_id, c.game_id));
            row.appendChild(joinBtn);
        }
        const dismissBtn = document.createElement('button');
        dismissBtn.textContent = '✕';
        dismissBtn.title = 'Remove this challenge';
        dismissBtn.addEventListener('click', () => dismissChallengeById(c.challenge_id));
        row.appendChild(dismissBtn);
        outgoingChallengesList.appendChild(row);
    }
}

async function refreshChallenges() {
    if (!currentProfile) return;
    try {
        const [incoming, outgoing] = await Promise.all([
            api.incomingChallenges(), api.outgoingChallenges(),
        ]);

        // For every accepted outgoing challenge, check its game's actual
        // status - dead (server restart orphaned it, self-heal by
        // dismissing, same as joinAcceptedGame's 404 handling) or finished
        // (still viewable, but "Join Game" shouldn't be offered as if
        // there's a live game to resume).
        const accepted = outgoing.filter((c) => c.status === 'accepted' && c.game_id);
        const gameStates = new Map(); // game_id -> state, or null once confirmed dead
        await Promise.all(accepted.map(async (c) => {
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
        const stillRelevant = outgoing.filter((c) => (
            c.status !== 'accepted' || !c.game_id || gameStates.get(c.game_id) !== null
        ));

        renderChallenges(incoming, stillRelevant, gameStates);
    } catch (e) { /* background poll - a transient failure just retries next tick */ }
}

async function acceptChallenge(challengeId) {
    setBusy(true);
    try {
        loadGame(await api.acceptChallenge(challengeId));
        await afterStateUpdate();
        await refreshChallenges();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

async function declineChallengeById(challengeId) {
    try {
        await api.declineChallenge(challengeId);
        await refreshChallenges();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    }
}

async function dismissChallengeById(challengeId) {
    try {
        await api.dismissChallenge(challengeId);
        await refreshChallenges();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    }
}

async function joinAcceptedGame(challengeId, joinGameId) {
    setBusy(true);
    try {
        loadGame(await api.getGame(joinGameId));
        await afterStateUpdate();
    } catch (e) {
        // server/'s game storage is in-memory only, so a server restart
        // during testing orphans every live game - self-heal by removing
        // the now-pointless challenge record rather than leaving a Join
        // Game button that 404s forever.
        if (e.message.includes('failed (404)')) {
            setStatus('That game no longer exists - removing it from your challenges.');
            await api.dismissChallenge(challengeId).catch(() => {});
            await refreshChallenges();
        } else {
            setStatus(`Error: ${e.message}`);
        }
    } finally {
        setBusy(false);
    }
}

sendChallengeBtn.addEventListener('click', async () => {
    if (!challengeUsernameInput.value) return;
    try {
        await api.createChallenge(
            challengeUsernameInput.value, challengeColorSelect.value, challengeTimeControlSelect.value);
        challengeUsernameInput.value = '';
        await refreshChallenges();
    } catch (e) {
        setStatus(friendlyErrorMessage(e));
    }
});

// ---- live games (spectating) -------------------------------------------
//
// Public - no sign-in required to watch. Opens read-only in the exact same
// board view a finished game's ledger link already uses (see loadGame/
// afterStateUpdate below) - humanColor() naturally returns null for a
// spectator, which already hides every write-capable control (moves,
// casting, resign/draw, chat).

const liveGamesList = document.getElementById('liveGamesList');

function renderLiveGames(games) {
    liveGamesList.innerHTML = '';
    if (games.length === 0) {
        const empty = document.createElement('p');
        empty.textContent = 'No live games right now.';
        liveGamesList.appendChild(empty);
        return;
    }
    for (const g of games) {
        const row = document.createElement('div');
        row.className = 'ledgerRow';
        const label = document.createElement('span');
        label.className = 'ledgerOpponent';
        label.textContent = `${g.white_username} vs ${g.black_username}`;
        const timeControl = document.createElement('span');
        timeControl.className = 'ledgerTimeControl';
        timeControl.textContent = g.time_control || '';
        const watchBtn = document.createElement('button');
        watchBtn.textContent = 'Watch';
        watchBtn.addEventListener('click', () => spectateGame(g.id));
        row.append(label, timeControl, watchBtn);
        liveGamesList.appendChild(row);
    }
}

async function refreshLiveGames() {
    try {
        renderLiveGames(await api.liveGames());
    } catch (e) { /* background poll - a transient failure just retries next tick */ }
}

async function spectateGame(watchGameId) {
    setBusy(true);
    try {
        loadGame(await api.getGame(watchGameId));
        await afterStateUpdate();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

// Matches board.py's notation convention: "++" prefixes every Raise-family
// cast (raise, raise-from-grave, raise-queen), "--" every Strike. The free
// queen placement on jack-house infiltration is a plain move (no cards, no
// cast prefix - see feedback-check-rulebook-not-just-code) so it never
// triggers thunder/lightning, which is correct: desktop doesn't either.
function castKindFromNotation(notation) {
    if (!notation) return null;
    if (notation.startsWith('++')) return 'raise';
    if (notation.startsWith('--')) return 'strike';
    // Rulebook 6.1.3's "raider enters the queen's house, queen is raised
    // in the same turn" move isn't a card-based cast move, but desktop
    // fires the same raise thunder/lightning for it regardless (see
    // main.py: both the AI's engine_move.spawn_sq branch and the human
    // click-handler's queen_house_raided branch call play_raise_sound()/
    // lightning.trigger() right after appending this exact
    // "<move>/Q@<dst>" notation shape to the log).
    if (notation.includes('/Q@')) return 'raise';
    return null;
}

THEME_PRESETS.forEach((theme, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = theme.name;
    themeSelect.appendChild(opt);
});
PIECE_SET_NAMES.forEach(({ key, label }) => {
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = label;
    pieceSetSelect.appendChild(opt);
});
themeSelect.addEventListener('change', () => {
    setTheme(Number(themeSelect.value));
    drawCanvas();
});
pieceSetSelect.addEventListener('change', () => {
    setPieceSet(pieceSetSelect.value);
    drawCanvas();
});
flipBoardBtn.addEventListener('click', () => {
    userFlippedManually = true;
    setFlipped(!isFlipped());
    drawCanvas();
});

// Preload the custom button font so the very first canvas draw doesn't
// silently fall back to the default serif before it's ready.
document.fonts.load('600 20px "Cinzel Web"').catch(() => {});

let gameId = null;
let state = null;
let selected = null;
let legalDestinations = [];
let lastMoveSquares = [];
let aiThinking = false;
let busy = false;

// Set once pollActiveGame has failed several times in a row (see
// registerPollFailure/clearPollFailures below) - surfaces the same kind of
// stall that used to freeze the board silently (see the web/js/api.js
// request timeout) as an actual on-screen message instead.
let reconnecting = false;
let pollFailureStreak = 0;
const RECONNECTING_AFTER_FAILURES = 2;
let hoverSquare = null;
let hoverButton = null;
let hoverDeckCard = null;

// Set while a raider's move into the enemy queen's house is awaiting the
// rulebook 6.1.3 "same turn" queen placement - {from: {col,row}, to:
// {col,row}} once the raider's own destination click is captured, until
// the player clicks one of queenSpawnDestinations to finish the move (or
// clicks elsewhere to cancel, discarding both - the underlying move was
// never actually submitted, matching how a committed cast can be walked
// back before its destination click).
let pendingQueenMove = null;
let queenSpawnDestinations = [];

// History-viewer state. viewIndex/viewState are null while live; browsing
// is strictly read-only (no casting/moving) and never touches `state`,
// which always stays the true live position - see GameSession.state_at.
let viewIndex = null;
let viewState = null;

// "Moves" dropdown state - moveLabels is the human-readable move list
// (api.moves), fetched lazily (only while the dropdown is actually open,
// not on every poll tick - see server/app.py's /moves endpoint comment)
// and re-fetched only when state.history has actually grown since the
// last fetch (moveLabelsForLength tracks that).
let movesOpen = false;
let moveLabels = null;
let moveLabelsForLength = -1;

// Casting state - mirrors clicker.py's clicked_cards/clicked_btn.
let clickedCards = []; // {source:'deck', color, rank} | {source:'board', col, row, rank}
let committedButton = null; // 'strike' | 'raise' | null
let castDestinations = []; // [{col, row, category, index}] once committed
let transientMessage = null; // e.g. "No eligible raider to strike."

function squaresEqual(a, b) {
    if (!a && !b) return true;
    if (!a || !b) return false;
    return a.col === b.col && a.row === b.row;
}

function deckCardsEqual(a, b) {
    if (!a && !b) return true;
    if (!a || !b) return false;
    return a.color === b.color && a.rank === b.rank;
}

// ---- notation parsing (display only - the server already applied the
// move; this just figures out which squares to highlight) ----------------

function parseSquareToken(token) {
    const m = token.match(/^(\d+)([a-f])/);
    if (!m) return null;
    const col = parseInt(m[1], 10) - 1;
    const row = 5 - (m[2].charCodeAt(0) - 'a'.charCodeAt(0));
    return [col, row];
}

function parseLastMoveSquares(notation) {
    if (!notation) return [];
    if (notation.includes('/')) {
        const spawnPart = notation.split('/')[1];
        const target = spawnPart.split('@')[1];
        const sq = target ? parseSquareToken(target) : null;
        return sq ? [sq] : [];
    }
    if (notation.includes('++') || notation.includes('--')) {
        const targetPart = notation.split('@')[1].split('(')[0];
        const sq = parseSquareToken(targetPart);
        return sq ? [sq] : [];
    }
    if (notation.includes('>')) {
        const [srcStr, dstStr] = notation.slice(1).split('>');
        const src = parseSquareToken(srcStr);
        const dst = parseSquareToken(dstStr);
        return [src, dst].filter(Boolean);
    }
    return [];
}

// The piece's own destination square for a plain move ("R6c>4f") or the
// move-part of a compound queen-placement notation ("R6c>4f/Q@3e",
// ignoring the "/Q@" spawn suffix) - null for a card-based cast notation
// ("++"/"--"), which has no such relocation at all.
function moveDestinationFromNotation(notation) {
    if (!notation || notation.startsWith('++') || notation.startsWith('--')) return null;
    const movePart = notation.split('/')[0];
    if (!movePart.includes('>')) return null;
    return parseSquareToken(movePart.slice(1).split('>')[1]);
}

// undefined (not a relocation at all) unless notation actually moved a
// piece - matches afterStateUpdate's captured===undefined "skip the
// move/capture sound entirely" gate for a pure cast move.
function capturedByNotation(priorPieces, notation) {
    const dst = moveDestinationFromNotation(notation);
    if (!dst) return undefined;
    const [col, row] = dst;
    return priorPieces.some((p) => p.col === col && p.row === row);
}

// ---- history viewer -------------------------------------------------------

function isBrowsingHistory() {
    return viewState !== null;
}

function activeState() {
    return viewState || state;
}

function historyLastMoveSquares(idx) {
    if (!state || idx <= 0) return [];
    return parseLastMoveSquares(state.history[idx - 1]);
}

function updateHistoryButtons() {
    if (!state) {
        historyFirstBtn.disabled = true;
        historyPrevBtn.disabled = true;
        historyNextBtn.disabled = true;
        historyLastBtn.disabled = true;
        return;
    }
    const total = state.history.length;
    const currentIndex = viewIndex === null ? total : viewIndex;
    historyFirstBtn.disabled = busy || currentIndex <= 0;
    historyPrevBtn.disabled = busy || currentIndex <= 0;
    historyNextBtn.disabled = busy || currentIndex >= total;
    historyLastBtn.disabled = busy || currentIndex >= total;
}

async function goToHistory(index) {
    if (!state) return;
    const total = state.history.length;
    const clamped = Math.max(0, Math.min(index, total));
    if (clamped >= total) {
        goLive();
        return;
    }
    setBusy(true);
    try {
        viewState = await api.historyAt(gameId, clamped);
        viewIndex = clamped;
        drawCanvas();
        renderMovesList(); // just re-highlights the now-active move, no fetch
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

function goLive() {
    viewState = null;
    viewIndex = null;
    drawCanvas();
    renderMovesList();
    // goToHistory() returns straight here for "the latest position"
    // without ever going through setBusy() (the only other thing that
    // refreshes these), so without this the arrows kept their stale
    // while-browsing enabled/disabled state after jumping back to live.
    updateHistoryButtons();
}

// ---- small display helpers ----------------------------------------------

function cap(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function isGameOver(s) {
    // s.result (server/game_session.py's unified summary) now covers
    // checkmate/stalemate too, not just resignation/draw - king_mated/
    // king_stalemated are kept in the response for anything that still
    // reads them directly, but this is the one place that should reflect
    // every way a game can end.
    return Boolean(s.result);
}

function humanColor() {
    if (state.ai_color) return state.ai_color === 'white' ? 'black' : 'white';
    // human-vs-human game (see challenges.py): "my" color is whichever
    // side server/ assigned my uid to, not inferred from an AI opponent.
    if (currentProfile) {
        if (state.white_uid === currentProfile.uid) return 'white';
        if (state.black_uid === currentProfile.uid) return 'black';
    }
    return null;
}

// Matches _enemy_jack_house_occupied(color) in board.py: COLOR can start
// casting once their own piece has infiltrated the enemy's jack house.
function jackHouseSquare(color) {
    return color === 'white' ? { col: 4, row: 0 } : { col: 5, row: 5 };
}

function jackHouseOccupiedBy(s, color) {
    const sq = jackHouseSquare(color);
    const piece = s.pieces.find((p) => p.col === sq.col && p.row === sq.row);
    return Boolean(piece && piece.color === color);
}

// Matches Square.is_enemy_queen_house(color) in square.py.
function queenHouseSquare(color) {
    return color === 'white' ? { col: 3, row: 0 } : { col: 6, row: 5 };
}

function queenIsDead(s, color) {
    const grave = color === 'white' ? s.white_grave : s.black_grave;
    return grave.includes('queen');
}

// Matches GameSession._queen_spawn_squares(color) - the same raise-a-
// raider zone rows used everywhere else for spawning a piece back onto
// the board.
function queenSpawnDestinationsFor(s, color) {
    const rows = color === 'white' ? [3, 4] : [1, 2];
    const dests = [];
    for (let col = 0; col < 10; col++) {
        for (const row of rows) {
            if (!s.pieces.some((p) => p.col === col && p.row === row)) dests.push([col, row]);
        }
    }
    return dests;
}

// Blackjack-style sum with ace flexibility, matching clicker.py's
// has_sum_21 (ace counts as 1, or the whole hand as 11 instead of 21 if an
// ace is present).
function handSum21(cards) {
    let total = 0;
    let hasAce = false;
    for (const c of cards) {
        total += CARD_VAL[c.rank];
        if (c.rank === 0) hasAce = true;
    }
    return total === 21 || (hasAce && total === 11);
}

// Matches board.py's board-card click gating: a card square, not a house
// row, carrying one of the current human player's own raiders.
function isBoardCardSquare(col, row) {
    if (row === 0 || row === ROWS - 1) return false;
    if (!CARD_SQUARES.has(`${col},${row}`)) return false;
    const piece = state.pieces.find((p) => p.col === col && p.row === row);
    // NB: the server's piece entries use "piece" for the type string (e.g.
    // {col, row, piece: 'raider', color}), not "name".
    return Boolean(piece && piece.piece === 'raider' && piece.color === humanColor());
}

function toggleClickedCard(card) {
    transientMessage = null;
    if (committedButton) {
        committedButton = null;
        castDestinations = [];
    }
    const idx = clickedCards.findIndex((c) => c.source === card.source &&
        c.color === card.color && c.rank === card.rank &&
        c.col === card.col && c.row === card.row);
    if (idx >= 0) {
        clickedCards.splice(idx, 1);
    } else if (clickedCards.length < 3) {
        clickedCards.push(card);
    }
    drawCanvas();
}

function cancelCasting() {
    clickedCards = [];
    committedButton = null;
    castDestinations = [];
    pendingQueenMove = null;
    queenSpawnDestinations = [];
    transientMessage = null;
    drawCanvas();
}

// ---- turning "the cards I clicked" into what the server's combo-aware
// endpoints expect ({rank, suit} using the server's own raw suit indices,
// not the display symbols) ----------------------------------------------

function toCardSpec(card) {
    if (card.source === 'deck') {
        return { rank: card.rank, suit: DECK_SUIT_INDEX[card.color] };
    }
    return { rank: card.rank, suit: boardCardSuitIndex(card.col, card.row) };
}

async function commitCastButton(button) {
    const boardCardCount = clickedCards.filter((c) => c.source === 'board').length;
    if (button === 'strike' && boardCardCount < 2) return; // has_2_raider_cards
    if (button === 'raise' && boardCardCount < 1) return; // has_board_card
    if (!handSum21(clickedCards)) return;

    setBusy(true);
    try {
        const cardSpecs = clickedCards.map(toCardSpec);
        const destinations = await api.castComboDestinations(gameId, cardSpecs, button);
        const squares = [];
        for (const category of ['strike', 'raise_raider', 'raise_queen']) {
            for (const mv of destinations[category] || []) {
                squares.push({ col: mv.to[0], row: mv.to[1], category });
            }
        }
        if (squares.length === 0) {
            committedButton = null;
            castDestinations = [];
            transientMessage = button === 'strike'
                ? 'No eligible raider to strike.'
                : 'No eligible square to raise on.';
        } else {
            committedButton = button;
            castDestinations = squares;
            transientMessage = null;
        }
        drawCanvas();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

function computeStatus(s) {
    if (isBrowsingHistory()) {
        return `Viewing move ${viewIndex} of ${state.history.length}.`;
    }
    if (s.result) {
        const { winner, reason } = s.result;
        switch (reason) {
            // Wording matches game.py's set_mated_prompt exactly (it never
            // distinguishes an ordinary checkmate from a mate by capture,
            // so neither does this) - but with a trailing period added:
            // desktop's own render of this is two blits, "White mated
            // Black" immediately followed by "-- Press "r" key to start
            // new game." on the same line, so the *combined* sentence
            // already ends in a period there. The web client never renders
            // that second half (there's no keyboard shortcut to restart),
            // so without this it was left as a permanently unterminated
            // fragment - not an intentional style match.
            case 'checkmate':
            case 'mate_by_capture':
                return `${cap(winner)} mated ${cap(winner === 'white' ? 'black' : 'white')}.`;
            case 'resignation': return `${cap(winner === 'white' ? 'black' : 'white')} resigned - ${cap(winner)} wins!`;
            case 'draw_agreement': return 'Draw by agreement.';
            case 'timeout': return `${cap(winner === 'white' ? 'black' : 'white')} ran out of time - ${cap(winner)} wins!`;
            // Matches game.py's set_repetition_prompt/is_draw_by_
            // insufficient_material wording exactly.
            case 'repetition': return 'Draw by repetition';
            case 'insufficient_material': return 'Draw by insufficient material';
            // Matches game.py's set_mated_prompt('stale-mated', ...)
            // wording exactly - stalemated_color is missing only for a
            // persisted game recorded before the server tracked it.
            case 'stalemate':
            default:
                return s.result.stalemated_color ? `${cap(s.result.stalemated_color)} stalemated` : 'Stalemate.';
        }
    }
    if (s.in_check) {
        return `${cap(s.in_check)}'s king is in check -- `;
    }
    // Below result/in_check (a known, correctly-synced fact always wins)
    // but above everything else, since a stalled poll makes every one of
    // those messages potentially stale too.
    if (reconnecting) {
        return 'Reconnecting...';
    }
    if (s.draw_offered_by && s.draw_offered_by !== humanColor()) {
        return `${cap(s.draw_offered_by)} has offered a draw.`;
    }
    if (aiThinking) {
        return `${cap(s.next_player)} (AI) is thinking...`;
    }
    if (transientMessage) {
        return transientMessage;
    }
    if (pendingQueenMove) {
        return 'Choose a tile where you want to place the queen.';
    }
    if (committedButton === 'strike') {
        return 'Choose a raider to send to the grave.';
    }
    if (committedButton === 'raise') {
        const hasQueen = castDestinations.some((d) => d.category === 'raise_queen');
        return hasQueen
            ? 'Choose a tile where you want to place the queen.'
            : 'Choose a tile where you want to place a raider.';
    }
    if (s.next_player === humanColor() && jackHouseOccupiedBy(s, s.next_player)) {
        if (clickedCards.length === 0) {
            return 'To begin casting, click on a card in your deck.';
        }
        if (handSum21(clickedCards)) {
            return 'Click one of the "strike" or "raise" buttons.';
        }
        return 'Choose cards from your deck and from the board that sum to 21.';
    }
    return `${cap(s.next_player)} to move.`;
}

// ---- canvas <-> page coordinate conversion (canvas is CSS-scaled) --------

function pageToCanvas(evt) {
    const rect = canvas.getBoundingClientRect();
    if (isMobileBoardActive()) {
        // The mobile board's logical space IS its CSS pixel size
        // (syncMobileCanvasResolution sets canvas.style.width/height to
        // exactly boardSize(mobileCell)) - normally a 1:1 scale, but still
        // computed rather than assumed so browser zoom/rounding can't drift
        // clicks off the intended square.
        const { width, height } = boardSize(mobileCell);
        return {
            x: (evt.clientX - rect.left) * (width / rect.width),
            y: (evt.clientY - rect.top) * (height / rect.height),
        };
    }
    // Maps into the fixed logical DESIGN_WIDTH/DESIGN_HEIGHT space that
    // every hit-testing helper (colRowFromPoint, buttonAt, deckCardAt - all
    // built on RWIDTH/RHEIGHT etc. from constants.js) actually works in -
    // NOT canvas.width/height, which since the devicePixelRatio fix above
    // is a physical backing-store pixel count that no longer equals
    // DESIGN_WIDTH/DESIGN_HEIGHT. Using canvas.width/rect.width here (the
    // original, pre-DPR-fix formula) silently broke every click on any
    // screen with devicePixelRatio != 1 - it mapped clicks into backing-
    // store space instead of logical space, so colRowFromPoint always
    // computed the wrong square (or none at all).
    const scaleX = DESIGN_WIDTH / rect.width;
    const scaleY = DESIGN_HEIGHT / rect.height;
    return {
        x: (evt.clientX - rect.left) * scaleX,
        y: (evt.clientY - rect.top) * scaleY,
    };
}

// Dispatches to the active renderer's own hit-testing. buttonAt/deckCardAt
// simply have no mobile equivalent yet (Strike/Raise and deck-card taps are
// a later phase - see the approved mobile plan), so they're just inert on
// a mobile board rather than a missing feature to route somewhere.
function currentColRowFromPoint(x, y) {
    return isMobileBoardActive() ? colRowFromPointMobile(x, y, mobileCell) : colRowFromPoint(x, y);
}
function currentButtonAt(x, y) {
    return isMobileBoardActive() ? null : buttonAt(x, y);
}
function currentDeckCardAt(x, y) {
    return isMobileBoardActive() ? null : deckCardAt(x, y);
}

// ---- rendering ------------------------------------------------------------

function drawCanvas() {
    const s = activeState();
    if (!s) return;
    updateNamesClocksOrder();
    const browsing = isBrowsingHistory();
    const ui = {
        selected: browsing ? null : selected,
        legalDestinations: browsing ? [] : legalDestinations,
        lastMoveSquares: browsing ? historyLastMoveSquares(viewIndex) : lastMoveSquares,
        committedButton: browsing ? null : committedButton,
        // Reuses the same cast-destination dot styling for the queen-
        // placement picker (step 2.5 in the click handler) - visually the
        // same "choose where to place a piece" action as a raise, and
        // castDestinations/pendingQueenMove are never both active at once.
        castDestinations: browsing ? [] : (pendingQueenMove
            ? queenSpawnDestinations.map(([col, row]) => ({ col, row, category: 'raise' }))
            : castDestinations),
        hoverSquare: browsing ? null : hoverSquare,
        hoverButton: browsing ? null : hoverButton,
        hoverDeckCard: browsing ? null : hoverDeckCard,
        clickedCards: browsing ? [] : clickedCards,
        aiThinking: !browsing && aiThinking,
        promptText: computeStatus(s),
        // matches game.py's in-check prompt, rendered in red instead of
        // the default white - only while it's actually the live reason
        // for the prompt (not overridden by a higher-priority message
        // computeStatus already returns first, e.g. game-over/draw-offer).
        promptColor: (!browsing && !s.result && s.in_check) ? 'rgb(255, 0, 0)' : undefined,
    };
    // render-mobile.js only draws the board itself (no decks/graves - those
    // are DOM, via renderMobilePanels below; Strike/Raise/the prompt are
    // also DOM now, via positionMobileCastOverlay), so most of `ui` above
    // is simply unused there for now; it still takes the same object so
    // this call site doesn't need two different shapes.
    if (isMobileBoardActive()) {
        drawBoardMobile(ctx, s, ui, mobileCell);
        renderMobilePanels(s, browsing ? [] : clickedCards);
        positionMobileCastOverlay();
        mobilePromptTextEl.textContent = ui.promptText;
        // Same idea as desktop's own committed-button styling (render.js's
        // button-hover/pressed treatment) - shows which of the two is
        // currently the active cast action, not just two static buttons.
        mobileStrikeBtn.classList.toggle('active', ui.committedButton === 'strike');
        mobileRaiseBtn.classList.toggle('active', ui.committedButton === 'raise');
    } else {
        drawScreen(ctx, s, ui);
    }
    // The capture-ring/move-dot/clicked-card highlights (render.js) now
    // breathe with a wall-clock pulse - keep the rAF loop below alive
    // while any of them are actually on screen, or they'd freeze at
    // whatever phase they happened to be drawn at instead of animating.
    if (!browsing && (selected || legalDestinations.length || castDestinations.length || clickedCards.length || queenSpawnDestinations.length)) {
        ensureAnimationLoop();
    }
}

// Lightning/hourglass animate off wall-clock time (see render.js), and the
// highlight pulse above does too, so all three need this redraw loop
// independent of the click/hover-driven drawCanvas() calls above; idles
// (no rAF churn) whenever none of them are active.
let animationLoopRunning = false;

// Unlike lightning (a couple hundred ms) or the hourglass (only during the
// AI's own think time), a selected piece or an in-progress cast combo can
// sit on screen indefinitely - as long as a human is thinking. Redrawing
// the whole board at full, uncapped display refresh rate (60Hz, sometimes
// 120Hz+) the entire time just to animate a slow 900ms breathing pulse
// would burn far more CPU/battery than the effect is worth, so that case
// (only that case - lightning/hourglass keep redrawing every frame) is
// capped to a much lower rate that still reads as smooth for something
// this slow.
const PULSE_FRAME_INTERVAL_MS = 1000 / 24;
let lastPulseFrameTime = 0;

function animationTick(now) {
    const pulsingHighlights = !isBrowsingHistory()
        && (selected || legalDestinations.length || castDestinations.length || clickedCards.length);
    const activeEffect = isLightningActive() || isLightningActiveMobile() || isHourglassActive();
    if (activeEffect || pulsingHighlights) {
        if (activeEffect || now - lastPulseFrameTime >= PULSE_FRAME_INTERVAL_MS) {
            drawCanvas();
            lastPulseFrameTime = now;
        }
        requestAnimationFrame(animationTick);
    } else {
        animationLoopRunning = false;
    }
}

function ensureAnimationLoop() {
    if (animationLoopRunning) return;
    animationLoopRunning = true;
    requestAnimationFrame(animationTick);
}

function setStatus(text) {
    statusLineTextEl.textContent = text;
}

function setBusy(b) {
    busy = b;
    canvas.style.cursor = b ? 'wait' : 'pointer';
    newGameBtn.disabled = b;
    updateHistoryButtons();
}

// Resign is always available (either participant, any time, regardless of
// whose turn it is); Offer Draw only makes sense between two real human
// opponents - there's no one for the AI to negotiate with.
function updateGameActionButtons() {
    if (!state || isBrowsingHistory() || isGameOver(state) || !humanColor()) {
        gameActions.hidden = true;
        abortBtn.hidden = true;
        resignBtn.hidden = true;
        return;
    }

    // Before any move, aborting (disposing of the game, no result recorded)
    // replaces resigning (which would record a loss and get saved) - see
    // server/app.py's /abort.
    const noMovesPlayed = state.history.length === 0;
    abortBtn.hidden = !noMovesPlayed;
    resignBtn.hidden = noMovesPlayed;

    const isHumanVsHuman = state.ai_color === null;

    // An AI game never has Offer Draw competing for room (there's no one
    // for the AI to negotiate with), so Resign lives next to Abort in
    // #quickActions there. Human-vs-human moves Resign into #gameActions
    // instead, alongside the draw-offer buttons - both #quickActions and
    // #gameActions sit in the same row of #belowBoard either way, this
    // only changes which of the two groups Resign visually sits with.
    const resignHome = isHumanVsHuman ? gameActions : quickActions;
    if (resignBtn.parentElement !== resignHome) {
        resignHome.insertBefore(resignBtn, resignHome.firstChild);
    }
    gameActions.hidden = !isHumanVsHuman;

    const mine = humanColor();
    const incomingOffer = isHumanVsHuman && state.draw_offered_by && state.draw_offered_by !== mine;
    const myOwnPendingOffer = isHumanVsHuman && state.draw_offered_by === mine;

    offerDrawBtn.hidden = !isHumanVsHuman || incomingOffer;
    offerDrawBtn.disabled = myOwnPendingOffer;
    offerDrawBtn.textContent = myOwnPendingOffer ? 'Draw Offered...' : 'Offer Draw';

    acceptDrawBtn.hidden = !incomingOffer;
    declineDrawBtn.hidden = !incomingOffer;
}

// ---- chat (human-vs-human games only) ----------------------------------
//
// Same participant-only gating as offer_draw/#gameActions - server/chat.py
// rejects anything else, but hiding the panel entirely for an AI game (or
// a signed-out spectator with no humanColor()) avoids ever hitting that.

let chatMessages = []; // cache of the last list fetched from the server

function renderChatMessages() {
    chatMessagesEl.innerHTML = '';
    for (const msg of chatMessages) {
        const row = document.createElement('div');
        row.className = 'chatMsg';
        const author = document.createElement('span');
        author.className = 'chatAuthor';
        author.textContent = msg.uid === currentProfile?.uid ? 'You' : msg.username;
        row.appendChild(author);
        row.appendChild(document.createTextNode(`: ${msg.text}`));
        chatMessagesEl.appendChild(row);
    }
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
}

function updateChatPanel() {
    const show = Boolean(state) && state.ai_color === null && Boolean(humanColor());
    chatPanel.hidden = !show;
}

// Unlike chat, the Moves list is useful for a vs-AI game too (reviewing
// your own game against the AI is just as valid as reviewing a human-vs-
// human one) - shown for any game the viewer is actually playing.
function updateMovesPanel() {
    const show = Boolean(state) && Boolean(humanColor());
    movesPanel.hidden = !show;
    if (!show) {
        movesOpen = false;
        movesListEl.hidden = true;
        moveLabels = null;
        moveLabelsForLength = -1;
    }
}

function renderMovesList() {
    movesListEl.innerHTML = '';
    if (!moveLabels || moveLabels.length === 0) {
        const empty = document.createElement('div');
        empty.id = 'movesEmpty';
        empty.textContent = 'No moves yet.';
        movesListEl.appendChild(empty);
        return;
    }
    // The ply currently on screen: whatever's being browsed (viewIndex),
    // or the live position otherwise - matches goToHistory's own index
    // convention (0 = start, history.length = live).
    const currentPly = viewIndex === null ? (state ? state.history.length : moveLabels.length) : viewIndex;
    for (let i = 0; i < moveLabels.length; i += 2) {
        const numEl = document.createElement('span');
        numEl.className = 'moveNum';
        numEl.textContent = `${i / 2 + 1}.`;
        movesListEl.appendChild(numEl);
        movesListEl.appendChild(makeMoveCell(moveLabels[i], i + 1, currentPly));
        if (i + 1 < moveLabels.length) {
            movesListEl.appendChild(makeMoveCell(moveLabels[i + 1], i + 2, currentPly));
        } else {
            movesListEl.appendChild(document.createElement('span')); // black hasn't moved yet this pair
        }
    }
}

function makeMoveCell(label, plyAfterThisMove, currentPly) {
    const el = document.createElement('span');
    el.className = plyAfterThisMove === currentPly ? 'moveEntry active' : 'moveEntry';
    el.textContent = label;
    el.addEventListener('click', () => goToHistory(plyAfterThisMove));
    return el;
}

// Only actually fetches while the dropdown is open (see server/app.py's
// /moves endpoint comment - it replays the whole game on every call, so
// there's no reason to pay for that on every few-second poll when the
// panel is collapsed), and only when history has actually grown since
// the last fetch.
async function refreshMovesIfOpen() {
    if (!movesOpen || !state || !gameId) return;
    if (moveLabelsForLength === state.history.length) return;
    const fetchingGameId = gameId;
    const fetchingLength = state.history.length;
    try {
        const res = await api.moves(fetchingGameId);
        if (gameId !== fetchingGameId) return; // a different game loaded meanwhile
        moveLabels = res.moves;
        moveLabelsForLength = fetchingLength;
        renderMovesList();
    } catch (e) {
        // Non-critical - leave whatever was already shown rather than
        // clobbering the main status line for a side panel's own fetch.
    }
}

movesToggleBtn.addEventListener('click', () => {
    movesOpen = !movesOpen;
    movesListEl.hidden = !movesOpen;
    movesToggleBtn.setAttribute('aria-expanded', String(movesOpen));
    movesToggleArrow.textContent = movesOpen ? '▴' : '▾';
    if (movesOpen) refreshMovesIfOpen();
});

async function sendChatMessage() {
    const text = chatInput.value.trim();
    if (!text || !gameId) return;
    chatInput.value = '';
    try {
        chatMessages.push(await api.sendChatMessage(gameId, text));
        renderChatMessages();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    }
}

chatSendBtn.addEventListener('click', sendChatMessage);
chatInput.addEventListener('keydown', (evt) => {
    if (evt.key === 'Enter') sendChatMessage();
});

let chatFlashTimer = null;

// Only one of statusLineChatFlash/mobileChatFlash is ever actually visible
// at once (whichever prompt is currently on-screen - desktop's #statusLine
// vs mobile board mode's #mobilePrompt, mutually exclusive by the same
// fullscreen mechanism that already keeps their TEXT mutually exclusive) -
// simplest to just flash both rather than re-deriving which one that is
// here too.
function flashChatIndicator() {
    try {
        chatSound.currentTime = 0;
        if (effectsEnabled) chatSound.play().catch(() => {});
    } catch (_) { /* ignore */ }
    for (const el of [statusLineChatFlash, mobileChatFlash]) {
        el.hidden = false;
        el.classList.remove('flashing');
        // Re-triggering the same animation needs a reflow in between, or
        // the browser just no-ops the re-add of a class that's already
        // there (irrelevant the FIRST time, but matters if a second
        // message arrives while the first flash is still mid-animation).
        void el.offsetWidth;
        el.classList.add('flashing');
    }
    // #chatPanel's own shown/hidden state is entirely owned by
    // updateChatPanel() - never touched here, only its border/glow, as a
    // second cue for anyone already looking right at the panel instead of
    // the status prompt. Same cast-button magenta accent, same 3-blink
    // timing as the icon above (see #chatPanel.flashing in style.css).
    chatPanel.classList.remove('flashing');
    void chatPanel.offsetWidth;
    chatPanel.classList.add('flashing');
    clearTimeout(chatFlashTimer);
    // 3 blinks * 0.5s each (see the .chatFlashIcon.flashing animation) -
    // matches its real duration rather than guessing a round number, so
    // this can't cut the last blink short or leave a dead gap after it.
    chatFlashTimer = setTimeout(() => {
        statusLineChatFlash.hidden = true;
        mobileChatFlash.hidden = true;
        chatPanel.classList.remove('flashing');
    }, 1500);
}

async function pollChat() {
    if (!gameId || !state || state.ai_color !== null || !humanColor()) return;
    const pollingGameId = gameId;
    let fresh;
    try {
        fresh = await api.chatMessages(pollingGameId);
    } catch (e) {
        return; // transient - next tick retries
    }
    if (gameId !== pollingGameId) return; // stale response - a different game loaded meanwhile
    if (fresh.length === chatMessages.length) return;
    const previousCount = chatMessages.length;
    chatMessages = fresh;
    renderChatMessages();
    // Only messages genuinely new since the last poll, and never your own
    // (sendChatMessage already pushes those locally - no need to toast
    // yourself for something you just typed).
    const newIncoming = fresh.slice(previousCount).filter((m) => m.uid !== currentProfile?.uid);
    if (newIncoming.length > 0) flashChatIndicator();
}

// ---- clocks -----------------------------------------------------------
//
// Plain numeric display for now - a placeholder for the alchemical-
// hourglass look planned for these later (see render.js's Hourglass_effect
// port, which was built for the "AI thinking" indicator but is the obvious
// starting point once that design is ready). Server is the sole time
// authority (game_session.py); this only interpolates smoothly BETWEEN
// syncs so the countdown doesn't visibly jump once per poll - see
// clockSyncedAt, set fresh every time renderAll() processes a new state.

let clockSyncedAt = null;

function formatClock(ms) {
    if (ms == null) return '--:--';
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return hours > 0 ? `${hours}:${minutes}:${seconds}` : `${minutes}:${seconds}`;
}

// Player names + clocks stay on the same physical side as that color's
// graveyard (render.js's screenSide() convention: unflipped puts black's
// stuff on the left, white's on the right) - checked on every draw (cheap
// style writes) via drawCanvas() rather than only when the Flip Board
// button is clicked, so it can never drift out of sync regardless of what
// triggered the redraw.
function updateNamesClocksOrder() {
    const blackOrder = isFlipped() ? 2 : 1;
    const whiteOrder = isFlipped() ? 1 : 2;
    blackPlayerSlot.style.order = blackOrder;
    whitePlayerSlot.style.order = whiteOrder;
    blackClockEl.style.order = blackOrder;
    whiteClockEl.style.order = whiteOrder;
}

function updateClocks() {
    if (!state || !state.time_control) {
        clocksBar.hidden = true;
        return;
    }
    clocksBar.hidden = false;
    // Frozen (no live interpolation) while over, while browsing a past
    // position, or before white's first move has actually started the
    // clock (see clock_running in game_session.py) - state itself is still
    // the live game either way, so this just stops the display from
    // ticking rather than changing what it reads.
    const frozen = isBrowsingHistory() || isGameOver(state) || clockSyncedAt === null || !state.clock_running;
    const elapsedSinceSync = frozen ? 0 : Date.now() - clockSyncedAt;
    let whiteMs = state.white_time_ms;
    let blackMs = state.black_time_ms;
    if (!frozen) {
        if (state.next_player === 'white') whiteMs = Math.max(0, whiteMs - elapsedSinceSync);
        else blackMs = Math.max(0, blackMs - elapsedSinceSync);
    }
    whiteClockEl.textContent = `White: ${formatClock(whiteMs)}`;
    blackClockEl.textContent = `Black: ${formatClock(blackMs)}`;
    whiteClockEl.classList.toggle('clockActive', !frozen && state.next_player === 'white');
    blackClockEl.classList.toggle('clockActive', !frozen && state.next_player === 'black');
}

// ---- player name/avatar/rating labels ("respective sides of the board") -
//
// Fetched once per game (usernames/ratings don't change mid-game) rather
// than on every render - see the playerLabelsForGameId guard in renderAll.
// Rating/avatar are looked up fresh via the public profile endpoint rather
// than trusting anything cached, since they can differ from what this
// client last saw. A human side is a clickable link to that player's
// profile (with their avatar); the AI side is plain text naming its
// difficulty, since there's no profile to link to.

let playerLabelsForGameId = null;

async function buildPlayerEntry(slot, username, isAiSide, difficulty) {
    slot.innerHTML = '';
    if (isAiSide) {
        // Same row layout as the human side below (.playerNameLink's flex
        // row) - just a <span>, not an <a>, since there's no profile to
        // link to.
        const row = document.createElement('span');
        row.className = 'playerNameLink';

        const avatarPath = aiOpponentAvatar(difficulty);
        if (avatarPath) {
            const avatarWrap = document.createElement('span');
            avatarWrap.className = 'playerAvatarWrap';
            const img = document.createElement('img');
            img.src = avatarPath;
            img.alt = '';
            avatarWrap.appendChild(img);
            row.appendChild(avatarWrap);
        }

        const span = document.createElement('span');
        span.className = 'playerNameText';
        const flag = flagNode('US');
        if (flag) span.append(flag, ' ');
        span.append(difficulty ? `${aiOpponentName(difficulty)} (${difficulty})` : 'Computer');
        row.appendChild(span);

        slot.appendChild(row);
        return true;
    }
    if (!username) return false;

    let profile = null;
    try {
        profile = await api.playerProfile(username);
    } catch (e) { /* fall back to a plain, avatar-less name below */ }

    const link = document.createElement('a');
    link.className = 'playerNameLink';
    link.href = `profile.html?user=${encodeURIComponent(username)}`;

    if (profile) {
        const avatarWrap = document.createElement('span');
        avatarWrap.className = 'playerAvatarWrap';
        const img = document.createElement('img');
        img.alt = '';
        img.hidden = true;
        const canvas = document.createElement('canvas');
        canvas.width = 24;
        canvas.height = 24;
        avatarWrap.append(img, canvas);
        link.appendChild(avatarWrap);

        const url = await getAvatarUrl(profile.uid);
        if (url) {
            img.src = url;
            img.hidden = false;
        } else {
            drawIdenticon(canvas, profile.uid);
        }
    }

    const textSpan = document.createElement('span');
    textSpan.className = 'playerNameText';
    const flag = flagNode(profile?.country);
    if (flag) textSpan.append(flag, ' ');
    textSpan.append(`${username} (${profile?.rating ?? 1200})`);
    link.appendChild(textSpan);

    slot.appendChild(link);

    // One trophy per category - whichever badge in that category was
    // earned most recently (see badges.js's highestPerCategory) - shown
    // in a row beneath the name. Purely decorative, so a lookup failure
    // (e.g. no account behind this username) just means no trophy row,
    // never a broken player label.
    if (profile) {
        try {
            const earned = await api.playerBadges(username);
            const trophies = highestPerCategory(earned);
            if (trophies.length) {
                const row = document.createElement('span');
                row.className = 'playerTrophyRow';
                for (const badge of trophies) {
                    const iconEl = badge.image ? document.createElement('img') : document.createElement('span');
                    iconEl.className = 'playerTrophyIcon';
                    attachTapLabel(iconEl, badge.name);
                    if (badge.image) {
                        iconEl.src = badge.image;
                        iconEl.alt = badge.name;
                    } else {
                        iconEl.textContent = badge.icon;
                    }
                    row.appendChild(iconEl);
                }
                slot.appendChild(row);
            }
        } catch (e) { /* decorative only - see comment above */ }
    }

    return true;
}

async function refreshPlayerLabels() {
    const forGameId = gameId;
    const [whiteHasContent, blackHasContent] = await Promise.all([
        buildPlayerEntry(whitePlayerSlot, state.white_username, state.ai_color === 'white', state.ai_difficulty),
        buildPlayerEntry(blackPlayerSlot, state.black_username, state.ai_color === 'black', state.ai_difficulty),
    ]);
    if (gameId !== forGameId) return; // switched games while these lookups were in flight
    playerNamesBar.hidden = !whiteHasContent && !blackHasContent;
}

function renderAll() {
    clockSyncedAt = Date.now(); // state.*_time_ms above is only ever fresh right here
    drawCanvas();
    updateHistoryButtons();
    updateGameActionButtons();
    updateChatPanel();
    updateMovesPanel();
    refreshMovesIfOpen(); // no-op unless the dropdown is open AND history actually grew
    updateClocks();
    if (gameId !== playerLabelsForGameId) {
        playerLabelsForGameId = gameId;
        if (gameId) refreshPlayerLabels(); else playerNamesBar.hidden = true;
    }
    setStatus(gameId ? '' : 'Start a new game.');
}

// ---- game flow --------------------------------------------------------

async function afterStateUpdate(notation, casterColor, captured) {
    if (notation !== undefined) lastMoveSquares = parseLastMoveSquares(notation);
    const castKind = castKindFromNotation(notation);
    if (castKind && casterColor && effectsEnabled) {
        triggerLightning(casterColor);
        triggerLightningMobile(casterColor, mobileCell);
        playCastSound(castKind);
        ensureAnimationLoop();
    }
    // Matches game.py's play_sound(captured) - fires for the underlying
    // piece relocation itself, independent of the raise effect above: a
    // queen-house-entry move (castKind 'raise' via its "/Q@" notation)
    // still moved a real raider onto an empty square first, exactly like
    // _execute_normal_move's unconditional play_sound(captured) call
    // before main.py's separate queen-spawn/lightning branch even runs.
    if (captured !== undefined && effectsEnabled) {
        playMoveSound(captured);
    }
    clickedCards = [];
    committedButton = null;
    castDestinations = [];
    transientMessage = null;
    viewState = null;
    viewIndex = null;
    renderAll();
    if (isGameOver(state)) return;
    if (state.next_player === state.ai_color) {
        await triggerAiMove();
    }
}

async function triggerAiMove() {
    aiThinking = true;
    startHourglass();
    ensureAnimationLoop();
    setBusy(true);
    drawCanvas();
    const priorPieces = state.pieces;
    try {
        const result = await api.aiMove(gameId);
        state = result;
        aiThinking = false;
        stopHourglass();
        await afterStateUpdate(result.notation, state.ai_color, capturedByNotation(priorPieces, result.notation));
    } catch (e) {
        aiThinking = false;
        stopHourglass();
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}

// Shared by startNewGame and joining a game via an accepted challenge -
// resets every piece of local UI/casting/history-view state to match a
// freshly-fetched game object before afterStateUpdate() takes over.
function loadGame(newState) {
    state = newState;
    gameId = state.id;
    selected = null;
    legalDestinations = [];
    lastMoveSquares = [];
    viewState = null;
    viewIndex = null;
    cancelCasting();
    chatMessages = [];
    chatMessagesEl.innerHTML = '';
    chatInput.value = '';
    statusLineChatFlash.hidden = true;
    mobileChatFlash.hidden = true;
    chatPanel.classList.remove('flashing');
    clearTimeout(chatFlashTimer);
    // orient the board toward whoever's actually looking at it (chess.com/
    // lichess convention) - humanColor() already resolves correctly for
    // both an AI opponent and a real human-vs-human game. A player can
    // still flip away from this via the Flip Board button afterward - a
    // fresh game always starts auto-oriented again, so a manual flip from
    // a PREVIOUS game never leaks into this one.
    userFlippedManually = false;
    setFlipped(humanColor() === 'black');
}

async function startNewGame() {
    const aiColor = aiColorSelect.value;
    const aiDifficulty = aiDifficultySelect.value;
    setBusy(true);
    setStatus('Starting new game...');
    try {
        loadGame(await api.newGame(aiColor, aiDifficulty));
        await afterStateUpdate();
    } catch (e) {
        setStatus(`Error: ${e.message} (is the server running at the configured API base URL?)`);
    } finally {
        setBusy(false);
    }
}

// ---- input --------------------------------------------------------------

canvas.addEventListener('mousemove', (evt) => {
    if (!state || isBrowsingHistory()) return;
    const { x, y } = pageToCanvas(evt);
    const newHoverButton = currentButtonAt(x, y);
    let newHoverSquare = newHoverButton ? null : currentColRowFromPoint(x, y);
    if (newHoverSquare && !isPlayableSquare(newHoverSquare.col, newHoverSquare.row)) {
        newHoverSquare = null;
    }
    const newHoverDeckCard = (newHoverButton || newHoverSquare) ? null : currentDeckCardAt(x, y);

    if (newHoverButton !== hoverButton || !squaresEqual(newHoverSquare, hoverSquare) ||
        !deckCardsEqual(newHoverDeckCard, hoverDeckCard)) {
        hoverButton = newHoverButton;
        hoverSquare = newHoverSquare;
        hoverDeckCard = newHoverDeckCard;
        drawCanvas();
    }
});

canvas.addEventListener('mouseleave', () => {
    if (hoverButton || hoverSquare || hoverDeckCard) {
        hoverButton = null;
        hoverSquare = null;
        hoverDeckCard = null;
        drawCanvas();
    }
});

// Shared by the canvas click handler's own STRIKE/RAISE hit-test (desktop)
// and #mobileStrikeBtn/#mobileRaiseBtn (mobile - real DOM buttons instead
// of a canvas hit-rect, since currentButtonAt() is deliberately a no-op in
// mobile mode).
async function handleCastButtonTap(button) {
    if (!state || isBrowsingHistory()) return;
    if (busy || isGameOver(state) || state.next_player !== humanColor()) return;
    if (committedButton === button) {
        cancelCasting();
    } else {
        await commitCastButton(button);
    }
}

// Shared by the canvas click handler's own deck-card hit-test (desktop) and
// each .mobileDeckCard's own click listener (mobile-panels.js, via
// setDeckCardTapHandler below) - currentDeckCardAt() is deliberately a
// no-op in mobile mode since the deck isn't drawn on the canvas there.
function handleDeckCardTap(deckCard) {
    if (!state || isBrowsingHistory()) return;
    if (busy || isGameOver(state) || state.next_player !== humanColor()) return;
    if (deckCard.color !== humanColor()) return; // not your deck
    const deckArray = deckCard.color === 'black' ? state.black_deck : state.white_deck;
    if (deckArray[deckCard.rank]) return; // already used
    if (!jackHouseOccupiedBy(state, deckCard.color)) return; // not eligible to cast yet
    toggleClickedCard({ source: 'deck', color: deckCard.color, rank: deckCard.rank });
}
setDeckCardTapHandler(handleDeckCardTap);

const mobileStrikeBtn = document.getElementById('mobileStrikeBtn');
const mobileRaiseBtn = document.getElementById('mobileRaiseBtn');
const mobilePrompt = document.getElementById('mobilePrompt');
const mobilePromptTextEl = document.getElementById('mobilePromptText');
const mobileChatFlash = document.getElementById('mobileChatFlash');
mobileStrikeBtn.addEventListener('click', () => handleCastButtonTap('strike'));
mobileRaiseBtn.addEventListener('click', () => handleCastButtonTap('raise'));

// Strike/Raise/the prompt live over specific unplayable house-row squares -
// bottom-left cluster (row ROWS-1) for casting, top-right cluster (row 0)
// for the prompt - rather than desktop's on-canvas buttons/text, since
// these need to be real tappable DOM here. Positioned in boardWrap-relative
// pixels (canvas.offsetLeft/Top + cellRect()'s canvas-relative rect) so
// they land exactly on top of those cells regardless of how wide the side
// panels end up being on a given device.
function positionMobileCastOverlay() {
    const ox = canvas.offsetLeft;
    const oy = canvas.offsetTop;
    // Measured fresh from the canvas's own current rendered width, rather
    // than trusting the mobileCell module variable - column-anchored
    // pieces of this overlay (the prompt, at column 5) scale visibly with
    // any mismatch between the two, while column-0-anchored ones (Strike/
    // Raise) don't (multiplying by 0 hides it) - masking a stale-cell bug
    // as "only the prompt is wrong" when it's really a shared value that's
    // out of sync with what actually got drawn.
    const cell = canvas.getBoundingClientRect().width / COLS;
    // Deliberately NOT snapped to individual cell boundaries (cellRect()
    // per-cell) - these treat the whole 5-cell cluster as one region and
    // lay out a nicer rect within it (inset margin, a real gap between
    // Strike/Raise, shorter than the full cell height), which reads much
    // better than two edge-to-edge full-cell buttons ever did.
    const inset = cell * 0.12;
    const gap = cell * 0.15;

    // Bottom-left cluster: row ROWS-1, cols 0-4.
    const clusterBL = cellRect(0, ROWS - 1, cell);
    const clusterWidth = cell * 5;
    const btnHeight = cell * 0.55;
    const btnTop = oy + clusterBL.y + (cell - btnHeight) / 2;
    // Narrower than the full available half-width each (0.65x) - the pair,
    // plus the gap between them, is then centered within the cluster
    // rather than left-aligned, so shrinking them doesn't just leave dead
    // space on the right.
    const btnWidth = (clusterWidth - inset * 2 - gap) / 2 * 0.65;
    const pairLeft = ox + clusterBL.x + inset + (clusterWidth - inset * 2 - (btnWidth * 2 + gap)) / 2;
    const btnFontSize = Math.max(9, btnHeight * 0.45);
    mobileStrikeBtn.style.left = `${pairLeft}px`;
    mobileStrikeBtn.style.top = `${btnTop}px`;
    mobileStrikeBtn.style.width = `${btnWidth}px`;
    mobileStrikeBtn.style.height = `${btnHeight}px`;
    mobileStrikeBtn.style.fontSize = `${btnFontSize}px`;
    mobileRaiseBtn.style.left = `${pairLeft + btnWidth + gap}px`;
    mobileRaiseBtn.style.top = `${btnTop}px`;
    mobileRaiseBtn.style.width = `${btnWidth}px`;
    mobileRaiseBtn.style.height = `${btnHeight}px`;
    mobileRaiseBtn.style.fontSize = `${btnFontSize}px`;

    // Top-right cluster: row 0, cols 5-9. Shifted right 30px and
    // shortened 20px (net: right edge moves right 10px) per explicit ask.
    const clusterTR = cellRect(5, 0, cell);
    // Right edge is pinned to the board's own right edge (where the
    // graveyard column starts) minus a small gap, rather than derived from
    // a width guess - the font is what flexes to fit (below), not the box.
    // The .fakeFullscreen path paints this 7px further left via a CSS
    // transform (style.css), so its layout edge sits 7px further right to
    // land the same visible gap.
    const promptLeft = clusterTR.x + inset + 28;
    const promptRightGap = isFakeFullscreenActive() ? -3 : 4;
    const promptWidth = clusterTR.x + clusterWidth - promptRightGap - promptLeft;
    mobilePrompt.style.left = `${ox + promptLeft}px`;
    mobilePrompt.style.top = `${oy + clusterTR.y + inset}px`;
    mobilePrompt.style.width = `${promptWidth}px`;
    mobilePrompt.style.height = `${cell - inset * 2}px`;
    // A fixed em size only ever happens to fit at one particular cell size
    // - computeStatus() ranges from "White to move." up to a 62-character
    // sentence, and this box is only ~5 cells wide, so the font has to
    // scale with the actual available space (like render-mobile.js's own
    // card-label text does) rather than assume one size fits every device.
    // Tuned so the longest real message wraps onto 2 lines and fits both
    // axes, not just picked to look right on one test screen.
    // The body font (Georgia -> whatever serif the device falls back to) has
    // different widths per device, so a cell-scaled size alone can't
    // guarantee the longest sentence fits 2 lines everywhere - shrink it
    // until it does, using the device's real resolved font.
    mobilePrompt.style.fontSize = `${fitPromptFontSize(promptWidth, cell - inset * 2, Math.max(9, cell * 0.28))}px`;
}

// The longest real computeStatus() message - the one the console must be
// able to show on two lines.
const PROMPT_LONGEST_MESSAGE = 'Choose cards from your deck and from the board that sum to 21.';
const PROMPT_MAX_LINES = 2;
const PROMPT_LINE_HEIGHT = 1.15; // keep in sync with style.css #mobilePrompt
let promptFitCache = { key: '', size: 0 };
let promptMeasureCtx = null;

// Largest font size <= maxSize (in 0.5px steps, floor 9) at which
// PROMPT_LONGEST_MESSAGE word-wraps into at most PROMPT_MAX_LINES lines
// inside a box of boxWidth x boxHeight (its padding/border subtracted).
// Greedy word wrap on canvas measureText - the same algorithm the browser
// uses for normal text - with a small safety margin. Cached: this runs on
// every redraw but its inputs only change with the board size.
function fitPromptFontSize(boxWidth, boxHeight, maxSize) {
    const cs = getComputedStyle(mobilePrompt);
    const key = [boxWidth.toFixed(1), boxHeight.toFixed(1), maxSize.toFixed(2), cs.fontFamily, cs.fontWeight].join('|');
    if (promptFitCache.key === key) return promptFitCache.size;

    promptMeasureCtx ??= document.createElement('canvas').getContext('2d');
    const innerWidth = boxWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) -
        parseFloat(cs.borderLeftWidth) - parseFloat(cs.borderRightWidth) - 3;
    const innerHeight = boxHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom) -
        parseFloat(cs.borderTopWidth) - parseFloat(cs.borderBottomWidth);
    const words = PROMPT_LONGEST_MESSAGE.split(' ');

    let size = maxSize;
    for (; size > 9; size -= 0.5) {
        promptMeasureCtx.font = `${cs.fontWeight} ${size}px ${cs.fontFamily}`;
        let lines = 1;
        let lineWidth = 0;
        const space = promptMeasureCtx.measureText(' ').width;
        for (const word of words) {
            const w = promptMeasureCtx.measureText(word).width;
            if (lineWidth === 0) lineWidth = w;
            else if (lineWidth + space + w <= innerWidth) lineWidth += space + w;
            else { lines++; lineWidth = w; }
        }
        if (lines <= PROMPT_MAX_LINES && lines * size * PROMPT_LINE_HEIGHT <= innerHeight) break;
    }
    size = Math.max(9, size);
    promptFitCache = { key, size };
    return size;
}

canvas.addEventListener('click', async (evt) => {
    if (!state || isBrowsingHistory()) return;
    const { x, y } = pageToCanvas(evt);

    // 1. STRIKE/RAISE button
    const button = currentButtonAt(x, y);
    if (button) {
        await handleCastButtonTap(button);
        return;
    }

    // 2. deck card - always the way a combo selection begins
    const deckCard = currentDeckCardAt(x, y);
    if (deckCard) {
        handleDeckCardTap(deckCard);
        return;
    }

    if (busy || isGameOver(state) || state.next_player !== humanColor()) return;

    const cr = currentColRowFromPoint(x, y);
    if (!cr) return;
    const { col, row } = cr;

    // 2.5. awaiting a queen placement - a highlighted spawn square finishes
    // the move that's already been provisionally chosen (see step 5 below);
    // anything else cancels back to idle without ever having submitted
    // anything (the underlying raider move was never sent to the server).
    if (pendingQueenMove) {
        const dest = queenSpawnDestinations.find(([c, r]) => c === col && r === row);
        if (dest) {
            const { from, to } = pendingQueenMove;
            const casterColor = state.pieces.find((p) => p.col === from.col && p.row === from.row)?.color;
            setBusy(true);
            try {
                const result = await api.move(gameId, from.col, from.row, to.col, to.row, col, row);
                state = result;
                pendingQueenMove = null;
                queenSpawnDestinations = [];
                // false, not derived from state: the queen's-house target
                // square is always empty (only one raider can ever occupy
                // it, permanently, per the raider-in-a-house rule), so this
                // relocation is guaranteed a plain move, never a capture -
                // matches _execute_normal_move's unconditional play_sound()
                // for this exact event on desktop.
                await afterStateUpdate(result.notation, casterColor, false);
            } catch (e) {
                setStatus(`Error: ${e.message}`);
            } finally {
                setBusy(false);
            }
        } else {
            pendingQueenMove = null;
            queenSpawnDestinations = [];
            drawCanvas();
        }
        return;
    }

    // 3. board card - only ever completes a combo already started with a
    // deck card, matching the desktop client exactly.
    if (clickedCards.length > 0 && isBoardCardSquare(col, row)) {
        toggleClickedCard({
            source: 'board', col, row, rank: boardCardRankIndex(col, row),
        });
        return;
    }

    // 4. committed to a cast - a highlighted destination executes it,
    // anything else while committed is a no-op (matches the desktop
    // client: once clicked_btn is set, board clicks only mean "choose a
    // destination").
    if (committedButton) {
        const dest = castDestinations.find((d) => d.col === col && d.row === row);
        if (dest) {
            setBusy(true);
            try {
                const cardSpecs = clickedCards.map(toCardSpec);
                const result = await api.castComboMove(gameId, cardSpecs, committedButton, col, row);
                state = result;
                cancelCasting();
                await afterStateUpdate(result.notation, humanColor());
            } catch (e) {
                setStatus(`Error: ${e.message}`);
            } finally {
                setBusy(false);
            }
        }
        return;
    }

    // 5. normal piece move/select - only reachable with no cards selected
    if (clickedCards.length > 0) return;

    if (selected) {
        const isDest = legalDestinations.some(([c, r]) => c === col && r === row);
        if (isDest) {
            const from = selected;

            // Rulebook 6.1.3: a raider landing on the enemy queen's house
            // raises the queen in the same turn - pause here for the
            // player to pick where, instead of submitting the move yet
            // (see step 2.5 above, and GameSession.apply_normal_move on
            // the server, which requires that placement atomically with
            // this exact move). Skipped if there's nowhere to place her
            // (every spawn-zone square occupied) - the move just goes
            // through as an ordinary one, matching the AI engine's own
            // fallback for that same rare edge case.
            const movingPiece = state.pieces.find((p) => p.col === from.col && p.row === from.row);
            const qHouse = movingPiece && queenHouseSquare(movingPiece.color);
            if (movingPiece && movingPiece.piece === 'raider' && qHouse
                    && qHouse.col === col && qHouse.row === row
                    && queenIsDead(state, movingPiece.color)) {
                const spawns = queenSpawnDestinationsFor(state, movingPiece.color);
                if (spawns.length) {
                    pendingQueenMove = { from, to: { col, row } };
                    queenSpawnDestinations = spawns;
                    selected = null;
                    legalDestinations = [];
                    drawCanvas();
                    return;
                }
            }

            const captured = state.pieces.some((p) => p.col === col && p.row === row);
            setBusy(true);
            try {
                const result = await api.move(gameId, from.col, from.row, col, row);
                state = result;
                selected = null;
                legalDestinations = [];
                await afterStateUpdate(result.notation, undefined, captured);
            } catch (e) {
                setStatus(`Error: ${e.message}`);
            } finally {
                setBusy(false);
            }
            return;
        }
    }

    const piece = state.pieces.find((p) => p.col === col && p.row === row);
    if (piece && piece.color === humanColor()) {
        setBusy(true);
        try {
            const res = await api.legalMoves(gameId, col, row);
            selected = res.destinations.length ? { col, row } : null;
            legalDestinations = res.destinations;
            drawCanvas();
        } catch (e) {
            setStatus(`Error: ${e.message}`);
        } finally {
            setBusy(false);
        }
    } else {
        selected = null;
        legalDestinations = [];
        drawCanvas();
    }
});

newGameBtn.addEventListener('click', () => {
    closePlayModeMenus();
    startNewGame();
});

// ---- Play vs Computer / Play vs Human dropdowns ---------------------------
// Same "click to open, click elsewhere to close" behavior as nav.js's
// setupDropdown, plus only ever one open at a time (setupDropdown's
// stopPropagation-on-trigger would otherwise leave the other one open).
const playModeMenus = [
    { btn: document.getElementById('aiMenuBtn'), panel: document.getElementById('aiMenuPanel') },
    { btn: document.getElementById('humanMenuBtn'), panel: document.getElementById('humanMenuPanel') },
];

function closePlayModeMenus(except) {
    for (const m of playModeMenus) {
        if (m === except) continue;
        m.panel.hidden = true;
        m.btn.setAttribute('aria-expanded', 'false');
    }
}

for (const m of playModeMenus) {
    m.btn.addEventListener('click', (evt) => {
        evt.stopPropagation();
        m.panel.hidden = !m.panel.hidden;
        m.btn.setAttribute('aria-expanded', String(!m.panel.hidden));
        closePlayModeMenus(m);
        if (!m.panel.hidden) keepOnScreen(m.panel);
    });
    // Picking a color/difficulty from a <select> inside the panel isn't
    // "elsewhere".
    m.panel.addEventListener('click', (evt) => evt.stopPropagation());
}
document.addEventListener('click', () => closePlayModeMenus());
document.addEventListener('keydown', (evt) => {
    if (evt.key === 'Escape') closePlayModeMenus();
});

historyPrevBtn.addEventListener('click', () => {
    if (!state || busy) return;
    const currentIndex = viewIndex === null ? state.history.length : viewIndex;
    goToHistory(currentIndex - 1);
});
historyNextBtn.addEventListener('click', () => {
    if (!state || busy) return;
    const currentIndex = viewIndex === null ? state.history.length : viewIndex;
    goToHistory(currentIndex + 1);
});
historyFirstBtn.addEventListener('click', () => {
    if (!state || busy) return;
    goToHistory(0);
});
historyLastBtn.addEventListener('click', () => {
    if (!state || busy) return;
    goToHistory(state.history.length);
});

updateHistoryButtons();

// ---- ending a game (resign / draw) ---------------------------------------

resignBtn.addEventListener('click', async () => {
    if (!state || busy) return;
    if (!confirm('Are you sure you want to resign?')) return;
    setBusy(true);
    try {
        state = await api.resign(gameId);
        cancelCasting();
        renderAll();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
});

abortBtn.addEventListener('click', async () => {
    if (!state || busy) return;
    if (!confirm("Abort this game? It hasn't started yet, so it won't be saved.")) return;
    setBusy(true);
    try {
        await api.abort(gameId);
        // The game no longer exists anywhere (session dropped, any record
        // deleted) - a full reload is the simplest way back to a clean
        // "no game" state instead of trying to unwind local UI state for a
        // game that's gone.
        window.location.href = 'index.html';
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
});

offerDrawBtn.addEventListener('click', async () => {
    if (!state || busy || offerDrawBtn.disabled) return;
    setBusy(true);
    try {
        state = await api.offerDraw(gameId);
        renderAll();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
});

async function respondToDraw(accept) {
    if (!state || busy) return;
    setBusy(true);
    try {
        state = await api.respondDraw(gameId, accept);
        cancelCasting();
        renderAll();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
}
acceptDrawBtn.addEventListener('click', () => respondToDraw(true));
declineDrawBtn.addEventListener('click', () => respondToDraw(false));

// ---- polling bridge for human-vs-human games -----------------------------
//
// Placeholder for real push-based sync (io_src_dev's move protocol, ported
// to be server-relayed - see project-rampart-browser-port memory note).
// Only ever touches human-vs-human games (ai_color === null); an AI game
// already updates its own local `state` synchronously after every move, so
// there's nothing for this to catch there.

function registerPollFailure() {
    pollFailureStreak += 1;
    if (pollFailureStreak >= RECONNECTING_AFTER_FAILURES && !reconnecting) {
        reconnecting = true;
        drawCanvas();
    }
}

function clearPollFailures() {
    const wasReconnecting = reconnecting;
    pollFailureStreak = 0;
    reconnecting = false;
    return wasReconnecting;
}

async function pollActiveGame() {
    if (!gameId || !state || busy || isBrowsingHistory()) return;
    if (state.ai_color !== null || isGameOver(state)) return;
    // Snapshot gameId - the request below can take a moment, and if the
    // user accepts/joins a *different* game while it's in flight, this
    // response describes a game that's no longer the active one at all.
    const pollingGameId = gameId;
    let fresh;
    try {
        fresh = await api.getGame(pollingGameId);
    } catch (e) {
        registerPollFailure();
        return; // transient - next tick retries
    }
    // Re-check everything after the await, not just before it - loadGame()
    // (new game / accepted challenge / joined game) may have run while this
    // request was in flight, and a stale response must never clobber it.
    if (gameId !== pollingGameId || !state || busy || isBrowsingHistory()) return;
    const wasReconnecting = clearPollFailures();

    const hasNewMove = fresh.history.length > state.history.length;
    // Resignation/draw-agreement never append to history, so they'd
    // otherwise never be noticed here at all.
    const hasNewResult = Boolean(fresh.result) && !state.result;
    const hasNewDrawOffer = fresh.draw_offered_by !== state.draw_offered_by;
    // Specifically: I had a pending offer, and it's now cleared without the
    // game ending in a draw - i.e. the opponent declined it (accepting
    // instead ends the game via a 'draw_agreement' result, already surfaced
    // by computeStatus's own s.result branch, which outranks any
    // transientMessage anyway - see below).
    const myOfferWasDeclined = state.draw_offered_by === humanColor() && !fresh.draw_offered_by && !fresh.result;
    if (!hasNewMove && !hasNewResult && !hasNewDrawOffer) {
        // Nothing changed in the game itself, but if we were showing
        // "Reconnecting..." until just now, that alone needs a redraw.
        if (wasReconnecting) drawCanvas();
        return;
    }

    const newNotation = hasNewMove ? fresh.history[fresh.history.length - 1] : undefined;
    const moverColor = state.next_player; // whoever's turn it was before this catch-up
    const captured = newNotation !== undefined ? capturedByNotation(state.pieces, newNotation) : undefined;
    state = fresh;
    await afterStateUpdate(newNotation, moverColor, captured);
    // afterStateUpdate() unconditionally clears transientMessage near its
    // own start (matching its "cleared by the next real update" contract
    // for the strike/raise "no eligible..." messages), so this has to be
    // set after it returns, not before.
    if (myOfferWasDeclined) {
        const opponentColor = humanColor() === 'white' ? 'black' : 'white';
        transientMessage = `${cap(opponentColor)} declined your draw offer.`;
        drawCanvas();
    }
}

setInterval(() => { if (currentProfile) refreshChallenges(); }, 5000);
setInterval(pollActiveGame, 3000);
setInterval(pollChat, 3000);
refreshLiveGames();
setInterval(refreshLiveGames, 8000);
setInterval(updateClocks, 250); // smooth countdown between the poll's 3s syncs

// Backgrounded tabs get their setInterval calls throttled by the browser
// (sometimes to once a minute or less), so a player who alt-tabs away while
// waiting for their opponent's move can miss several 3s poll ticks in a
// row. Firing an immediate poll the moment the tab becomes visible again
// closes that gap without changing the steady-state polling behavior at all.
document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    pollActiveGame();
    pollChat();
});

// ---- opening a game linked from the Profile page's ledger ----------------

(async function loadGameFromUrl() {
    const gameId = new URLSearchParams(window.location.search).get('game');
    if (!gameId) return;
    setBusy(true);
    try {
        loadGame(await api.getGame(gameId));
        await afterStateUpdate();
    } catch (e) {
        setStatus(`Error: ${e.message}`);
    } finally {
        setBusy(false);
    }
})();
