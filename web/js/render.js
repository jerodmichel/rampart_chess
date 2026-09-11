// Canvas rendering of the whole game screen, at the same 1000x860 design
// resolution and pixel positions as the pygame client's game.py (flipped
// board perspective isn't implemented yet - always drawn as white-at-bottom,
// matching Board(flipped=False)). Ported directly from game.py's
// show_bg/show_pieces/show_dead/show_dead_cards/show_cast_buttons/
// show_cast_prompt so this reads as the same game, not a re-skin.

import {
    COLS, ROWS, WIDTH, HEIGHT, RWIDTH, RHEIGHT, RAMPART_HEIGHT, DECK, GRAVES,
    CEM_HEIGHT, CWIDTH, CHEIGHT, GWIDTH, GHEIGHT,
    BOARD_X, DESIGN_WIDTH, DESIGN_HEIGHT,
    RANKS, DECK_SUIT, CARD_SQUARES, CARD_TABLE, ROW_LETTERS,
} from './constants.js';

export const PROMPT_POS = { x: 320, y: 805 + RAMPART_HEIGHT };

export { DESIGN_WIDTH, DESIGN_HEIGHT };

// "green" theme from io_src_dev_ai/theme.py's default.
// All four theme color sets from io_src_dev_ai/config.py's _add_themes,
// ported as-is (light bg, dark bg, light trace, dark trace).
export const THEME_PRESETS = [
    { name: 'Green', bgLight: 'rgb(234, 235, 200)', bgDark: 'rgb(119, 154, 88)', traceLight: 'rgb(244, 247, 116)', traceDark: 'rgb(172, 195, 51)' },
    { name: 'Brown', bgLight: 'rgb(235, 209, 166)', bgDark: 'rgb(165, 117, 80)', traceLight: 'rgb(245, 234, 100)', traceDark: 'rgb(209, 185, 59)' },
    { name: 'Blue', bgLight: 'rgb(229, 228, 200)', bgDark: 'rgb(60, 95, 135)', traceLight: 'rgb(123, 187, 227)', traceDark: 'rgb(43, 119, 191)' },
    { name: 'Gray', bgLight: 'rgb(120, 119, 118)', bgDark: 'rgb(86, 85, 84)', traceLight: 'rgb(99, 126, 143)', traceDark: 'rgb(82, 102, 128)' },
];

let THEME = THEME_PRESETS[0];

export function setTheme(index) {
    const clamped = THEME_PRESETS[index] ? index : 0;
    THEME = THEME_PRESETS[clamped];
    emblemIdx = EMBLEM_PRESETS[clamped] ? clamped : 0;
    cardBackIdx = clamped % CARD_BACK_PRESETS.length;
}

export const STRIKE_RECT = { x: 102, y: 802 + RAMPART_HEIGHT, w: 100, h: 35 };
export const RAISE_RECT = { x: 205, y: 802 + RAMPART_HEIGHT, w: 83, h: 35 };

function inRect(x, y, r) {
    return x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
}

// ---- image loading (lazy, cached) ----------------------------------------

const images = new Map();
function loadImage(src) {
    if (!images.has(src)) {
        const img = new Image();
        img.src = src;
        images.set(src, img);
    }
    return images.get(src);
}

// Two selectable piece styles, matching piece.py's Piece.idx3 exactly:
// 'new_kset' has no bishop art, so bishop always falls back to 'default'
// there regardless of which set is active - same override piece.py's own
// Bishop.set_texture does.
export const PIECE_SET_NAMES = [
    { key: 'default', label: 'Default' },
    { key: 'new_kset', label: 'New' },
];

let pieceSetKey = 'default';

export function setPieceSet(key) {
    pieceSetKey = PIECE_SET_NAMES.some((s) => s.key === key) ? key : 'default';
}

function pieceImage(color, name) {
    const set = (name === 'bishop') ? 'default' : pieceSetKey;
    return loadImage(`assets/piece_sets/${set}/${color}_${name}.png`);
}

