// ─────────────────────────────────────────────
//  Country ID → simulation name mapping
//  Keys: ISO 3166-1 numeric codes (as strings)
//  Values: exact names used in countries.json
// ─────────────────────────────────────────────
const COUNTRY_IDS = {
  "4":"Afghanistan","8":"Albania","12":"Algeria","20":"Andorra","24":"Angola",
  "32":"Argentina","51":"Armenia","36":"Australia","40":"Austria","31":"Azerbaijan",
  "44":"Bahamas","48":"Bahrain","50":"Bangladesh","52":"Barbados","112":"Belarus",
  "56":"Belgium","84":"Belize","204":"Benin","64":"Bhutan","68":"Bolivia",
  "70":"Bosnia","72":"Botswana","76":"Brazil","96":"Brunei","854":"Burkina Faso",
  "108":"Burundi","116":"Cambodia","120":"Cameroon","124":"Canada","132":"Cape Verde",
  "140":"Central African Republic","148":"Chad","152":"Chile","156":"China",
  "170":"Colombia","174":"Comoros","178":"Congo","188":"Costa Rica","191":"Croatia",
  "192":"Cuba","196":"Cyprus","203":"Czech Republic","180":"DR Congo","208":"Denmark",
  "262":"Djibouti","214":"Dominican Republic","218":"Ecuador","818":"Egypt",
  "222":"El Salvador","226":"Equatorial Guinea","232":"Eritrea","233":"Estonia",
  "238":"United Kingdom",
  "748":"Eswatini","231":"Ethiopia","242":"Fiji","246":"Finland","250":"France",
  "260":"France",
  "266":"Gabon","270":"Gambia","268":"Georgia","275":"Israel","276":"Germany","288":"Ghana",
  "300":"Greece","304":"Denmark","320":"Guatemala","324":"Guinea","624":"Guinea-Bissau","328":"Guyana",
  "332":"Haiti","340":"Honduras","344":"Hong Kong","348":"Hungary","352":"Iceland",
  "356":"India","360":"Indonesia","364":"Iran","368":"Iraq","372":"Ireland",
  "376":"Israel","384":"Ivory Coast","388":"Jamaica","392":"Japan","400":"Jordan",
  "398":"Kazakhstan","404":"Kenya","296":"Kiribati","414":"Kuwait","417":"Kyrgyzstan",
  "418":"Laos","428":"Latvia","422":"Lebanon","426":"Lesotho","430":"Liberia",
  "434":"Libya","438":"Liechtenstein","440":"Lithuania","442":"Luxembourg",
  "450":"Madagascar","454":"Malawi","458":"Malaysia","462":"Maldives","466":"Mali","470":"Malta",
  "584":"Marshall Islands","478":"Mauritania","480":"Mauritius","484":"Mexico",
  "583":"Micronesia","498":"Moldova","492":"Monaco","496":"Mongolia","499":"Montenegro",
  "504":"Morocco","508":"Mozambique","104":"Myanmar","516":"Namibia","520":"Nauru",
  "524":"Nepal","528":"Netherlands","540":"France","554":"New Zealand","558":"Nicaragua","562":"Niger",
  "566":"Nigeria","408":"North Korea","807":"North Macedonia","578":"Norway",
  "512":"Oman","586":"Pakistan","585":"Palau","591":"Panama","598":"Papua New Guinea",
  "600":"Paraguay","604":"Peru","608":"Philippines","616":"Poland","620":"Portugal",
  "634":"Qatar","642":"Romania","643":"Russia","646":"Rwanda","882":"Samoa",
  "674":"San Marino","678":"Sao Tome and Principe","682":"Saudi Arabia","686":"Senegal",
  "688":"Serbia","690":"Seychelles","694":"Sierra Leone","702":"Singapore",
  "703":"Slovakia","705":"Slovenia","90":"Solomon Islands","706":"Somalia",
  "710":"South Africa","410":"South Korea","728":"South Sudan","724":"Spain",
  "144":"Sri Lanka","729":"Sudan","732":"Morocco","740":"Suriname","752":"Sweden","756":"Switzerland",
  "760":"Syria","158":"Taiwan","762":"Tajikistan","834":"Tanzania","764":"Thailand",
  "626":"Timor-Leste","630":"United States","768":"Togo","776":"Tonga","780":"Trinidad and Tobago",
  "788":"Tunisia","792":"Turkey","795":"Turkmenistan","798":"Tuvalu","784":"UAE",
  "800":"Uganda","804":"Ukraine","826":"United Kingdom","840":"United States",
  "858":"Uruguay","860":"Uzbekistan","548":"Vanuatu","336":"Vatican","862":"Venezuela",
  "704":"Vietnam","887":"Yemen","894":"Zambia","716":"Zimbabwe"
};

