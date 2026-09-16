// DOM (not canvas-drawn) content for the mobile board's side panels - deck
// and graveyard, both pure display for now (no click interaction, unlike
// desktop's canvas-based deck/cast-button UI - that's a separate, later
// piece of work). Lives beside #boardCanvas in #mobileBoardRow (index.html)
// rather than inside the canvas itself, since it only ever makes sense in
// the leftover width next to the height-bound square board (see
// render-mobile.js) - a separate DOM layer is what lets it sit there
// independent of the canvas's own size.
//
// Deck styling (a plain rank+suit row) is ported from the old mobile/
// prototype's own renderDeck - the one piece of that prototype worth
// carrying over verbatim, since it was always a display-only list there
// too (that prototype's actual cast interaction went through a separate
// precomputed move-list UI, never the deck itself). The used/unused
// treatment matches desktop instead, though: a used slot shows the real
// card-back art (object-fit:contain, so it's never distorted regardless of
// how the slot's own proportions compare to the image's - deliberately not
// forcing this slot to desktop's own 90x26 aspect ratio, which would make
// it too thin to comfortably tap), not just a dimmed/struck-through label.

import { RANKS, DECK_SUIT } from './constants.js';
import { deadPieceImageSrc, getActiveEmblemSrc, getActiveCardBackSrc, getActiveTheme, isFlipped } from './render.js';

// #mobileDeckBlack/#mobileGraveBlack are the physically-LEFT panel elements,
// #mobileDeckWhite/#mobileGraveWhite the physically-RIGHT ones - named for
// their default (unflipped) occupant, not a permanent color assignment.
// screenSide() below (same logic as render.js's own screenSide, used for
// desktop's deck/grave placement) decides which physical side each color's
// content actually lands on for a given flip state.
const leftDeckEl = document.getElementById('mobileDeckBlack');
const rightDeckEl = document.getElementById('mobileDeckWhite');
const leftGraveEl = document.getElementById('mobileGraveBlack');
const rightGraveEl = document.getElementById('mobileGraveWhite');

function screenSide(color) {
    if (!isFlipped()) return color;
    return color === 'black' ? 'white' : 'black';
}
const emblemBottomLeftEl = document.getElementById('mobileEmblemBottomLeft');
const emblemTopRightEl = document.getElementById('mobileEmblemTopRight');

// Keyed by a cheap string fingerprint of each array so a redraw triggered
// by something unrelated (the highlight-pulse animation loop, hover state)
// doesn't needlessly rebuild this DOM on every frame - only an actual
// cast/capture changes any of these.
let lastBlackDeckKey = null;
let lastWhiteDeckKey = null;
let lastBlackGraveKey = null;
let lastWhiteGraveKey = null;
let lastEmblemSrc = null;

// Set once by main.js (avoids mobile-panels.js importing main.js directly,
// which already imports from here) - called when a non-used deck card is
// tapped, with the same {source:'deck', color, rank} shape the desktop
// canvas's own deck-click handling builds.
let deckCardTapHandler = null;
export function setDeckCardTapHandler(fn) {
    deckCardTapHandler = fn;
}

function renderDeckColumn(el, colorLabel, deckArray, selectedRanks, reversed) {
    el.innerHTML = '';
    const suit = DECK_SUIT[colorLabel];
    // Matches desktop's drawDecks exactly: white's deck reads as a "card
    // square" color, black's as a "non-card square" color - not an
    // arbitrary fixed color of its own.
    const theme = getActiveTheme();
    const background = colorLabel === 'white' ? theme.bgDark : theme.bgLight;
    // Matches desktop's own deckSlotPos: the physically-left deck lists
    // rank 0 at the top running down to rank 12 at the bottom, but the
    // physically-right one runs the OTHER way (rank 0 at the bottom, rank
    // 12 at the top) - without this, switching which deck lands on which
    // side (via screenSide()/board flip) would show the same deck in a
    // different order than the non-fullscreen board does.
    const order = reversed ? [...RANKS.keys()].reverse() : [...RANKS.keys()];
    order.forEach((i) => {
        const rank = RANKS[i];
        const used = deckArray[i];
        const row = document.createElement('div');
        row.className = 'mobileDeckCard' + (used ? ' used' : '');
        if (selectedRanks.has(i)) row.classList.add('selected');
        row.style.background = background;
        if (used) {
            // Matches desktop's drawDecks: a used slot shows ONLY the
            // card-back art, no rank/suit text underneath it. A CSS
            // background-image (not a child <img> with object-fit) -
            // background-size:100% 100% resolves directly against this
            // element's own padding-box with none of the nested-element
            // percentage/aspect-ratio-parent quirks that made an <img>
            // child intermittently render narrower than its slot despite
            // computed styles showing it as an exact (or overflowing)
            // fill.
            row.style.backgroundImage = `url(${getActiveCardBackSrc()})`;
            row.style.backgroundSize = '100% 100%';
            row.style.backgroundRepeat = 'no-repeat';
        } else {
            row.textContent = `${rank} ${suit}`;
            row.addEventListener('click', () => {
                if (deckCardTapHandler) deckCardTapHandler({ color: colorLabel, rank: i });
            });
        }
        el.appendChild(row);
    });
}

