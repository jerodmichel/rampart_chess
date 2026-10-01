// Canvas rendering of the whole game screen, at the same design resolution
// (1000x860; 1000x820 off phones, where the strip below the board is gone -
// see constants.js) and pixel positions as the pygame client's game.py (flipped
// board perspective isn't implemented yet - always drawn as white-at-bottom,
// matching Board(flipped=False)). Ported directly from game.py's
// show_bg/show_pieces/show_dead/show_dead_cards/show_cast_buttons/
// show_cast_prompt so this reads as the same game, not a re-skin.

import {
    COLS, ROWS, WIDTH, HEIGHT, RWIDTH, RHEIGHT, RAMPART_HEIGHT, DECK, GRAVES,
    CEM_HEIGHT, CWIDTH, CHEIGHT, GWIDTH, GHEIGHT,
    BOARD_X, DESIGN_WIDTH, DESIGN_HEIGHT, LEGACY_STRIP,
    RANKS, DECK_SUIT, CARD_SQUARES, CARD_TABLE, ROW_LETTERS,
} from './constants.js';
import { drawCardSquare, drawCardBody, drawSuit, roundedRectPath, CARD_FONT_FAMILY } from './cardface.js';
import { isMobileBoardActive } from './mobile.js';

// The prompt banner covers the top-right dead squares (display row 0,
// display cols 5-9) and Strike/Raise sit on the bottom-left ones (display
// row 5, cols 0-4) - the same spots the phone fullscreen board uses. Both
// are display positions, not board squares, and the board is symmetric
// under a 180 flip, so they stay on dead squares whichever way it faces.
const DEAD_W = 5 * RWIDTH - 2;          // five squares, minus the grid gap
const DEAD_H = RHEIGHT - 2;
const BOTTOM_ROW_Y = 5 * RHEIGHT + RAMPART_HEIGHT;
// 95 tall (owner, 9/26: no message needs the full square height), centered
// in the row like the Strike/Raise pair on the opposite corner.
const BANNER_H = 95;
export const BANNER_RECT = { x: BOARD_X + 5 * RWIDTH + 6, y: Math.round((DEAD_H - BANNER_H) / 2), w: DEAD_W - 12, h: BANNER_H };

export { DESIGN_WIDTH, DESIGN_HEIGHT };

// "green" theme from io_src_dev_ai/theme.py's default.
// All four theme color sets from io_src_dev_ai/config.py's _add_themes,
// ported as-is (light bg, dark bg, light trace, dark trace).
export const THEME_PRESETS = [
    { name: 'Green', bgLight: 'rgb(234, 235, 200)', bgDark: 'rgb(119, 154, 88)', traceLight: 'rgb(244, 247, 116)', traceDark: 'rgb(172, 195, 51)' },
    { name: 'Brown', bgLight: 'rgb(241, 222, 188)', bgDark: 'rgb(165, 117, 80)', traceLight: 'rgb(245, 234, 100)', traceDark: 'rgb(209, 185, 59)' },
    { name: 'Blue', bgLight: 'rgb(229, 228, 200)', bgDark: 'rgb(60, 95, 135)', traceLight: 'rgb(123, 187, 227)', traceDark: 'rgb(43, 119, 191)' },
    { name: 'Gray', bgLight: 'rgb(222, 219, 210)', bgDark: 'rgb(86, 85, 84)', traceLight: 'rgb(99, 126, 143)', traceDark: 'rgb(82, 102, 128)' },
];

let THEME = THEME_PRESETS[0];

export function setTheme(index) {
    const clamped = THEME_PRESETS[index] ? index : 0;
    THEME = THEME_PRESETS[clamped];
    emblemIdx = EMBLEM_PRESETS[clamped] ? clamped : 0;
    cardBackIdx = CARD_BACK_PRESETS[clamped] ? clamped : 0;
}

// So render-mobile.js's own board-square/highlight drawing can match
// whichever theme/piece-set the player picked in Display Settings, instead
// of hardcoding one the way the old mobile/ prototype did.
export function getActiveTheme() {
    return THEME;
}

export function getActivePieceSetKey() {
    return pieceSetKey;
}

// Card-style squares (cardface.js) vs the original flat squares with typed
// rank/suit - a Display Settings toggle so the two looks can be compared.
let cardStyle = true;

export function setCardStyle(v) {
    cardStyle = Boolean(v);
}

export function isCardStyle() {
    return cardStyle;
}

// Deck card colors: each player's deck matches their pieces - ivory cards
// with black suits for White, charcoal cards with ivory suits for Black.
// 'theme' is the original look (white's deck = card-square color, black's
// = plain-square color), kept selectable via localStorage 'rampart.deckStyle'
// in case we want to go back.
const IVORY = 'rgb(246, 242, 230)';
const DECK_STYLES = {
    charcoal: (c) => (c === 'white'
        ? { fill: IVORY, ink: 'rgb(20,20,20)' }
        : { fill: 'rgb(50, 50, 46)', ink: 'rgb(236, 230, 214)' }),
    theme: (c) => ({ fill: c === 'white' ? THEME.bgDark : THEME.bgLight, ink: 'rgb(0,0,0)' }),
};
let deckStyle = 'charcoal';

export function setDeckStyle(name) {
    deckStyle = DECK_STYLES[name] ? name : 'charcoal';
}

export function deckCardColors(colorLabel) {
    return DECK_STYLES[deckStyle](colorLabel);
}

// The pair is centered on the five bottom-left squares, both ways - at
// this height they still clear the row letter / column numbers along
// those squares' bottom edge.
const CAST_BTN_W = 150;
const CAST_BTN_H = 46;
const CAST_BTN_GAP = 16;
const CAST_BTN_X = BOARD_X + Math.round((DEAD_W - (2 * CAST_BTN_W + CAST_BTN_GAP)) / 2);
const CAST_BTN_Y = BOTTOM_ROW_Y + Math.round((DEAD_H - CAST_BTN_H) / 2);
export const STRIKE_RECT = LEGACY_STRIP
    ? { x: 102, y: 802 + RAMPART_HEIGHT, w: 100, h: 35 }
    : { x: CAST_BTN_X, y: CAST_BTN_Y, w: CAST_BTN_W, h: CAST_BTN_H };
export const RAISE_RECT = LEGACY_STRIP
    ? { x: 205, y: 802 + RAMPART_HEIGHT, w: 83, h: 35 }
    : { x: CAST_BTN_X + CAST_BTN_W + CAST_BTN_GAP, y: CAST_BTN_Y, w: CAST_BTN_W, h: CAST_BTN_H };
// Phones' original prompt spot in the strip (LEGACY_STRIP).
const PROMPT_POS = { x: 320, y: 805 + RAMPART_HEIGHT };

function inRect(x, y, r) {
    return x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
}

// ---- image loading (lazy, cached) ----------------------------------------

// A not-yet-loaded image is simply skipped when drawing; once it arrives,
// the whole canvas is redrawn from the CURRENT state via this callback
// (main.js registers it). The old approach - queueing a drawImage with the
// coordinates from the moment it was requested - painted stale pieces onto
// whatever the canvas showed by then: start a new game (or flip/resize)
// while images were still downloading and the previous board's pieces got
// stamped over the new one until the next move redrew it.
let imageLoadedCallback = null;
let imageRedrawQueued = false;
export function onImageLoaded(cb) {
    imageLoadedCallback = cb;
}
function queueImageRedraw() {
    if (imageRedrawQueued || !imageLoadedCallback) return;
    imageRedrawQueued = true;
    requestAnimationFrame(() => {
        imageRedrawQueued = false;
        imageLoadedCallback();
    });
}

// Canvas text silently falls back to Georgia until the card-index webfont
// has loaded, and nothing redraws on its own afterward - same deal as a
// late-arriving image, so reuse that redraw path.
if (document.fonts && document.fonts.load) {
    document.fonts.load(`600 20px ${CARD_FONT_FAMILY}`).then(queueImageRedraw, () => {});
    // the prompt banner's header/big-moment face (drawBanner)
    document.fonts.load('700 20px "Cinzel Decorative Web"').then(queueImageRedraw, () => {});
    // the Necromancer title (drawElectricTitle)
    document.fonts.load('400 20px "October Crow Web"').then(queueImageRedraw, () => {});
    // the Regicide title (drawBloodTitle)
    document.fonts.load('400 20px "Ghastly Panic Web"').then(queueImageRedraw, () => {});
    // the Out of Time title (drawSteelTitle)
    document.fonts.load('400 20px "Dystopian Canticle Web"').then(queueImageRedraw, () => {});
}

const images = new Map();
function loadImage(src) {
    if (!images.has(src)) {
        const img = new Image();
        img.addEventListener('load', queueImageRedraw, { once: true });
        img.src = src;
        images.set(src, img);
    }
    return images.get(src);
}

// Selectable piece styles. 'default' is the original set (back as the
// default 9/26); 'vecteezy' and 'staunton' are licensed stock art cut from
// their sheets and traced to SVG - each one's svg/ folder holds those
// masters and the PNGs here are rendered from them.
// A set flagged noFullscreen draws as 'default' on the phone fullscreen
// board (Staunton's tall pieces aren't tuned for it yet); it's checked per
// draw, so leaving fullscreen brings the chosen set straight back.
// fullscreenScale shrinks a set's pieces on that board only (render-mobile.js).
export const PIECE_SET_NAMES = [
    { key: 'default', label: 'Default' },
    { key: 'vecteezy', label: 'Icon', fullscreenScale: 0.95 },
    { key: 'staunton', label: 'Staunton', noFullscreen: true },
];

let pieceSetKey = 'default';

export function setPieceSet(key) {
    pieceSetKey = PIECE_SET_NAMES.some((s) => s.key === key) ? key : 'default';
}

function pieceSetFor() {
    const set = PIECE_SET_NAMES.find((s) => s.key === pieceSetKey);
    return (set.noFullscreen && isMobileBoardActive()) ? 'default' : pieceSetKey;
}