const UNKNOWN_COLOR  = '#0a0e17';  // never part of simulation
const STROKE_DEFAULT = '#1c2333';
const STROKE_WAR     = '#ff4444';
const STROKE_ALLY    = '#58a6ff';

// world-atlas zero-pads ISO codes ("004", "032"…) — strip leading zeros before lookup
function featureSimName(feature) {
  if (feature.id == null) return null;
  const key = String(feature.id).replace(/^0+/, '') || '0';
  return COUNTRY_IDS[key] || null;
}

// ─────────────────────────────────────────────
//  State
// ─────────────────────────────────────────────
let worldState    = null;
let byName        = new Map();
let territoryInfo = {};   // original sim name → {c, o, w, a}
let mapReady      = false;
let svgEl, pathFn, countrySel, borderSel, nukeSel;
let topoWorld     = null;   // kept for dynamic border mesh

// ─────────────────────────────────────────────
//  Colour resolvers
// ─────────────────────────────────────────────
function getTerritoryInfo(feature) {
  const simName = featureSimName(feature);
  if (!simName) return null;
  return territoryInfo[simName] || null;
}

const _warnedUnmapped = new Set();
function countryFill(feature) {
  const simName = featureSimName(feature);
  if (!simName) return UNKNOWN_COLOR;  // non-simulation territory (Western Sahara, Antarctica, etc.)
  const info = territoryInfo[simName];
  if (!info && Object.keys(territoryInfo).length > 0) {
    if (!_warnedUnmapped.has(simName)) {
      _warnedUnmapped.add(simName);
      console.warn(`[MAP] "${simName}" missing from territory_info`);
    }
    return UNKNOWN_COLOR;
  }
  return info ? info.c : UNKNOWN_COLOR;
}

function countryStroke(feature) {
  const info = getTerritoryInfo(feature);
  if (!info) return STROKE_DEFAULT;
  if (info.w) return STROKE_WAR;
  if (info.a) return STROKE_ALLY;
  return STROKE_DEFAULT;
}

function countryStrokeWidth(feature) {
  const info = getTerritoryInfo(feature);
  if (!info) return 0.4;
  return (info.w || info.a) ? 1.4 : 0.4;
}

// Which simulation country "owns" a TopoJSON feature (used for border filtering)
function getFeatureOwner(feature) {
  const simName = featureSimName(feature);
  if (!simName) return `__${feature.id}`;   // unmapped — keep its own border
  const info = territoryInfo[simName];
  return info ? info.o : simName;           // owner name, or original name if not yet in state
}

function updateBorders() {
  if (!topoWorld || !borderSel) return;
  // Redraw mesh: only draw arcs between features with DIFFERENT owners (or coastlines)
  const mesh = topojson.mesh(
    topoWorld,
    topoWorld.objects.countries,
    (a, b) => a === b || getFeatureOwner(a) !== getFeatureOwner(b)
  );
  borderSel.attr('d', pathFn(mesh));
}

