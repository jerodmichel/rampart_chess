// Names for trophies and flags on a touch screen. A `title` attribute only
// ever shows on mouse hover - there's no hover on a phone - so this also
// pops a small bubble with the same text when the element is TAPPED.
//
// Desktop is left exactly as it was (native title tooltip on hover); the
// bubble only fires for pointerType 'touch'/'pen', never for a mouse click.
// Doesn't preventDefault or stop propagation, so an icon sitting inside a
// link or button (e.g. the header's account button) still does its normal
// tap action alongside showing the name.

const HIDE_AFTER_MS = 2200;

let bubble = null;
let hideTimer = null;

function hideBubble() {
    clearTimeout(hideTimer);
    if (bubble) bubble.hidden = true;
}

function showBubble(target, text) {
    if (!bubble) {
        bubble = document.createElement('div');
        bubble.id = 'tapLabelBubble';
        bubble.setAttribute('role', 'status');
        document.body.appendChild(bubble);
        // Any tap elsewhere / scroll dismisses it early. Registered once,
        // lazily, so pages that never show a bubble pay nothing.
        document.addEventListener('pointerdown', (evt) => {
            if (evt.target.closest?.('[data-tap-label]') == null) hideBubble();
        }, true);
        window.addEventListener('scroll', hideBubble, { passive: true, capture: true });
    }
    bubble.textContent = text;
    bubble.hidden = false;

    // Centered above the icon, flipped below it if there's no room, and
    // clamped so it never runs off either screen edge.
    const r = target.getBoundingClientRect();
    const b = bubble.getBoundingClientRect();
    const margin = 8;
    let left = r.left + r.width / 2 - b.width / 2;
    left = Math.max(margin, Math.min(left, window.innerWidth - b.width - margin));
    let top = r.top - b.height - 6;
    if (top < margin) top = r.bottom + 6;
    bubble.style.left = `${left}px`;
    bubble.style.top = `${top}px`;

    clearTimeout(hideTimer);
    hideTimer = setTimeout(hideBubble, HIDE_AFTER_MS);
}

// Sets `title` (desktop hover) and wires the touch bubble. Safe to call with
// empty text - it just does nothing.
export function attachTapLabel(el, text) {
    if (!text) return el;
    el.title = text;
    el.dataset.tapLabel = '1';
    el.addEventListener('pointerup', (evt) => {
        if (evt.pointerType === 'mouse') return;
        showBubble(el, text);
    });
    return el;
}
