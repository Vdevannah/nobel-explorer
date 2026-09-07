// Phase 7.5O-B persisted a scientific/conceptual visual (not a portrait) as
// image_url for these 15 laureates, since no rights-clear portrait exists.
// visual_type isn't stored in the database yet (see artifacts/
// final_16_scientific_visual_audit.json), so the detail hero classifies
// them here, keyed by the stable nobel_laureate_id, to render them with
// object-fit: contain instead of the portrait crop.
const SCIENTIFIC_VISUAL_NOBEL_LAUREATE_IDS = new Set([
  "267", // Donald J. Cram
  "447", // Edwin G. Krebs
  "253", // Georg Wittig
  "421", // George D. Snell
  "751", // H. Robert Horvitz
  "442", // Joseph E. Murray
  "1000", // Klaus Hasselmann
  "735", // Leland H. Hartwell
  "383", // Peyton Rous
  "996", // Robert B. Wilson
  "242", // Stanford Moore
  "243", // William H. Stein
  "209", // William Francis Giauque
  "716", // William Vickrey
  "137", // Wolfgang Paul
]);

export function isScientificVisual(laureate) {
  return SCIENTIFIC_VISUAL_NOBEL_LAUREATE_IDS.has(String(laureate?.nobel_laureate_id));
}

export default SCIENTIFIC_VISUAL_NOBEL_LAUREATE_IDS;