function updateNukeBadges() {
  if (!mapReady || !nukeSel) return;

  // Only countries that have actually launched a nuclear strike get a badge
  const nukedOwners = new Set();
  if (worldState) {
    for (const c of worldState.countries) {
      if (c.nuked) nukedOwners.add(c.name);
    }
  }

  // For each nation that has struck, find the centroid of their largest map feature
  const ownerPos  = new Map();
  const ownerArea = new Map();
  for (const feature of countrySel.data()) {
    const simName = featureSimName(feature);
    if (!simName) continue;
    const info = territoryInfo[simName];
    if (!info || !nukedOwners.has(info.o)) continue;
    const centroid = pathFn.centroid(feature);
    if (isNaN(centroid[0]) || isNaN(centroid[1])) continue;
    const [[x0, y0], [x1, y1]] = pathFn.bounds(feature);
    const area = (x1 - x0) * (y1 - y0);
    if (!ownerArea.has(info.o) || area > ownerArea.get(info.o)) {
      ownerArea.set(info.o, area);
      ownerPos.set(info.o, centroid);
    }
  }

  const badgeData = [...ownerPos.entries()].map(([name, pos]) => ({ name, pos }));

  nukeSel.selectAll('.nuke-badge')
    .data(badgeData, d => d.name)
    .join('text')
      .attr('class', 'nuke-badge')
      .attr('x', d => d.pos[0])
      .attr('y', d => d.pos[1])
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '12px')
      .attr('fill', '#f0a500')
      .attr('stroke', '#0d1117')
      .attr('stroke-width', '2px')
      .attr('paint-order', 'stroke')
      .attr('pointer-events', 'none')
      .text('☢');
}

function updateMap() {
  if (!mapReady) return;
  countrySel
    .attr('fill', countryFill)
    .attr('stroke', countryStroke)
    .attr('stroke-width', countryStrokeWidth);
  updateBorders();
  updateNukeBadges();
}

// ─────────────────────────────────────────────
//  D3 map initialisation
// ─────────────────────────────────────────────
async function initMap() {
  const panel = document.getElementById('map-panel');
  const W = panel.clientWidth;
  const H = panel.clientHeight;

  svgEl = d3.select('#world-map')
    .attr('width', W)
    .attr('height', H);

  // Ocean
  svgEl.append('rect')
    .attr('width', W).attr('height', H)
    .attr('fill', '#070d1a');

  const projection = d3.geoNaturalEarth1()
    .scale(W / 6.2)
    .translate([W / 2, H / 2]);

  pathFn = d3.geoPath().projection(projection);

  const world = await d3.json(
    'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'
  );
  topoWorld = world;
  const countries = topojson.feature(world, world.objects.countries);

  countrySel = svgEl.selectAll('.country')
    .data(countries.features)
    .enter().append('path')
    .attr('class', 'country')
    .attr('d', pathFn)
    .attr('fill', UNKNOWN_COLOR)
    .on('mousemove', onMouseMove)
    .on('mouseleave', onMouseLeave);

  // Dynamic border mesh — drawn on top, updated every state tick
  borderSel = svgEl.append('path')
    .attr('class', 'border-mesh')
    .attr('fill', 'none')
    .attr('stroke', '#1c2333')
    .attr('stroke-width', 0.4);

  // Nuclear badge layer — sits above everything else
  nukeSel = svgEl.append('g').attr('class', 'nuke-badges');

  mapReady = true;
  if (worldState) updateMap(); else updateBorders();
}

// ─────────────────────────────────────────────
//  Tooltip
// ─────────────────────────────────────────────
const tooltip = document.getElementById('tooltip');

function fmt(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(0) + 'K';
  return String(n);
}