// For render-mobile.js: the scale of whichever set is actually drawn there
// (after any noFullscreen fallback).
export function fullscreenPieceScale() {
    const key = pieceSetFor();
    return PIECE_SET_NAMES.find((s) => s.key === key).fullscreenScale ?? 1;
}

// Exported so render-mobile.js can draw pieces without duplicating the
// image cache/bishop-override logic.
export function pieceImage(color, name) {
    return loadImage(`assets/piece_sets/${pieceSetFor()}/${color}_${name}.png`);
}

function deadPieceImage(color, name) {
    return loadImage(`assets/piece_sets/${pieceSetFor()}/dead_${color}_${name}.png`);
}

// Same path formula as deadPieceImage above, but returning the URL string
// rather than a canvas-cache Image object - for the mobile graveyard
// panels (mobile-panels.js), which are plain <img> elements the browser
// already loads/caches on its own.
export function deadPieceImageSrc(color, name) {
    return `assets/piece_sets/${pieceSetFor()}/dead_${color}_${name}.png`;
}

// Exported so render-mobile.js can draw the real rampart art too, instead
// of a flat color fill standing in for it.
export const rampartImage = loadImage('assets/misc/rampart.png');

// Card-back and emblem art ride along with the theme, like desktop's K_t
// handler (change_theme() + change_emblem() + change_dead_card() together).
// One back per theme, in THEME_PRESETS order - licensed stock card backs
// (9/26, replacing the earlier two), each cut twice from the card's middle
// band with its own frame kept on all four sides: 'strip' for the desktop
// canvas deck slot (90x25, 3x) and 'wide' for the phone fullscreen deck
// (style.css's 680:336), so neither is ever stretched.
const CARD_BACK_PRESETS = ['green', 'brown', 'blue', 'gray'].map((t) => ({
    strip: `assets/misc/card_backs/${t}_strip.png`,
    wide: `assets/misc/card_backs/${t}_wide.png`,
}));
// One per theme, in THEME_PRESETS order. Brown and Gray share the licensed
// gold-and-silver Alpha Omega (Vecteezy 2125552, cut out of its navy
// background); Blue's is traced to SVG (emblems/svg/) and squared so the
// 80x80 slot no longer squeezes it.
const EMBLEM_PRESETS = [
    'assets/misc/alpha_omega88.png',
    'assets/misc/emblems/alpha_omega_gold.png',
    'assets/misc/emblems/alpha_omega_blue.png',
    'assets/misc/emblems/alpha_omega_gold.png',
];

let cardBackIdx = 0;
let emblemIdx = 0;

function cardBackImage() {
    return loadImage(CARD_BACK_PRESETS[cardBackIdx].strip);
}

// Same card-back art as the desktop canvas's used deck slots (drawDecks
// below), in the phone fullscreen deck's shape and as a URL string - for
// mobile-panels.js's plain DOM deck rows.
export function getActiveCardBackSrc() {
    return CARD_BACK_PRESETS[cardBackIdx].wide;
}

function emblemImage() {
    return loadImage(EMBLEM_PRESETS[emblemIdx]);
}

// Same emblem the desktop canvas draws (drawEmblems below), as a URL string
// rather than a canvas-cache Image object - for the mobile side panels'
// plain <img> elements (mobile-panels.js).
export function getActiveEmblemSrc() {
    return EMBLEM_PRESETS[emblemIdx];
}

// Exported so render-mobile.js can draw rampartImage the same way. Not
// loaded yet -> skipped; loadImage's listener redraws everything once it is.
export function drawImageWhenReady(ctx, img, x, y, w, h) {
    if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, x, y, w, h);
    }
}

// ---- board flip (purely a rendering concern - board.py's own `flipped`
// flag never actually transforms move validation or coordinates either,
// see game_session.py/board.py; game.py just mirrors both axes for
// display). Every col/row -> screen-pixel conversion in this file goes
// through boardColX/rowY so nothing else needs to know about this. ---------

let boardFlipped = false;

export function setFlipped(v) {
    boardFlipped = Boolean(v);
}

export function isFlipped() {
    return boardFlipped;
}

// Row letters/column numbers anchor themselves to column 0 / row ROWS-1
// (the board's actual edges) and let this transform carry them to whichever
// screen edge that logical reference now lands on when flipped - same
// visual result as game.py's separately-coded "opposite edge" branches,
// without needing to duplicate that logic.
function boardColX(col) {
    const displayCol = boardFlipped ? COLS - 1 - col : col;
    return BOARD_X + displayCol * RWIDTH;
}

function rowY(row) {
    const displayRow = boardFlipped ? ROWS - 1 - row : row;
    return displayRow < 3 ? displayRow * RHEIGHT : displayRow * RHEIGHT + RAMPART_HEIGHT;
}

// Each color's deck/grave panel swaps to the opposite physical side of the
// screen when flipped, exactly like the board itself rotating 180 - matches
// game.py's suit/side-swap logic under self.flipped.
function screenSide(colorLabel) {
    if (!boardFlipped) return colorLabel;
    return colorLabel === 'black' ? 'white' : 'black';
}

export function colRowFromPoint(canvasX, canvasY) {
    const x = canvasX - BOARD_X;
    if (x < 0 || x >= WIDTH) return null;
    const dispCol = Math.floor(x / RWIDTH);

    let dispRow;
    if (canvasY < 3 * RHEIGHT) {
        dispRow = Math.floor(canvasY / RHEIGHT);
    } else if (canvasY < 3 * RHEIGHT + RAMPART_HEIGHT) {
        return null; // on the rampart band itself
    } else {
        dispRow = Math.floor((canvasY - RAMPART_HEIGHT) / RHEIGHT);
    }
    if (dispCol < 0 || dispCol >= COLS || dispRow < 0 || dispRow >= ROWS) return null;
    // undo the flip so callers always get real (logical) board coordinates
    const col = boardFlipped ? COLS - 1 - dispCol : dispCol;
    const row = boardFlipped ? ROWS - 1 - dispRow : dispRow;
    return { col, row };
}

// Matches game.py's set_sq_hover: on the house rows (0 and ROWS-1), only
// the K/Q/J house columns are "playable" for hover purposes - the rest of
// those two rows have no card and are never a real destination. Rows 1-4
// have no such restriction (every column there is playable, card square or
// not) - this is specifically about the house rows, not CARD_SQUARES.
export function isPlayableSquare(col, row) {
    if (row === 0) return col === 2 || col === 3 || col === 4;
    if (row === ROWS - 1) return col === 5 || col === 6 || col === 7;
    return true;
}

export function buttonAt(x, y) {
    if (inRect(x, y, STRIKE_RECT)) return 'strike';
    if (inRect(x, y, RAISE_RECT)) return 'raise';
    return null;
}

// ---- main draw ------------------------------------------------------------

export function drawScreen(ctx, state, ui) {
    ctx.clearRect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT);
    ctx.fillStyle = '#141410';
    ctx.fillRect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT);

    drawBoardSquares(ctx);
    drawRampart(ctx);
    drawCardLabels(ctx);
    drawRowLetters(ctx);
    drawColumnNumbers(ctx);
    drawBoardLighting(ctx);
    drawDecks(ctx, state);
    drawDeckHover(ctx, ui);
    drawClickedDeckCards(ctx, ui);
    drawGraves(ctx, state, ui);
    drawEmblems(ctx);
    drawHighlights(ctx, state, ui);
    drawClickedBoardCards(ctx, ui);
    drawPieces(ctx, state);
    drawCastButtons(ctx, ui);
    drawButtonHover(ctx, ui);
    if (LEGACY_STRIP) {
        if (ui.promptText) drawPrompt(ctx, ui.promptText, ui.promptColor, ui);
    } else {
        drawBanner(ctx, ui.promptInfo || { kind: 'plain', text: ui.promptText }, ui);
    }
    drawLightning(ctx); // drawn last so the glow overlays everything else
}

// Phones' original one-line prompt in the strip below the board.
function drawPrompt(ctx, text, color, ui) {
    ctx.font = 'bold 20px Georgia, serif';
    ctx.fillStyle = color || 'rgb(255,255,255)';
    ctx.textBaseline = 'top';
    ctx.fillText(text, PROMPT_POS.x, PROMPT_POS.y);
    if (ui && ui.aiThinking) {
        const width = ctx.measureText(text).width;
        drawHourglass(ctx, PROMPT_POS.x + width + 18, PROMPT_POS.y + 10, 9);
    }
}

// ---- desktop prompt banner --------------------------------------------------
//
// Owner's picks (9/26, from the Banner Type Lab): Cinzel Decorative for
// headers and big moments, Georgia bold for sentences; 20 / 15 / 45px;
// silver sweep as the shimmer. Every effect is drawn here in code - no
// images. Message kinds come from main.js's computeStatusInfo.
const BANNER_DISPLAY_FONT = '"Cinzel Decorative Web", "Cinzel Web", Georgia, serif';
const BANNER_BODY_FONT = (size) => `bold ${size}px Georgia, serif`;
const BANNER_BODY_PX = 20;
const BANNER_HEADER_PX = 15;
const BANNER_BIG_PX = 45;
const BANNER_KINDS = {
    turn:    { accent: [232, 228, 208] },
    think:   { accent: [143, 143, 132] },
    casting: { accent: [159, 43, 104], header: 'Casting', headerColor: 'rgb(228, 111, 174)' },
    check:   { accent: [255, 40, 40], header: 'Check', headerColor: 'rgb(255, 40, 40)' },
    herald:  { accent: [201, 201, 184], header: 'Herald', headerColor: 'rgb(201, 201, 184)' },
    result:  { accent: [216, 216, 207] },
    plain:   { accent: [110, 110, 100] },
};
const BANNER_FADE_MS = 280;
const BANNER_ACCENT_MS = 450;
const reducedMotion = typeof matchMedia === 'function'
    ? matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };

let bannerKey = null;
let bannerChangedAt = -Infinity;
let bannerKind = 'plain';
let accentFrom = BANNER_KINDS.plain.accent;
let accentTo = BANNER_KINDS.plain.accent;
let accentChangedAt = -Infinity;

