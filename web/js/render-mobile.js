// Mobile board renderer - the one thing carried over from the old mobile/
// prototype's approach (see mobile/js/render.js, since retired): a plain
// COLS x ROWS grid of TRUE SQUARE cells, drawn on its own, independent of
// decks/graveyards/cast UI (those get their own DOM treatment in a later
// change - see the approved mobile plan). Unlike the old prototype, CELL is
// computed dynamically to fill whatever space is available (so it actually
// fills a landscape phone screen at any size) and this reads the SAME live
// constants.js/render.js state (card squares, active theme, active piece
// set) as the desktop renderer, rather than a separate hardcoded copy.
//
// Desktop's render.js can't just be resized for this: it composites board +
// decks + graveyards + cast UI onto one canvas at a fixed 1000x860 logical
// aspect ratio (RWIDTH=80/RHEIGHT=133 rectangular cells) - a landscape
// phone's aspect ratio is nothing like that, so reusing it would either
// letterbox badly or distort everything. This module only ever draws the
// board itself.

import { COLS, ROWS, CARD_SQUARES, CARD_TABLE } from './constants.js';
import { getActiveTheme, pieceImage, rampartImage, drawImageWhenReady, isFlipped, isCardStyle } from './render.js';
import { drawCardSquare } from './cardface.js';

// Same proportion as the old mobile/ prototype's CELL=64/RAMPART_BAND=14
// (14/64), just no longer a fixed pixel value - the rampart band scales
// with whatever CELL ends up being.
const RAMPART_RATIO = 14 / 64;

// Largest square CELL (in CSS px) that fits `availableWidth` x
// `availableHeight` without the board (COLS wide, ROWS tall plus the
// rampart band) overflowing either axis.
export function computeCellSize(availableWidth, availableHeight) {
    const cellFromWidth = availableWidth / COLS;
    const cellFromHeight = availableHeight / (ROWS + RAMPART_RATIO);
    return Math.max(1, Math.floor(Math.min(cellFromWidth, cellFromHeight)));
}

export function boardSize(cell) {
    return { width: cell * COLS, height: Math.round(cell * (ROWS + RAMPART_RATIO)) };
}

function rampartBand(cell) {
    return cell * RAMPART_RATIO;
}

// Board flip (setFlipped/isFlipped in render.js) is shared, global state -
// main.js already calls setFlipped(humanColor() === 'black') on load and
// wires the Flip Board button regardless of which renderer is active, so
// this only needs to READ it, the same shared flag desktop's boardColX/
// rowY already read. A 180-degree rotation (both axes), matching desktop
// exactly - not just flipping rows, or the board would read as mirrored
// rather than rotated.
function colX(col, cell) {
    const displayCol = isFlipped() ? COLS - 1 - col : col;
    return displayCol * cell;
}

// Screen-space y for a given board row - rows above the rampart band sit at
// row*cell, rows below it get pushed down by the band's height.
function rowY(row, cell) {
    const displayRow = isFlipped() ? ROWS - 1 - row : row;
    return displayRow < 3 ? displayRow * cell : displayRow * cell + rampartBand(cell);
}

// Matches render.js's isPlayableSquare / game.py's set_sq_hover exactly:
// on the house rows (0 and ROWS-1) only the K/Q/J house columns are real
// squares - the rest of those two rows have no card and aren't a
// destination. Exported for the house-row overlay content (player name/
// clock/deck/graveyard) a later change places over the *unplayable* cells.
export function isPlayableSquare(col, row) {
    if (row === 0) return col === 2 || col === 3 || col === 4;
    if (row === ROWS - 1) return col === 5 || col === 6 || col === 7;
    return true;
}

// Pixel rect (relative to the canvas) of a single cell, for main.js's mobile
// Strike/Raise/prompt overlays. Deliberately NOT flip-aware, unlike colX/
// rowY above - matches desktop, where STRIKE_RECT/RAISE_RECT/PROMPT_POS
// (render.js) are fixed canvas positions that never move on flip either.
// Using the flip-aware helpers here would make those controls swap corners
// every time the board flips, instead of staying put like their desktop
// equivalents.
function unflippedRowY(row, cell) {
    return row < 3 ? row * cell : row * cell + rampartBand(cell);
}