function renderGraveGrid(el, color, graveArray) {
    el.innerHTML = '';
    for (const name of graveArray) {
        const slot = document.createElement('div');
        slot.className = 'mobileGraveSlot';
        if (name) {
            const img = document.createElement('img');
            img.src = deadPieceImageSrc(color, name);
            img.alt = '';
            slot.appendChild(img);
        }
        el.appendChild(slot);
    }
}

// Same emblem the desktop canvas shows (render.js's drawEmblems), one at
// the bottom of black's column and one at the top of white's - matches
// desktop's bottom-left/top-right placement. Doesn't depend on `state` (only
// on the active theme), so it's not keyed to a state fingerprint like the
// deck/grave renders above - just a plain equality check against whatever
// changed it last (a theme switch, via Display Settings).
function renderMobileEmblems() {
    const src = getActiveEmblemSrc();
    if (src === lastEmblemSrc) return;
    lastEmblemSrc = src;
    emblemBottomLeftEl.src = src;
    emblemTopRightEl.src = src;
}

export function renderMobilePanels(state, clickedCards) {
    renderMobileEmblems();
    const blackSelected = new Set(
        clickedCards.filter((c) => c.source === 'deck' && c.color === 'black').map((c) => c.rank));
    const whiteSelected = new Set(
        clickedCards.filter((c) => c.source === 'deck' && c.color === 'white').map((c) => c.rank));
    const blackEl = screenSide('black') === 'black' ? leftDeckEl : rightDeckEl;
    const whiteEl = screenSide('white') === 'black' ? leftDeckEl : rightDeckEl;
    const blackGraveEl = screenSide('black') === 'black' ? leftGraveEl : rightGraveEl;
    const whiteGraveEl = screenSide('white') === 'black' ? leftGraveEl : rightGraveEl;
    // Includes the active card-back art, the current combo selection, AND
    // flip state in the key, not just the deck array itself - a theme
    // switch changes which image a used slot should show, toggling a card
    // into/out of the combo changes its .selected highlight, and flipping
    // the board changes which physical panel this color belongs in, even
    // though none of those actually used/unused a card.
    const cardBack = getActiveCardBackSrc();
    const flipTag = isFlipped() ? 'f' : 'n';
    const blackDeckKey = `${state.black_deck.join(',')}|${cardBack}|${[...blackSelected].join(',')}|${flipTag}`;
    const whiteDeckKey = `${state.white_deck.join(',')}|${cardBack}|${[...whiteSelected].join(',')}|${flipTag}`;
    if (blackDeckKey !== lastBlackDeckKey) {
        renderDeckColumn(blackEl, 'black', state.black_deck, blackSelected, blackEl === rightDeckEl);
        lastBlackDeckKey = blackDeckKey;
    }
    if (whiteDeckKey !== lastWhiteDeckKey) {
        renderDeckColumn(whiteEl, 'white', state.white_deck, whiteSelected, whiteEl === rightDeckEl);
        lastWhiteDeckKey = whiteDeckKey;
    }

    const blackGraveKey = `${state.black_grave.join(',')}|${flipTag}`;
    const whiteGraveKey = `${state.white_grave.join(',')}|${flipTag}`;
    if (blackGraveKey !== lastBlackGraveKey) {
        renderGraveGrid(blackGraveEl, 'black', state.black_grave);
        lastBlackGraveKey = blackGraveKey;
    }
    if (whiteGraveKey !== lastWhiteGraveKey) {
        renderGraveGrid(whiteGraveEl, 'white', state.white_grave);
        lastWhiteGraveKey = whiteGraveKey;
    }
}
