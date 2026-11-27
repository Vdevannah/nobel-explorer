// Decorative welcome illustration: a golden atomic orbital inside a faint
// knowledge network. Pure inline SVG styled by assistant.css (colour comes from
// currentColor, motion is CSS and stops under prefers-reduced-motion). Hidden
// from assistive technology because it carries no information.

const CENTER = { x: 120, y: 80 };

// Knowledge-network nodes around the atom, and the links between them.
const NODES = [
  [22, 34], [52, 16], [38, 72], [16, 112], [56, 138], [94, 20],
  [188, 18], [222, 42], [204, 80], [226, 120], [186, 142], [146, 146],
];
const LINKS = [
  [0, 1], [0, 2], [1, 5], [2, 3], [3, 4], [2, 4],
  [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [6, 8], [8, 10],
];
// A few nodes reach toward the atom with very faint spokes.
const SPOKES = [2, 5, 8, 11];

const ORBIT_ANGLES = [0, 60, 120];

function WelcomeIllustration() {
  return (
    <div className="assistant-welcome-art" aria-hidden="true">
      <svg viewBox="0 0 240 160" focusable="false" role="presentation">
        <g className="assistant-network">
          {LINKS.map(([a, b]) => (
            <line
              key={`${a}-${b}`}
              x1={NODES[a][0]}
              y1={NODES[a][1]}
              x2={NODES[b][0]}
              y2={NODES[b][1]}
            />
          ))}
          {SPOKES.map((index) => (
            <line
              key={`spoke-${index}`}
              className="assistant-network-spoke"
              x1={NODES[index][0]}
              y1={NODES[index][1]}
              x2={CENTER.x}
              y2={CENTER.y}
            />
          ))}
          {NODES.map(([x, y], index) => (
            <circle
              key={`node-${x}-${y}`}
              className={`assistant-network-node assistant-network-node--${index % 3}`}
              cx={x}
              cy={y}
              r={index % 4 === 0 ? 2.4 : 1.8}
            />
          ))}
        </g>

        <g className="assistant-atom">
          <circle className="assistant-atom-halo" cx={CENTER.x} cy={CENTER.y} r="22" />
          <g className="assistant-atom-orbits">
            {ORBIT_ANGLES.map((angle) => (
              <g key={angle} transform={`rotate(${angle} ${CENTER.x} ${CENTER.y})`}>
                <ellipse className="assistant-atom-orbit" cx={CENTER.x} cy={CENTER.y} rx="50" ry="17" />
                <circle className="assistant-atom-electron" cx={CENTER.x + 50} cy={CENTER.y} r="3" />
              </g>
            ))}
          </g>
          <circle className="assistant-atom-nucleus" cx={CENTER.x} cy={CENTER.y} r="6" />
        </g>
      </svg>
    </div>
  );
}

export default WelcomeIllustration;
