// Canvas rendering for the board only - everything else (decks, cast-move
// lists, move history, prompts) is plain DOM/CSS, updated from main.js.

import { COLS, ROWS, CARD_SQUARES, CARD_TABLE } from './constants.js';

export const CELL = 64;
const RAMPART_BAND = 14;
export const BOARD_WIDTH = COLS * CELL;
export const BOARD_HEIGHT = ROWS * CELL + RAMPART_BAND;

// "green" theme from io_src_dev_ai/theme.py's default, ported directly so
// the web board reads the same way the desktop client does.
const THEME = {
    bgLight: 'rgb(234, 235, 200)',
    bgDark: 'rgb(119, 154, 88)',
    traceLight: 'rgb(244, 247, 116)',
    traceDark: 'rgb(172, 195, 51)',
    rampart: '#6b4a2f',
    rampartLine: '#8a6640',
};

const pieceImages = new Map();
function pieceImage(color, name) {
    const key = `${color}_${name}`;
    if (!pieceImages.has(key)) {
        const img = new Image();
        img.src = `assets/pieces/${key}.png`;
        pieceImages.set(key, img);
    }
    return pieceImages.get(key);
}

// Screen-space y for a given board row: rows 0-2 sit above the rampart
// band, rows 3-5 sit below it - mirrors game.py's show_bg exactly.
function rowY(row) {
    return row < 3 ? row * CELL : row * CELL + RAMPART_BAND;
}

export function colRowFromPoint(x, y) {
    const col = Math.floor(x / CELL);
    let row;
    if (y < 3 * CELL) {
        row = Math.floor(y / CELL);
    } else if (y < 3 * CELL + RAMPART_BAND) {
        return null; // clicked on the rampart band itself
    } else {
        row = Math.floor((y - RAMPART_BAND) / CELL);
    }
    if (col < 0 || col >= COLS || row < 0 || row >= ROWS) return null;
    return { col, row };
}

export function drawBoard(ctx, state, ui) {
    ctx.clearRect(0, 0, BOARD_WIDTH, BOARD_HEIGHT);

    // squares
    for (let row = 0; row < ROWS; row++) {
        for (let col = 0; col < COLS; col++) {
            const isCard = CARD_SQUARES.has(`${col},${row}`);
            ctx.fillStyle = isCard ? THEME.bgDark : THEME.bgLight;
            ctx.fillRect(col * CELL, rowY(row), CELL, CELL);
        }
    }

    // rampart band between row 2 and row 3
    ctx.fillStyle = THEME.rampart;
    ctx.fillRect(0, 3 * CELL, BOARD_WIDTH, RAMPART_BAND);
    ctx.fillStyle = THEME.rampartLine;
    ctx.fillRect(0, 3 * CELL + RAMPART_BAND / 2 - 1, BOARD_WIDTH, 2);

    // fixed card rank/suit labels
    ctx.font = 'bold 13px Georgia, serif';
    ctx.fillStyle = '#c00000';
    ctx.textBaseline = 'top';
    for (const [key, card] of CARD_TABLE.entries()) {
        const [col, row] = key.split(',').map(Number);
        const x = col * CELL + 4;
        const y = rowY(row) + 3;
        ctx.fillText(card.rank, x, y);
        ctx.fillText(card.suit, x, y + 15);
    }

    // last-move highlight
    if (ui.lastMoveSquares) {
        for (const [col, row] of ui.lastMoveSquares) {
            const isCard = CARD_SQUARES.has(`${col},${row}`);
            ctx.strokeStyle = isCard ? THEME.traceLight : THEME.traceDark;
            ctx.lineWidth = 4;
            ctx.strokeRect(col * CELL + 2, rowY(row) + 2, CELL - 4, CELL - 4);
        }
    }

    // selected piece origin
    if (ui.selected) {
        ctx.strokeStyle = 'rgba(20, 90, 200, 0.9)';
        ctx.lineWidth = 4;
        ctx.strokeRect(ui.selected.col * CELL + 2, rowY(ui.selected.row) + 2, CELL - 4, CELL - 4);
    }

    // legal destinations (dots)
    if (ui.legalDestinations) {
        ctx.fillStyle = 'rgba(20, 90, 200, 0.55)';
        for (const [col, row] of ui.legalDestinations) {
            const cx = col * CELL + CELL / 2;
            const cy = rowY(row) + CELL / 2;
            ctx.beginPath();
            ctx.arc(cx, cy, CELL * 0.14, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    // cast-option destination(s), if the player is browsing a strike/raise list
    if (ui.castHighlight) {
        const [col, row] = ui.castHighlight;
        ctx.strokeStyle = 'rgba(200, 40, 40, 0.9)';
        ctx.lineWidth = 4;
        ctx.setLineDash([6, 4]);
        ctx.strokeRect(col * CELL + 2, rowY(row) + 2, CELL - 4, CELL - 4);
        ctx.setLineDash([]);
    }

    // pieces
    for (const p of state.pieces) {
        const img = pieceImage(p.color, p.piece);
        const x = p.col * CELL;
        const y = rowY(p.row);
        if (img.complete && img.naturalWidth > 0) {
            ctx.drawImage(img, x + 3, y + 3, CELL - 6, CELL - 6);
        } else {
            img.onload = () => ctx.drawImage(img, x + 3, y + 3, CELL - 6, CELL - 6);
        }
    }
}
