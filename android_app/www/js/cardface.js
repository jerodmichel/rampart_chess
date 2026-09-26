// Card-style drawing shared by the desktop (render.js) and mobile
// (render-mobile.js) boards: a card square is drawn as a playing card lying
// on the board - slightly rounded corners, a faint printed inner frame, and
// a rank + vector suit index in the top-left corner - instead of a flat
// rectangle with rank/suit typed over it. Kept deliberately understated so
// the board still reads as a board first.
//
// Suits are Path2D outlines in a 100x100 box rather than the ♥♦♣♠ text
// glyphs, so they're identical on every platform/font and stay crisp at any
// devicePixelRatio.

function heartPath() {
    return new Path2D(
        'M50,92 C20,70 3,52 3,31 C3,15 15,5 29,5 C39,5 46,11 50,19 ' +
        'C54,11 61,5 71,5 C85,5 97,15 97,31 C97,52 80,70 50,92 Z');
}

function diamondPath() {
    return new Path2D(
        'M50,2 C58,20 72,37 88,50 C72,63 58,80 50,98 C42,80 28,63 12,50 C28,37 42,20 50,2 Z');
}

function spadePath() {
    return new Path2D(
        'M50,3 C38,22 5,38 5,60 C5,74 15,82 27,82 C36,82 43,77 47,70 ' +
        'C46,82 42,90 33,97 L67,97 C58,90 54,82 53,70 ' +
        'C57,77 64,82 73,82 C85,82 95,74 95,60 C95,38 62,22 50,3 Z');
}

function clubPath() {
    const p = new Path2D();
    for (const [cx, cy] of [[50, 27], [27, 57], [73, 57]]) {
        p.moveTo(cx + 21, cy);
        p.arc(cx, cy, 21, 0, Math.PI * 2);
    }
    p.moveTo(60, 48);
    p.arc(50, 48, 12, 0, Math.PI * 2);
    p.addPath(new Path2D('M47,55 C46,78 42,88 33,97 L67,97 C58,88 54,78 53,55 Z'));
    return p;
}

const SUIT_PATHS = {
    '♥': heartPath(),
    '♦': diamondPath(),
    '♠': spadePath(),
    '♣': clubPath(),
};

export const CARD_RED = 'rgb(200, 16, 32)';
export const CARD_BLACK = 'rgb(20, 20, 20)';

export function suitColor(suit) {
    return suit === '♥' || suit === '♦' ? CARD_RED : CARD_BLACK;
}

// Draws `suit` centered on (cx, cy), `size` px tall.
export function drawSuit(ctx, suit, cx, cy, size, color = suitColor(suit)) {
    const path = SUIT_PATHS[suit];
    if (!path) return;
    ctx.save();
    ctx.translate(cx - size / 2, cy - size / 2);
    ctx.scale(size / 100, size / 100);
    ctx.fillStyle = color;
    ctx.fill(path);
    ctx.restore();
}

export const CARD_FONT_FAMILY = '"Cinzel Web", Georgia, serif';

export function roundedRectPath(ctx, x, y, w, h, r) {
    ctx.beginPath();
    if (ctx.roundRect) {
        ctx.roundRect(x, y, w, h, r);
    } else {
        ctx.rect(x, y, w, h);
    }
}

// Card body only (rounded fill + edge + inner frame) - shared by board
// squares and deck slots, which place their own index.
export function drawCardBody(ctx, x, y, w, h, fill, { radius, frameInset } = {}) {
    const r = radius ?? Math.max(2, Math.min(w, h) * 0.07);
    ctx.save();
    roundedRectPath(ctx, x, y, w, h, r);
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.28)';
    ctx.stroke();
    const inset = frameInset ?? Math.max(2.5, Math.min(w, h) * 0.055);
    if (inset > 0) {
        roundedRectPath(ctx, x + inset, y + inset, w - inset * 2, h - inset * 2, Math.max(1, r - inset / 2));
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
        ctx.stroke();
    }
    ctx.restore();
}

// A board card square: body plus a top-left index (rank above suit).
export function drawCardSquare(ctx, x, y, w, h, fill, card, { indexScale = 0.23 } = {}) {
    drawCardBody(ctx, x, y, w, h, fill);
    const unit = Math.min(w, h);
    const fontSize = Math.max(8, Math.round(unit * indexScale));
    const pad = Math.max(3, unit * 0.1);
    const color = suitColor(card.suit);
    ctx.save();
    ctx.font = `600 ${fontSize}px ${CARD_FONT_FAMILY}`;
    ctx.fillStyle = color;
    ctx.textBaseline = 'top';
    ctx.textAlign = 'center';
    const colCenter = x + pad + fontSize * 0.42;
    ctx.fillText(card.rank, colCenter, y + pad);
    ctx.restore();
    const suitSize = fontSize * 0.8;
    drawSuit(ctx, card.suit, colCenter, y + pad + fontSize * 1.05 + suitSize / 2, suitSize, color);
}