function onMouseMove(event, feature) {
  const simName = featureSimName(feature);
  if (!simName) { tooltip.classList.add('hidden'); return; }

  const info = territoryInfo[simName];
  if (!info) { tooltip.classList.add('hidden'); return; }

  // The active country that controls this territory
  const owner = byName.get(info.o);
  const isAbsorbed = info.o !== simName;

  // "formerly" subtitle for merged/renamed nations (current name not among original names)
  let formerlyHtml = '';
  if (owner && owner.absorbed_names && !owner.absorbed_names.includes(owner.name)) {
    const names = owner.absorbed_names.length > 6
      ? owner.absorbed_names.slice(0, 6).join(', ') + '…'
      : owner.absorbed_names.join(', ');
    formerlyHtml = `<div style="font-size:10px;color:#8b949e;margin-bottom:4px">(formerly ${names})</div>`;
  }

  // Show current nation as primary; original territory name as secondary when absorbed
  let nameHtml;
  if (isAbsorbed) {
    nameHtml = `<div class="tt-name">${info.o}</div>
                ${formerlyHtml}
                <div style="font-size:10px;color:#8b949e;margin-bottom:6px">Territory: ${simName}</div>`;
  } else {
    nameHtml = `<div class="tt-name">${info.o}</div>${formerlyHtml}`;
  }

  let statusHtml;
  if (info.w) {
    statusHtml = '<div class="tt-status war">&#9888; At War</div>';
  } else if (info.a && worldState) {
    const allianceMembers = worldState.alliances.find(a => a.includes(info.o));
    const allianceName = allianceMembers ? allianceMembers.join(' & ') : info.o;
    statusHtml = `<div class="tt-status alliance">&#9776; Alliance</div>
                  <div style="font-size:10px;color:#58a6ff;margin-top:2px">${allianceName}</div>`;
  } else {
    statusHtml = '<div class="tt-status peace">&#9679; At Peace</div>';
  }

  // owner may be briefly undefined between state ticks — fall back to info flags
  const milPct = owner ? Math.round(owner.military / Math.max(owner.military_cap, 1) * 100) : 0;

  // Tech level: numeric value + descriptive label (logarithmic scale, no cap)
  const techDisplay = owner ? (() => {
    const t = owner.tech_level;
    const label = t < 2.0 ? 'Primitive'
                : t < 3.0 ? 'Basic'
                : t < 4.0 ? 'Modern'
                : t < 5.0 ? 'Advanced'
                : t < 6.5 ? 'Superior'
                : 'Cutting Edge';
    return `${t.toFixed(1)} · ${label}`;
  })() : '';

  const nukesRow = (owner && owner.nukes > 0)
    ? `<div class="tt-row"><span>&#9762; Nuclear</span><span class="tt-val tt-nukes">${owner.nukes.toLocaleString()} warheads</span></div>`
    : '';

  tooltip.innerHTML = `
    ${nameHtml}
    ${owner ? `
    <div class="tt-row"><span>Military</span><span class="tt-val">${fmt(owner.military)} / ${fmt(owner.military_cap)} (${milPct}%)</span></div>
    <div class="tt-row"><span>Economy</span><span class="tt-val">$${fmt(owner.economy)}</span></div>
    <div class="tt-row"><span>Population</span><span class="tt-val">${fmt(owner.population)}</span></div>
    <div class="tt-row"><span>Technology</span><span class="tt-val tt-tech">${techDisplay}</span></div>
    ${nukesRow}
    ` : `<div style="color:#555;font-size:10px">Updating…</div>`}
    ${statusHtml}
  `;

  const panel = document.getElementById('map-panel');
  const rect  = panel.getBoundingClientRect();
  let x = event.clientX - rect.left + 14;
  let y = event.clientY - rect.top  + 14;
  if (x + 220 > rect.width)  x = event.clientX - rect.left - 220;
  if (y + 160 > rect.height) y = event.clientY - rect.top  - 160;

  tooltip.style.left = x + 'px';
  tooltip.style.top  = y + 'px';
  tooltip.classList.remove('hidden');
}

function onMouseLeave() {
  tooltip.classList.add('hidden');
}

