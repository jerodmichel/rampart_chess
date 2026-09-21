// Shared "Report this player" dialog, used from the profile page, the
// Messages thread, and the in-game chat panel. Built in JS (not per-page
// HTML) so all three stay identical, and appended to whatever is currently
// fullscreen - in mobile board mode only #boardWrap's descendants render, so
// a dialog appended to <body> would be invisible there.

import { api, apiErrorDetail } from './api.js';

const REASONS = [
    ['harassment', 'Harassment or bullying'],
    ['hate', 'Hate speech'],
    ['inappropriate_image', 'Inappropriate image or profile text'],
    ['spam', 'Spam'],
    ['cheating', 'Cheating'],
    ['other', 'Something else'],
];

function el(tag, props = {}, ...children) {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children);
    return node;
}

// Resolves { reported, blocked } when the dialog closes.
//   kind: 'profile' | 'chat' | 'dm' - what is being reported (see server/reports.py)
//   gameId: required when kind === 'chat'
export function openReportDialog({ targetUsername, kind, gameId = null }) {
    return new Promise((resolve) => {
        const host = document.fullscreenElement || document.querySelector('.fakeFullscreen') || document.body;
        const previouslyFocused = document.activeElement;

        const reasonSelect = el('select', { id: 'modReportReason' },
            el('option', { value: '', textContent: 'Choose a reason...', disabled: true, selected: true }),
            ...REASONS.map(([value, label]) => el('option', { value, textContent: label })));
        const details = el('textarea', {
            id: 'modReportDetails', maxLength: 500, rows: 3,
            placeholder: 'Anything else we should know? (optional)',
        });
        const alsoBlock = el('input', { type: 'checkbox', id: 'modReportBlock' });
        const status = el('p', { className: 'modReportStatus' });
        const submit = el('button', { type: 'button', className: 'modReportSubmit', textContent: 'Send report' });
        const cancel = el('button', { type: 'button', textContent: 'Cancel' });

        const dialog = el('div', { className: 'modReportDialog', role: 'dialog' },
            el('h3', { textContent: `Report ${targetUsername}` }),
            el('p', { className: 'modReportHint',
                textContent: 'Reports are reviewed by a person. The reported player is not told who reported them.' }),
            el('label', {}, 'Reason ', reasonSelect),
            details,
            el('label', { className: 'modReportBlockRow' }, alsoBlock, ` Also block ${targetUsername}`),
            status,
            el('div', { className: 'modReportButtons' }, submit, cancel));
        dialog.setAttribute('aria-modal', 'true');
        dialog.setAttribute('aria-label', `Report ${targetUsername}`);
        const overlay = el('div', { className: 'modReportOverlay' }, dialog);
        host.appendChild(overlay);
        reasonSelect.focus();

        let result = { reported: false, blocked: false };
        const close = () => {
            document.removeEventListener('keydown', onKey, true);
            overlay.remove();
            if (previouslyFocused && previouslyFocused.focus) previouslyFocused.focus();
            resolve(result);
        };
        const onKey = (evt) => { if (evt.key === 'Escape') close(); };
        document.addEventListener('keydown', onKey, true);
        overlay.addEventListener('click', (evt) => { if (evt.target === overlay) close(); });
        cancel.addEventListener('click', close);

        submit.addEventListener('click', async () => {
            if (!reasonSelect.value) {
                status.textContent = 'Please choose a reason.';
                return;
            }
            submit.disabled = cancel.disabled = true;
            status.textContent = 'Sending...';
            try {
                await api.reportPlayer(targetUsername, kind, reasonSelect.value, details.value.trim(), gameId);
                result.reported = true;
            } catch (e) {
                status.textContent = apiErrorDetail(e);
                submit.disabled = cancel.disabled = false;
                return;
            }
            if (alsoBlock.checked) {
                try {
                    await api.blockPlayer(targetUsername);
                    result.blocked = true;
                } catch (e) {
                    status.textContent = `Report sent, but blocking failed: ${apiErrorDetail(e)}`;
                    cancel.disabled = false;
                    cancel.textContent = 'Close';
                    return;
                }
            }
            dialog.replaceChildren(
                el('h3', { textContent: 'Thanks - report sent' }),
                el('p', { textContent: result.blocked
                    ? `We'll review it. ${targetUsername} has also been blocked.`
                    : "We'll review it." }),
                el('div', { className: 'modReportButtons' },
                    Object.assign(el('button', { type: 'button', textContent: 'Close' }), { onclick: close })));
        });
    });
}

// Plain confirm() - the same pattern the Remove-friend buttons use.
export async function confirmAndBlock(username) {
    if (!confirm(`Block ${username}? They won't be able to message, challenge, or send you friend requests, and any friendship will end. You can unblock them any time from your Profile.`)) {
        return false;
    }
    await api.blockPlayer(username);
    return true;
}
