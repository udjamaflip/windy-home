/**
 * Windy Home — Custom Lovelace Cards
 *
 * Cards:
 *   windy-weather-card     — Current conditions overview
 *   windy-forecast-card    — Hourly forecast timeline
 *   windy-wind-card        — Wind compass rose
 *   windy-waves-card       — Wave / swell conditions
 *
 * All cards auto-discover entities from the windy_home integration.
 */

/* ═══════════════════════════════════════════════════════════════════════════
   Shared helpers
   ═══════════════════════════════════════════════════════════════════════════ */

const WINDY_VERSION = "1.0.0";

const CONDITION_ICONS = {
  "clear-night": "mdi:weather-night",
  cloudy: "mdi:weather-cloudy",
  exceptional: "mdi:alert-circle-outline",
  fog: "mdi:weather-fog",
  hail: "mdi:weather-hail",
  lightning: "mdi:weather-lightning",
  "lightning-rainy": "mdi:weather-lightning-rainy",
  partlycloudy: "mdi:weather-partly-cloudy",
  pouring: "mdi:weather-pouring",
  rainy: "mdi:weather-rainy",
  snowy: "mdi:weather-snowy",
  "snowy-rainy": "mdi:weather-snowy-rainy",
  sunny: "mdi:weather-sunny",
  windy: "mdi:weather-windy",
  "windy-variant": "mdi:weather-windy-variant",
};

const CONDITION_LABELS = {
  "clear-night": "Clear",
  cloudy: "Cloudy",
  exceptional: "Exceptional",
  fog: "Fog",
  hail: "Hail",
  lightning: "Lightning",
  "lightning-rainy": "Thunderstorm",
  partlycloudy: "Partly Cloudy",
  pouring: "Pouring",
  rainy: "Rainy",
  snowy: "Snowy",
  "snowy-rainy": "Sleet",
  sunny: "Sunny",
  windy: "Windy",
  "windy-variant": "Windy",
};

function windDirectionLabel(deg) {
  if (deg == null) return "—";
  const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  return dirs[Math.round(deg / 22.5) % 16];
}

function round1(v) {
  if (v == null) return "—";
  return Math.round(v * 10) / 10;
}

function getEntityState(hass, entityId) {
  const s = hass.states[entityId];
  return s ? s.state : undefined;
}

function getEntityAttr(hass, entityId, attr) {
  const s = hass.states[entityId];
  return s && s.attributes ? s.attributes[attr] : undefined;
}

/** Check if an entity belongs to the Windy Home integration. */
function isWindyEntity(hass, entityId) {
  const s = hass.states[entityId];
  if (!s || !s.attributes) return false;
  // Match by attribution (set by our integration)
  return s.attributes.attribution === "Data provided by Windy.com";
}

/** Find the first Windy entity in a given domain, optionally matching a suffix. */
function findWindyEntity(hass, domain, suffix) {
  const keys = Object.keys(hass.states);
  return keys.find(
    (k) =>
      k.startsWith(`${domain}.`) &&
      isWindyEntity(hass, k) &&
      (suffix ? k.endsWith(`_${suffix}`) : true)
  );
}

/** Find all Windy entities in a given domain. */
function findWindyEntities(hass, domain) {
  return Object.keys(hass.states).filter(
    (k) => k.startsWith(`${domain}.`) && isWindyEntity(hass, k)
  );
}

/* shared CSS */
const CARD_STYLES = `
  :host {
    --windy-primary: #283593;
    --windy-accent: #42a5f5;
    --windy-bg: var(--ha-card-background, var(--card-background-color, #fff));
    --windy-text: var(--primary-text-color, #212121);
    --windy-secondary: var(--secondary-text-color, #757575);
  }
  ha-card {
    padding: 16px;
    overflow: hidden;
  }
  .card-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }
  .card-title {
    font-size: 16px;
    font-weight: 500;
    color: var(--windy-text);
  }
  .card-subtitle {
    font-size: 12px;
    color: var(--windy-secondary);
  }
  .attribution {
    font-size: 10px;
    color: var(--windy-secondary);
    text-align: right;
    margin-top: 8px;
  }
  .grid {
    display: grid;
    gap: 8px;
  }
  .metric {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  .metric .value {
    font-size: 20px;
    font-weight: 500;
    color: var(--windy-text);
  }
  .metric .label {
    font-size: 11px;
    color: var(--windy-secondary);
    margin-top: 2px;
  }
  .metric .unit {
    font-size: 12px;
    color: var(--windy-secondary);
    font-weight: normal;
  }
`;