export function cellRect(col, row, cell) {
    return { x: col * cell, y: unflippedRowY(row, cell), width: cell, height: cell };
}

export function colRowFromPointMobile(x, y, cell) {
    const dispCol = Math.floor(x / cell);
    const band = rampartBand(cell);
    let dispRow;
    if (y < 3 * cell) {
        dispRow = Math.floor(y / cell);
    } else if (y < 3 * cell + band) {
        return null; // on the rampart band itself
    } else {
        dispRow = Math.floor((y - band) / cell);
    }
    if (dispCol < 0 || dispCol >= COLS || dispRow < 0 || dispRow >= ROWS) return null;
    // undo the flip so callers always get real (logical) board coordinates
    const col = isFlipped() ? COLS - 1 - dispCol : dispCol;
    const row = isFlipped() ? ROWS - 1 - dispRow : dispRow;
    return { col, row };
}

function drawBoardSquares(ctx, theme, cell) {
    // Unplayable house-row squares get the normal checkerboard coloring,
    // same as desktop - tried solid black to visually flag them, but
    // without desktop's other cues (hover, legal-move highlights on click,
    // the status prompt) to already make "not a real square" obvious, it
    // read as a mistake rather than a signal. Two of those squares now
    // carry the Strike/Raise buttons and one region carries the status
    // prompt (see main.js) - clearer affordances than a color could be.
    for (let row = 0; row < ROWS; row++) {
        for (let col = 0; col < COLS; col++) {
            const key = `${col},${row}`;
            const isCard = CARD_SQUARES.has(key);
            if (isCard && isCardStyle()) {
                // No grid gaps on mobile, so the card sits on a light square
                // with a hairline margin - that's what its rounded corners
                // reveal.
                ctx.fillStyle = theme.bgLight;
                ctx.fillRect(colX(col, cell), rowY(row, cell), cell, cell);
                const m = Math.max(0.75, cell * 0.02);
                drawCardSquare(ctx, colX(col, cell) + m, rowY(row, cell) + m, cell - 2 * m, cell - 2 * m,
                    theme.bgDark, CARD_TABLE.get(key), { indexScale: 0.2 });
                continue;
            }
            ctx.fillStyle = isCard ? theme.bgDark : theme.bgLight;
            ctx.fillRect(colX(col, cell), rowY(row, cell), cell, cell);
        }
    }
}

function drawRampart(ctx, theme, cell) {
    const band = rampartBand(cell);
    drawImageWhenReady(ctx, rampartImage, 0, 3 * cell, cell * COLS, band);
}

function drawCardLabels(ctx, cell) {
    if (isCardStyle()) return; // drawCardSquare already drew each card's index
    const fontSize = Math.max(9, Math.round(cell * 0.19));
    ctx.font = `bold ${fontSize}px Georgia, serif`;
    ctx.fillStyle = 'rgb(200,0,0)';
    ctx.textBaseline = 'top';
    for (const [key, card] of CARD_TABLE.entries()) {
        const [col, row] = key.split(',').map(Number);
        const x = colX(col, cell) + cell * 0.08;
        const y = rowY(row, cell) + cell * 0.05;
        ctx.fillText(card.rank, x, y);
        ctx.fillText(card.suit, x, y + fontSize * 1.05);
    }
}

const MOVE_DOT_COLOR = 'rgba(20, 90, 200, 0.55)';
const CAPTURE_RING_COLOR = 'rgb(20, 90, 200)';
const CAST_DOT_COLOR = 'rgb(159, 43, 104)';
const CLICKED_CARD_COLOR = 'rgb(100, 216, 220)';

// Same "breathing" pulse desktop's own clicked-card glow uses (render.js's
// pulsePhase) - shared period so it doesn't read as a different cadence
// between the two renderers if someone somehow saw both.
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

function drawDot(ctx, col, row, cell, color) {
    const cx = colX(col, cell) + cell / 2;
    const cy = rowY(row, cell) + cell / 2;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, cell * 0.14, 0, Math.PI * 2);
    ctx.fill();
}

function drawCaptureRing(ctx, col, row, cell, color) {
    const cx = colX(col, cell) + cell / 2;
    const cy = rowY(row, cell) + cell / 2;
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, cell * 0.05);
    ctx.beginPath();
    ctx.arc(cx, cy, cell * 0.42, 0, Math.PI * 2);
    ctx.stroke();
}