// For main.js's redraw loop: fullRate while a message is fading in or the
// accent bar is gliding; ambient (fine at the loop's capped rate) while a
// pulse or shimmer is on screen. Phones (LEGACY_STRIP) have no banner.
export function bannerAnimationState(now = performance.now()) {
    if (LEGACY_STRIP || reducedMotion.matches) return { fullRate: false, ambient: false };
    return {
        fullRate: now - bannerChangedAt < BANNER_FADE_MS || now - accentChangedAt < BANNER_ACCENT_MS
            || Boolean(blood && blood.key === bannerKey && blood.moving),
        ambient: bannerKind === 'check' || bannerKind === 'think' || bannerKind === 'result',
    };
}

// Greedy word wrap at the largest size (maxSize down to 12px) where the
// text fits maxW x maxH in at most maxLines lines.
function fitText(ctx, text, fontFor, maxSize, maxW, maxH, maxLines) {
    const words = text.trim().split(/\s+/);
    for (let size = maxSize; size >= 12; size--) {
        ctx.font = fontFor(size);
        const lines = [];
        let line = '';
        for (const w of words) {
            const next = line ? `${line} ${w}` : w;
            if (line && ctx.measureText(next).width > maxW) {
                lines.push(line);
                line = w;
            } else {
                line = next;
            }
        }
        if (line) lines.push(line);
        const lineH = Math.round(size * 1.22);
        const fits = lines.length <= maxLines && lines.length * lineH <= maxH
            && lines.every((l) => ctx.measureText(l).width <= maxW);
        if (fits || size === 12) return { size, lines: lines.slice(0, maxLines), lineH };
    }
    return null;
}

// Canvas letterSpacing isn't everywhere yet, so space the caps by hand.
function fillSpaced(ctx, text, x, y, spacing) {
    for (const ch of text) {
        ctx.fillText(ch, x, y);
        x += ctx.measureText(ch).width + spacing;
    }
}

// A bright band sweeping left to right across [x, x + w] once per period.
function sweepGradient(ctx, x, w, now, period, base, hi) {
    const p = ((now % period) / period) * 1.6 - 0.3;
    const g = ctx.createLinearGradient(x, 0, x + w, 0);
    const stops = [[0, base], [p - 0.18, base], [p, hi], [p + 0.18, base], [1, base]]
        .filter(([o]) => o >= 0 && o <= 1)
        .sort((m, n) => m[0] - n[0]);
    for (const [o, c] of stops) g.addColorStop(o, c);
    return g;
}

function drawBanner(ctx, info, ui) {
    const r = BANNER_RECT;
    const now = performance.now();
    const still = reducedMotion.matches;
    const kind = BANNER_KINDS[info && info.kind] ? info.kind : 'plain';
    const spec = BANNER_KINDS[kind];
    const text = info ? (info.bannerText || info.text || '') : '';

    const key = `${kind}|${info && info.title}|${text}|${info && info.player}`;
    if (key !== bannerKey) {
        bannerKey = key;
        bannerChangedAt = now;
    }
    const accent = info && info.effect === 'blood' ? BLOOD_ACCENT
        : info && info.effect === 'electric' ? ELECTRIC_ACCENT
        : kind === 'result' ? STEEL_ACCENT : spec.accent;
    if (kind !== bannerKind || accent !== accentTo) {
        accentFrom = currentAccent(now);
        accentTo = accent;
        accentChangedAt = now;
        bannerKind = kind;
    }

    ctx.save();
    roundedRectPath(ctx, r.x, r.y, r.w, r.h, 4);
    ctx.fillStyle = 'rgb(52, 52, 52)';
    ctx.fill();
    ctx.strokeStyle = 'rgb(80, 80, 80)';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.clip();
    const [ar, ag, ab] = still ? accentTo : currentAccent(now);
    ctx.fillStyle = `rgb(${ar}, ${ag}, ${ab})`;
    ctx.fillRect(r.x, r.y, 5, r.h);

    if (text) {
        const t = still ? 1 : Math.min(1, (now - bannerChangedAt) / BANNER_FADE_MS);
        const ease = 1 - (1 - t) ** 3;
        ctx.globalAlpha = ease;
        ctx.translate(0, 8 * (1 - ease));
        drawBannerContent(ctx, r, kind, spec, info, text, ui, now, still);
    }
    ctx.restore();
}

function currentAccent(now) {
    const t = Math.min(1, (now - accentChangedAt) / BANNER_ACCENT_MS);
    return accentFrom.map((v, i) => Math.round(v + (accentTo[i] - v) * t));
}

function drawBannerContent(ctx, r, kind, spec, info, text, ui, now, still) {
    const left = r.x + 20;
    const right = r.x + r.w - 14;
    const areaTop = r.y + 6;
    const areaH = r.h - 12;
    ctx.textBaseline = 'middle';

    // Turn / AI thinking: just the sentence (the king icon in front of it
    // was dropped as clutter - owner, 9/29), plus the hourglass while the
    // AI thinks.
    if (kind === 'turn' || kind === 'think') {
        const tx = left;
        const hourglassW = kind === 'think' && ui && ui.aiThinking ? 30 : 0;
        const fit = fitText(ctx, text, BANNER_BODY_FONT, BANNER_BODY_PX, right - tx - hourglassW, areaH, 3);
        ctx.font = BANNER_BODY_FONT(fit.size);
        const top = areaTop + (areaH - fit.lines.length * fit.lineH) / 2;
        const widest = Math.max(...fit.lines.map((l) => ctx.measureText(l).width));
        ctx.fillStyle = kind === 'think' && !still
            ? sweepGradient(ctx, tx, widest, now, 1900, 'rgb(207, 207, 196)', 'rgb(255, 255, 255)')
            : 'rgb(255, 255, 255)';
        fit.lines.forEach((l, i) => ctx.fillText(l, tx, top + fit.lineH * (i + 0.5)));
        if (hourglassW) {
            const last = fit.lines[fit.lines.length - 1];
            drawHourglass(ctx, tx + ctx.measureText(last).width + 18, top + fit.lineH * (fit.lines.length - 0.5), 9);
        }
        return;
    }

    // Big moment: a title over the result sentence - its own effect for
    // Necromancer and Regicide, cold steel for the rest.
    if (kind === 'result') {
        const title = info.title || '';
        const titleFont = info.effect === 'electric' ? ELECTRIC_TITLE_FONT
            : info.effect === 'blood' ? bloodTitleFont
            : STEEL_TITLE_FONT;
        let big = BANNER_BIG_PX;
        ctx.font = titleFont(big);
        while (big > 24 && ctx.measureText(title).width > right - left) {
            big -= 1;
            ctx.font = titleFont(big);
        }
        const titleH = Math.round(big * 1.05);
        const fit = fitText(ctx, text, BANNER_BODY_FONT, BANNER_BODY_PX, right - left, areaH - titleH - 2, 1);
        const blockH = titleH + 2 + fit.lineH;
        const top = areaTop + (areaH - blockH) / 2;
        if (info.effect === 'electric') {
            drawElectricTitle(ctx, title, big, left, top + titleH / 2, titleH, now, still, right - left);
            ctx.font = BANNER_BODY_FONT(fit.size);
            ctx.fillStyle = 'rgb(255, 255, 255)';
            ctx.fillText(fit.lines[0], left, top + titleH + 2 + fit.lineH / 2);
            return;
        }
        if (info.effect === 'blood') {
            drawBloodTitle(ctx, r, title, big, left, top + titleH / 2, titleH, now, still, right - left);
            ctx.font = BANNER_BODY_FONT(fit.size);
            ctx.fillStyle = 'rgb(255, 255, 255)';
            ctx.fillText(fit.lines[0], left, top + titleH + 2 + fit.lineH / 2);
            return;
        }
        // Every other result (Checkmate, Out of Time, Resignation, Draw,
        // Stalemate): cold steel, centered, title and sentence both
        // (owner, 9/28; was a left-aligned silver-sweep Cinzel Decorative).
        drawSteelTitle(ctx, r, title, big, top + titleH / 2, now, still);
        ctx.font = BANNER_BODY_FONT(fit.size);
        ctx.fillStyle = 'rgb(255, 255, 255)';
        ctx.textAlign = 'center';
        ctx.fillText(fit.lines[0], r.x + r.w / 2, top + titleH + 2 + fit.lineH / 2);
        ctx.textAlign = 'left';
        return;
    }

    // Casting / Check / Herald: small caps header over the sentence; plain:
    // the sentence alone.
    const header = spec.header ? spec.header.toUpperCase() : '';
    const headerH = header ? Math.round(BANNER_HEADER_PX * 1.25) + 3 : 0;
    const fit = fitText(ctx, text, BANNER_BODY_FONT, BANNER_BODY_PX, right - left, areaH - headerH, 3);
    const blockH = headerH + fit.lines.length * fit.lineH;
    const top = areaTop + (areaH - blockH) / 2;
    if (header) {
        ctx.font = `700 ${BANNER_HEADER_PX}px ${BANNER_DISPLAY_FONT}`;
        ctx.fillStyle = spec.headerColor;
        if (kind === 'check' && !still) {
            const pulse = 0.5 - 0.5 * Math.cos((2 * Math.PI * now) / 1800);
            ctx.shadowColor = `rgba(255, 40, 40, ${0.25 + 0.6 * pulse})`;
            ctx.shadowBlur = 2 + 9 * pulse;
        }
        fillSpaced(ctx, header, left, top + (headerH - 3) / 2, BANNER_HEADER_PX * 0.14);
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
    }
    ctx.font = BANNER_BODY_FONT(fit.size);
    ctx.fillStyle = 'rgb(255, 255, 255)';
    fit.lines.forEach((l, i) => ctx.fillText(l, left, top + headerH + fit.lineH * (i + 0.5)));
}

