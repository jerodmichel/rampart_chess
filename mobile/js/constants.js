// Board geometry and card-layout constants, ported from io_src_dev_ai/const.py.
// Only what the client needs to render/hit-test the board - the rules
// engine itself stays server-side (see server/game_session.py).

export const COLS = 10;
export const ROWS = 6;

export const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
export const SUITS = ['♣', '♥', '♦', '♠']; // clubs, hearts, diamonds, spades

// Fixed card printed on each "card square" of the board, keyed by "col,row".
// Ported directly from const.py's TABLE_DICT-building loop (same formulas,
// same square set) rather than hand-copying its output, so this can't
// silently drift from the Python source of truth.
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
// (see const.py's DECK_TABLE).
export const DECK_SUIT = { black: SUITS[0], white: SUITS[3] };

export const GRAVES = 9;
