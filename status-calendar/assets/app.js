(() => {
  "use strict";

  const app = document.getElementById("app");
  let snapshot;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  async function calendarRequest(options) {
    let response;
    try {
      response = await fetch("/api/calendar", options);
    } catch {
      throw new Error("连不上本机日历。请重新打开技能，再试一次。");
    }
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "读取或保存失败，请重试。");
    document.querySelector(".storage-label").textContent =
      result.source && result.source !== "local" ? "数据保存在云端" : "数据保存在本机";
    return result;
  }

  async function persist(states, days) {
    snapshot = await calendarRequest({
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ revision: snapshot.revision, source: snapshot.source || "local", states, days }),
    });
    return snapshot;
  }

  function saveDays(dateKey, entries) {
    const days = { ...snapshot.days };
    if (entries.length) days[dateKey] = entries;
    else delete days[dateKey];
    return persist(snapshot.states, days);
  }

  function renderPreview(states, activeId) {
    const now = new Date();
    const month = now.getFullYear() + "-" + String(now.getMonth() + 1).padStart(2, "0");
    const activeStates = states.filter(state => !state.archived);
    const examples = {};
    const sample = state => {
      const entry = { stateId: state.id, emoji: "" };
      if (state.kind === "gym") entry.parts = [snapshot.bodyParts[0][0]];
      return entry;
    };
    const dayNumbers = [3, 6, 10, 12, 17, 18, 24, 27];
    const active = activeStates.find(state => state.id === activeId);
    for (const [i, state] of activeStates.slice(0, dayNumbers.length).entries()) {
      examples[month + "-" + String(dayNumbers[i]).padStart(2, "0")] = [sample(state)];
    }
    if (active) examples[month + "-27"] = [sample(active)];
    const strength = activeStates.find(state => state.kind === "gym");
    const cardio = activeStates.find(state => state.kind === "run");
    if (strength && cardio) examples[month + "-15"] = [sample(strength), sample(cardio)];
    window.renderStatusMonth(document.getElementById("preview-grid"),
      { states: activeStates, days: examples, month, bodyParts: snapshot.bodyParts }, () => {});
  }

  function renderSettings() {
    const draft = (snapshot.states || snapshot.defaultStates).map(state => ({ ...state }));
    const usedIds = new Set(Object.values(snapshot.days).flat().map(entry => entry.stateId));
    app.replaceChildren(document.getElementById("settings-page").content.cloneNode(true));
    const form = document.getElementById("settings-form");
    const list = document.getElementById("state-list");
    const error = document.getElementById("form-error");

    function addRow(state) {
      const row = element("div", "state-row state-grid");
      const name = element("input", "name-input");
      name.type = "text";
      name.required = true;
      name.maxLength = 48;
      name.value = state.label;
      name.placeholder = "状态名称";
      const colorField = element("label", "color-field");
      const chip = element("span", "color-chip");
      chip.style.backgroundColor = state.color;
      const hex = element("span", "color-value", state.color.toUpperCase());
      const color = element("input");
      color.type = "color";
      color.value = state.color;
      colorField.append(chip, hex, color);
      const emoji = element("input", "emoji-input");
      emoji.type = "text";
      emoji.required = state.kind === "custom";
      emoji.disabled = state.kind !== "custom";
      emoji.hidden = state.kind !== "custom";
      emoji.maxLength = 32;
      emoji.value = state.emoji;
      const iconField = element("span");
      iconField.append(emoji);
      row.append(name, colorField, iconField);
      const remove = element("button", "remove-state", "×");
      if (state.kind === "custom" && !usedIds.has(state.id)) {
        remove.type = "button";
        remove.addEventListener("click", () => {
          draft.splice(draft.indexOf(state), 1);
          row.remove();
          renderPreview(draft);
          document.getElementById("add-state").focus();
        });
        row.append(remove);
      }
      function updateLabels() {
        const label = state.label.trim() || "新状态";
        name.setAttribute("aria-label", label + "的名称");
        color.setAttribute("aria-label", label + "的背景色");
        emoji.setAttribute("aria-label", label + "的 emoji");
        remove.setAttribute("aria-label", "移除" + label);
      }
      updateLabels();
      name.addEventListener("input", () => {
        state.label = name.value;
        name.setCustomValidity(name.value.trim() ? "" : "请输入状态名称。");
        updateLabels();
        renderPreview(draft, state.id);
      });
      color.addEventListener("input", () => {
        state.color = color.value.toUpperCase();
        chip.style.backgroundColor = state.color;
        hex.textContent = state.color;
        renderPreview(draft, state.id);
      });
      emoji.addEventListener("input", () => {
        state.emoji = emoji.value;
        emoji.setCustomValidity(emoji.value.trim() ? "" : "请输入一个 emoji。");
        renderPreview(draft, state.id);
      });
      list.append(row);
      return name;
    }

    draft.filter(state => !state.archived).forEach(addRow);
    const parts = document.getElementById("body-parts");
    parts.textContent = snapshot.bodyParts.map(([emoji, name]) => emoji + " " + name).join("　");
    renderPreview(draft);
    document.getElementById("add-state").addEventListener("click", () => {
      const state = { id: crypto.randomUUID(), label: "", color: "#E6E6E6", emoji: "✨", kind: "custom" };
      draft.push(state);
      addRow(state).focus();
      renderPreview(draft, state.id);
    });
    const cancel = document.getElementById("cancel-settings");
    cancel.hidden = !snapshot.states;
    cancel.addEventListener("click", () => navigate("#month"));
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const fields = document.getElementById("state-fields");
      fields.disabled = true;
      error.textContent = "";
      try {
        const states = draft.map(state => ({ ...state, label: state.label.trim(), emoji: state.emoji.trim() }));
        await persist(states, snapshot.days);
        navigate("#month");
      } catch (failure) {
        error.textContent = failure.message;
      } finally {
        fields.disabled = false;
      }
    });
  }

  function navigate(hash) {
    if (location.hash !== hash) location.hash = hash;
    else showPage();
  }

  function showPage() {
    if (!snapshot) return;
    if (location.hash === "#month" && snapshot.states) {
      document.title = "月历 · 状态日历";
      window.StatusMonth.render(app, snapshot, { onConfigure: () => navigate("#configure"), saveDays });
    } else {
      document.title = "配置状态 · 状态日历";
      renderSettings();
    }
    app.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  async function start() {
    try {
      snapshot = await calendarRequest();
      showPage();
    } catch (failure) {
      const message = element("p", "error-text", failure.message);
      message.setAttribute("role", "alert");
      const retry = element("button", "quiet-button", "重新读取");
      retry.addEventListener("click", start);
      app.replaceChildren(message, retry);
    }
  }
  window.addEventListener("hashchange", showPage);
  start();
})();