// ---- Necromancer: electricity jumping around the letters -------------------
//
// Shown when a player raises on two consecutive turns (main.js). A dark
// storm-gray October Crow title (owner, 9/28; was silver Cinzel Decorative),
// backlit electric blue, with arcs leaping between neighbouring letters and
// sparking off their tops, re-forking every ~90ms. Procedural, no art.
const ELECTRIC_ACCENT = [111, 208, 255];
const ELECTRIC_TITLE_FONT = (size) => `400 ${size}px "October Crow Web", ${BANNER_DISPLAY_FONT}`;
const ELECTRIC_TITLE_COLOR = 'rgb(72, 88, 110)'; // 'storm'
const ELECTRIC_REFORK_MS = 90;

// Small deterministic PRNG, so each ~90ms bucket keeps the same arcs for
// every redraw inside it (a steady flicker, not per-frame noise).
function seededRandom(seed) {
    let t = seed >>> 0;
    return () => {
        t += 0x6D2B79F5;
        let x = Math.imul(t ^ (t >>> 15), 1 | t);
        x ^= x + Math.imul(x ^ (x >>> 7), 61 | x);
        return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
}

// Jagged path from a to b by midpoint displacement.
function boltPoints(a, b, rand, depth, spread) {
    if (depth === 0) return [a, b];
    const mid = {
        x: (a.x + b.x) / 2 + (rand() - 0.5) * spread,
        y: (a.y + b.y) / 2 + (rand() - 0.5) * spread,
    };
    return [...boltPoints(a, mid, rand, depth - 1, spread / 2).slice(0, -1), ...boltPoints(mid, b, rand, depth - 1, spread / 2)];
}

function strokeBolt(ctx, pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (const p of pts.slice(1)) ctx.lineTo(p.x, p.y);
    // wide soft glow, then a thin white-hot core
    ctx.strokeStyle = 'rgba(111, 208, 255, 0.45)';
    ctx.lineWidth = 3.5;
    ctx.shadowColor = 'rgba(111, 208, 255, 0.9)';
    ctx.shadowBlur = 10;
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(235, 250, 255, 0.95)';
    ctx.lineWidth = 1.1;
    ctx.stroke();
}

function drawElectricTitle(ctx, title, big, x, cy, titleH, now, still, maxW) {
    ctx.font = ELECTRIC_TITLE_FONT(big);
    // Stretched sideways to span the banner (owner, 9/28) - October Crow is
    // narrow and only filled ~60% of it. Only the letters are scaled; the
    // arcs are drawn unscaled between the stretched letter boxes.
    const sx = Math.max(1, maxW / ctx.measureText(title).width);
    // letter boxes, for where arcs start and land
    const letters = [];
    let lx = x;
    for (const ch of title) {
        const w = ctx.measureText(ch).width * sx;
        if (ch !== ' ') letters.push({ x: lx, w });
        lx += w;
    }
    const capTop = cy - big * 0.36;
    const capBot = cy + big * 0.34;

    // the dark title, lit blue from behind - the glow is what makes dark
    // letters read on the dark banner, so it's stronger than the old
    // silver title's and laid down twice, then the letters go on top with
    // no shadow so the glow never fogs them (owner, 9/28)
    ctx.save();
    ctx.translate(x, 0);
    ctx.scale(sx, 1);
    ctx.shadowColor = 'rgba(111, 208, 255, 0.95)';
    ctx.shadowBlur = still ? 10 : 12 + 4 * Math.sin(now / 70);
    ctx.fillStyle = ELECTRIC_TITLE_COLOR;
    ctx.fillText(title, 0, cy);
    ctx.fillText(title, 0, cy);
    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;
    ctx.fillText(title, 0, cy);
    ctx.restore();

    if (letters.length < 2) return;
    const rand = seededRandom(still ? 7 : Math.floor(now / ELECTRIC_REFORK_MS));
    const pointOn = (l) => ({ x: l.x + l.w * (0.2 + rand() * 0.6), y: capTop + rand() * (capBot - capTop) });
    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    // arcs between neighbouring letters (sometimes skipping one)
    const arcs = still ? 3 : 3 + Math.floor(rand() * 3);
    for (let i = 0; i < arcs; i++) {
        const a = Math.floor(rand() * (letters.length - 1));
        const b = Math.min(letters.length - 1, a + 1 + (rand() < 0.3 ? 1 : 0));
        strokeBolt(ctx, boltPoints(pointOn(letters[a]), pointOn(letters[b]), rand, 4, big * 0.5));
    }
    // sparks leaping up off the tops of a couple of letters
    const sparks = still ? 1 : 1 + Math.floor(rand() * 2);
    for (let i = 0; i < sparks; i++) {
        const l = letters[Math.floor(rand() * letters.length)];
        const from = { x: l.x + l.w * (0.3 + rand() * 0.4), y: capTop };
        const to = { x: from.x + (rand() - 0.5) * big * 0.9, y: capTop - titleH * (0.25 + rand() * 0.2) };
        strokeBolt(ctx, boltPoints(from, to, rand, 3, big * 0.35));
    }
    ctx.restore();
}

// ---- results: a cold steel title ---------------------------------------------
//
// First built for "Out of Time", then given to every result except
// Necromancer and Regicide (owner, 9/28): Dystopian Canticle, centered and stretched
// to 90% of the banner, dark blue steel with a slow cold glint crossing it.
// No other motion.
const STEEL_ACCENT = [96, 128, 168];
const STEEL_TITLE_FONT = (size) => `400 ${size}px "Dystopian Canticle Web", ${BANNER_DISPLAY_FONT}`;
const STEEL_GLINT_MS = 4200;

function drawSteelTitle(ctx, r, title, big, cy, now, still) {
    ctx.font = STEEL_TITLE_FONT(big);
    const nativeW = ctx.measureText(title).width;
    const targetW = r.w * 0.9;
    const sx = targetW / nativeW;
    const tTop = cy - big * 0.5;
    const tBot = cy + big * 0.5;
    ctx.save();
    ctx.translate(r.x + (r.w - targetW) / 2, 0);
    ctx.scale(sx, 1);
    const g = ctx.createLinearGradient(0, tTop, 0, tBot);
    g.addColorStop(0, 'rgb(138, 160, 188)');
    g.addColorStop(1, 'rgb(62, 82, 110)');
    ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
    ctx.shadowOffsetY = 1;
    ctx.fillStyle = g;
    ctx.fillText(title, 0, cy);
    ctx.shadowColor = 'transparent';
    ctx.shadowOffsetY = 0;
    if (!still) {
        // the glint: a pale band laid over the letters, crossing left to right
        ctx.fillStyle = sweepGradient(ctx, 0, nativeW, now, STEEL_GLINT_MS,
            'rgba(210, 228, 250, 0)', 'rgba(210, 228, 250, 0.6)');
        ctx.fillText(title, 0, cy);
    }
    ctx.restore();
}

// ---- mate by capture: the title bleeds and drips ---------------------------
//
// Ported from the Banner Type Lab prototype the owner approved (9/26): the
// silver title fills with crimson from the top, then blood gathers on the
// undersides of the actual letters and drips, a few beads break off and
// fall, and afterwards one bead falls every few seconds. All drawn here;
// the sentence is drawn over it afterwards so it always reads.
const BLOOD_ACCENT = [128, 10, 16]; // 'Darker' oxblood (owner, 9/27; was 176,20,28)
const BLOOD_DRIPS = 9;
const BLOOD_MAX_LEN = 24;
let blood = null; // { key, drips, drops, nextIdle, moving }

// Ghastly Panic (owner, 9/28; was Cinzel Decorative) - picked over
// Dystopian Canticle side by side.
const bloodTitleFont = (size) => `400 ${size}px "Ghastly Panic Web", ${BANNER_DISPLAY_FONT}`;

// Undersides of the letters: an opaque pixel with clear air right below.
function bloodSources(r, title, big, x, cy, sx) {
    const k = 2;
    const m = document.createElement('canvas');
    m.width = r.w * k;
    m.height = r.h * k;
    const mc = m.getContext('2d');
    mc.scale(k, k);
    mc.translate(-r.x, -r.y);
    mc.translate(x, 0);
    mc.scale(sx, 1);
    mc.font = bloodTitleFont(big);
    mc.textBaseline = 'middle';
    mc.fillText(title, 0, cy);
    const a = mc.getImageData(0, 0, m.width, m.height).data;
    const at = (px, py) => a[(py * m.width + px) * 4 + 3];
    const pts = [];
    for (let px = 0; px < m.width; px += 2) {
        for (let py = 2; py < m.height - 2; py++) {
            if (at(px, py) > 160 && at(px, py - 2) > 160 && at(px, py + 1) < 60 && at(px, py + 2) < 30) {
                pts.push({ x: r.x + px / k, y: r.y + py / k });
            }
        }
    }
    return pts;
}

function makeDrips(pts, cy, titleH) {
    // favour the lower edges (baseline, serifs) but let a few arms drip too
    const lowCut = cy + titleH * 0.15;
    const ordered = pts.map((p) => ({ p, s: Math.random() * (p.y > lowCut ? 1 : 0.35) }))
        .sort((m, n) => n.s - m.s).map((q) => q.p);
    const picked = [];
    for (const p of ordered) {
        if (picked.length >= BLOOD_DRIPS) break;
        if (picked.every((q) => Math.abs(q.x - p.x) > 10)) picked.push(p);
    }
    return picked.map((p) => ({
        x: p.x,
        y: p.y,
        w: 2.2 + Math.random() * 2.2,
        len: Math.max(5, BLOOD_MAX_LEN * (0.25 + 0.75 * Math.random() ** 1.8)),
        start: 900 + Math.random() * 900,
        dur: 900 + Math.random() * 1100,
        drops: Math.random() < 0.45,
        dropped: false,
        regrowAt: 0,
        cur: 0,
    }));
}

function drawDrip(ctx, d, len) {
    if (len <= 0.3) return;
    const r = d.w * (0.5 + 0.3 * Math.min(1, len / d.len)); // the bead swells as it sags
    const top = d.y - 1.5;                                  // tucked into the letter
    const tipY = d.y + len;
    ctx.beginPath();
    ctx.moveTo(d.x - d.w / 2, top);
    ctx.bezierCurveTo(d.x - d.w / 2, top + len * 0.5, d.x - d.w * 0.3, tipY - r * 1.6, d.x - r * 0.8, tipY - r * 0.6);
    ctx.arc(d.x, tipY - r * 0.2, r, Math.PI * 0.95, Math.PI * 0.05, true);
    ctx.bezierCurveTo(d.x + d.w * 0.3, tipY - r * 1.6, d.x + d.w / 2, top + len * 0.5, d.x + d.w / 2, top);
    ctx.closePath();
    ctx.fill();
    ctx.save();
    ctx.fillStyle = 'rgba(255, 190, 190, 0.28)'; // wet glint on the bead
    ctx.beginPath();
    ctx.ellipse(d.x - r * 0.35, tipY - r * 0.45, r * 0.28, r * 0.4, -0.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

function drawBloodTitle(ctx, r, title, big, x, cy, titleH, now, still, maxW) {
    // Stretched sideways to span the banner, like Necromancer (owner, 9/28).
    // Only the letters are scaled - the drips are found on the stretched
    // letters but drawn unscaled, so they keep their shape.
    ctx.font = bloodTitleFont(big);
    const sx = Math.max(1, maxW / ctx.measureText(title).width);
    if (!blood || blood.key !== bannerKey) {
        blood = {
            key: bannerKey,
            drips: makeDrips(bloodSources(r, title, big, x, cy, sx), cy, titleH),
            drops: [],
            nextIdle: 0,
            moving: true,
        };
    }
    const t = still ? 1e9 : now - bannerChangedAt;
    const ease = (v) => 1 - (1 - v) ** 3;
    const lerp = (m, n, v) => m + (n - m) * v;
    const tTop = cy - titleH / 2;
    const tBot = cy + titleH / 2;

    // silver first, then crimson seeping down from the top
    ctx.save();
    ctx.translate(x, 0);
    ctx.scale(sx, 1);
    ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
    ctx.shadowOffsetY = 1;
    ctx.fillStyle = 'rgb(216, 216, 207)';
    ctx.fillText(title, 0, cy);
    ctx.restore();
    const bleed = Math.min(1, Math.max(0, (t - 250) / 700));
    if (bleed > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(r.x, r.y - 10, r.w, lerp(tTop - 2, tBot + 4, ease(bleed)) - (r.y - 10));
        ctx.clip();
        ctx.translate(x, 0);
        ctx.scale(sx, 1);
        const g = ctx.createLinearGradient(0, tTop, 0, tBot);
        g.addColorStop(0, 'rgb(128, 10, 16)');
        g.addColorStop(1, 'rgb(72, 3, 7)');
        ctx.fillStyle = g;
        ctx.fillText(title, 0, cy);
        ctx.restore();
    }

    ctx.fillStyle = 'rgb(80, 4, 9)';
    let settled = bleed >= 1;
    for (const d of blood.drips) {
        const p = Math.min(1, Math.max(0, (t - d.start) / d.dur));
        if (p < 1) settled = false;
        let len = d.len * ease(p);
        if (p >= 1 && d.drops && !d.dropped && !still) {
            d.dropped = true;
            blood.drops.push({ x: d.x, y: d.y + d.len, r: d.w * 0.7, born: now });
            d.regrowAt = now;
        }
        if (d.regrowAt) { // the bead that fell regathers slowly
            len = d.len * lerp(0.72, 1, ease(Math.min(1, (now - d.regrowAt) / 1400)));
        }
        d.cur = len;
        drawDrip(ctx, d, len);
    }

    // after it settles, one drip lets a bead go every few seconds
    if (settled && !still && blood.drips.length) {
        if (!blood.nextIdle) blood.nextIdle = now + 1500 + Math.random() * 2500;
        if (now >= blood.nextIdle) {
            const d = blood.drips[Math.floor(Math.random() * blood.drips.length)];
            blood.drops.push({ x: d.x, y: d.y + d.cur, r: d.w * 0.7, born: now });
            d.regrowAt = now;
            blood.nextIdle = now + 2500 + Math.random() * 3000;
        }
    }

    // falling drops, stretched by their speed
    const bottom = r.y + r.h + 20;
    blood.drops = blood.drops.filter((dr) => {
        const dt = (now - dr.born) / 1000;
        const y = dr.y + 350 * dt * dt;
        if (y > bottom) return false;
        const stretch = 1 + Math.min(1.6, (700 * dt) / 250);
        ctx.beginPath();
        ctx.ellipse(dr.x, y, dr.r, dr.r * stretch, 0, 0, Math.PI * 2);
        ctx.fill();
        return true;
    });
    const regathering = blood.drips.some((d) => d.regrowAt && now - d.regrowAt < 1400);
    blood.moving = !still && (!settled || blood.drops.length > 0 || regathering);
}

// ---- depth (owner's picks, 9/28) --------------------------------------------
//
// Subtle 3D touches: board cards cast a soft shadow down-right like real
// cards, deck cards do too (face-down ones show a pile edge), plain squares
// get a light top/left and dark bottom/right bevel, and faint light falls
// across the whole board from the top left. (A board drop shadow and piece
// contact shadows were offered too - not wanted for now.)

function drawBoardSquares(ctx) {
    const cards = [];
    for (let row = 0; row < ROWS; row++) {
        for (let col = 0; col < COLS; col++) {
            const key = `${col},${row}`;
            const isCard = CARD_SQUARES.has(key);
            if (isCard && cardStyle) {
                cards.push({ x: boardColX(col), y: rowY(row), card: CARD_TABLE.get(key) });
                continue;
            }
            const x = boardColX(col);
            const y = rowY(row);
            ctx.fillStyle = isCard ? THEME.bgDark : THEME.bgLight;
            ctx.fillRect(x, y, RWIDTH - 2, RHEIGHT - 2);
            drawSquareBevel(ctx, x, y, RWIDTH - 2, RHEIGHT - 2);
        }
    }
    // Cards go down after every plain square, so a card's shadow can fall
    // onto the squares to its right and below (and never on another card).
    const w = RWIDTH - 2;
    const h = RHEIGHT - 2;
    ctx.save();
    ctx.beginPath();
    ctx.rect(BOARD_X, 0, WIDTH, HEIGHT + RAMPART_HEIGHT);
    ctx.clip();
    for (const c of cards) castCardShadow(ctx, c.x, c.y, w, h, Math.max(2, Math.min(w, h) * 0.07), 2, 3, 7, 0.38);
    ctx.restore();
    for (const c of cards) drawCardSquare(ctx, c.x, c.y, w, h, THEME.bgDark, c.card);
}

// A soft shadow shaped like the card, offset down-right. Only the shadow is
// painted: the shape itself is drawn far off to the left and the shadow is
// offset back by the same amount. Shadow offsets and blur ignore the
// canvas transform (they're in device pixels), so they're scaled by hand -
// otherwise any window size but 1:1 threw the shadows hundreds of pixels
// sideways, onto the board's cards.
function castCardShadow(ctx, x, y, w, h, radius, dx, dy, blur, alpha) {
    const FAR = 4000;
    const { a: sx, d: sy } = ctx.getTransform();
    ctx.save();
    ctx.shadowColor = `rgba(0, 0, 0, ${alpha})`;
    ctx.shadowBlur = blur * sx;
    ctx.shadowOffsetX = (FAR + dx) * sx;
    ctx.shadowOffsetY = dy * sy;
    roundedRectPath(ctx, x - FAR, y, w, h, radius);
    ctx.fillStyle = '#000';
    ctx.fill();
    ctx.restore();
}

function drawSquareBevel(ctx, x, y, w, h) {
    // 2px edges: warm light top/left, shade bottom/right (a 1px white one
    // didn't show on the cream squares at all)
    ctx.save();
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(255, 252, 240, 0.7)';
    ctx.beginPath();
    ctx.moveTo(x + 1, y + h - 1);
    ctx.lineTo(x + 1, y + 1);
    ctx.lineTo(x + w - 1, y + 1);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.28)';
    ctx.beginPath();
    ctx.moveTo(x + w - 1, y + 1);
    ctx.lineTo(x + w - 1, y + h - 1);
    ctx.lineTo(x + 1, y + h - 1);
    ctx.stroke();
    ctx.restore();
}

function drawBoardLighting(ctx) {
    const H = HEIGHT + RAMPART_HEIGHT;
    const g = ctx.createLinearGradient(BOARD_X, 0, BOARD_X + WIDTH, H);
    g.addColorStop(0, 'rgba(255, 250, 235, 0.10)');
    g.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
    g.addColorStop(1, 'rgba(0, 0, 0, 0.12)');
    ctx.fillStyle = g;
    ctx.fillRect(BOARD_X, 0, WIDTH, H);
}

function drawRampart(ctx) {
    // matches game.py's show_bg: rampart_img scaled to (RWIDTH*COLS,
    // RAMPART_HEIGHT), blit at (100, 3*RHEIGHT).
    drawImageWhenReady(ctx, rampartImage, BOARD_X, 3 * RHEIGHT, WIDTH, RAMPART_HEIGHT);
}

function drawEmblems(ctx) {
    // matches game.py's show_cemetery: two 80x80 emblem blits at fixed
    // design-canvas positions (not board-relative).
    drawImageWhenReady(ctx, emblemImage(), 5, 715 + RAMPART_HEIGHT, 80, 80);
    drawImageWhenReady(ctx, emblemImage(), 908, 2, 80, 80);
}

function drawCardLabels(ctx) {
    if (cardStyle) return; // drawCardSquare already drew each card's index
    ctx.font = 'bold 20px Georgia, serif';
    ctx.fillStyle = 'rgb(255,0,0)';
    ctx.textBaseline = 'top';
    for (const [key, card] of CARD_TABLE.entries()) {
        const [col, row] = key.split(',').map(Number);
        const x = boardColX(col) + 7;
        const y = rowY(row) + 4;
        ctx.fillText(card.rank, x, y);
        ctx.fillText(card.suit, x, y + 20);
    }
}

function drawRowLetters(ctx) {
    ctx.font = 'bold 16px monospace';
    for (let row = 0; row < ROWS; row++) {
        // matches game.py's row-letter color rule exactly - not the same
        // condition as CARD_SQUARES (that one depends on col too).
        const useDark = row === 5 || row % 2 === 0;
        ctx.fillStyle = useDark ? THEME.bgDark : THEME.bgLight;
        const label = ROW_LETTERS[row];
        const y = rowY(row) + RHEIGHT - 25;
        // anchored to column 0's own screen position, not a fixed side, so
        // this naturally lands on the opposite edge when flipped.
        ctx.fillText(label, boardColX(0) + 5, y);
    }
}

// Column numbers (1-10) along the board's bottom edge (game.py's own
// "column numbers (horizontal labels)") - a separate feature from the row
// letters above that never got ported to this file at all, not a bug in
// existing code. Reuses boardColX/rowY the same way drawRowLetters does
// (anchored to the board's actual logical edges - col 0..COLS-1, row
// ROWS-1 - letting the flip transform carry them to whichever screen edge
// that lands on) rather than game.py's own separately-coded flipped/
// unflipped branches, matching this file's already-established approach
// for row letters instead of duplicating game.py's more ad-hoc version.
function drawColumnNumbers(ctx) {
    ctx.font = 'bold 16px monospace';
    for (let col = 0; col < COLS; col++) {
        // matches game.py's column-number color rule exactly - based on
        // the original (logical) bottom-row square, not whichever edge it
        // visually lands on when flipped.
        const isCardSquare = CARD_SQUARES.has(`${col},${ROWS - 1}`);
        ctx.fillStyle = isCardSquare ? THEME.bgLight : THEME.bgDark;
        const label = String(col + 1);
        const x = boardColX(col) + RWIDTH - 25;
        const y = rowY(ROWS - 1) + RHEIGHT - 25;
        ctx.fillText(label, x, y);
    }
}

// deck slot screen position: black (suit 0) on the left, white (suit 3
// display) on the right - mirrors game.py's DECK_SQS loop exactly. Goes
// through screenSide() so each color's panel swaps sides when flipped.
function deckSlotPos(colorLabel, rankIdx) {
    if (screenSide(colorLabel) === 'black') {
        return { x: 2, y: rankIdx * CHEIGHT + 2 };
    }
    return { x: DESIGN_WIDTH - 92, y: (12 - rankIdx) * CHEIGHT + CEM_HEIGHT + RAMPART_HEIGHT };
}

export function deckCardAt(x, y) {
    for (const colorLabel of ['black', 'white']) {
        for (let rank = 0; rank < DECK; rank++) {
            const { x: sx, y: sy } = deckSlotPos(colorLabel, rank);
            if (x >= sx && x <= sx + CWIDTH && y >= sy && y <= sy + CHEIGHT) {
                return { color: colorLabel, rank };
            }
        }
    }
    return null;
}

function drawDecks(ctx, state) {
    // shadows (and pile edges) for every slot first, so none lands on a card
    if (cardStyle) {
        for (const colorLabel of ['black', 'white']) {
            const deckArray = colorLabel === 'black' ? state.black_deck : state.white_deck;
            for (let rank = 0; rank < DECK; rank++) {
                const { x, y } = deckSlotPos(colorLabel, rank);
                const h = CHEIGHT - 2;
                castCardShadow(ctx, x, y, CWIDTH, h, DECK_CARD_RADIUS, 1.5, 2, 4, 0.45);
                if (deckArray[rank]) { // face down: two card edges peeking out below
                    for (const k of [2, 1]) {
                        roundedRectPath(ctx, x + k * 0.5, y + k, CWIDTH, h, DECK_CARD_RADIUS);
                        ctx.fillStyle = k === 2 ? 'rgb(150, 146, 136)' : 'rgb(205, 201, 190)';
                        ctx.fill();
                    }
                }
            }
        }
    }
    for (const colorLabel of ['black', 'white']) {
        const deckArray = colorLabel === 'black' ? state.black_deck : state.white_deck;
        const suitSymbol = DECK_SUIT[colorLabel];
        for (let rank = 0; rank < DECK; rank++) {
            const { x, y } = deckSlotPos(colorLabel, rank);
            const used = deckArray[rank];

            const { fill, ink } = deckCardColors(colorLabel);
            if (cardStyle) {
                drawDeckCard(ctx, x, y, fill, ink, used, RANKS[rank], suitSymbol, colorLabel);
                continue;
            }
            ctx.fillStyle = fill;
            ctx.fillRect(x, y, CWIDTH, CHEIGHT - 2);

            if (used) {
                drawImageWhenReady(ctx, cardBackImage(), x, y, CWIDTH, CHEIGHT - 1);
                continue;
            }
            ctx.font = 'bold 16px Georgia, serif';
            ctx.fillStyle = ink;
            ctx.textBaseline = 'middle';
            const textY = y + (CHEIGHT - 2) / 2;
            if (colorLabel === 'black') {
                ctx.fillText(RANKS[rank], x + 5, textY);
                ctx.fillText(suitSymbol, x + 30, textY);
            } else {
                ctx.fillText(RANKS[rank], x + 42, textY);
                ctx.fillText(suitSymbol, x + 67, textY);
            }
        }
    }
}

// Card-style deck slot: same rounded body as the board's card squares
// (no inner frame - the slots are only ~24px tall), index laid out in one
// row like the flat version, suit drawn as a vector pip. A used card shows
// the card-back art clipped to the same rounded shape.
const DECK_CARD_RADIUS = 3;
function drawDeckCard(ctx, x, y, fill, ink, used, rank, suit, colorLabel) {
    const h = CHEIGHT - 2;
    if (used) {
        ctx.save();
        roundedRectPath(ctx, x, y, CWIDTH, h, DECK_CARD_RADIUS);
        ctx.clip();
        drawImageWhenReady(ctx, cardBackImage(), x, y, CWIDTH, h + 1);
        ctx.restore();
        return;
    }
    drawCardBody(ctx, x, y, CWIDTH, h, fill, { radius: DECK_CARD_RADIUS, frameInset: 0 });
    ctx.save();
    ctx.font = `600 15px ${CARD_FONT_FAMILY}`;
    ctx.fillStyle = ink;
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    const midY = y + h / 2 + 1;
    const rankX = colorLabel === 'black' ? x + 16 : x + CWIDTH - 34;
    ctx.fillText(rank, rankX, midY);
    ctx.restore();
    drawSuit(ctx, suit, rankX + 23, y + h / 2, 13, ink);
}

function drawDeckHover(ctx, ui) {
    // matches show_hover's hovered_crd - drawn AFTER drawDecks (like the
    // button hover), since deck slots are opaque fills/card-back images
    // that would otherwise hide a border drawn underneath them.
    if (!ui.hoverDeckCard) return;
    const { color, rank } = ui.hoverDeckCard;
    const { x, y } = deckSlotPos(color, rank);
    ctx.strokeStyle = 'rgb(173, 216, 230)';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, CWIDTH, CHEIGHT - 1);
}

// Soft glow behind a highlight instead of a hard flat line, plus a gentle
// breathing pulse (period/amplitude shared by every glowing highlight
// below, so they all "breathe" in sync rather than looking busy) - the
// main visual ask behind drawClickedDeckCards/drawClickedBoardCards below.
// ctx.save()/restore() (rather than resetting shadowBlur back to 0 by hand
// afterward) is what keeps this from bleeding shadow state into whatever
// draws next.
const PULSE_PERIOD_MS = 900;
function pulsePhase() {
    return 0.5 + 0.5 * Math.sin((2 * Math.PI * performance.now()) / PULSE_PERIOD_MS);
}

function strokeRoundedRect(ctx, x, y, w, h, radius) {
    ctx.beginPath();
    if (ctx.roundRect) {
        ctx.roundRect(x, y, w, h, radius);
    } else {
        ctx.rect(x, y, w, h);
    }
    ctx.stroke();
}

function drawClickedDeckCards(ctx, ui) {
    // matches show_clicked_cards's teal highlight for deck cards in the
    // player's current combo selection.
    if (!ui.clickedCards) return;
    const pulse = pulsePhase();
    ctx.save();
    ctx.strokeStyle = 'rgb(100, 216, 220)';
    ctx.shadowColor = 'rgb(100, 216, 220)';
    ctx.shadowBlur = 5 + 4 * pulse;
    ctx.lineWidth = 2.5;
    for (const card of ui.clickedCards) {
        if (card.source !== 'deck') continue;
        const { x, y } = deckSlotPos(card.color, card.rank);
        strokeRoundedRect(ctx, x, y, CWIDTH, CHEIGHT - 1, 5);
    }
    ctx.restore();
}

function drawClickedBoardCards(ctx, ui) {
    // matches show_clicked_cards's teal highlight for board cards in the
    // player's current combo selection.
    if (!ui.clickedCards) return;
    const pulse = pulsePhase();
    ctx.save();
    ctx.strokeStyle = 'rgb(100, 216, 220)';
    ctx.shadowColor = 'rgb(100, 216, 220)';
    ctx.shadowBlur = 5 + 4 * pulse;
    ctx.lineWidth = 2.5;
    for (const card of ui.clickedCards) {
        if (card.source !== 'board') continue;
        strokeRoundedRect(ctx, boardColX(card.col), rowY(card.row), RWIDTH - 2, RHEIGHT - 2, 5);
    }
    ctx.restore();
}

// Also goes through screenSide() - see deckSlotPos.
function graveSlotPos(colorLabel, idx) {
    if (screenSide(colorLabel) === 'black') {
        return { x: GWIDTH / 2 + 2, y: idx * GHEIGHT + GHEIGHT / 2 + (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT };
    }
    return { x: DESIGN_WIDTH - GWIDTH / 2 - 2, y: idx * GHEIGHT + GHEIGHT / 2 + 90 };
}

// Which cemetery slot (if any) is at design point (x, y) - for choosing the
// piece to raise, like the desktop client's clicked_grv.
export function graveSlotAt(x, y) {
    for (const colorLabel of ['black', 'white']) {
        for (let idx = 0; idx < GRAVES; idx++) {
            const c = graveSlotPos(colorLabel, idx);
            if (Math.abs(x - c.x) <= GWIDTH / 2 && Math.abs(y - c.y) <= GHEIGHT / 2) {
                return { color: colorLabel, idx };
            }
        }
    }
    return null;
}

function drawGraves(ctx, state, ui) {
    // choosing what to raise: the pieces that can be chosen get a thin
    // cast-magenta ring, the chosen one a bold glowing one
    const choice = ui && ui.graveChoice;
    if (choice) {
        for (const idx of choice.selectable) {
            const { x, y } = graveSlotPos(choice.color, idx);
            const chosen = idx === choice.chosenIdx;
            ctx.save();
            ctx.strokeStyle = CAST_DOT_COLOR;
            ctx.lineWidth = chosen ? 3 : 1.5;
            if (chosen) {
                ctx.shadowColor = CAST_DOT_COLOR;
                ctx.shadowBlur = 8;
            }
            roundedRectPath(ctx, x - GWIDTH / 2 + 4, y - GHEIGHT / 2 + 1, GWIDTH - 8, GHEIGHT - 2, 5);
            ctx.stroke();
            ctx.restore();
        }
    }
    for (const colorLabel of ['black', 'white']) {
        const graveArray = colorLabel === 'black' ? state.black_grave : state.white_grave;
        graveArray.forEach((name, idx) => {
            if (!name) return;
            const { x, y } = graveSlotPos(colorLabel, idx);
            const img = deadPieceImage(colorLabel, name);
            drawImageWhenReady(ctx, img, x - 17, y - 17, 35, 35);
        });
    }
}

// ---- cast effects (ported from io_src_dev_ai/effects.py) -----------------
//
// Both effects there are pure procedural pygame drawing (no sprites), so
// they're reproduced here as canvas paths rather than images. Timing is
// driven by wall-clock time (performance.now()), not a frame counter, since
// this client has no fixed-rate render loop to hang a frame count off of -
// main.js's requestAnimationFrame loop just calls drawCanvas() repeatedly
// while either effect is active.

const LIGHTNING_DURATION_MS = 500; // ~ effects.py's max_frames=30 at 60fps

let lightning = null; // { points: [[x,y],...], startTime }

// Jagged polyline generator - ported from effects.py's generate_lightning:
// each interior point is the straight-line interpolation plus a random
// offset that shrinks (`scale`) as it nears the endpoint.
function generateLightningPoints(x1, y1, x2, y2, depth = 24) {
    const points = [];
    for (let i = 0; i <= depth; i++) {
        const t = i / depth;
        const scale = 1 - t;
        const jitterX = (i > 0 && i < depth) ? (Math.random() * 30 - 15) * scale : 0;
        const jitterY = (i > 0 && i < depth) ? (Math.random() * 10 - 5) * scale : 0;
        points.push([x1 + (x2 - x1) * t + jitterX, y1 + (y2 - y1) * t + jitterY]);
    }
    return points;
}

// Anchor points: caster's graveyard column -> their deck column, matching
// effects.py's Lightning_effect.trigger (graveyard center to deck center).
function lightningAnchor(color) {
    const grave = graveSlotPos(color, Math.floor(GRAVES / 2));
    const deck = deckSlotPos(color, Math.floor(DECK / 2));
    return { x1: grave.x, y1: grave.y, x2: deck.x + CWIDTH / 2, y2: deck.y + CHEIGHT / 2 };
}

export function triggerLightning(color) {
    const { x1, y1, x2, y2 } = lightningAnchor(color);
    lightning = { points: generateLightningPoints(x1, y1, x2, y2), startTime: performance.now() };
}

export function isLightningActive() {
    return lightning !== null && (performance.now() - lightning.startTime) < LIGHTNING_DURATION_MS;
}

function drawLightning(ctx) {
    if (!lightning) return;
    const elapsed = performance.now() - lightning.startTime;
    if (elapsed >= LIGHTNING_DURATION_MS) {
        lightning = null;
        return;
    }
    const fade = 1 - elapsed / LIGHTNING_DURATION_MS;

    ctx.save();
    ctx.globalCompositeOperation = 'lighter'; // additive blend, matches BLEND_ADD
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    const strokePass = (color, alpha, width) => {
        if (width <= 0) return;
        ctx.strokeStyle = color;
        ctx.globalAlpha = alpha;
        ctx.lineWidth = width;
        ctx.beginPath();
        lightning.points.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
        ctx.stroke();
    };
    strokePass('rgb(100,150,255)', 0.31 * fade, 18 * fade); // outer bloom/glow
    strokePass('rgb(150,220,255)', 0.78 * fade, 10 * fade); // main bolt
    strokePass('rgb(220,240,255)', fade, 4 * fade);         // white-hot core

    // one-frame full-canvas flash, matching effects.py's frame==0 special case
    if (elapsed < 16) {
        ctx.globalAlpha = 0.35;
        ctx.fillStyle = 'rgb(220,240,255)';
        ctx.fillRect(0, 0, DESIGN_WIDTH, DESIGN_HEIGHT);
    }
    ctx.restore();
}

// Hourglass "AI thinking" indicator - ported from effects.py's
// Hourglass_effect. Virtual-frame math kept identical to desktop
// (VIRTUAL_FPS/SAND_FRAMES/FLIP_FRAMES) so the sand-drain/flip timing feels
// the same; geometry is redrawn as canvas paths instead of pygame polygons.
const SAND_FRAMES = 90;
const FLIP_FRAMES = 20;
const VIRTUAL_FPS = 60;

let hourglassActive = false;
let hourglassStart = 0;

export function startHourglass() {
    hourglassActive = true;
    hourglassStart = performance.now();
}

export function stopHourglass() {
    hourglassActive = false;
}

export function isHourglassActive() {
    return hourglassActive;
}

function drawHourglass(ctx, cx, cy, size) {
    if (!hourglassActive) return;
    const frame = Math.floor(((performance.now() - hourglassStart) / 1000) * VIRTUAL_FPS);
    const cycle = SAND_FRAMES + FLIP_FRAMES;
    const fullCycles = Math.floor(frame / cycle);
    const phase = frame % cycle;
    const orientation = 180 * (fullCycles % 2);
    let angle;
    let sandFraction;
    if (phase < SAND_FRAMES) {
        angle = orientation;
        sandFraction = phase / SAND_FRAMES;
    } else {
        const t = (phase - SAND_FRAMES) / FLIP_FRAMES;
        angle = orientation + 180 * t;
        sandFraction = 1;
    }

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((angle * Math.PI) / 180);

    ctx.fillStyle = 'rgb(156,116,48)'; // brass
    ctx.strokeStyle = 'rgb(94,66,24)'; // brass dark outline
    ctx.lineWidth = 1;
    ctx.fillRect(-size, -size - 3, size * 2, 4);
    ctx.strokeRect(-size, -size - 3, size * 2, 4);
    ctx.fillRect(-size, size - 1, size * 2, 4);
    ctx.strokeRect(-size, size - 1, size * 2, 4);

    ctx.strokeStyle = 'rgb(196,186,150)'; // glass
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(-size, -size); ctx.lineTo(size, -size); ctx.lineTo(0, 0); ctx.closePath();
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(-size, size); ctx.lineTo(size, size); ctx.lineTo(0, 0); ctx.closePath();
    ctx.stroke();

    ctx.fillStyle = 'rgb(224,168,47)'; // sand
    if (sandFraction < 0.98) {
        const h = size * (1 - sandFraction);
        ctx.beginPath();
        ctx.moveTo(-h, -size); ctx.lineTo(h, -size); ctx.lineTo(0, -size + h); ctx.closePath();
        ctx.fill();
    }
    if (sandFraction > 0.02) {
        const h = size * sandFraction;
        ctx.beginPath();
        ctx.moveTo(-h, size); ctx.lineTo(h, size); ctx.lineTo(0, size - h); ctx.closePath();
        ctx.fill();
    }
    if (sandFraction > 0 && sandFraction < 1) {
        ctx.fillStyle = 'rgb(255,208,90)'; // sand glow (trickle)
        for (let i = 0; i < 3; i++) {
            const fallT = ((frame * 5 + i * 7) % 15) / 15;
            const y = -size / 2 + fallT * size;
            ctx.beginPath();
            ctx.arc(0, y, 1.2, 0, Math.PI * 2);
            ctx.fill();
        }
    }
    ctx.restore();
}

// Soft red radial glow behind an in-check king, so it peeks out around the
// piece's (transparent-background) silhouette - ported from game.py's
// _get_check_halo, using a canvas radial gradient instead of the per-pixel
// pygame surface it builds and caches there (a gradient needs no cache
// here, it's cheap to construct fresh every frame).
function drawCheckHalo(ctx, cx, cy, size = 104) {
    const r = size / 2;
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    gradient.addColorStop(0, 'rgba(220, 30, 30, 0.55)');
    gradient.addColorStop(0.5, 'rgba(220, 30, 30, 0.3)');
    gradient.addColorStop(1, 'rgba(220, 30, 30, 0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();
}

function drawPieces(ctx, state) {
    for (const p of state.pieces) {
        const img = pieceImage(p.color, p.piece);
        const x = boardColX(p.col) + RWIDTH / 2;
        const y = rowY(p.row) + RHEIGHT / 2;
        if (p.piece === 'king' && state.in_check === p.color) {
            drawCheckHalo(ctx, x, y);
        }
        drawImageWhenReady(ctx, img, x - 40, y - 40, 80, 80);
    }
}

const MOVE_DOT_COLOR = 'rgb(20, 90, 200)';
const LIGHT_DOT_COLOR = 'rgb(160, 215, 255)';        // for dark blue squares
const LIGHT_DOT_FILL = 'rgba(160, 215, 255, 0.85)';
const CAST_DOT_COLOR = 'rgb(159, 43, 104)'; // same accent used for the
                                             // committed button / hovered_dom

function drawDot(ctx, col, row, color) {
    const cx = boardColX(col) + RWIDTH / 2;
    const cy = rowY(row) + RHEIGHT / 2;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, Math.min(RWIDTH, RHEIGHT) * 0.16, 0, Math.PI * 2);
    ctx.fill();
}

// chess.com-style capture indicator: a thin full-perimeter border with
// thicker bracket accents at each corner, for a legal destination that
// would capture a piece there (a plain dot would sit awkwardly on top of
// the piece art instead of marking the square itself).
function drawCaptureRing(ctx, col, row, color) {
    const x = boardColX(col) + 2;
    const y = rowY(row) + 2;
    const w = RWIDTH - 4;
    const h = RHEIGHT - 4;
    const arm = Math.min(w, h) * 0.28;

    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x, y, w, h);

    ctx.lineWidth = 4;
    ctx.lineCap = 'square';
    ctx.beginPath();
    ctx.moveTo(x, y + arm); ctx.lineTo(x, y); ctx.lineTo(x + arm, y);
    ctx.moveTo(x + w - arm, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + arm);
    ctx.moveTo(x + w, y + h - arm); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w - arm, y + h);
    ctx.moveTo(x + arm, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + h - arm);
    ctx.stroke();
}