// ─────────────────────────────────────────────
//  Stats
// ─────────────────────────────────────────────
function updateStats(state) {
  document.getElementById('s-nations').textContent      = state.total_countries;
  document.getElementById('s-wars').textContent         = state.conflicts.length;
  document.getElementById('s-alliances').textContent    = state.alliances.length;
  document.getElementById('world-pop-value').textContent = fmt(state.world_population);
  document.getElementById('sim-date').textContent = state.date;
  const yr  = Math.floor((state.day - 1) / 12) + 1;
  const mo  = ((state.day - 1) % 12) + 1;
  document.getElementById('sim-day').textContent  = `Year ${yr}, Month ${mo}`;
}

function updateTopPowers(top5) {
  if (!top5 || !top5.length) return;
  const maxMil = top5[0].military_cap || 1;
  const list = document.getElementById('top-list');
  list.innerHTML = top5.map((c, i) => `
    <div class="top-item">
      <span class="top-rank">${i + 1}</span>
      <span class="top-swatch" style="background:${c.color || '#888'}"></span>
      <span class="top-name" title="${c.name}">${c.name}${c.nukes > 0 ? ' <span class="top-nuke-badge">&#9762;</span>' : ''}</span>
      <div class="top-bar-wrap">
        <div class="top-bar" style="width:${Math.round(c.military / maxMil * 70)}px;background:${c.color || '#238636'}"></div>
      </div>
      <span class="top-val">${fmt(c.military)}</span>
    </div>
  `).join('');
}

// ─────────────────────────────────────────────
//  Log tooltip
// ─────────────────────────────────────────────
const logTip = document.createElement('div');
logTip.id = 'log-tooltip';
logTip.className = 'hidden';
document.body.appendChild(logTip);

function buildLogTipContent(cls) {
  if (!worldState) return '';

  if (cls.includes('log-war')) {
    if (!worldState.conflicts.length)
      return '<div class="lt-title">No Active Wars</div>';
    return `<div class="lt-title">Active Wars (${worldState.conflicts.length})</div>` +
      worldState.conflicts.map(c =>
        `<div class="lt-row"><span>${c.attacker}</span> <em>vs</em> <span>${c.defender}</span> · Month ${c.day}</div>`
      ).join('');
  }

  if (cls.includes('log-alliance') || cls.includes('log-union')) {
    if (!worldState.alliances.length)
      return '<div class="lt-title">No Active Alliances</div>';
    return `<div class="lt-title">Alliances (${worldState.alliances.length})</div>` +
      worldState.alliances.map(members =>
        `<div class="lt-row">${members.map(m => `<span>${m}</span>`).join(' <em>&amp;</em> ')}</div>`
      ).join('');
  }

  if (cls.includes('log-nuclear')) {
    const nukes = worldState.countries.filter(c => c.nukes > 0)
      .sort((a, b) => b.nukes - a.nukes);
    if (!nukes.length) return '<div class="lt-title">No Nuclear Powers</div>';
    return `<div class="lt-title">Nuclear Powers (${nukes.length})</div>` +
      nukes.map(c =>
        `<div class="lt-row"><span>${c.name}</span>: ${c.nukes.toLocaleString()} warheads</div>`
      ).join('');
  }

  if (cls.includes('log-date')) {
    const nations = [...worldState.countries].sort((a, b) => a.name.localeCompare(b.name));
    return `<div class="lt-title">Surviving Nations (${worldState.total_countries})</div>` +
      nations.map(c =>
        `<div class="lt-row"><span>${c.name}</span></div>`
      ).join('');
  }

  return '';
}

function showLogTip(e, cls) {
  const html = buildLogTipContent(cls);
  if (!html) return;
  logTip.innerHTML = html;
  logTip.classList.remove('hidden');
  const x = e.clientX - logTip.offsetWidth - 14;
  const y = Math.max(4, Math.min(e.clientY - 10, window.innerHeight - logTip.offsetHeight - 4));
  logTip.style.left = Math.max(4, x) + 'px';
  logTip.style.top  = y + 'px';
}

