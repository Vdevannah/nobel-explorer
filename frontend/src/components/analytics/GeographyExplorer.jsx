import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ComposableMap, Geographies, Geography, ZoomableGroup } from "react-simple-maps";

import worldGeography from "../../data/world-countries-110m.json";
import { COUNTRY_NAME_TO_MAP_NAME } from "../../data/countryGeographyMap";
import { getCountryFlag } from "../../utils/countryFlags";

const BUCKETS = [
  { id: "0", label: "0", min: 0, max: 0 },
  { id: "1-4", label: "1–4", min: 1, max: 4 },
  { id: "5-19", label: "5–19", min: 5, max: 19 },
  { id: "20-49", label: "20–49", min: 20, max: 49 },
  { id: "50-99", label: "50–99", min: 50, max: 99 },
  { id: "100plus", label: "100+", min: 100, max: Infinity },
];

function bucketFor(count) {
  return BUCKETS.find((bucket) => count >= bucket.min && count <= bucket.max) ?? BUCKETS[0];
}

const MOBILE_LIST_DEFAULT_QUERY = "(max-width: 40rem)";

function GeographyExplorer({ data, emptyMessage = "No country data is available." }) {
  const [view, setView] = useState(() => (
    typeof window !== "undefined" && window.matchMedia(MOBILE_LIST_DEFAULT_QUERY).matches
      ? "list"
      : "map"
  ));
  const [zoom, setZoom] = useState(1);
  const [tooltip, setTooltip] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState(null);
  const containerRef = useRef(null);
  const tooltipRef = useRef(null);

  // Position the tooltip after it renders (and after the map wrapper has
  // its final layout), so we can measure its actual rendered size and the
  // wrapper's bounds, then clamp it fully inside the map instead of
  // relying on a fixed "always above, always centered" offset -- that
  // fixed offset is what let the tooltip get clipped by the wrapper's
  // overflow:hidden for countries near the top/left/right edges (Sweden,
  // Norway, Iceland, Alaska, eastern Russia, New Zealand). useLayoutEffect
  // runs synchronously before the browser paints, so the corrected
  // position is what actually shows -- no visible flicker.
  useLayoutEffect(() => {
    if (!tooltip) {
      setTooltipPosition(null);
      return;
    }
    const containerEl = containerRef.current;
    const tooltipEl = tooltipRef.current;
    if (!containerEl || !tooltipEl) return;

    const containerWidth = containerEl.clientWidth;
    const containerHeight = containerEl.clientHeight;
    const tooltipWidth = tooltipEl.offsetWidth;
    const tooltipHeight = tooltipEl.offsetHeight;
    const OFFSET = 12;

    // Keyboard focus doesn't carry a cursor position -- anchor near the
    // top-center of the map instead, then run it through the same
    // clamping logic below.
    const anchorX = tooltip.x ?? containerWidth / 2;
    const anchorY = tooltip.y ?? OFFSET;

    let top = anchorY - OFFSET - tooltipHeight;
    if (top < 0) {
      // Not enough room above -- place it below the point instead.
      top = anchorY + OFFSET;
    }
    top = Math.max(0, Math.min(top, containerHeight - tooltipHeight));

    let left = anchorX - tooltipWidth / 2;
    left = Math.max(0, Math.min(left, containerWidth - tooltipWidth));

    setTooltipPosition({ left, top });
  }, [tooltip]);

  // Keep the default view sensible if the window is resized across the
  // mobile breakpoint before the user has made an explicit choice.
  const userChoseView = useRef(false);
  useEffect(() => {
    const mql = window.matchMedia(MOBILE_LIST_DEFAULT_QUERY);
    function handleChange(event) {
      if (userChoseView.current) return;
      setView(event.matches ? "list" : "map");
    }
    mql.addEventListener("change", handleChange);
    return () => mql.removeEventListener("change", handleChange);
  }, []);

  function selectView(nextView) {
    userChoseView.current = true;
    setView(nextView);
  }

  const total = useMemo(
    () => data.reduce((sum, row) => sum + row.laureate_count, 0),
    [data],
  );

  // Aggregate raw birth-country rows onto map polygon names for shading
  // only -- this never changes what "View List" displays. Rows with no
  // confident polygon match (see countryGeographyMap.js) are skipped
  // here but remain fully visible in the list below.
  const countsByMapName = useMemo(() => {
    const map = new Map();
    for (const row of data) {
      const mapName = COUNTRY_NAME_TO_MAP_NAME[row.country] ?? row.country;
      map.set(mapName, (map.get(mapName) ?? 0) + row.laureate_count);
    }
    return map;
  }, [data]);

  function shareOf(count) {
    if (!total) return 0;
    return Math.round((count / total) * 1000) / 10;
  }

  function showTooltipFor(name, count, sourceEvent) {
    const rect = containerRef.current?.getBoundingClientRect();
    const x = sourceEvent?.clientX != null && rect ? sourceEvent.clientX - rect.left : null;
    const y = sourceEvent?.clientY != null && rect ? sourceEvent.clientY - rect.top : null;
    setTooltip({ name, count, share: shareOf(count), x, y });
  }

  function hideTooltip() {
    setTooltip(null);
  }

  const rankedRows = useMemo(
    () => [...data].sort((a, b) => b.laureate_count - a.laureate_count),
    [data],
  );

  if (!data.length) {
    return <p className="analytics-empty">{emptyMessage}</p>;
  }

  return (
    <div className="geo-explorer">
      <div className="geo-explorer-toolbar">
        <div className="geo-legend" aria-hidden="true">
          {BUCKETS.map((bucket) => (
            <span className="geo-legend-item" key={bucket.id}>
              <i className={`geo-swatch geo-swatch--${bucket.id}`} />
              {bucket.label}
            </span>
          ))}
        </div>
        <div className="geo-toolbar-actions">
          {view === "map" && (
            <div className="geo-zoom-controls" role="group" aria-label="Map zoom">
              <button
                type="button"
                className="geo-zoom-button"
                onClick={() => setZoom((z) => Math.max(1, Math.round((z / 1.4) * 100) / 100))}
                disabled={zoom <= 1}
                aria-label="Zoom out"
              >
                −
              </button>
              <button
                type="button"
                className="geo-zoom-button"
                onClick={() => setZoom((z) => Math.min(6, Math.round(z * 1.4 * 100) / 100))}
                disabled={zoom >= 6}
                aria-label="Zoom in"
              >
                +
              </button>
            </div>
          )}
          <button
            type="button"
            className="geo-view-toggle"
            onClick={() => selectView(view === "map" ? "list" : "map")}
          >
            {view === "map" ? <>☰ View List</> : <>🌐 View Map</>}
          </button>
        </div>
      </div>

      {view === "map" ? (
        <div className="geo-map-wrap" ref={containerRef}>
          <ComposableMap
            projection="geoEqualEarth"
            projectionConfig={{ scale: 161 }}
            width={900}
            height={430}
            role="img"
            aria-label="World map shaded by number of Nobel laureates born in each country"
          >
            <ZoomableGroup zoom={zoom} center={[0, 0]} minZoom={1} maxZoom={6}>
              <Geographies geography={worldGeography}>
                {({ geographies }) =>
                  geographies
                    // Antarctica has no recorded Nobel laureates and would
                    // otherwise force a much taller viewport just to draw an
                    // always-empty shape, so it's intentionally left out --
                    // no populated, laureate-eligible country is affected.
                    .filter((geo) => geo.properties.name !== "Antarctica")
                    .map((geo) => {
                      const name = geo.properties.name;
                      const count = countsByMapName.get(name) ?? 0;
                      const bucket = bucketFor(count);
                      const share = shareOf(count);
                      return (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          tabIndex={0}
                          className={`geo-country geo-country--${bucket.id}`}
                          aria-label={
                            count > 0
                              ? `${name}: ${count} laureate${count === 1 ? "" : "s"}, ${share}% of filtered laureates`
                              : `${name}: no recorded laureates in this selection`
                          }
                          onMouseEnter={(event) => showTooltipFor(name, count, event)}
                          onMouseMove={(event) => showTooltipFor(name, count, event)}
                          onMouseLeave={hideTooltip}
                          onFocus={(event) => showTooltipFor(name, count, event)}
                          onBlur={hideTooltip}
                        />
                      );
                    })
                }
              </Geographies>
            </ZoomableGroup>
          </ComposableMap>

          {tooltip && (
            <div
              className="geo-tooltip"
              ref={tooltipRef}
              style={{
                left: tooltipPosition ? tooltipPosition.left : (tooltip.x ?? 0),
                top: tooltipPosition ? tooltipPosition.top : (tooltip.y ?? 0),
                // Hide the very first, unmeasured frame so there's no
                // visible flash at the old fixed offset before the
                // layout effect above corrects the position.
                visibility: tooltipPosition ? "visible" : "hidden",
              }}
              role="status"
            >
              <strong>{tooltip.name}</strong>
              <span>Laureates: {tooltip.count}</span>
              <span>Share: {tooltip.share}%</span>
            </div>
          )}
        </div>
      ) : (
        <ol className="geo-country-list">
          {rankedRows.map((row, index) => (
            <li key={row.country}>
              <span className="geo-country-list-rank">{index + 1}</span>
              <span className="geo-country-list-flag" aria-hidden="true">{getCountryFlag(row.country)}</span>
              <span className="geo-country-list-name">{row.country}</span>
              <span className="geo-country-list-count">{row.laureate_count}</span>
              <span className="geo-country-list-share">{shareOf(row.laureate_count)}%</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default GeographyExplorer;
