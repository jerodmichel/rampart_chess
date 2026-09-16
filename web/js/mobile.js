// Mobile board mode is opt-in (a tapped fullscreen button, like YouTube's),
// not forced by orientation - a touch device in portrait just sees the
// ordinary page; only the live game view offers the fullscreen affordance.

// `pointer: coarse` + `hover: none` is the standard "primary input is a
// finger" signal - true on phones and tablets of any size, false for a
// desktop window regardless of how it's resized (a mouse always reports
// pointer: fine, hover: hover), so this can't accidentally fire for someone
// just shrinking their browser.
const touchQuery = window.matchMedia('(pointer: coarse) and (hover: none)');
const landscapeQuery = window.matchMedia('(orientation: landscape)');

export function isTouchDevice() {
    return touchQuery.matches;
}

// True once fullscreen has actually been entered AND the device is actually
// in landscape - on Android this becomes true immediately after
// enterMobileFullscreen() resolves (the orientation lock forces it); on iOS
// (no orientation-lock support) it only becomes true once the player
// physically rotates the phone while fullscreen is active.
export function isMobileBoardActive() {
    return Boolean(document.fullscreenElement) && landscapeQuery.matches;
}

// True while fullscreen has been requested but the device is still
// portrait - the signal for "show the rotate hint" rather than the full
// mobile board.
export function isAwaitingRotation() {
    return Boolean(document.fullscreenElement) && !landscapeQuery.matches;
}

// `cb` fires on every fullscreenchange and every orientation flip, i.e.
// anything that could change what isMobileBoardActive()/isAwaitingRotation()
// return - the caller just re-checks those rather than being handed args.
export function onLayoutModeChange(cb) {
    document.addEventListener('fullscreenchange', cb);
    landscapeQuery.addEventListener('change', cb);
}

// Requests fullscreen on `el` (the live game view container) and, where
// supported, locks the screen to landscape. The orientation lock is only
// honored by the browser while an element is actually fullscreen, and
// WebKit/iOS Safari doesn't implement it at all - both are why this is
// wrapped in try/catch and never awaited by the caller as a guarantee of
// landscape, just a best effort (isAwaitingRotation() covers the fallback).
export async function enterMobileFullscreen(el) {
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
    if (screen.orientation && screen.orientation.unlock) {
        screen.orientation.unlock();
    }
    if (document.fullscreenElement) {
        await document.exitFullscreen();
    }
}