/* ═══════════════════════════════════════════════════════════════════════════
   1. WINDY WEATHER CARD — Current conditions overview
   ═══════════════════════════════════════════════════════════════════════════ */

class WindyWeatherCard extends HTMLElement {
  static getConfigElement() { return document.createElement("div"); }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = config;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) return;

    const entity =
      this._config.entity || findWindyEntity(this._hass, "weather", null);
    if (!entity) {
      this.shadowRoot.innerHTML = `<ha-card><p>No Windy weather entity found</p></ha-card>`;
      return;
    }

    const s = this._hass.states[entity];
    if (!s) {
      this.shadowRoot.innerHTML = `<ha-card><p>Entity ${entity} not found</p></ha-card>`;
      return;
    }

    const a = s.attributes;
    const condition = s.state;
    const temp = round1(a.temperature);
    const humidity = round1(a.humidity);
    const pressure = round1(a.pressure);
    const windSpeed = round1(a.wind_speed);
    const windBearing = a.wind_bearing;
    const windDir = windDirectionLabel(windBearing);
    const windGust = round1(a.wind_gust_speed);
    const dewPoint = round1(a.dew_point);
    const cloudCoverage = a.cloud_coverage != null ? Math.round(a.cloud_coverage) : "—";
    const condIcon = CONDITION_ICONS[condition] || "mdi:weather-cloudy";
    const condLabel = CONDITION_LABELS[condition] || condition;
    const name = this._config.name || a.friendly_name || "Windy Weather";

    // Find extra sensors
    const capeEntity = findWindyEntity(this._hass, "sensor", "cape");
    const cape = capeEntity ? getEntityState(this._hass, capeEntity) : null;

    this.shadowRoot.innerHTML = `
      <style>
        ${CARD_STYLES}
        .hero {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 16px;
        }
        .hero-icon {
          --mdc-icon-size: 48px;
          color: var(--windy-accent);
        }
        .hero-temp {
          font-size: 42px;
          font-weight: 300;
          color: var(--windy-text);
          line-height: 1;
        }
        .hero-temp .unit {
          font-size: 22px;
          vertical-align: super;
          color: var(--windy-secondary);
        }
        .hero-condition {
          font-size: 14px;
          color: var(--windy-secondary);
        }
        .details {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
          gap: 12px;
        }
        .detail-item {
          text-align: center;
        }
        .detail-item .val {
          font-size: 16px;
          font-weight: 500;
        }
        .detail-item .lbl {
          font-size: 11px;
          color: var(--windy-secondary);
          margin-top: 2px;
        }
        .detail-item ha-icon {
          --mdc-icon-size: 18px;
          color: var(--windy-secondary);
          margin-bottom: 4px;
        }
      </style>
      <ha-card>
        <div class="card-header-row">
          <div>
            <div class="card-title">${name}</div>
          </div>
        </div>

        <div class="hero">
          <ha-icon icon="${condIcon}" class="hero-icon"></ha-icon>
          <div>
            <div class="hero-temp">${temp}<span class="unit">°</span></div>
            <div class="hero-condition">${condLabel}</div>
          </div>
        </div>

        <div class="details">
          <div class="detail-item">
            <ha-icon icon="mdi:water-percent"></ha-icon>
            <div class="val">${humidity}%</div>
            <div class="lbl">Humidity</div>
          </div>
          <div class="detail-item">
            <ha-icon icon="mdi:gauge"></ha-icon>
            <div class="val">${pressure}</div>
            <div class="lbl">hPa</div>
          </div>
          <div class="detail-item">
            <ha-icon icon="mdi:weather-windy"></ha-icon>
            <div class="val">${windSpeed} <small>${windDir}</small></div>
            <div class="lbl">Wind m/s</div>
          </div>
          <div class="detail-item">
            <ha-icon icon="mdi:wind-power"></ha-icon>
            <div class="val">${windGust}</div>
            <div class="lbl">Gust m/s</div>
          </div>
          <div class="detail-item">
            <ha-icon icon="mdi:thermometer-water"></ha-icon>
            <div class="val">${dewPoint}°</div>
            <div class="lbl">Dew Point</div>
          </div>
          <div class="detail-item">
            <ha-icon icon="mdi:cloud"></ha-icon>
            <div class="val">${cloudCoverage}%</div>
            <div class="lbl">Cloud</div>
          </div>
          ${cape != null && cape !== "unknown" && cape !== "unavailable" ? `
          <div class="detail-item">
            <ha-icon icon="mdi:weather-lightning"></ha-icon>
            <div class="val">${round1(cape)}</div>
            <div class="lbl">CAPE J/kg</div>
          </div>
          ` : ""}
        </div>

        <div class="attribution">Data provided by Windy.com</div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 4;
  }
}


/* ═══════════════════════════════════════════════════════════════════════════
   2. WINDY FORECAST CARD — Hourly forecast timeline
   ═══════════════════════════════════════════════════════════════════════════ */

class WindyForecastCard extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._forecast = [];
    this._lastFetch = 0;
    this._fetchEntity = null;
    this._fetching = false;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    const entity =
      this._config.entity || findWindyEntity(this._hass, "weather", null);

    // Re-fetch forecast every 5 min or on entity change
    const now = Date.now();
    const stale = now - this._lastFetch > 5 * 60 * 1000;
    const entityChanged = entity !== this._fetchEntity;
    if (entity && (stale || entityChanged) && !this._fetching) {
      this._fetchForecast(entity);
    }
    this._render();
  }

  async _fetchForecast(entity) {
    this._fetching = true;
    this._fetchEntity = entity;

    // Strategy 1: callService with return_response (HA 2024.4+)
    try {
      const resp = await this._hass.callService(
        "weather",
        "get_forecasts",
        { type: "hourly" },
        { entity_id: [entity] },
        false,
        true
      );
      if (resp && resp.response) {
        const entityResp = resp.response[entity];
        if (entityResp && entityResp.forecast) {
          this._forecast = entityResp.forecast;
          this._lastFetch = Date.now();
          this._fetching = false;
          this._render();
          return;
        }
      }
    } catch (e1) {
      console.warn("Windy forecast: callService failed, trying subscription:", e1);
    }

    // Strategy 2: WebSocket subscription (one-shot)
    try {
      let resolved = false;
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => { if (!resolved) { resolved = true; reject(new Error("timeout")); } }, 5000);
        this._hass.connection.subscribeMessage(
          (event) => {
            if (!resolved) {
              resolved = true;
              clearTimeout(timer);
              if (event && event.forecast) {
                this._forecast = event.forecast;
              } else if (Array.isArray(event)) {
                this._forecast = event;
              }
              this._lastFetch = Date.now();
              this._render();
              resolve();
            }
          },
          {
            type: "weather/subscribe_forecast",
            entity_id: entity,
            forecast_type: "hourly",
          }
        ).then((unsub) => {
          // Unsubscribe after getting initial data (we re-fetch on next hass update)
          setTimeout(() => { try { unsub(); } catch (_) {} }, 2000);
          if (!resolved) resolve();
        }).catch((err) => {
          if (!resolved) { resolved = true; clearTimeout(timer); reject(err); }
        });
      });
      this._fetching = false;
      return;
    } catch (e2) {
      console.warn("Windy forecast: subscription failed, trying attributes:", e2);
    }

    // Strategy 3: State attributes (HA < 2023.9)
    try {
      const s = this._hass.states[entity];
      if (s && s.attributes && s.attributes.forecast) {
        this._forecast = s.attributes.forecast;
        this._lastFetch = Date.now();
      }
    } catch (_) {}
    this._fetching = false;
    this._render();
  }

  _render() {
    if (!this._hass) return;

    const entity =
      this._config.entity || findWindyEntity(this._hass, "weather", null);
    if (!entity) {
      this.shadowRoot.innerHTML = `<ha-card><p>No Windy weather entity found</p></ha-card>`;
      return;
    }

    const s = this._hass.states[entity];
    if (!s) {
      this.shadowRoot.innerHTML = `<ha-card><p>Entity ${entity} not found</p></ha-card>`;
      return;
    }

    const forecast = this._forecast;
    const hours = this._config.hours || 12;
    const items = forecast.slice(0, hours);
    const name = this._config.name || "Windy Forecast";

    if (!items.length) {
      this.shadowRoot.innerHTML = `<ha-card>
        <div class="card-header-row"><div class="card-title">${name}</div></div>
        <p style="color:var(--secondary-text-color)">No forecast data available</p>
      </ha-card>`;
      return;
    }

    // Find temp range for bar chart
    const temps = items.map((f) => f.temperature).filter((t) => t != null);
    const minT = Math.min(...temps);
    const maxT = Math.max(...temps);
    const range = maxT - minT || 1;

    const rows = items
      .map((f) => {
        const dt = new Date(f.datetime);
        const hour = dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
        const icon = CONDITION_ICONS[f.condition] || "mdi:weather-cloudy";
        const t = round1(f.temperature);
        const barPct = Math.round(((f.temperature - minT) / range) * 100);
        const wind = f.wind_speed != null ? round1(f.wind_speed) : "";
        const precip = f.precipitation != null && f.precipitation > 0 ? round1(f.precipitation) : "";
        return `
          <div class="fc-row">
            <span class="fc-time">${hour}</span>
            <ha-icon icon="${icon}" class="fc-icon"></ha-icon>
            <span class="fc-temp">${t}°</span>
            <div class="fc-bar-bg">
              <div class="fc-bar" style="width:${Math.max(barPct, 5)}%"></div>
            </div>
            <span class="fc-wind">${wind ? wind + " m/s" : ""}</span>
            <span class="fc-precip">${precip ? precip + " mm" : ""}</span>
          </div>
        `;
      })
      .join("");

    this.shadowRoot.innerHTML = `
      <style>
        ${CARD_STYLES}
        .fc-row {
          display: grid;
          grid-template-columns: 48px 24px 45px 1fr 60px 50px;
          align-items: center;
          gap: 6px;
          padding: 4px 0;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        .fc-row:last-child { border-bottom: none; }
        .fc-time {
          font-size: 12px;
          color: var(--windy-secondary);
        }
        .fc-icon {
          --mdc-icon-size: 20px;
          color: var(--windy-accent);
        }
        .fc-temp {
          font-size: 14px;
          font-weight: 500;
          text-align: right;
        }
        .fc-bar-bg {
          height: 6px;
          border-radius: 3px;
          background: var(--divider-color, #e0e0e0);
          overflow: hidden;
        }
        .fc-bar {
          height: 100%;
          border-radius: 3px;
          background: linear-gradient(90deg, var(--windy-accent), #1565c0);
        }
        .fc-wind {
          font-size: 11px;
          color: var(--windy-secondary);
          text-align: right;
        }
        .fc-precip {
          font-size: 11px;
          color: #1e88e5;
          text-align: right;
        }
        .fc-scroll {
          max-height: 400px;
          overflow-y: auto;
        }
      </style>
      <ha-card>
        <div class="card-header-row">
          <div class="card-title">${name}</div>
          <div class="card-subtitle">Hourly</div>
        </div>
        <div class="fc-scroll">
          ${rows}
        </div>
        <div class="attribution">Data provided by Windy.com</div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 6;
  }
}


/* ═══════════════════════════════════════════════════════════════════════════
   3. WINDY WIND CARD — Compass rose with speed/gust/direction
   ═══════════════════════════════════════════════════════════════════════════ */

class WindyWindCard extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) return;

    const weatherEntity =
      this._config.entity || findWindyEntity(this._hass, "weather", null);
    const s = weatherEntity ? this._hass.states[weatherEntity] : null;
    const a = s ? s.attributes : {};

    const windSpeed = round1(a.wind_speed);
    const windGust = round1(a.wind_gust_speed);
    const bearing = a.wind_bearing;
    const bearingDeg = bearing != null ? Math.round(bearing) : 0;
    const windDir = windDirectionLabel(bearing);
    const name = this._config.name || "Wind";

    // Beaufort scale color
    const speed = a.wind_speed || 0;
    let beaufort = 0;
    const bScale = [0.5, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7];
    for (let i = 0; i < bScale.length; i++) {
      if (speed >= bScale[i]) beaufort = i + 1;
    }
    const bColors = [
      "#78909c", "#81d4fa", "#4fc3f7", "#29b6f6", "#039be5",
      "#43a047", "#ffb300", "#fb8c00", "#f4511e", "#d32f2f",
      "#b71c1c", "#880e4f", "#4a148c"
    ];
    const bColor = bColors[Math.min(beaufort, bColors.length - 1)];

    this.shadowRoot.innerHTML = `
      <style>
        ${CARD_STYLES}
        .wind-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }
        .compass {
          position: relative;
          width: 180px;
          height: 180px;
        }
        .compass-ring {
          width: 100%;
          height: 100%;
        }
        .compass-labels {
          position: absolute;
          top: 0; left: 0; right: 0; bottom: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .compass-center {
          text-align: center;
        }
        .compass-speed {
          font-size: 28px;
          font-weight: 400;
          color: var(--windy-text);
          line-height: 1.1;
        }
        .compass-unit {
          font-size: 12px;
          color: var(--windy-secondary);
        }
        .compass-dir {
          font-size: 14px;
          font-weight: 500;
          color: ${bColor};
        }
        .wind-details {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr;
          gap: 8px;
          width: 100%;
        }
        .wind-detail {
          text-align: center;
        }
        .wind-detail .val {
          font-size: 16px;
          font-weight: 500;
        }
        .wind-detail .lbl {
          font-size: 11px;
          color: var(--windy-secondary);
        }
        .beaufort-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 12px;
          font-weight: 500;
          color: white;
          background: ${bColor};
        }
      </style>
      <ha-card>
        <div class="card-header-row">
          <div class="card-title">${name}</div>
          <span class="beaufort-badge">Bft ${beaufort}</span>
        </div>

        <div class="wind-container">
          <div class="compass">
            <svg viewBox="0 0 200 200" class="compass-ring">
              <!-- Compass circle -->
              <circle cx="100" cy="100" r="85" fill="none"
                      stroke="var(--divider-color, #e0e0e0)" stroke-width="2"/>
              <!-- Cardinal labels -->
              <text x="100" y="20" text-anchor="middle" font-size="13"
                    fill="var(--secondary-text-color)">N</text>
              <text x="185" y="105" text-anchor="middle" font-size="13"
                    fill="var(--secondary-text-color)">E</text>
              <text x="100" y="195" text-anchor="middle" font-size="13"
                    fill="var(--secondary-text-color)">S</text>
              <text x="15" y="105" text-anchor="middle" font-size="13"
                    fill="var(--secondary-text-color)">W</text>
              <!-- Wind arrow — points FROM the wind direction -->
              <g transform="rotate(${bearingDeg}, 100, 100)">
                <line x1="100" y1="28" x2="100" y2="75"
                      stroke="${bColor}" stroke-width="3" stroke-linecap="round"/>
                <polygon points="92,38 100,22 108,38"
                         fill="${bColor}"/>
              </g>
            </svg>
            <div class="compass-labels">
              <div class="compass-center">
                <div class="compass-speed">${windSpeed}</div>
                <div class="compass-unit">m/s</div>
                <div class="compass-dir">${windDir} ${bearing != null ? bearingDeg + "°" : ""}</div>
              </div>
            </div>
          </div>

          <div class="wind-details">
            <div class="wind-detail">
              <div class="val">${windSpeed}</div>
              <div class="lbl">Speed</div>
            </div>
            <div class="wind-detail">
              <div class="val">${windGust}</div>
              <div class="lbl">Gust</div>
            </div>
            <div class="wind-detail">
              <div class="val">${windDir}</div>
              <div class="lbl">Direction</div>
            </div>
          </div>
        </div>

        <div class="attribution">Data provided by Windy.com</div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 5;
  }
}


/* ═══════════════════════════════════════════════════════════════════════════
   4. WINDY WAVES CARD — Wave / swell conditions
   ═══════════════════════════════════════════════════════════════════════════ */

class WindyWavesCard extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _getSensor(suffix) {
    const e = this._config[suffix] || findWindyEntity(this._hass, "sensor", suffix);
    if (!e) return null;
    const s = this._hass.states[e];
    if (!s || s.state === "unknown" || s.state === "unavailable") return null;
    return parseFloat(s.state);
  }

  _render() {
    if (!this._hass) return;

    const waveHeight = this._getSensor("wave_height");
    const wavePeriod = this._getSensor("wave_period");
    const waveDir = this._getSensor("wave_direction");
    const wwHeight = this._getSensor("wind_wave_height");
    const wwPeriod = this._getSensor("wind_wave_period");
    const wwDir = this._getSensor("wind_wave_direction");
    const s1Height = this._getSensor("swell1_height");
    const s1Period = this._getSensor("swell1_period");
    const s1Dir = this._getSensor("swell1_direction");
    const s2Height = this._getSensor("swell2_height");
    const s2Period = this._getSensor("swell2_period");
    const s2Dir = this._getSensor("swell2_direction");

    const hasAnyWave = waveHeight != null;
    const name = this._config.name || "Wave Conditions";

    if (!hasAnyWave) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="card-header-row"><div class="card-title">${name}</div></div>
          <p style="color:var(--secondary-text-color);padding:8px 0;">
            No wave data available. Enable wave data in integration options.
          </p>
        </ha-card>`;
      return;
    }

    // Wave height color scale (0–5m)
    function waveColor(h) {
      if (h == null) return "var(--windy-secondary)";
      if (h < 0.5) return "#4caf50";
      if (h < 1.0) return "#8bc34a";
      if (h < 1.5) return "#ffb300";
      if (h < 2.5) return "#fb8c00";
      if (h < 4.0) return "#f4511e";
      return "#d32f2f";
    }

    function waveSection(label, icon, height, period, dir) {
      if (height == null) return "";
      return `
        <div class="wave-row">
          <div class="wave-label">
            <ha-icon icon="${icon}" style="--mdc-icon-size:20px;color:${waveColor(height)}"></ha-icon>
            <span>${label}</span>
          </div>
          <div class="wave-height" style="color:${waveColor(height)}">
            ${round1(height)}<small>m</small>
          </div>
          <div class="wave-period">${period != null ? round1(period) + "s" : "—"}</div>
          <div class="wave-dir">${dir != null ? windDirectionLabel(dir) + " " + Math.round(dir) + "°" : "—"}</div>
        </div>
      `;
    }

    this.shadowRoot.innerHTML = `
      <style>
        ${CARD_STYLES}
        .wave-header-row {
          display: grid;
          grid-template-columns: 1fr 60px 50px 70px;
          gap: 4px;
          padding-bottom: 4px;
          margin-bottom: 4px;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        .wave-header-row span {
          font-size: 10px;
          color: var(--windy-secondary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .wave-row {
          display: grid;
          grid-template-columns: 1fr 60px 50px 70px;
          align-items: center;
          gap: 4px;
          padding: 6px 0;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        .wave-row:last-child { border-bottom: none; }
        .wave-label {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
        }
        .wave-height {
          font-size: 16px;
          font-weight: 600;
          text-align: right;
        }
        .wave-height small {
          font-size: 11px;
          font-weight: normal;
        }
        .wave-period {
          font-size: 13px;
          text-align: right;
          color: var(--windy-secondary);
        }
        .wave-dir {
          font-size: 12px;
          text-align: right;
          color: var(--windy-secondary);
        }

        .hero-wave {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        .hero-wave-icon {
          --mdc-icon-size: 40px;
          color: ${waveColor(waveHeight)};
        }
        .hero-wave-val {
          font-size: 36px;
          font-weight: 300;
          color: var(--windy-text);
        }
        .hero-wave-val small {
          font-size: 16px;
          color: var(--windy-secondary);
        }
        .hero-wave-meta {
          font-size: 13px;
          color: var(--windy-secondary);
        }
      </style>
      <ha-card>
        <div class="card-header-row">
          <div class="card-title">${name}</div>
        </div>

        <div class="hero-wave">
          <ha-icon icon="mdi:waves" class="hero-wave-icon"></ha-icon>
          <div>
            <div class="hero-wave-val">${round1(waveHeight)}<small>m</small></div>
            <div class="hero-wave-meta">
              ${wavePeriod != null ? round1(wavePeriod) + "s period" : ""}
              ${waveDir != null ? " · " + windDirectionLabel(waveDir) + " " + Math.round(waveDir) + "°" : ""}
            </div>
          </div>
        </div>

        <div class="wave-header-row">
          <span>Component</span>
          <span style="text-align:right">Height</span>
          <span style="text-align:right">Period</span>
          <span style="text-align:right">Direction</span>
        </div>

        ${waveSection("Wind Waves", "mdi:waves-arrow-up", wwHeight, wwPeriod, wwDir)}
        ${waveSection("Primary Swell", "mdi:wave", s1Height, s1Period, s1Dir)}
        ${waveSection("Secondary Swell", "mdi:wave", s2Height, s2Period, s2Dir)}

        <div class="attribution">Data provided by Windy.com</div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 5;
  }
}


/* ═══════════════════════════════════════════════════════════════════════════
   5. WINDY WEBCAM CARD — Live webcam image
   ═══════════════════════════════════════════════════════════════════════════ */

class WindyWebcamCard extends HTMLElement {
  setConfig(config) {
    this._config = config;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) return;

    // Find camera entity
    let entity = this._config.entity;
    if (!entity) {
      // Find first windy camera entity
      const cameras = Object.keys(this._hass.states).filter(
        (k) => k.startsWith("camera.") && isWindyEntity(this._hass, k)
      );
      entity = cameras[0];
    }

    if (!entity) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div style="padding:16px;">
            <div class="card-title" style="font-size:16px;font-weight:500;margin-bottom:8px;">Windy Webcam</div>
            <p style="color:var(--secondary-text-color)">
              No webcam configured. Add a Webcam API key and webcam IDs in the integration options.
            </p>
          </div>
        </ha-card>`;
      return;
    }

    const s = this._hass.states[entity];
    if (!s) {
      this.shadowRoot.innerHTML = `<ha-card><p style="padding:16px">Webcam entity not found</p></ha-card>`;
      return;
    }

    const a = s.attributes;
    const name = this._config.name || a.friendly_name || "Webcam";
    const city = a.city || "";
    const country = a.country || "";
    const locationStr = [city, country].filter(Boolean).join(", ");
    const accessToken = a.access_token || "";
    // HA serves camera images at /api/camera_proxy/<entity_id>?token=<access_token>
    const imgUrl = `/api/camera_proxy/${entity}?token=${accessToken}&t=${Date.now()}`;

    // Show all available webcam entities for multi-cam support
    const allCams = Object.keys(this._hass.states).filter(
      (k) => k.startsWith("camera.") && isWindyEntity(this._hass, k)
    );

    const camTabs = allCams.length > 1
      ? allCams.map((c) => {
          const cs = this._hass.states[c];
          const label = cs ? (cs.attributes.friendly_name || c) : c;
          const active = c === entity ? "active" : "";
          return `<button class="cam-tab ${active}" data-entity="${c}">${label}</button>`;
        }).join("")
      : "";

    this.shadowRoot.innerHTML = `
      <style>
        ${CARD_STYLES}
        .webcam-img {
          width: 100%;
          border-radius: 8px;
          display: block;
          background: var(--divider-color, #e0e0e0);
          min-height: 180px;
          object-fit: cover;
        }
        .webcam-img-error {
          display: none;
          padding: 40px 16px;
          text-align: center;
          color: var(--secondary-text-color);
          font-size: 13px;
        }
        .webcam-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 8px;
        }
        .webcam-location {
          font-size: 12px;
          color: var(--windy-secondary);
        }
        .webcam-refresh {
          cursor: pointer;
          background: none;
          border: none;
          color: var(--windy-accent);
          font-size: 12px;
          padding: 4px 8px;
          border-radius: 4px;
        }
        .webcam-refresh:hover {
          background: var(--divider-color, #e0e0e0);
        }
        .cam-tabs {
          display: flex;
          gap: 4px;
          margin-bottom: 8px;
          overflow-x: auto;
        }
        .cam-tab {
          cursor: pointer;
          background: none;
          border: 1px solid var(--divider-color, #e0e0e0);
          border-radius: 12px;
          padding: 2px 10px;
          font-size: 11px;
          color: var(--windy-secondary);
          white-space: nowrap;
        }
        .cam-tab.active {
          background: var(--windy-accent);
          color: white;
          border-color: var(--windy-accent);
        }
      </style>
      <ha-card>
        <div style="padding:16px;">
          <div class="card-header-row">
            <div class="card-title">${name}</div>
          </div>
          ${camTabs ? `<div class="cam-tabs">${camTabs}</div>` : ""}
          <img class="webcam-img" src="${imgUrl}"
               onerror="this.style.display='none';this.nextElementSibling.style.display='block';"
               alt="${name}"/>
          <div class="webcam-img-error">
            <ha-icon icon="mdi:camera-off" style="--mdc-icon-size:32px;"></ha-icon>
            <br/>Image unavailable
          </div>
          <div class="webcam-meta">
            <span class="webcam-location">${locationStr}</span>
            <button class="webcam-refresh" id="refresh-btn">
              <ha-icon icon="mdi:refresh" style="--mdc-icon-size:14px;"></ha-icon> Refresh
            </button>
          </div>
          <div class="attribution">Data provided by Windy.com</div>
        </div>
      </ha-card>
    `;

    // Refresh button handler
    const btn = this.shadowRoot.getElementById("refresh-btn");
    if (btn) {
      btn.addEventListener("click", () => this._render());
    }

    // Camera tab switch
    const tabs = this.shadowRoot.querySelectorAll(".cam-tab");
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        this._config = { ...this._config, entity: tab.dataset.entity };
        this._render();
      });
    });
  }

  getCardSize() {
    return 5;
  }
}