// Last-move / selection frame. On a card square in card style it follows
// the card's rounded corners instead of poking out past them.
function strokeSquareFrame(ctx, col, row, color, width = 4) {
    const inset = width / 2;
    const x = boardColX(col) + inset;
    const y = rowY(row) + inset;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    if (cardStyle && CARD_SQUARES.has(`${col},${row}`)) {
        strokeRoundedRect(ctx, x, y, RWIDTH - 2 - width, RHEIGHT - 2 - width, 4);
    } else {
        ctx.strokeRect(x, y, RWIDTH - 2 - width, RHEIGHT - 2 - width);
    }
}

// 'rgb(r, g, b)' scaled toward black by f (0-1)
export function darkenRgb(rgb, f) {
    const [r, g, b] = rgb.match(/\d+/g).map(Number);
    return `rgb(${Math.round(r * (1 - f))}, ${Math.round(g * (1 - f))}, ${Math.round(b * (1 - f))})`;
}

function drawHighlights(ctx, state, ui) {
    if (ui.lastMoveSquares) {
        for (const [col, row] of ui.lastMoveSquares) {
            // Plain squares: a bolder, darker frame (owner, 9/30) - the
            // theme's trace color at 4px vanished on the cream squares and
            // under the bevel. Card squares keep the original yellow frame.
            if (CARD_SQUARES.has(`${col},${row}`)) {
                strokeSquareFrame(ctx, col, row, THEME.traceLight);
            } else {
                strokeSquareFrame(ctx, col, row, darkenRgb(THEME.traceDark, 0.2), 6);
            }
        }
    }
    if (ui.selected) {
        strokeSquareFrame(ctx, ui.selected.col, ui.selected.row, 'rgba(20, 90, 200, 0.9)');
    }
    if (ui.legalDestinations) {
        for (const [col, row] of ui.legalDestinations) {
            const captures = state.pieces.some((p) => p.col === col && p.row === row);
            // Blue board's blue card squares: the usual blue dot vanished
            // there, so a light, bright sky blue instead (owner, 9/30)
            const onBlue = THEME.name === 'Blue' && CARD_SQUARES.has(`${col},${row}`);
            if (captures) {
                drawCaptureRing(ctx, col, row, onBlue ? LIGHT_DOT_COLOR : MOVE_DOT_COLOR);
            } else {
                drawDot(ctx, col, row, onBlue ? LIGHT_DOT_FILL : 'rgba(20, 90, 200, 0.55)');
            }
        }
    }
    if (ui.castDestinations) {
        // Strike destinations are always an enemy raider's occupied square
        // (the piece being sent to the grave), so - like a capturing normal
        // move above - a dot would sit awkwardly on top of the piece art.
        // Use the same bracket-ring treatment there instead; raise
        // destinations are typically empty squares, so keep the dot.
        for (const { col, row, category } of ui.castDestinations) {
            if (category === 'strike') {
                drawCaptureRing(ctx, col, row, CAST_DOT_COLOR);
            } else {
                drawDot(ctx, col, row, CAST_DOT_COLOR);
            }
        }
    }
    if (ui.hoverSquare) {
        // matches show_hover's hovered_sqr
        // A shade darker and a pixel thicker on the plain squares (owner,
        // 9/28) - the bevel's edges run right where this ring does and had
        // swallowed it. Card squares keep the original ring.
        const { col, row } = ui.hoverSquare;
        const plain = !CARD_SQUARES.has(`${col},${row}`);
        ctx.strokeStyle = plain ? 'rgb(150, 150, 150)' : 'rgb(180, 180, 180)';
        ctx.lineWidth = plain ? 4 : 3;
        const inset = plain ? 2 : 1;
        ctx.strokeRect(boardColX(col) + inset, rowY(row) + inset, RWIDTH - 2 - 2 * inset, RHEIGHT - 2 - 2 * inset);
    }
}

