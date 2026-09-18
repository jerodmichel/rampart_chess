// Historical/extinct states, for the "Not finding your state?" fallback
// beneath the regular country picker (see profile.js) - these have no ISO
// 3166-1 code and no Unicode flag emoji, so unlike COUNTRIES/flagEmoji()
// (countries.js) they need a real image asset per entry. Sourced from
// Wikimedia Commons' "Flags of extinct states" category, one single
// canonical source (see web/assets/flags/extinct/SOURCES.md for where each
// SVG came from, which region it's from, and a note on ~10 Europe entries
// that used to come from a different category and were removed to keep
// this list matching exactly one source) - Africa/Americas/Australia-
// Oceania done (all 27, all 31, all 17), Asia underway (29 of 46 unique
// states - 17 more hit Wikimedia's rate limit mid-batch and are still
// pending), Europe just getting started (10 of 78).
//
// `code` is our own invented short id (never a real ISO code - accepted
// by the same server-side country field, see accounts.py's _COUNTRY_RE).
// Sorted by code, matching insertion order - not alphabetical by name.

import { COUNTRIES, flagEmoji } from './countries.js';

export const EXTINCT_STATES = [
    { code: 'ACEH', name: 'Aceh Sultanate', flag: 'assets/flags/extinct/aceh.png' },
    { code: 'ACR1', name: 'First Republic of Acre', flag: 'assets/flags/extinct/acr1.svg' },
    { code: 'ACR3', name: 'Third Republic of Acre', flag: 'assets/flags/extinct/acr3.svg' },
    { code: 'ALBA', name: 'Principality of Albania', flag: 'assets/flags/extinct/alba.svg' },
    { code: 'ANGU', name: 'Republic of Anguilla', flag: 'assets/flags/extinct/angu.svg' },
    { code: 'ANJO', name: 'State of Anjouan', flag: 'assets/flags/extinct/anjo.svg' },
    { code: 'ARAG', name: 'Crown of Aragon', flag: 'assets/flags/extinct/arag.svg' },
    { code: 'ARAR', name: 'Republic of Ararat', flag: 'assets/flags/extinct/arar.svg' },
    { code: 'ARAU', name: 'Kingdom of Araucanía and Patagonia', flag: 'assets/flags/extinct/arau.svg' },
    { code: 'ASHE', name: 'Ashanti Empire', flag: 'assets/flags/extinct/ashe.svg' },
    { code: 'AUEM', name: 'Austrian Empire', flag: 'assets/flags/extinct/auem.svg' },
    { code: 'AUHU', name: 'Austro-Hungarian Empire', flag: 'assets/flags/extinct/auhu.svg' },
    { code: 'BANT', name: 'Sultanate of Banten', flag: 'assets/flags/extinct/bant.svg' },
    { code: 'BAU', name: 'Kingdom of Bau', flag: 'assets/flags/extinct/bau.svg' },
    { code: 'BIAF', name: 'Biafra', flag: 'assets/flags/extinct/biaf.svg' },
    { code: 'BNB', name: 'Republic of Biak-na-Bato', flag: 'assets/flags/extinct/bnb.svg' },
    { code: 'BOPH', name: 'Bophuthatswana', flag: 'assets/flags/extinct/boph.svg' },
    { code: 'BORA', name: 'Kingdom of Bora Bora', flag: 'assets/flags/extinct/bora.svg' },
    { code: 'BURM', name: 'State of Burma', flag: 'assets/flags/extinct/burm.svg' },
    { code: 'BYZ', name: 'Byzantine Empire', flag: 'assets/flags/extinct/byz.svg' },
    { code: 'CABI', name: 'Cabinda', flag: 'assets/flags/extinct/cabi.svg' },
    { code: 'CALR', name: 'California Republic', flag: 'assets/flags/extinct/calr.svg' },
    { code: 'CAST', name: 'Kingdom of Castile', flag: 'assets/flags/extinct/cast.svg' },
    { code: 'CHAM', name: 'Kingdom of Champasak', flag: 'assets/flags/extinct/cham.svg' },
    { code: 'CIFI', name: 'Confederacy of Independent Kingdoms of Fiji', flag: 'assets/flags/extinct/cifi.svg' },
    { code: 'CISK', name: 'Ciskei', flag: 'assets/flags/extinct/cisk.svg' },
    { code: 'CSA', name: 'Confederate States of America', flag: 'assets/flags/extinct/csa.svg' },
    { code: 'CSK', name: 'Czechoslovakia', flag: 'assets/flags/extinct/csk.svg' },
    { code: 'CYRE', name: 'Emirate of Cyrenaica', flag: 'assets/flags/extinct/cyre.svg' },
    { code: 'DDR', name: 'East Germany', flag: 'assets/flags/extinct/ddr.svg' },
    { code: 'DESE', name: 'State of Deseret', flag: 'assets/flags/extinct/dese.svg' },
    { code: 'EFLA', name: 'Republic of East Florida', flag: 'assets/flags/extinct/efla.svg' },
    { code: 'ENGL', name: 'Kingdom of England', flag: 'assets/flags/extinct/engl.svg' },
    { code: 'ENRI', name: 'Republic of Entre Ríos', flag: 'assets/flags/extinct/enri.svg' },
    { code: 'ETUR', name: 'East Turkestan', flag: 'assets/flags/extinct/etur.svg' },
    { code: 'EZO', name: 'Republic of Ezo', flag: 'assets/flags/extinct/ezo.svg' },
    { code: 'FEAR', name: 'Far Eastern Republic', flag: 'assets/flags/extinct/fear.svg' },
    { code: 'FIJI', name: 'Kingdom of Fiji', flag: 'assets/flags/extinct/fiji.svg' },
    { code: 'FORM', name: 'Republic of Formosa', flag: 'assets/flags/extinct/form.svg' },
    { code: 'FRANC', name: 'Franceville', flag: 'assets/flags/extinct/franc.svg' },
    { code: 'FRBR', name: 'Kingdom of France (Bourbon Restoration)', flag: 'assets/flags/extinct/frbr.svg' },
    { code: 'FRCA', name: 'Federal Republic of Central America', flag: 'assets/flags/extinct/frca.svg' },
    { code: 'FSAR', name: 'Federation of South Arabia', flag: 'assets/flags/extinct/fsar.svg' },
    { code: 'GENO', name: 'Republic of Genoa', flag: 'assets/flags/extinct/geno.svg' },
    { code: 'GERC', name: 'German Confederation', flag: 'assets/flags/extinct/gerc.svg' },
    { code: 'GORY', name: 'Goryeo', flag: 'assets/flags/extinct/gory.svg' },
    { code: 'HAIL', name: "Ha'il State", flag: 'assets/flags/extinct/hail.svg' },
    { code: 'HAWA', name: 'Kingdom of Hawaiʻi', flag: 'assets/flags/extinct/hawa.svg' },
    { code: 'HEJA', name: 'Kingdom of Hejaz', flag: 'assets/flags/extinct/heja.svg' },
    { code: 'HRE', name: 'Holy Roman Empire', flag: 'assets/flags/extinct/hre.svg' },
    { code: 'HUAH', name: 'Kingdom of Huahine', flag: 'assets/flags/extinct/huah.svg' },
    { code: 'HYDE', name: 'Hyderabad State', flag: 'assets/flags/extinct/hyde.svg' },
    { code: 'IREF', name: 'Islands of Refreshment', flag: 'assets/flags/extinct/iref.svg' },
    { code: 'JAPN', name: 'Empire of Japan', flag: 'assets/flags/extinct/japn.svg' },
    { code: 'JOSE', name: 'Joseon', flag: 'assets/flags/extinct/jose.svg' },
    { code: 'JULI', name: 'Juliana Republic', flag: 'assets/flags/extinct/juli.svg' },
    { code: 'KATA', name: 'State of Katanga', flag: 'assets/flags/extinct/kata.svg' },
    { code: 'KHME', name: 'Khmer Empire', flag: 'assets/flags/extinct/khme.svg' },
    { code: 'KNGO', name: 'Kingdom of Kongo', flag: 'assets/flags/extinct/kngo.svg' },
    { code: 'KORE', name: 'Korean Empire', flag: 'assets/flags/extinct/kore.svg' },
    { code: 'LALT', name: 'Republic of Los Altos', flag: 'assets/flags/extinct/lalt.svg' },
    { code: 'LAU', name: 'Confederation of Lau', flag: 'assets/flags/extinct/lau.svg' },
    { code: 'LCAL', name: 'Republic of Lower California', flag: 'assets/flags/extinct/lcal.svg' },
    { code: 'LCAN', name: 'Republic of Lower Canada', flag: 'assets/flags/extinct/lcan.svg' },
    { code: 'LUAN', name: 'Kingdom of Luang Prabang', flag: 'assets/flags/extinct/luan.svg' },
    { code: 'MALI', name: 'Mali Empire', flag: 'assets/flags/extinct/mali.svg' },
    { code: 'MANC', name: 'Manchukuo', flag: 'assets/flags/extinct/manc.svg' },
    { code: 'MANG', name: 'Kingdom of Mangareva', flag: 'assets/flags/extinct/mang.svg' },
    { code: 'MERI', name: 'Kingdom of Merina', flag: 'assets/flags/extinct/meri.svg' },
    { code: 'MOHE', name: 'Mohéli', flag: 'assets/flags/extinct/mohe.svg' },
    { code: 'MRYL', name: 'Republic of Maryland', flag: 'assets/flags/extinct/mryl.svg' },
    { code: 'MUSK', name: 'State of Muskogee', flag: 'assets/flags/extinct/musk.svg' },
    { code: 'NAPL', name: 'Kingdom of Naples', flag: 'assets/flags/extinct/napl.svg' },
    { code: 'NATA', name: 'Natalia Republic', flag: 'assets/flags/extinct/nata.svg' },
    { code: 'NEGR', name: 'Cantonal Republic of Negros', flag: 'assets/flags/extinct/negr.svg' },
    { code: 'NFLD', name: 'Dominion of Newfoundland', flag: 'assets/flags/extinct/nfld.svg' },
    { code: 'ORFS', name: 'Orange Free State', flag: 'assets/flags/extinct/orfs.svg' },
    { code: 'OTTO', name: 'Ottoman Empire', flag: 'assets/flags/extinct/otto.svg' },
    { code: 'PAPS', name: 'Papal States', flag: 'assets/flags/extinct/paps.svg' },
    { code: 'PBCO', name: 'Peru-Bolivian Confederation', flag: 'assets/flags/extinct/pbco.svg' },
    { code: 'PRUS', name: 'Kingdom of Prussia', flag: 'assets/flags/extinct/prus.svg' },
    { code: 'PRZA', name: "People's Republic of Zanzibar", flag: 'assets/flags/extinct/prza.svg' },
    { code: 'PTRI', name: 'Principality of Trinidad', flag: 'assets/flags/extinct/ptri.svg' },
    { code: 'QING', name: 'Qing Dynasty', flag: 'assets/flags/extinct/qing.svg' },
    { code: 'RAIA', name: 'Kingdom of Raʻiātea', flag: 'assets/flags/extinct/raia.svg' },
    { code: 'RAPA', name: 'Kingdom of Rapa Nui', flag: 'assets/flags/extinct/rapa.svg' },
    { code: 'RARO', name: 'Kingdom of Rarotonga', flag: 'assets/flags/extinct/raro.svg' },
    { code: 'RGDE', name: 'Riograndense Republic', flag: 'assets/flags/extinct/rgde.svg' },
    { code: 'RHOD', name: 'Rhodesia', flag: 'assets/flags/extinct/rhod.svg' },
    { code: 'RIGU', name: 'Republic of Independent Guiana', flag: 'assets/flags/extinct/rigu.svg' },
    { code: 'RIMA', name: 'Kingdom of Rimatara', flag: 'assets/flags/extinct/rima.svg' },
    { code: 'RIOG', name: 'Republic of the Rio Grande', flag: 'assets/flags/extinct/riog.svg' },
    { code: 'RRIF', name: 'Republic of the Rif', flag: 'assets/flags/extinct/rrif.svg' },
    { code: 'RURU', name: 'Kingdom of Rūrutu', flag: 'assets/flags/extinct/ruru.svg' },
    { code: 'RUSE', name: 'Russian Empire', flag: 'assets/flags/extinct/ruse.svg' },
    { code: 'SARD', name: 'Kingdom of Sardinia', flag: 'assets/flags/extinct/sard.svg' },
    { code: 'SCNA', name: 'Saint Christopher-Nevis-Anguilla', flag: 'assets/flags/extinct/scna.svg' },
    { code: 'SIKH', name: 'Sikh Empire', flag: 'assets/flags/extinct/sikh.svg' },
    { code: 'SKAS', name: 'South Kasai', flag: 'assets/flags/extinct/skas.svg' },
    { code: 'SONO', name: 'Republic of Sonora', flag: 'assets/flags/extinct/sono.svg' },
    { code: 'SPER', name: 'Republic of South Peru', flag: 'assets/flags/extinct/sper.svg' },
    { code: 'SULU', name: 'Sultanate of Sulu', flag: 'assets/flags/extinct/sulu.svg' },
    { code: 'SVIE', name: 'South Vietnam', flag: 'assets/flags/extinct/svie.svg' },
    { code: 'SZAN', name: 'Sultanate of Zanzibar', flag: 'assets/flags/extinct/szan.svg' },
    { code: 'TAHI', name: 'Kingdom of Tahiti', flag: 'assets/flags/extinct/tahi.svg' },
    { code: 'TANG', name: 'Tanganyika', flag: 'assets/flags/extinct/tang.svg' },
    { code: 'TCAU', name: 'Transcaucasian Democratic Federative Republic', flag: 'assets/flags/extinct/tcau.svg' },
    { code: 'TEUT', name: 'State of the Teutonic Order', flag: 'assets/flags/extinct/teut.svg' },
    { code: 'TEXR', name: 'Republic of Texas', flag: 'assets/flags/extinct/texr.svg' },
    { code: 'TRKI', name: 'Transkei', flag: 'assets/flags/extinct/trki.svg' },
    { code: 'TRVL', name: 'South African Republic', flag: 'assets/flags/extinct/trvl.svg' },
    { code: 'TSAR', name: 'Tsardom of Russia', flag: 'assets/flags/extinct/tsar.svg' },
    { code: 'TSIC', name: 'Kingdom of the Two Sicilies', flag: 'assets/flags/extinct/tsic.svg' },
    { code: 'TUAM', name: 'Kingdom of Tuamotu', flag: 'assets/flags/extinct/tuam.svg' },
    { code: 'TUCU', name: 'Republic of Tucumán', flag: 'assets/flags/extinct/tucu.svg' },
    { code: 'TUSC', name: 'Grand Duchy of Tuscany', flag: 'assets/flags/extinct/tusc.svg' },
    { code: 'UARE', name: 'United Arab Republic', flag: 'assets/flags/extinct/uare.svg' },
    { code: 'UCAN', name: 'Republic of Upper Canada', flag: 'assets/flags/extinct/ucan.svg' },
    { code: 'USAF', name: 'Union of South Africa', flag: 'assets/flags/extinct/usaf.svg' },
    { code: 'USSR', name: 'Soviet Union', flag: 'assets/flags/extinct/ussr.svg' },
    { code: 'UVEA', name: 'Kingdom of Uvea', flag: 'assets/flags/extinct/uvea.svg' },
    { code: 'VEND', name: 'Venda', flag: 'assets/flags/extinct/vend.svg' },
    { code: 'VENI', name: 'Republic of Venice', flag: 'assets/flags/extinct/veni.svg' },
    { code: 'VERM', name: 'Vermont Republic', flag: 'assets/flags/extinct/verm.svg' },
    { code: 'VIEN', name: 'Kingdom of Vientiane', flag: 'assets/flags/extinct/vien.svg' },
    { code: 'WEIM', name: 'Weimar Republic', flag: 'assets/flags/extinct/weim.svg' },
    { code: 'WFLA', name: 'Republic of West Florida', flag: 'assets/flags/extinct/wfla.svg' },
    { code: 'WIFE', name: 'West Indies Federation', flag: 'assets/flags/extinct/wife.svg' },
    { code: 'YUCA', name: 'Republic of Yucatán', flag: 'assets/flags/extinct/yuca.svg' },
    { code: 'YUG', name: 'Yugoslavia', flag: 'assets/flags/extinct/yug.svg' },
    { code: 'YUGK', name: 'Kingdom of Yugoslavia', flag: 'assets/flags/extinct/yugk.svg' },
    { code: 'ZRHO', name: 'Zimbabwe Rhodesia', flag: 'assets/flags/extinct/zrho.svg' },
];

