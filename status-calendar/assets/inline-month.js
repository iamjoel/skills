(() => {
  const weekdays = Array.from("一二三四五六日");
  const legacyPartNames = { "🦸": "胸部", "🤷": "肩部", "🎯": "核心", "🏋️": "全身" };
  const levels = { "short-gym": 1, "long-gym": 2, "short-run": 1, "mid-run": 2, "over-ten-run": 3 };

  function element(tag, classes, text) {
    const node = document.createElement(tag);
    if (classes) node.className = classes;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function swatch(state) {
    const node = element("span", "status-month-swatch");
    if (state) node.style.backgroundColor = state.color;
    node.setAttribute("aria-hidden", "true");
    return node;
  }

  function textColor(color) {
    const [r, g, b] = color.slice(1).match(/../g).map(hex => {
      const n = parseInt(hex, 16) / 255;
      return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4;
    });
    return r * 0.2126 + g * 0.7152 + b * 0.0722 > 0.179 ? "#000" : "#fff";
  }

  window.renderStatusMonth = function renderStatusMonth(root, { states, days, month, bodyParts = [] }, submitDay) {
    const byId = new Map(states.map(state => [state.id, state]));
    const partsByEmoji = new Map(bodyParts);
    const partByName = new Map(bodyParts.map(([emoji, name]) => [name, emoji]));
    const partSymbols = bodyParts.map(([emoji]) => emoji.replaceAll("\uFE0F", ""));

    function partsFor(entry) {
      if (Array.isArray(entry.parts)) return entry.parts.filter(emoji => partsByEmoji.has(emoji));
      const oldName = legacyPartNames[entry.emoji] || partsByEmoji.get(entry.emoji);
      const emoji = partByName.get(oldName);
      return emoji ? [emoji] : [];
    }

    function primaryState(entries, kind) {
      const choices = entries.map(entry => byId.get(entry.stateId)).filter(state => state.kind === kind);
      return choices.reduce((best, state) => !best || (levels[state.id] || 0) > (levels[best.id] || 0) ? state : best, null);
    }

    function measurements(entry) {
      const values = [];
      if (Number.isFinite(entry.distanceKm) && entry.distanceKm > 0) values.push(entry.distanceKm.toFixed(2) + " 公里");
      if (Number.isFinite(entry.durationMinutes) && entry.durationMinutes > 0) values.push(entry.durationMinutes + " 分钟");
      return values.join(" · ");
    }

    function describe(entry) {
      const state = byId.get(entry.stateId);
      let label = state.label;
      if (state.kind === "gym") {
        const names = partsFor(entry).map(emoji => partsByEmoji.get(emoji));
        if (!names.length && !Array.isArray(entry.parts) && legacyPartNames[entry.emoji]) {
          names.push(legacyPartNames[entry.emoji] + " · 旧记录");
        }
        if (names.length) label += "（" + names.join("、") + "）";
      }
      const actual = measurements(entry);
      return actual ? label + " · " + actual : label;
    }

    const start = new Date(month + "-01T12:00:00");
    const monthName = (start.getMonth() + 1) + " 月";
    const last = new Date(start);
    last.setMonth(last.getMonth() + 1, 0);
    const today = new Date();
    const localMonth = today.getFullYear() + "-" + String(today.getMonth() + 1).padStart(2, "0");
    const section = element("section", "status-inline-month");
    const calendar = element("div", "status-month-view");
    const editor = element("div");
    const heading = element("h2", "", start.getFullYear() + " 年 " + monthName);
    const help = element("p", "text-small text-muted", "点选日期记录运动。两项同日时，左侧为力量，右侧为有氧。");
    const grid = element("div", "status-month-grid");
    grid.setAttribute("role", "group");
    grid.setAttribute("aria-label", heading.textContent + "状态日历");
    for (const weekday of weekdays) grid.append(element("span", "text-small text-muted text-center", "周" + weekday));
    const offset = (start.getDay() + 6) % 7;
    for (let i = 0; i < offset; i++) grid.append(element("span"));

    const datesInView = new Set();
    for (let day = 1; day <= last.getDate(); day++) {
      const dateKey = month + "-" + String(day).padStart(2, "0");
      const entries = (days[dateKey] || []).filter(entry => byId.has(entry.stateId));
      entries.forEach(entry => datesInView.add(entry.stateId));
      const strength = primaryState(entries, "gym");
      const cardio = primaryState(entries, "run");
      const custom = entries.filter(entry => byId.get(entry.stateId).kind === "custom");
      const first = strength || cardio;
      const button = element("button", "btn viz-tile tabular-nums status-month-day");
      button.type = "button";
      button.dataset.date = dateKey;
      button.style.backgroundColor = first ? first.color : "transparent";
      if (first) button.style.color = textColor(first.color);
      if (strength && cardio) {
        button.classList.add("status-month-mixed");
        button.style.backgroundImage = "linear-gradient(to right, " + strength.color + " 50%, " + cardio.color + " 50%)";
      }
      const dateLabel = element("span", "status-month-date", day);
      const face = element("span", "status-month-face");
      face.append(dateLabel);
      let marks = [];
      if (strength) {
        marks = entries.filter(entry => byId.get(entry.stateId).kind === "gym").flatMap(partsFor);
      } else if (!cardio) {
        marks = custom.map(entry => entry.emoji || byId.get(entry.stateId).emoji)
          .filter(mark => mark && !partSymbols.some(emoji => mark.replaceAll("\uFE0F", "").includes(emoji)));
      }
      const symbols = [...new Set(marks)].slice(0, 3);
      if (symbols.length) {
        const row = element("span", "status-month-marks");
        row.setAttribute("aria-hidden", "true");
        for (const emoji of symbols) row.append(element("span", "", emoji));
        face.append(row);
      }
      const isToday = month === localMonth && day === today.getDate();
      if (isToday) button.setAttribute("aria-current", "date");
      const name = monthName + day + " 日" + (isToday ? "（今天）" : "");
      const description = entries.map(describe).join("、");
      button.setAttribute("aria-label", name + "，" + (description || "无运动记录"));
      if (description) button.dataset.tooltip = description;
      button.append(face);
      button.addEventListener("click", () => openEditor(dateKey, name, entries, button));
      grid.append(button);
    }

    const legend = element("div", "viz-row status-month-legend");
    legend.setAttribute("role", "group");
    legend.setAttribute("aria-label", "状态图例");
    function addLegend(state, label) {
      const item = element("span", "status-month-key text-small");
      item.append(swatch(state), document.createTextNode(label));
      legend.append(item);
    }
    for (const state of states) {
      if (!state.archived || datesInView.has(state.id)) addLegend(state, state.label);
    }
    addLegend(null, "无运动");
    calendar.append(heading, help, grid, legend);
    editor.hidden = true;
    section.append(calendar, editor);
    root.replaceChildren(section);

    function openEditor(dateKey, name, entries, opener) {
      const form = element("form", "status-month-edit");
      form.addEventListener("submit", event => event.preventDefault());
      const title = element("h2", "", name);
      form.append(title);
      const measured = entries.filter(entry => measurements(entry));
      if (measured.length) {
        form.append(element("p", "text-small", "原记录 · " + measured.map(describe).join("，")));
      }

      function group(kind, label) {
        const original = entries.filter(entry => byId.get(entry.stateId).kind === kind);
        const ids = new Set(original.map(entry => entry.stateId));
        const select = element("select", "form-select");
        select.setAttribute("aria-label", label);
        select.add(new Option("无", ""));
        for (const state of states) {
          if (state.kind === kind && (!state.archived || ids.has(state.id))) select.add(new Option(state.label, state.id));
        }
        let initial = original.length ? original[0].stateId : "";
        let keep;
        if (ids.size > 1) {
          keep = new Option("保留已有记录：" + [...ids].map(id => byId.get(id).label).join("、"));
          select.add(keep);
          keep.selected = true;
          initial = keep.value;
        } else {
          select.value = initial;
        }
        const field = element("label", "form-label status-month-field", label);
        field.append(select);
        if (select.options.length > 1) form.append(field);
        return { select, original, initial, keep };
      }

      const gym = group("gym", "力量训练");
      const selectedParts = [...new Set(gym.original.flatMap(partsFor))].slice(0, 3);
      const fieldset = element("fieldset", "status-month-part-field");
      fieldset.append(element("legend", "form-label", "锻炼部位（最多 3 个）"));
      const choices = element("div", "viz-row status-month-part-options");
      const partControls = [];
      let partsChanged = false;
      for (const [emoji, name] of bodyParts) {
        const item = element("label", "form-check");
        const input = element("input", "form-check-input");
        input.type = "checkbox";
        input.value = emoji;
        input.checked = selectedParts.includes(emoji);
        input.addEventListener("change", () => {
          partsChanged = true;
          updateParts();
        });
        partControls.push(input);
        item.append(input, element("span", "form-check-label", emoji + " " + name));
        choices.append(item);
      }
      function updateParts() {
        fieldset.hidden = !gym.select.value || !!gym.keep?.selected;
        const count = partControls.filter(input => input.checked).length;
        for (const input of partControls) input.disabled = !input.checked && count >= 3;
      }
      gym.select.addEventListener("change", updateParts);
      updateParts();
      fieldset.append(choices);
      form.append(fieldset);
      const cardio = group("run", "跑步或其他有氧");

      const custom = [];
      const customOptions = element("div", "viz-row status-month-part-options");
      for (const state of states.filter(state => state.kind === "custom")) {
        const original = entries.filter(entry => entry.stateId === state.id);
        if (state.archived && !original.length) continue;
        const item = element("label", "form-check");
        const input = element("input", "form-check-input");
        input.type = "checkbox";
        input.checked = original.length > 0;
        item.append(input, element("span", "form-check-label", state.label));
        customOptions.append(item);
        custom.push({ state, input, original });
      }
      if (custom.length) form.append(customOptions);

      const actions = element("div", "viz-controls");
      const submit = element("button", "btn btn-primary", "保存记录");
      submit.type = "button";
      const back = element("button", "btn btn-ghost", "返回月历");
      back.type = "button";
      back.addEventListener("click", () => {
        editor.hidden = true;
        editor.replaceChildren();
        calendar.hidden = false;
        opener.focus();
      });
      const message = element("p", "text-small");
      message.setAttribute("role", "status");
      const error = element("p", "text-small text-destructive");
      error.setAttribute("role", "alert");

      function selectedGroup(control, editedParts) {
        const id = control.select.value;
        if (!id) return [];
        if (control.keep?.selected || (id === control.initial && !editedParts)) return control.original;
        const entry = id === control.initial && control.original.length === 1
          ? { ...control.original[0], emoji: "" } : { stateId: id, emoji: "" };
        if (control === gym) entry.parts = partControls.filter(input => input.checked).map(input => input.value);
        return [entry];
      }

      submit.addEventListener("click", async () => {
        if (submit.disabled) return;
        const updated = [...selectedGroup(gym, partsChanged), ...selectedGroup(cardio, false)];
        for (const { state, input, original } of custom) {
          if (input.checked) updated.push(...(original.length ? original : [{ stateId: state.id, emoji: "" }]));
        }
        const enabled = Array.from(form.elements).filter(control => !control.disabled);
        enabled.forEach(control => { control.disabled = true; });
        error.textContent = "";
        message.textContent = "正在提交…";
        try {
          await submitDay(dateKey, updated);
          message.textContent = "已提交保存请求。";
        } catch (reason) {
          message.textContent = "";
          error.textContent = reason?.message || "提交失败，请重试。";
        } finally {
          enabled.forEach(control => { control.disabled = false; });
          updateParts();
        }
      });
      actions.append(submit, back);
      form.append(actions, message, error);
      editor.replaceChildren(form);
      calendar.hidden = true;
      editor.hidden = false;
      (form.querySelector("select, input") || back).focus();
    }
  };
})();