function drawButtonHover(ctx, ui) {
    // matches show_hover's hovered_btn - drawn AFTER drawCastButtons (unlike
    // the other highlights above), since the buttons are opaque fills and
    // would otherwise completely hide a border drawn underneath them.
    if (!ui.hoverButton) return;
    const rect = ui.hoverButton === 'strike' ? STRIKE_RECT : RAISE_RECT;
    if (LEGACY_STRIP) {
        ctx.strokeStyle = 'rgb(173, 216, 230)';
        ctx.lineWidth = 2;
        ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
        return;
    }
    // The old pale blue vanished on the cream dead squares (Green/Brown/Blue).
    // A deep blue ring just outside the button, with a soft glow, reads on
    // light squares; a thin pale line on the button's own edge reads on
    // dark ones (Gray).
    // Lighter sky blue on Green and Brown (owner, 9/27); deep blue elsewhere.
    const lightRing = THEME.name === 'Green' || THEME.name === 'Brown';
    ctx.save();
    ctx.shadowColor = lightRing ? 'rgba(70, 140, 215, 0.55)' : 'rgba(20, 70, 160, 0.55)';
    ctx.shadowBlur = 10;
    ctx.strokeStyle = lightRing ? 'rgb(70, 140, 215)' : 'rgb(22, 78, 170)';
    ctx.lineWidth = 3.5;
    roundedRectPath(ctx, rect.x - 2.5, rect.y - 2.5, rect.w + 5, rect.h + 5, 6);
    ctx.stroke();
    ctx.restore();
    ctx.strokeStyle = 'rgb(190, 225, 245)';
    ctx.lineWidth = 1.5;
    roundedRectPath(ctx, rect.x + 0.75, rect.y + 0.75, rect.w - 1.5, rect.h - 1.5, 4);
    ctx.stroke();
}

