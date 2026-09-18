// Mobile board mode is opt-in (a tapped fullscreen button, like YouTube's),
// not forced by orientation - a touch device in portrait just sees the
// ordinary page; only the live game view offers the fullscreen affordance.

const landscapeQuery = window.matchMedia('(orientation: landscape)');

// `pointer: coarse` (the standard "primary input is a finger" media
// feature) was tried first here and reverted: confirmed via live
// inspection (both a real Android phone browser and the packaged
// Capacitor app's WebView, per the user's own report of both being
// affected) that this Chrome-on-Android combination reports `pointer:
// coarse` as FALSE despite genuinely being a touchscreen - `hover: none`
// still correctly reports true there, just not `pointer`. navigator.
// maxTouchPoints doesn't share that bug (correctly non-zero in the same
// environment) and is otherwise just as reliable a "this is a touch
// device" signal - it's what every major touch-detection library falls
// back to for exactly this kind of platform inconsistency, so this uses
// it directly rather than a CSS media feature at all.
export function isTouchDevice() {
    return navigator.maxTouchPoints > 0;
}

// iPhone Safari has never implemented Element.requestFullscreen() for
// anything but <video> - not a version gap (confirmed on iOS 26.5, the
// current release at the time this was found), a permanent platform
// restriction; iPadOS Safari, notably, does support it. Where it's
// missing, #boardWrap gets a plain .fakeFullscreen class instead (see
// enterMobileFullscreen/exitMobileFullscreen below) - same landscape
// square-cell board layout (style.css matches both), just without the
// browser hiding its own chrome, since that part genuinely needs the real
// API this device doesn't have.
const supportsRealFullscreen = typeof document.documentElement.requestFullscreen === 'function';
let fakeFullscreenEl = null; // the element currently faking fullscreen, or null
const layoutModeListeners = [];

function fireLayoutModeChange() {
    for (const cb of layoutModeListeners) cb();
}

// True once fullscreen (real or faked) has actually been entered AND the
// device is actually in landscape - on Android this becomes true
// immediately after enterMobileFullscreen() resolves (the orientation lock
// forces it); on iOS (no orientation-lock support, real or faked) it only
// becomes true once the player physically rotates the phone.
export function isMobileBoardActive() {
    return (Boolean(document.fullscreenElement) || fakeFullscreenEl !== null) && landscapeQuery.matches;
}

// True while fullscreen (real or faked) has been requested but the device
// is still portrait - the signal for "show the rotate hint" rather than
// the full mobile board.
export function isAwaitingRotation() {
    return (Boolean(document.fullscreenElement) || fakeFullscreenEl !== null) && !landscapeQuery.matches;
}

// For the handful of pixel-level adjustments (see main.js's
// positionMobileCastOverlay) that only need to differ on the .fakeFullscreen
// path - real fullscreen is already tuned and shouldn't be touched by them.
export function isFakeFullscreenActive() {
    return fakeFullscreenEl !== null;
}

// `cb` fires on every fullscreenchange and every orientation flip, i.e.
// anything that could change what isMobileBoardActive()/isAwaitingRotation()
// return - the caller just re-checks those rather than being handed args.
// The .fakeFullscreen path has no native event for entering/exiting, so
// enterMobileFullscreen/exitMobileFullscreen fire these listeners by hand.
export function onLayoutModeChange(cb) {
    document.addEventListener('fullscreenchange', cb);
    landscapeQuery.addEventListener('change', cb);
    layoutModeListeners.push(cb);
}

// Requests fullscreen on `el` (the live game view container) and, where
// supported, locks the screen to landscape. The orientation lock is only
// honored by the browser while an element is actually fullscreen, and
// WebKit/iOS Safari doesn't implement it at all - both are why this is
// wrapped in try/catch and never awaited by the caller as a guarantee of
// landscape, just a best effort (isAwaitingRotation() covers the fallback).
export async function enterMobileFullscreen(el) {
    if (!supportsRealFullscreen) {
        fakeFullscreenEl = el;
        el.classList.add('fakeFullscreen');
        el.scrollTop = 0;
        fireLayoutModeChange();
        return;
    }
    if (!document.fullscreenElement) {
        await el.requestFullscreen();
    }
    // `el` (#boardWrap) scrolls internally in mobile board mode (its
    // content - belowBoard/chat/moves/liveGames - is taller than one
    // screen). Without this it keeps whatever scroll position the ordinary
    // page was at (typically scrolled well past the header/lobby to see the
    // board at all), which after entering fullscreen leaves the view
    // partway down #boardWrap's content instead of at its top - pushing the
    // board out of its ideal spot and scrolling the exit button (anchored
    // near the true top) out of sight entirely.
    el.scrollTop = 0;
    try {
        await screen.orientation.lock('landscape');
    } catch (e) {
        // Unsupported (iOS Safari) or the platform refused it - the player
        // just rotates by hand; isAwaitingRotation() drives that hint.
    }
}

export async function exitMobileFullscreen() {
    if (fakeFullscreenEl) {
        fakeFullscreenEl.classList.remove('fakeFullscreen');
        fakeFullscreenEl = null;
        fireLayoutModeChange();
        return;
    }
    if (screen.orientation && screen.orientation.unlock) {
        screen.orientation.unlock();
    }
    if (document.fullscreenElement) {
        await document.exitFullscreen();
    }
}
