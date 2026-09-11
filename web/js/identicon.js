// Deterministic pixelated default avatar (GitHub-identicon style),
// generated purely client-side from a stable string (the user's uid) - no
// network or storage needed for the "no custom avatar" case, and it's
// reproducible anywhere without persisting anything.

// A simple, non-cryptographic string hash (FNV-1a) - fine for a
// deterministic visual pattern, not for anything security-relevant.
function hashString(str) {
    let hash = 0x811c9dc5;
    for (let i = 0; i < str.length; i++) {
        hash ^= str.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
    }
    return hash >>> 0;
}

// Renders a 5x5, left-right-symmetric grid into `canvas` (sized to its own
// width/height) - only the left 3 columns are drawn from the hash's bits,
// the right 2 mirror them, giving the classic identicon symmetry.
export function drawIdenticon(canvas, seedString) {
    const hash = hashString(seedString);
    const fg = `hsl(${hash % 360}, 55%, 55%)`;
    const bg = '#20211a';

    const ctx = canvas.getContext('2d');
    const size = canvas.width;
    const cells = 5;
    const cellSize = size / cells;

    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, size, size);
    ctx.fillStyle = fg;

    for (let col = 0; col < 3; col++) {
        for (let row = 0; row < cells; row++) {
            const bitIndex = col * cells + row;
            if (((hash >>> bitIndex) & 1) === 0) continue;
            ctx.fillRect(col * cellSize, row * cellSize, cellSize, cellSize);
            if (col < 2) {
                const mirrorCol = cells - 1 - col;
                ctx.fillRect(mirrorCol * cellSize, row * cellSize, cellSize, cellSize);
            }
        }
    }
}