/* ═══════════════════════════════════════════════════════════════════════════
   Registration
   ═══════════════════════════════════════════════════════════════════════════ */

customElements.define("windy-weather-card", WindyWeatherCard);
customElements.define("windy-forecast-card", WindyForecastCard);
customElements.define("windy-wind-card", WindyWindCard);
customElements.define("windy-waves-card", WindyWavesCard);
customElements.define("windy-webcam-card", WindyWebcamCard);

// Register with HA's custom card picker
window.customCards = window.customCards || [];
window.customCards.push(
  {
    type: "windy-weather-card",
    name: "Windy Weather",
    description: "Current weather conditions from Windy.com",
    preview: true,
  },
  {
    type: "windy-forecast-card",
    name: "Windy Forecast",
    description: "Hourly forecast timeline from Windy.com",
    preview: true,
  },
  {
    type: "windy-wind-card",
    name: "Windy Wind",
    description: "Wind compass with speed, gust, and direction",
    preview: true,
  },
  {
    type: "windy-waves-card",
    name: "Windy Waves",
    description: "Wave and swell conditions from Windy.com",
    preview: true,
  },
  {
    type: "windy-webcam-card",
    name: "Windy Webcam",
    description: "Live webcam image from Windy.com",
    preview: true,
  }
);

console.info(
  `%c WINDY HOME %c Cards v${WINDY_VERSION} loaded `,
  "background:#283593;color:white;padding:2px 6px;border-radius:3px 0 0 3px;",
  "background:#42a5f5;color:white;padding:2px 6px;border-radius:0 3px 3px 0;"
);
