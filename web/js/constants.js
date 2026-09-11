// Board/screen geometry, ported from io_src_dev_ai/const.py - this file
// intentionally mirrors that one's numbers exactly (not just "close
// enough") so the web board reads as the same game, not a re-skin.

export const COLS = 10;
export const ROWS = 6;

export const WIDTH = 800;   // board pixel width (matches const.py)
export const HEIGHT = 800;  // board pixel height (matches const.py)

export const RWIDTH = Math.floor(WIDTH / COLS);   // 80
export const RHEIGHT = Math.floor(HEIGHT / ROWS);  // 133

export const RAMPART_HEIGHT = 20;
export const DECK = 13;
export const CEM_HEIGHT = 450;
export const CWIDTH = 90;
export const CHEIGHT = Math.floor((HEIGHT - CEM_HEIGHT - 10) / DECK);
export const GRAVES = 9;
export const GWIDTH = CWIDTH;
export const GHEIGHT = Math.floor((CEM_HEIGHT - 150) / GRAVES);

// The pygame client's "design resolution" (main.py: WIDTH+200 x
// HEIGHT+40+RAMPART_HEIGHT) - 100px deck/grave margins each side of the
// board, 40px + the rampart band below it for the prompt/buttons.
export const BOARD_X = 100; // board's left edge within the design canvas
export const DESIGN_WIDTH = WIDTH + 200;
export const DESIGN_HEIGHT = HEIGHT + 40 + RAMPART_HEIGHT;

export const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

// blackjack-style card value, ported from const.py's CARD_VAL - ace is 1
// here; the "or 11" flexibility is handled separately by hand-sum logic.
export const CARD_VAL = {
    0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10,
    10: 10, 11: 10, 12: 10,
};
export const SUITS = ['♣', '♥', '♦', '♠']; // clubs, hearts, diamonds, spades

// Fixed card printed on each "card square" of the board, keyed by "col,row".
// Ported directly from const.py's TABLE_DICT-building loop (same formulas,
// same square set) rather than hand-copying its output, so this can't
// silently drift from the Python source of truth. (Verified byte-for-byte
// against a live dump of TABLE_DICT while building this.)
export function buildCardSquares() {
    const cardSquares = new Set();
    for (const x of [2, 3, 4]) cardSquares.add(`${x},0`);
    for (let x = 0; x < COLS; x++) if (x % 2 === 0) cardSquares.add(`${x},1`);
    for (let x = 0; x < COLS; x++) if (x % 2 === 1) cardSquares.add(`${x},2`);
    for (let x = 0; x < COLS; x++) if (x % 2 === 0) cardSquares.add(`${x},3`);
    for (let x = 0; x < COLS; x++) if (x % 2 === 1) cardSquares.add(`${x},4`);
    for (const x of [5, 6, 7]) cardSquares.add(`${x},5`);
    return cardSquares;
}

export function buildTable() {
    // Map "col,row" -> {rank, suit} for every card square, mirroring
    // const.py's TABLE_DICT exactly (rank/suit are raw indices there;
    // here they're resolved straight to display strings since that's
    // all the client ever needs them for).
    const table = new Map();
    const set = (x, y, rank, suit) => table.set(`${x},${y}`, { rank: RANKS[rank], suit: SUITS[suit] });

    for (const x of [2, 3, 4]) {
        if (x === 2) set(x, 0, 12, 3);
        else if (x === 3) set(x, 0, 11, 3);
        else if (x === 4) set(x, 0, 10, 3);
    }
    for (let x = 0; x < COLS; x++) if (x % 2 === 0) set(x, 1, x, 3);
    for (let x = 0; x < COLS; x++) if (x % 2 === 1) set(x, 2, x, 3);
    for (let x = 0; x < COLS; x++) if (x % 2 === 0) set(x, 3, COLS - x - 1, 2);
    for (let x = 0; x < COLS; x++) if (x % 2 === 1) set(x, 4, COLS - x - 1, 2);
    for (const x of [5, 6, 7]) {
        if (x === 5) set(x, 5, 10, 2);
        else if (x === 6) set(x, 5, 11, 2);
        else if (x === 7) set(x, 5, 12, 2);
    }
    return table;
}

export const CARD_SQUARES = buildCardSquares();
export const CARD_TABLE = buildTable();

// Deck card suits are fixed: black's deck is clubs, white's deck is spades
// (see const.py's DECK_TABLE). This is the *display* symbol only.
export const DECK_SUIT = { black: SUITS[0], white: SUITS[3] };

// The raw suit index Card objects actually carry server-side is different
// from the display symbol above (DECK_TABLE only changes what's *shown*
// for white's deck, not the stored suit) - verified against a live
// GameSession: deck cards are suit 0 (black) / 1 (white); board cards are
// 2 or 3 depending on which half of the board printed them (CARD_TABLE).
// Needed to match a manually-selected combo against the server's
// /cast_moves response, which reports cards using these raw indices.
export const DECK_SUIT_INDEX = { black: 0, white: 1 };

export function boardCardSuitIndex(col, row) {
    const symbol = CARD_TABLE.get(`${col},${row}`).suit;
    return SUITS.indexOf(symbol);
}

export function boardCardRankIndex(col, row) {
    const symbol = CARD_TABLE.get(`${col},${row}`).rank;
    return RANKS.indexOf(symbol);
}

// Row letters, bottom (white's back rank) to top: a..f, matching
// Square.get_alpharow / the notation parser in main.js.
export const ROW_LETTERS = ['f', 'e', 'd', 'c', 'b', 'a'];
