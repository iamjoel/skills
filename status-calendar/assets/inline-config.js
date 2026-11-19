function renderStatusConfig(root, data, submitEdit) {
  const draft = data.states.map(state => ({ ...state }));
  const used = new Set(data.usedIds);

  function el(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  const form = el("form", "sc-config");
  const list = el("div", "sc-config-list");
  const headings = el("div", "sc-config-grid sc-config-head text-muted text-small");
  headings.setAttribute("aria-hidden", "true");
  headings.append(el("span", "", "状态名称"), el("span", "", "背景色"));
  const iconHeading = el("span", "sc-custom-column", "图标");
  headings.append(iconHeading);
  const notice = el("p", "text-small");
  notice.setAttribute("role", "status");
  const add = el("button", "btn", "添加状态");
  add.type = "button";
  const save = el("button", "btn btn-primary", "保存并查看本月");
  save.type = "button";
  const actions = el("div", "viz-row");
  actions.append(add, save);
  form.append(el("h2", "", "状态配置"), headings, list);
  if (draft.some(state => !state.archived && state.kind === "gym") && data.bodyParts?.length) {
    const parts = el("section", "sc-config-parts");
    parts.append(el("h3", "", "力量训练部位"));
    const legend = el("ul", "sc-part-list");
    for (const [emoji, name] of data.bodyParts) legend.append(el("li", "", emoji + " " + name));
    parts.append(legend, el("p", "text-small text-muted",
      "每格最多显示 3 个部位。同日兼有两种运动时，左侧是力量，右侧是有氧。未运动的日期无底色。"));
    form.append(parts);
  }
  form.append(actions, notice);
  root.replaceChildren(form);

  function updateColumns() {
    const hasCustom = draft.some(state => !state.archived && state.kind === "custom");
    form.classList.toggle("sc-has-custom", hasCustom);
    iconHeading.hidden = !hasCustom;
  }

  function addRow(state) {
    const row = el("div", "sc-config-grid");
    function field(key, description, type, classes) {
      const label = el("label", "form-label");
      const name = el("span", "sr-only");
      const input = el("input", classes);
      input.type = type;
      input.value = state[key];
      input.required = true;
      input.dataset.field = key;
      input.addEventListener("input", () => {
        state[key] = input.value;
        input.setCustomValidity(input.value.trim() ? "" : "请填写" + description + "。");
        notice.textContent = "";
        updateNames();
      });
      label.append(name, input);
      row.append(label);
      return { input, name, description };
    }
    const name = field("label", "状态名称", "text", "form-control");
    name.input.placeholder = "新状态";
    name.input.maxLength = 48;
    const color = field("color", "背景色", "color", "form-control form-control-color");
    const fields = [name, color];
    if (state.kind === "custom") {
      const emoji = field("emoji", "图标", "text", "form-control");
      emoji.input.maxLength = 32;
      fields.push(emoji);
    }
    const remove = el("button", "btn btn-ghost", "×");
    remove.type = "button";
    if (state.kind === "custom" && !used.has(state.id)) {
      remove.addEventListener("click", () => {
        row.remove();
        draft.splice(draft.indexOf(state), 1);
        updateColumns();
        notice.textContent = "";
        add.focus();
      });
      row.append(remove);
    }
    function updateNames() {
      const label = state.label.trim() || "新状态";
      for (const field of fields) field.name.textContent = label + "的" + field.description;
      remove.setAttribute("aria-label", "移除" + label);
    }
    updateNames();
    list.append(row);
    return name.input;
  }

  draft.filter(state => !state.archived).forEach(addRow);
  updateColumns();
  add.addEventListener("click", () => {
    const bytes = crypto.getRandomValues(new Uint32Array(4));
    const id = Array.from(bytes, word => word.toString(16).padStart(8, "0")).join("");
    const state = { id, kind: "custom", label: "", color: "#E6E6E6", emoji: "✨" };
    draft.push(state);
    updateColumns();
    addRow(state).focus();
    notice.textContent = "";
  });
  save.addEventListener("click", async () => {
    if (!form.reportValidity()) return;
    try {
      const states = draft.map(state => ({ ...state, label: state.label.trim(), emoji: state.emoji.trim() }));
      await submitEdit({ action: "configure", states });
      notice.textContent = "请在聊天中确认保存，随后会显示本月日历。";
    } catch (error) {
      notice.textContent = error.message;
    }
  });
}
