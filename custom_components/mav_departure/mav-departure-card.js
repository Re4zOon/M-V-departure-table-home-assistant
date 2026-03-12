/**
 * mav-departure-card.js
 *
 * A custom Lovelace card for the MÁV Departure Table integration.
 * Displays a departure board showing scheduled / expected times and delays
 * for a configured MÁV sensor entity.
 *
 * This card is automatically registered when the integration is loaded.
 *
 * Card configuration example:
 *   type: custom:mav-departure-card
 *   entity: sensor.mav_005501016_005501057
 *   title: "Budapest-Keleti → Győr"
 *   max_departures: 8
 */

class MavDepartureCard extends HTMLElement {
  /* ------------------------------------------------------------------ */
  /* Lovelace card lifecycle                                              */
  /* ------------------------------------------------------------------ */

  set hass(hass) {
    this._hass = hass;
    if (!this._config || !hass?.states) return;

    const stateObj = hass.states[this._config.entity];
    const maxItems = this._config.max_departures || 10;
    const title = this._config.title || "";
    const departures = stateObj?.attributes?.departures || [];
    const lastError = stateObj?.attributes?.last_error ?? null;
    const baseKey = JSON.stringify({
      entity: this._config.entity,
      missing: !stateObj,
      lastUpdated: stateObj?.last_updated || null,
      state: stateObj?.state || null,
      lastError,
      maxItems,
      title,
    });

    if (this._lastBaseKey === baseKey && this._lastDeparturesRef === departures) {
      return;
    }

    const departuresKey = JSON.stringify(departures);
    if (this._lastBaseKey === baseKey && this._lastDeparturesKey === departuresKey) {
      this._lastDeparturesRef = departures;
      return;
    }

    this._lastBaseKey = baseKey;
    this._lastDeparturesKey = departuresKey;
    this._lastDeparturesRef = departures;
    this._render();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("MÁV Departure Card: 'entity' is required in card config.");
    }
    this._config = config;
    this._lastBaseKey = undefined;
    this._lastDeparturesKey = undefined;
    this._lastDeparturesRef = undefined;
    if (this._hass) this._render();
  }

  getCardSize() {
    const max = (this._config && this._config.max_departures) || 10;
    return Math.ceil(max / 2) + 2;
  }

  /* ------------------------------------------------------------------ */
  /* Rendering                                                            */
  /* ------------------------------------------------------------------ */

  _render() {
    if (!this._hass || !this._config) return;

    const stateObj = this._hass.states[this._config.entity];
    const title =
      this._config.title ||
      (stateObj ? stateObj.attributes.friendly_name : this._config.entity);
    const maxItems = this._config.max_departures || 10;

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    if (!stateObj) {
      const entity = this._escapeHtml(this._config.entity);
      this.shadowRoot.innerHTML = this._wrapCard(
        title,
        `<p class="warning">Entity not found: ${entity}</p>`
      );
      return;
    }

    if (stateObj.state === "unavailable") {
      const lastError = stateObj.attributes?.last_error;
      const errorDetail = lastError || "Unable to reach the MÁV API.";
      this.shadowRoot.innerHTML = this._wrapCard(
        title,
        this._renderErrorBanner(errorDetail)
      );
      return;
    }

    const lastError = stateObj.attributes?.last_error;
    const departures = (stateObj.attributes.departures || []).slice(0, maxItems);

    if (departures.length === 0) {
      const noDataMsg = lastError
        ? this._renderErrorBanner(lastError)
        : `<p class="no-data">No upcoming departures found.</p>`;
      this.shadowRoot.innerHTML = this._wrapCard(title, noDataMsg);
      return;
    }

    const rows = departures.map((d) => this._renderRow(d)).join("");
    const errorHtml = lastError ? this._renderErrorBanner(lastError) : "";

    this.shadowRoot.innerHTML = this._wrapCard(
      title,
      `${errorHtml}<table>
        <thead>
          <tr>
            <th>Train</th>
            <th>From</th>
            <th>To</th>
            <th>Scheduled</th>
            <th>Expected</th>
            <th>Delay</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`
    );
  }

  _renderRow(dep) {
    const scheduled = this._escapeHtml(this._formatTime(dep.scheduled));
    const expected = this._escapeHtml(this._formatTime(dep.expected));
    const delayClass = dep.has_delay ? "delayed" : "on-time";
    const delayLabel = dep.has_delay
      ? this._escapeHtml(`+${dep.delay_minutes} min`)
      : "On time";
    const sign = this._escapeHtml(dep.train_sign || "—");
    const origin = this._escapeHtml(dep.train_origin || "—");
    const destination = this._escapeHtml(dep.train_destination || "—");

    return `<tr class="${dep.has_delay ? "row-delayed" : ""}">
      <td class="train-sign">${sign}</td>
      <td>${origin}</td>
      <td>${destination}</td>
      <td>${scheduled}</td>
      <td class="${dep.has_delay ? "expected-delayed" : ""}">${expected}</td>
      <td class="delay ${delayClass}">${delayLabel}</td>
    </tr>`;
  }

  _wrapCard(title, bodyHtml) {
    return `
      <style>
        :host {
          display: block;
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        ha-card {
          padding: 0;
        }
        .card-header {
          padding: 16px 16px 8px;
          font-size: 1.1em;
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--primary-text-color);
        }
        .card-header svg {
          flex-shrink: 0;
          fill: var(--primary-color, #03a9f4);
        }
        .card-content {
          padding: 0 0 8px;
          overflow-x: auto;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.9em;
        }
        thead tr {
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        th {
          padding: 4px 12px;
          text-align: left;
          font-weight: 500;
          color: var(--secondary-text-color);
          white-space: nowrap;
        }
        td {
          padding: 6px 12px;
          border-bottom: 1px solid var(--divider-color, #f0f0f0);
          white-space: nowrap;
        }
        .row-delayed {
          background: rgba(255, 152, 0, 0.06);
        }
        .train-sign {
          font-weight: 500;
          color: var(--primary-text-color);
        }
        .expected-delayed {
          color: var(--error-color, #e53935);
          font-weight: 500;
        }
        .delay {
          font-weight: 500;
        }
        .on-time {
          color: var(--success-color, #43a047);
        }
        .delayed {
          color: var(--error-color, #e53935);
        }
        .warning, .no-data {
          padding: 12px 16px;
          color: var(--secondary-text-color);
          font-style: italic;
        }
        .warning {
          color: var(--error-color, #e53935);
        }
        .error-banner {
          padding: 12px 16px;
          margin: 0 8px 8px;
          background: rgba(229, 57, 53, 0.08);
          border-left: 3px solid var(--error-color, #e53935);
          border-radius: 4px;
          color: var(--primary-text-color);
          font-size: 0.9em;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .error-banner strong {
          color: var(--error-color, #e53935);
        }
      </style>
      <ha-card>
        <div class="card-header">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24">
            <path d="M12 2c-4 0-8 .5-8 4v9.5C4 17.43 5.57 19 7.5 19L6 20.5v.5h2.23l2-2H14l2 2H18v-.5L16.5 19c1.93 0 3.5-1.57 3.5-3.5V6c0-3.5-3.58-4-8-4zm0 2c3.51 0 5.5.48 5.93 1.5H6.07C6.5 4.48 8.49 4 12 4zm-5.5 3h11v5h-11V7zm.5 7.5a1 1 0 0 1 1 1 1 1 0 0 1-1 1 1 1 0 0 1-1-1 1 1 0 0 1 1-1zm9 0a1 1 0 0 1 1 1 1 1 0 0 1-1 1 1 1 0 0 1-1-1 1 1 0 0 1 1-1z"/>
          </svg>
          ${this._escapeHtml(title)}
        </div>
        <div class="card-content">${bodyHtml}</div>
      </ha-card>`;
  }

  /** Format an ISO-8601 datetime string to HH:MM using the browser locale. */
  _formatTime(isoString) {
    if (!isoString) return "—";
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoString;
    }
  }

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  _renderErrorBanner(message) {
    return `<div class="error-banner" role="alert" aria-live="assertive">
      <strong><span aria-hidden="true">⚠</span> Error</strong>
      <span>${this._escapeHtml(message)}</span>
    </div>`;
  }
}

if (!customElements.get("mav-departure-card")) {
  customElements.define("mav-departure-card", MavDepartureCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card?.type === "mav-departure-card")) {
  window.customCards.push({
    type: "mav-departure-card",
    name: "MÁV Departure Table",
    description:
      "Displays real-time MÁV (Hungarian Railways) departure times with delay information.",
    preview: false,
  });
}