function strokeSquare(ctx, col, row, cell, color, width) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    const inset = width / 2 + 1;
    const x = colX(col, cell) + inset;
    const y = rowY(row, cell) + inset;
    const size = cell - inset * 2;
    if (isCardStyle() && CARD_SQUARES.has(`${col},${row}`)) {
        // follow the card's rounded corners (see drawBoardSquares)
        strokeRoundedRect(ctx, x, y, size, size, Math.max(1, cell * 0.07 - inset / 2));
    } else {
        ctx.strokeRect(x, y, size, size);
    }
}

function drawHighlights(ctx, state, ui, theme, cell) {
    const lineWidth = Math.max(2, cell * 0.06);
    if (ui.lastMoveSquares) {
        for (const [col, row] of ui.lastMoveSquares) {
            const isCard = CARD_SQUARES.has(`${col},${row}`);
            strokeSquare(ctx, col, row, cell, isCard ? theme.traceLight : theme.traceDark, lineWidth);
        }
    }
    if (ui.selected) {
        strokeSquare(ctx, ui.selected.col, ui.selected.row, cell, 'rgba(20, 90, 200, 0.9)', lineWidth);
    }
    if (ui.legalDestinations) {
        for (const [col, row] of ui.legalDestinations) {
            const captures = state.pieces.some((p) => p.col === col && p.row === row);
            if (captures) {
                drawCaptureRing(ctx, col, row, cell, CAPTURE_RING_COLOR);
            } else {
                drawDot(ctx, col, row, cell, MOVE_DOT_COLOR);
            }
        }
    }
    // Strike destinations are always an enemy raider's occupied square (the
    // piece being sent to the grave), so a plain dot would sit awkwardly on
    // top of the piece art - use the bracket-ring treatment there instead,
    // matching desktop; raise destinations are typically empty, so a dot.
    if (ui.castDestinations) {
        for (const { col, row, category } of ui.castDestinations) {
            if (category === 'strike') {
                drawCaptureRing(ctx, col, row, cell, CAST_DOT_COLOR);
            } else {
                drawDot(ctx, col, row, cell, CAST_DOT_COLOR);
            }
        }
    }
}

// The in-progress cast combo's own board card(s) (deck cards are a separate
// DOM highlight - see mobile-panels.js's .selected) - same pulsing teal
// glow as desktop's drawClickedBoardCards. Deliberately called AFTER
// drawPieces (see drawBoardMobile below), unlike the rest of drawHighlights
// above - desktop draws its equivalent before the piece too, which is fine
// there since its cells are much taller than the fixed 80x80 piece image,
// leaving a wide margin for the glow to show even underneath it. Mobile's
// cell is square with the piece drawn at 90% of it, leaving almost no
// margin - drawn underneath, the piece nearly completely hid this glow.
function drawClickedBoardCards(ctx, ui, cell) {
    if (!ui.clickedCards) return;
    const pulse = pulsePhase();
    ctx.save();
    ctx.strokeStyle = CLICKED_CARD_COLOR;
    ctx.shadowColor = CLICKED_CARD_COLOR;
    ctx.shadowBlur = 5 + 4 * pulse;
    ctx.lineWidth = 2.5;
    for (const card of ui.clickedCards) {
        if (card.source !== 'board') continue;
        const inset = 2;
        strokeRoundedRect(
            ctx, colX(card.col, cell) + inset, rowY(card.row, cell) + inset,
            cell - inset * 2, cell - inset * 2, 5);
    }
    ctx.restore();
}