// `myProfile.country`/a player's `country` can hold either a real ISO code
// or one of the codes above - these two helpers are the single place that
// knows how to turn that one field into display output, so call sites
// (profile.js, main.js's board player labels) don't each re-implement the
// "which list is this code from" check.

// A flag as a DOM node - a <span> carrying the Unicode glyph for a real
// country (flagEmoji()) or an <img> for an extinct state - either way with
// a `title` attribute so hovering it (mouse only, obviously - there's no
// hover on a touch screen) shows the full state/country name, since the
// flag alone doesn't always identify it at a glance. null if code is
// falsy or unrecognized by either list.
export function flagNode(code) {
    if (!code) return null;
    const emoji = flagEmoji(code);
    if (emoji) {
        const span = document.createElement('span');
        span.className = 'flagIcon';
        span.textContent = emoji;
        span.title = stateName(code) ?? '';
        return span;
    }
    const extinct = EXTINCT_STATES.find((s) => s.code === code);
    if (!extinct) return null;
    const img = document.createElement('img');
    img.src = extinct.flag;
    img.alt = extinct.name;
    img.title = extinct.name;
    img.className = 'extinctFlagIcon flagIcon';
    return img;
}

// The display name for `code` from whichever list it's in, or null.
export function stateName(code) {
    const country = COUNTRIES.find((c) => c.code === code);
    if (country) return country.name;
    const extinct = EXTINCT_STATES.find((s) => s.code === code);
    return extinct ? extinct.name : null;
}