// Brushed silver on every board (owner, 9/26 - first tried on Gray, where
// the old olive read as green), rounded, magenta while committed. Phones
// (LEGACY_STRIP) keep the original flat dark buttons in the strip.
// Green and Brown get a deeper silver (owner, 9/27) - the standard one read
// too pale against their lighter boards. Darkened again to a gunmetal
// (owner, 9/28), with a bright band near the top to keep it reading metallic.
function castButtonFill(ctx, rect) {
    const deep = THEME.name === 'Green' || THEME.name === 'Brown';
    const g = ctx.createLinearGradient(0, rect.y, 0, rect.y + rect.h);
    if (deep) {
        g.addColorStop(0, 'rgb(112, 115, 121)');
        g.addColorStop(0.18, 'rgb(140, 143, 149)');
        g.addColorStop(0.5, 'rgb(82, 85, 91)');
        g.addColorStop(1, 'rgb(58, 60, 65)');
        return { fill: g, edge: 'rgb(132, 135, 141)' };
    }
    // Blue and Gray: a step darker too (owner, 9/28), with the same sheen
    // band - stops short of gunmetal so it doesn't sink into Gray's dark
    // squares.
    g.addColorStop(0, 'rgb(128, 131, 137)');
    g.addColorStop(0.18, 'rgb(154, 157, 163)');
    g.addColorStop(0.5, 'rgb(100, 103, 109)');
    g.addColorStop(1, 'rgb(76, 78, 83)');
    return { fill: g, edge: 'rgb(150, 153, 159)' };
}

