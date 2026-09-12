// Maps a recorded `birth_country` string (as stored in the Nobel Explorer
// database) to the matching polygon name in the bundled world topojson
// (frontend/src/data/world-countries-110m.json, Natural Earth 110m via the
// world-atlas project), so the choropleth map can shade the right country.
//
// This mapping exists ONLY for the map's shading. The ranked "View List"
// always shows the raw, unmodified birth_country values returned by the
// API -- nothing here changes what a laureate's recorded birthplace says,
// and nothing here is used for any other part of the dashboard.
//
// Every entry below is a same-territory rename or a colonial/administrative
// predecessor whose land is unambiguously inside one modern country's
// current borders. Historical states that could reasonably correspond to
// several different present-day countries (empires, unions, disputed or
// split territories) are deliberately left OUT of this map -- see
// UNMAPPED_HISTORICAL_COUNTRIES below for the full list and the reasoning
// for each.
export const COUNTRY_NAME_TO_MAP_NAME = {
  // Modern-name synonyms -- same country, different string.
  "USA": "United States of America",
  "the Netherlands": "Netherlands",

  // Constituent countries of the United Kingdom -- the topojson has no
  // separate Scotland/Northern Ireland polygon, only "United Kingdom".
  "Scotland": "United Kingdom",
  "Northern Ireland": "United Kingdom",

  // Direct predecessor states occupying the same modern territory.
  "West Germany": "Germany",
  "Burma": "Myanmar",
  "Persia": "Iran",
  "East Timor": "Timor-Leste",

  // Former colonial administrations over what is now a single modern
  // country's land area.
  "Java, Dutch East Indies": "Indonesia",
  "French Algeria": "Algeria",
  "French protectorate of Tunisia": "Tunisia",
  "Belgian Congo": "Dem. Rep. Congo",
  "Gold Coast": "Ghana",
  "Southern Rhodesia": "Zimbabwe",

  // Free City of Danzig = modern Gdańsk, and WWII German-occupied Poland,
  // both squarely inside modern Poland's territory.
  "Free City of Danzig": "Poland",
  "German-occupied Poland": "Poland",

  // Historical regions/city-states fully inside one modern country today.
  "Bosnia": "Bosnia and Herz.",
  "Crete": "Greece",
  "Tuscany": "Italy",
  "Bavaria": "Germany",
  "Württemberg": "Germany",
  "Hesse-Kassel": "Germany",
  "East Friesland": "Germany",
  "Mecklenburg": "Germany",
};

// Recorded birth countries that are intentionally NOT mapped to any map
// polygon. Each remains fully visible with its real count in "View List";
// it simply contributes no shading to the map, because assigning it to a
// single modern country would be a geographic or political guess this
// task explicitly says not to make.
export const UNMAPPED_HISTORICAL_COUNTRIES = {
  "Russian Empire": "Spanned many present-day countries (Russia, Poland, Finland, Ukraine, the Baltics, and more) -- no single successor state.",
  "USSR": "Spanned 15 present-day countries -- no single successor state.",
  "Austria-Hungary": "Spanned much of present-day Central/Eastern Europe -- no single successor state.",
  "Austrian Empire": "Same reasoning as Austria-Hungary.",
  "Prussia": "Historical Prussia's territory is split across modern Germany, Poland, Russia (Kaliningrad), and Lithuania.",
  "British India": "Spans present-day India, Pakistan, Bangladesh, and Myanmar.",
  "British Mandate of Palestine": "Mandate-era borders don't map cleanly to a single modern country without knowing the specific birth city.",
  "British Protectorate of Palestine": "Same reasoning as British Mandate of Palestine.",
  "British West Indies": "Spans many present-day Caribbean nations (Jamaica, Trinidad and Tobago, Barbados, and more).",
  "Ottoman Empire": "Spanned a very large multi-country area across Southeast Europe, the Middle East, and North Africa.",
  "Schleswig": "The historical Schleswig region is split between modern Germany and Denmark.",
  "Korea": "Recorded before the 1948 division -- could correspond to either North or South Korea.",
  "Guadeloupe, France": "Guadeloupe is a separate Caribbean territory, not part of mainland France's polygon in this map, and has no separate polygon at this map resolution.",
  "Faroe Islands (Denmark)": "A separate North Atlantic territory of Denmark with no separate polygon at this map resolution.",
  "Tibet": "Tibet's present-day political status is disputed; this map does not take a position on it, so no country assignment is made.",
};
