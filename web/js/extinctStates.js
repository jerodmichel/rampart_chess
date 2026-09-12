// Historical/extinct states, for the "Not finding your state?" fallback
// beneath the regular country picker (see profile.js) - these have no ISO
// 3166-1 code and no Unicode flag emoji, so unlike COUNTRIES/flagEmoji()
// (countries.js) they need a real image asset per entry. Starting with
// just Europe (see web/assets/flags/extinct/SOURCES.md for where each SVG
// came from) - more regions can follow the same pattern once this is in.
//
// `code` is our own invented short id (never a real ISO code - accepted
// by the same server-side country field, see accounts.py's _COUNTRY_RE).

import { COUNTRIES, flagEmoji } from './countries.js';

export const EXTINCT_STATES = [
    { code: 'AUEM', name: 'Austrian Empire', flag: 'assets/flags/extinct/auem.svg' },
    { code: 'AUHU', name: 'Austria-Hungary', flag: 'assets/flags/extinct/auhu.svg' },
    { code: 'BYZ', name: 'Byzantine Empire', flag: 'assets/flags/extinct/byz.svg' },
    { code: 'CSK', name: 'Czechoslovakia', flag: 'assets/flags/extinct/csk.svg' },
    { code: 'DDR', name: 'East Germany', flag: 'assets/flags/extinct/ddr.svg' },
    { code: 'GERE', name: 'German Empire', flag: 'assets/flags/extinct/gere.svg' },
    { code: 'HRE', name: 'Holy Roman Empire', flag: 'assets/flags/extinct/hre.svg' },
    { code: 'ITKG', name: 'Kingdom of Italy', flag: 'assets/flags/extinct/itkg.svg' },
    { code: 'LTGD', name: 'Grand Duchy of Lithuania', flag: 'assets/flags/extinct/ltgd.svg' },
    { code: 'MILA', name: 'Duchy of Milan', flag: 'assets/flags/extinct/mila.svg' },
    { code: 'OTTO', name: 'Ottoman Empire', flag: 'assets/flags/extinct/otto.svg' },
    { code: 'PAPS', name: 'Papal States', flag: 'assets/flags/extinct/paps.svg' },
    { code: 'PRUS', name: 'Prussia', flag: 'assets/flags/extinct/prus.svg' },
    { code: 'SARD', name: 'Kingdom of Sardinia', flag: 'assets/flags/extinct/sard.svg' },
    { code: 'SCG', name: 'Serbia and Montenegro', flag: 'assets/flags/extinct/scg.svg' },
    { code: 'SWNO', name: 'Sweden-Norway', flag: 'assets/flags/extinct/swno.svg' },
    { code: 'TUSC', name: 'Grand Duchy of Tuscany', flag: 'assets/flags/extinct/tusc.svg' },
    { code: 'UPR', name: "Ukrainian People's Republic", flag: 'assets/flags/extinct/upr.svg' },
    { code: 'USSR', name: 'Soviet Union', flag: 'assets/flags/extinct/ussr.svg' },
    { code: 'YUG', name: 'Yugoslavia', flag: 'assets/flags/extinct/yug.svg' },
];

// `myProfile.country`/a player's `country` can hold either a real ISO code
// or one of the codes above - these two helpers are the single place that
// knows how to turn that one field into display output, so call sites
// (profile.js, main.js's board player labels) don't each re-implement the
// "which list is this code from" check.

// A flag as a DOM node - a text node for a real country (flagEmoji()'s
// Unicode glyph) or an <img> for an extinct state. null if code is falsy
// or unrecognized by either list.
export function flagNode(code) {
    if (!code) return null;
    const emoji = flagEmoji(code);
    if (emoji) return document.createTextNode(emoji);
    const extinct = EXTINCT_STATES.find((s) => s.code === code);
    if (!extinct) return null;
    const img = document.createElement('img');
    img.src = extinct.flag;
    img.alt = extinct.name;
    img.className = 'extinctFlagIcon';
    return img;
}

// The display name for `code` from whichever list it's in, or null.
export function stateName(code) {
    const country = COUNTRIES.find((c) => c.code === code);
    if (country) return country.name;
    const extinct = EXTINCT_STATES.find((s) => s.code === code);
    return extinct ? extinct.name : null;
}
