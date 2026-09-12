// Achievement badge display metadata - phase 1 only (see server/badges.py
// for exactly what's checked and when). `icon` is a plain emoji placeholder
// until real trophy/medal art replaces it - swap the value here, nothing
// else needs to change since profile.js only ever reads this field.
//
// Grouped into the same four categories the design was pitched in, in
// display order.

export const BADGE_CATEGORIES = [
    {
        name: 'The Ladder Trophies',
        subtitle: 'Rating milestones - permanent once reached, even if your rating later drops.',
        badges: [
            { id: 'adept', name: 'Adept', description: 'Reached a peak rating of 1500.', icon: '🥉' },
            { id: 'tactician', name: 'Tactician', description: 'Reached a peak rating of 1800.', icon: '🥈' },
            { id: 'vanguard', name: 'Vanguard', description: 'Reached a peak rating of 2000.', icon: '🥇' },
            { id: 'apex', name: 'Apex', description: 'Reached a peak rating of 2200.', icon: '🏆' },
        ],
    },
    {
        name: 'The Slayer Trophies',
        subtitle: 'Matchup feats.',
        badges: [
            { id: 'giant_slayer', name: 'Giant Slayer', description: 'Defeated an opponent rated 150+ points higher than you.', icon: '🗡️' },
            { id: 'kingslayer', name: 'Kingslayer', description: 'Defeated an opponent holding Vanguard rank or higher.', icon: '👑' },
        ],
    },
    {
        name: 'The Execution Medals',
        subtitle: 'Tactical feats.',
        badges: [
            { id: 'blitzkrieg', name: 'Blitzkrieg', description: 'Won a rated game in a handful of moves.', icon: '⚡' },
        ],
    },
    {
        name: 'The Tenure Badges',
        subtitle: 'Volume and dedication.',
        badges: [
            { id: 'first_blood', name: 'First Blood', description: 'Completed your first rated match.', icon: '🩸' },
            { id: 'centurion', name: 'Centurion', description: 'Completed 100 rated matches.', icon: '💯' },
            { id: 'veteran', name: 'Veteran of the Front', description: 'Completed 1,000 rated matches.', icon: '🎖️' },
        ],
    },
];

// Flat id -> metadata lookup, for rendering a single earned badge without
// re-walking the category list.
export const BADGES_BY_ID = Object.fromEntries(
    BADGE_CATEGORIES.flatMap((cat) => cat.badges.map((b) => [b.id, b])),
);