function drawCastButtons(ctx, ui) {
    ctx.font = LEGACY_STRIP ? '600 20px "Cinzel Web", Georgia, serif' : '600 25px "Cinzel Web", Georgia, serif';
    for (const [rect, label, key] of [[STRIKE_RECT, 'STRIKE', 'strike'], [RAISE_RECT, 'RAISE', 'raise']]) {
        const active = ui.committedButton === key;
        if (LEGACY_STRIP) {
            ctx.fillStyle = active ? 'rgb(159, 43, 104)' : 'rgb(40, 40, 40)';
            ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
        } else {
            const look = castButtonFill(ctx, rect);
            roundedRectPath(ctx, rect.x, rect.y, rect.w, rect.h, 4);
            ctx.fillStyle = active ? 'rgb(159, 43, 104)' : look.fill;
            ctx.fill();
            ctx.strokeStyle = active ? 'rgb(159, 43, 104)' : look.edge;
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        if (ui.disabledButtons && ui.disabledButtons.has(key)) {
            ctx.fillStyle = 'rgba(255,255,255,0.35)';
        } else {
            ctx.fillStyle = 'rgb(255,255,255)';
        }
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, rect.x + rect.w / 2, rect.y + rect.h / 2 + 1);
        ctx.textAlign = 'left'; // restore default so other draw calls aren't affected
    }
}
