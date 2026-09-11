// Shared "click to open, click anywhere else to close" dropdown behavior,
// used by the main nav (hamburger) menu and the board's display-settings
// menu, and reusable as-is on any future page (Profile, Stats) that needs
// the same nav bar.

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
}