function deadPieceImage(color, name) {
    const set = (name === 'bishop') ? 'default' : pieceSetKey;
    return loadImage(`assets/piece_sets/${set}/dead_${color}_${name}.png`);
}

const rampartImage = loadImage('assets/misc/rampart.png');

// Card-back and emblem art ride along with the theme, exactly like desktop's
// K_t handler: pressing "T" there always calls change_theme() +
// change_emblem() + change_dead_card() together (main.py, all three call
// sites) - so despite Config tracking three separate indices, in practice
// they only ever advance in lockstep. CARD_BACK_PRESETS has 2 real images
// where desktop's 4-entry dead_cards list alternates card_back/dead_card0/
// card_back/dead_card0 - `% 2` below reproduces that exactly.
const CARD_BACK_PRESETS = [
    'assets/misc/card_back.png',
    'assets/misc/dead_card0.png',
];
const EMBLEM_PRESETS = [
    'assets/misc/alpha_omega88.png',
    'assets/misc/alpha-omega1.png',
    'assets/misc/alpha_omega.png',
    'assets/misc/alpha-omega2.png',
];

let cardBackIdx = 0;
let emblemIdx = 0;

function cardBackImage() {
    return loadImage(CARD_BACK_PRESETS[cardBackIdx]);
}

function emblemImage() {
    return loadImage(EMBLEM_PRESETS[emblemIdx]);
}

function drawImageWhenReady(ctx, img, x, y, w, h) {
    if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, x, y, w, h);
    } else {
        img.addEventListener('load', () => ctx.drawImage(img, x, y, w, h), { once: true });
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
    drawDecks(ctx, state);
    drawDeckHover(ctx, ui);
    drawClickedDeckCards(ctx, ui);
    drawGraves(ctx, state);
    drawEmblems(ctx);
    drawHighlights(ctx, state, ui);
    drawClickedBoardCards(ctx, ui);
    drawPieces(ctx, state);
    drawCastButtons(ctx, ui);
    drawButtonHover(ctx, ui);
    if (ui.promptText) drawPrompt(ctx, ui.promptText, ui.promptColor, ui);
    drawLightning(ctx); // drawn last so the glow overlays everything else
}

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

