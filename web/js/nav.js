// Shared "click to open, click anywhere else to close" dropdown behavior,
// used by the main nav (hamburger) menu and the board's display-settings
// menu, and reusable as-is on any future page (Profile, Stats) that needs
// the same nav bar.

import { isTouchDevice } from './mobile.js';

export function setupDropdown(btn, panel) {
    btn.addEventListener('click', (evt) => {
        evt.stopPropagation();
        panel.hidden = !panel.hidden;
    });
    // A click inside the panel (picking a theme, ticking the effects
    // checkbox) shouldn't count as "elsewhere" and close it.
    panel.addEventListener('click', (evt) => evt.stopPropagation());
    document.addEventListener('click', () => { panel.hidden = true; });
}

export function initNavMenu() {
    const btn = document.getElementById('navMenuBtn');
    const dropdown = document.getElementById('navMenuDropdown');
    if (btn && dropdown) setupDropdown(btn, dropdown);

    // The mobile header layout (style.css's #navMenu grid-area rules) needs
    // #navMenu to be a direct child of <header>, not nested inside
    // #headerLeft - CSS grid-area only applies to a grid container's own
    // direct children. This has to live here (called from every page, via
    // each page's own initNavMenu() call) rather than just main.js, or
    // profile.html/messages.html/stats.html would keep the desktop header
    // structure under the mobile media query and render inconsistently.
    // #displaySettings only exists on index.html (the game view), hence
    // the extra existence check before reparenting it too.
    if (isTouchDevice()) {
        const header = document.querySelector('header');
        if (header && btn) header.appendChild(btn.closest('#navMenu'));

        const displaySettings = document.getElementById('displaySettings');
        if (dropdown && displaySettings) dropdown.appendChild(displaySettings);
    }
}
