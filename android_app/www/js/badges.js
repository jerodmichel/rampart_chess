// Achievement badge display metadata - phase 1 only (see server/badges.py
// for exactly what's checked and when). Most badges still use `icon`, a
// plain emoji placeholder; a few now have a real `image` (a small PNG
// under assets/badges/, sourced from Flaticon - see
// assets/badges/SOURCES.md for attribution) instead, as real medieval-
// themed art replaces the emoji placeholders one at a time. profile.js's
// renderBadges() checks for `image` first and only falls back to the
// `icon` emoji glyph when a badge has no `image` set - nothing else needs
// to change here to swap a badge from one to the other.
//
// Grouped into the same four categories the design was pitched in, in
// display order.

export const BADGE_CATEGORIES = [
    {
        name: 'The Ladder Trophies',
        subtitle: 'Rating milestones - permanent once reached, even if your rating later drops.',
        badges: [
            { id: 'adept', name: 'Adept', description: 'Reached a peak rating of 1500.', image: 'assets/badges/adept.png' },
            { id: 'tactician', name: 'Tactician', description: 'Reached a peak rating of 1800.', image: 'assets/badges/tactician.png' },
            { id: 'vanguard', name: 'Vanguard', description: 'Reached a peak rating of 2000.', image: 'assets/badges/vanguard.png' },
            { id: 'apex', name: 'Apex', description: 'Reached a peak rating of 2200.', image: 'assets/badges/apex.png' },
        ],
    },
    {
        name: 'The Slayer Trophies',
        subtitle: 'Matchup feats.',
        badges: [
            { id: 'giant_slayer', name: 'Giant Slayer', description: 'Defeated an opponent rated 150+ points higher than you.', image: 'assets/badges/giant_slayer.png' },
            { id: 'kingslayer', name: 'Kingslayer', description: 'Defeated an opponent holding Vanguard rank or higher.', image: 'assets/badges/kingslayer.png' },
            { id: 'nemesis', name: 'Nemesis', description: 'Defeated the exact same opponent three times in a row.', image: 'assets/badges/nemesis.png' },
            { id: 'unbreakable', name: 'Unbreakable', description: "Beat an opponent who had beaten you in your last three encounters.", image: 'assets/badges/unbreakable.png' },
        ],
    },
    {
        name: 'The Execution Medals',
        subtitle: 'Tactical feats.',
        badges: [
            { id: 'first_blood', name: 'First Blood', description: 'Delivered checkmate to win a rated game for the first time.', image: 'assets/badges/first_blood.png' },
            { id: 'blitzkrieg', name: 'Blitzkrieg', description: 'Won a rated game in a handful of moves.', image: 'assets/badges/blitzkrieg.png' },
            { id: 'mate_by_capture', name: 'The Trap', description: "Won by mate by capture - infiltrating the enemy king's house while their king stood off a card square.", image: 'assets/badges/mate_by_capture.png' },
        ],
    },
    {
        name: 'The Tenure Badges',
        subtitle: 'Volume and dedication.',
        badges: [
            { id: 'centurion', name: 'Centurion', description: 'Completed 100 rated matches.', image: 'assets/badges/centurion.png' },
            { id: 'the_grind', name: 'The Grind', description: 'Played 5 rated matches in a single 24-hour period.', image: 'assets/badges/the_grind.png' },
            { id: 'veteran', name: 'Veteran of the Front', description: 'Completed 1,000 rated matches.', image: 'assets/badges/veteran.png' },
        ],
    },
];

// Flat id -> metadata lookup, for rendering a single earned badge without
// re-walking the category list.
export const BADGES_BY_ID = Object.fromEntries(
    BADGE_CATEGORIES.flatMap((cat) => cat.badges.map((b) => [b.id, b])),
);

// One badge per category - whichever of that category's badges has the
// most recent unlocked_at in `earned` ({badge_id: {unlocked_at}}, as
// api.playerBadges() returns) - skipping a category entirely if nothing
// in it is earned yet. Used for the small trophy row under a player's
// name (main.js) rather than the full Profile grid.
//
// "Most recent" stands in for "highest" here: the Ladder/Tenure
// categories have a real tier order (you can't unlock Apex before
// Vanguard, or Veteran before Centurion), so "most recent" already equals
// "highest tier" for those without any special-casing. The Slayer/
// Execution categories have no inherent ordering at all - their badges
// are independent one-off feats - so "most recent" is a principled
// stand-in there too (their newest feat) rather than an arbitrary pick
// by array order.
export function highestPerCategory(earned) {
    const result = [];
    for (const category of BADGE_CATEGORIES) {
        let best = null;
        let bestUnlockedAt = -Infinity;
        for (const badge of category.badges) {
            const unlock = earned[badge.id];
            if (!unlock) continue;
            if (unlock.unlocked_at > bestUnlockedAt) {
                best = badge;
                bestUnlockedAt = unlock.unlocked_at;
            }
        }
        if (best) result.push(best);
    }
    return result;
}