function hideLogTip() { logTip.classList.add('hidden'); }

// ─────────────────────────────────────────────
//  Log
// ─────────────────────────────────────────────
const MAX_DOM_LOG = 400;     // entries kept in the DOM (performance cap)
const fullLog     = [];      // every message ever — no cap, used for export
const logEl       = document.getElementById('log');
const logCountEl  = document.getElementById('log-count');

function classifyMessage(msg) {
  if (/\[NUCLEAR\]/.test(msg))            return 'log-nuclear';
  if (/\[UNION\]/.test(msg))              return 'log-union';
  if (/\[ALLIANCE\]/.test(msg))           return 'log-alliance';
  if (/\[EVENT\]/.test(msg))              return 'log-event';
  if (/>>/.test(msg))                     return 'log-war';
  if (/^---/.test(msg.trim()))            return 'log-date';
  if (/initialized|start|over/i.test(msg)) return 'log-system';
  return 'log-default';
}

function appendLog(msg) {
  if (!msg || !msg.trim()) return;
  const text = msg.trim();

  // Always keep the full history
  fullLog.push(text);
  if (logCountEl) logCountEl.textContent = `${fullLog.length} lines`;

  // DOM: append and prune oldest when over cap
  const div = document.createElement('div');
  div.className = 'log-entry ' + classifyMessage(text);
  div.textContent = text;
  logEl.insertBefore(div, logEl.firstChild);

  while (logEl.children.length > MAX_DOM_LOG) {
    logEl.removeChild(logEl.lastChild);
  }
}

function downloadLog() {
  const day    = worldState ? worldState.day : 0;
  const header = `World War Simulation — Log export\nDay ${day} | ${fullLog.length} entries\n${'─'.repeat(60)}\n`;
  const blob   = new Blob([header + fullLog.join('\n')], { type: 'text/plain' });
  const a      = document.createElement('a');
  a.href       = URL.createObjectURL(blob);
  a.download   = `ww-sim-day${day}.txt`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ─────────────────────────────────────────────
//  Socket.IO
// ─────────────────────────────────────────────
const socket = io();

socket.on('connect', () => {
  appendLog('Connected to server.');
});

socket.on('disconnect', () => {
  appendLog('Connection lost. Reconnecting...');
});

socket.on('state', (state) => {
  worldState    = state;
  byName        = new Map(state.countries.map(c => [c.name, c]));
  territoryInfo = state.territory_info || {};
  updateStats(state);
  updateTopPowers(state.top5);
  updateMap();
});

socket.on('log', (data) => {
  appendLog(data.message);
});

socket.on('gameover', (data) => {
  const banner = document.getElementById('gameover-banner');
  document.getElementById('go-winner').textContent = data.winner;
  document.getElementById('go-days').textContent   = `${data.years} years · ${data.months % 12} months`;
  banner.style.display = 'block';
  appendLog(`★ SIMULATION OVER — ${data.winner} has conquered the world!`);
});

// ─────────────────────────────────────────────
//  Stat-box tooltips
// ─────────────────────────────────────────────
(function wireStatBoxTips() {
  const boxes = [
    { id: 's-nations',   cls: 'log-date'     },
    { id: 's-wars',      cls: 'log-war'      },
    { id: 's-alliances', cls: 'log-alliance' },
  ];
  boxes.forEach(({ id, cls }) => {
    const box = document.getElementById(id).closest('.stat-box');
    if (!box) return;
    box.addEventListener('mousemove', e => showLogTip(e, cls));
    box.addEventListener('mouseleave', hideLogTip);
  });
})();

// ─────────────────────────────────────────────
//  Boot
// ─────────────────────────────────────────────
initMap().catch(err => {
  console.error('Map failed to load:', err);
  appendLog('ERROR: Could not load world map.');
});