function drawBoardSquares(ctx) {
    for (let row = 0; row < ROWS; row++) {
        for (let col = 0; col < COLS; col++) {
            const isCard = CARD_SQUARES.has(`${col},${row}`);
            ctx.fillStyle = isCard ? THEME.bgDark : THEME.bgLight;
            ctx.fillRect(boardColX(col), rowY(row), RWIDTH - 2, RHEIGHT - 2);
        }
    }
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
    for (const colorLabel of ['black', 'white']) {
        const deckArray = colorLabel === 'black' ? state.black_deck : state.white_deck;
        const suitSymbol = DECK_SUIT[colorLabel];
        for (let rank = 0; rank < DECK; rank++) {
            const { x, y } = deckSlotPos(colorLabel, rank);
            const used = deckArray[rank];

            ctx.fillStyle = colorLabel === 'white' ? THEME.bgDark : THEME.bgLight;
            ctx.fillRect(x, y, CWIDTH, CHEIGHT - 2);

            if (used) {
                drawImageWhenReady(ctx, cardBackImage(), x, y, CWIDTH, CHEIGHT - 1);
                continue;
            }
            ctx.font = 'bold 16px Georgia, serif';
            ctx.fillStyle = 'rgb(0,0,0)';
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

function drawClickedDeckCards(ctx, ui) {
    // matches show_clicked_cards's teal highlight for deck cards in the
    // player's current combo selection.
    if (!ui.clickedCards) return;
    ctx.strokeStyle = 'rgb(100, 216, 220)';
    ctx.lineWidth = 2;
    for (const card of ui.clickedCards) {
        if (card.source !== 'deck') continue;
        const { x, y } = deckSlotPos(card.color, card.rank);
        ctx.strokeRect(x, y, CWIDTH, CHEIGHT - 1);
    }
}

function drawClickedBoardCards(ctx, ui) {
    // matches show_clicked_cards's teal highlight for board cards in the
    // player's current combo selection.
    if (!ui.clickedCards) return;
    ctx.strokeStyle = 'rgb(100, 216, 220)';
    ctx.lineWidth = 2;
    for (const card of ui.clickedCards) {
        if (card.source !== 'board') continue;
        ctx.strokeRect(boardColX(card.col), rowY(card.row), RWIDTH - 2, RHEIGHT - 2);
    }
}

// Also goes through screenSide() - see deckSlotPos.
function graveSlotPos(colorLabel, idx) {
    if (screenSide(colorLabel) === 'black') {
        return { x: GWIDTH / 2 + 2, y: idx * GHEIGHT + GHEIGHT / 2 + (HEIGHT - CEM_HEIGHT + 65) + RAMPART_HEIGHT };
    }
    return { x: DESIGN_WIDTH - GWIDTH / 2 - 2, y: idx * GHEIGHT + GHEIGHT / 2 + 90 };
}

function drawGraves(ctx, state) {
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

function drawPieces(ctx, state) {
    for (const p of state.pieces) {
        const img = pieceImage(p.color, p.piece);
        const x = boardColX(p.col) + RWIDTH / 2;
        const y = rowY(p.row) + RHEIGHT / 2;
        drawImageWhenReady(ctx, img, x - 40, y - 40, 80, 80);
    }
}

const MOVE_DOT_COLOR = 'rgb(20, 90, 200)';
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

function drawHighlights(ctx, state, ui) {
    if (ui.lastMoveSquares) {
        for (const [col, row] of ui.lastMoveSquares) {
            const isCard = CARD_SQUARES.has(`${col},${row}`);
            ctx.strokeStyle = isCard ? THEME.traceLight : THEME.traceDark;
            ctx.lineWidth = 4;
            ctx.strokeRect(boardColX(col) + 2, rowY(row) + 2, RWIDTH - 6, RHEIGHT - 6);
        }
    }
    if (ui.selected) {
        ctx.strokeStyle = 'rgba(20, 90, 200, 0.9)';
        ctx.lineWidth = 4;
        ctx.strokeRect(boardColX(ui.selected.col) + 2, rowY(ui.selected.row) + 2, RWIDTH - 6, RHEIGHT - 6);
    }
    if (ui.legalDestinations) {
        for (const [col, row] of ui.legalDestinations) {
            const captures = state.pieces.some((p) => p.col === col && p.row === row);
            if (captures) {
                drawCaptureRing(ctx, col, row, MOVE_DOT_COLOR);
            } else {
                drawDot(ctx, col, row, 'rgba(20, 90, 200, 0.55)');
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
        const { col, row } = ui.hoverSquare;
        ctx.strokeStyle = 'rgb(180, 180, 180)';
        ctx.lineWidth = 3;
        ctx.strokeRect(boardColX(col) + 1, rowY(row) + 1, RWIDTH - 4, RHEIGHT - 4);
    }
}

function drawButtonHover(ctx, ui) {
    // matches show_hover's hovered_btn - drawn AFTER drawCastButtons (unlike
    // the other highlights above), since the buttons are opaque fills and
    // would otherwise completely hide a border drawn underneath them.
    if (!ui.hoverButton) return;
    const rect = ui.hoverButton === 'strike' ? STRIKE_RECT : RAISE_RECT;
    ctx.strokeStyle = 'rgb(173, 216, 230)';
    ctx.lineWidth = 2;
    ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
}

function drawCastButtons(ctx, ui) {
    ctx.font = '600 20px "Cinzel Web", Georgia, serif';
    for (const [rect, label, key] of [[STRIKE_RECT, 'STRIKE', 'strike'], [RAISE_RECT, 'RAISE', 'raise']]) {
        ctx.fillStyle = ui.committedButton === key ? 'rgb(159, 43, 104)' : 'rgb(40, 40, 40)';
        ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
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