function drawCheckHalo(ctx, cx, cy, radius) {
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    gradient.addColorStop(0, 'rgba(220, 30, 30, 0.55)');
    gradient.addColorStop(0.5, 'rgba(220, 30, 30, 0.3)');
    gradient.addColorStop(1, 'rgba(220, 30, 30, 0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
}

function drawPieces(ctx, state, cell) {
    const size = cell * 0.9;
    for (const p of state.pieces) {
        const img = pieceImage(p.color, p.piece);
        const cx = colX(p.col, cell) + cell / 2;
        const cy = rowY(p.row, cell) + cell / 2;
        if (p.piece === 'king' && state.in_check === p.color) {
            drawCheckHalo(ctx, cx, cy, cell * 0.65);
        }
        drawImageWhenReady(ctx, img, cx - size / 2, cy - size / 2, size, size);
    }
}

// ---- cast lightning effect (ported from render.js's own, itself ported
// from io_src_dev_ai/effects.py) - a separate copy rather than reusing
// render.js's triggerLightning/drawLightning directly, since those anchor
// to graveSlotPos/deckSlotPos, desktop-only pixel positions in an entirely
// different (1000x860 fixed) coordinate space that means nothing on a
// dynamically-sized mobile board. Deck/grave are DOM here, not on-canvas
// (see mobile-panels.js), so there's no equivalent anchor to reuse anyway -
// this instead flashes between the caster's own house row and the
// opposing one, fully expressible in mobile board coordinates from just
// the color, matching the spirit (a dramatic effect for casting) rather
// than the exact pixel positions. ----------------------------------------

// Longer than desktop's 500ms - deliberately kept this way (not reverted
// like the thickness/brightness below) so the effect has time to register
// on a phone screen mid-cast, per the user's explicit call to leave it. */
const LIGHTNING_DURATION_MS = 1200;
let mobileLightning = null; // { points: [[x,y],...], startTime }

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

export function triggerLightningMobile(color, cell) {
    // House-row center columns match isPlayableSquare's K/Q/J columns -
    // black's at row 0 (cols 2-4, center 3), white's at row ROWS-1 (cols
    // 5-7, center 6). Flashes from the caster's own house to the opposing
    // one, regardless of which side of the screen either currently is
    // (colX/rowY below already account for flip).
    const fromRow = color === 'white' ? ROWS - 1 : 0;
    const toRow = color === 'white' ? 0 : ROWS - 1;
    const fromCol = color === 'white' ? 6 : 3;
    const toCol = color === 'white' ? 3 : 6;
    const x1 = colX(fromCol, cell) + cell / 2;
    const y1 = rowY(fromRow, cell) + cell / 2;
    const x2 = colX(toCol, cell) + cell / 2;
    const y2 = rowY(toRow, cell) + cell / 2;
    mobileLightning = { points: generateLightningPoints(x1, y1, x2, y2), startTime: performance.now() };
}

export function isLightningActiveMobile() {
    return mobileLightning !== null && (performance.now() - mobileLightning.startTime) < LIGHTNING_DURATION_MS;
}

function drawLightningMobile(ctx, cell) {
    if (!mobileLightning) return;
    const elapsed = performance.now() - mobileLightning.startTime;
    if (elapsed >= LIGHTNING_DURATION_MS) {
        mobileLightning = null;
        return;
    }
    const fade = 1 - elapsed / LIGHTNING_DURATION_MS;

    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    const strokePass = (color, alpha, width) => {
        if (width <= 0) return;
        ctx.strokeStyle = color;
        ctx.globalAlpha = alpha;
        ctx.lineWidth = width;
        ctx.beginPath();
        mobileLightning.points.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
        ctx.stroke();
    };
    strokePass('rgb(100,150,255)', 0.31 * fade, 18 * fade); // outer bloom/glow
    strokePass('rgb(150,220,255)', 0.78 * fade, 10 * fade); // main bolt
    strokePass('rgb(220,240,255)', fade, 4 * fade);         // white-hot core

    if (elapsed < 16) {
        ctx.globalAlpha = 0.35;
        ctx.fillStyle = 'rgb(220,240,255)';
        const { width, height } = boardSize(cell);
        ctx.fillRect(0, 0, width, height);
    }
    ctx.restore();
}

export function drawBoardMobile(ctx, state, ui, cell) {
    const theme = getActiveTheme();
    const { width, height } = boardSize(cell);
    ctx.clearRect(0, 0, width, height);
    drawBoardSquares(ctx, theme, cell);
    drawRampart(ctx, theme, cell);
    drawCardLabels(ctx, cell);
    drawHighlights(ctx, state, ui, theme, cell);
    drawPieces(ctx, state, cell);
    drawClickedBoardCards(ctx, ui, cell);
    drawLightningMobile(ctx, cell); // drawn last so the glow overlays everything else
}
