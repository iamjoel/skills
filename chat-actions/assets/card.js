(() => {
  const root = document.getElementById("__ROOT__");

  root.addEventListener("click", event => {
    const link = event.target.closest?.("a[data-info-link]");
    if (event.defaultPrevented || !link || !window.openai?.openExternal) return;
    event.preventDefault();
    event.stopPropagation();
    window.openai.openExternal({ href: link.href });
  });

  function offerManual(container, prompt) {
    const fallback = container.querySelector("[data-manual]");
    const textarea = fallback.querySelector("textarea");
    textarea.value = prompt;
    fallback.hidden = false;
    textarea.focus();
    textarea.select();
    return fallback;
  }

  async function send(container, button, title, prompt, confirmation) {
    const status = container.querySelector("[data-status]");
    button.disabled = true;
    try {
      await window.openai.sendFollowUpMessage({ title, prompt });
      status.textContent = confirmation;
    } catch {
      offerManual(container, prompt);
      status.textContent = "请复制下方内容并发送到当前聊天。";
    } finally {
      button.disabled = false;
    }
  }

  const settings = root.querySelector("[data-settings]");
  if (settings) {
    const directory = settings.querySelector("input");
    const save = settings.querySelector("button");

    function saveDirectory() {
      const value = directory.value.trim();
      if (!value) {
        directory.setCustomValidity("请输入命令目录。");
        directory.reportValidity();
        return;
      }
      settings.querySelector("[data-manual]").hidden = true;
      const prompt = "用 $chat-actions 更新命令目录。\n#setting\n" +
        JSON.stringify({ directory: value });
      send(settings, save, "保存命令目录", prompt, "请在聊天中确认保存。");
    }

    save.addEventListener("click", saveDirectory);
    directory.addEventListener("input", () => directory.setCustomValidity(""));
    directory.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.isComposing) save.click();
    });
  }

  const picker = root.querySelector("[data-file-selection]");
  if (picker) {
    const file = picker.querySelector("select");
    const confirm = picker.querySelector("button");

    confirm.addEventListener("click", () => {
      if (!file.reportValidity()) return;
      picker.querySelector("[data-manual]").hidden = true;
      const prompt = "用 $chat-actions 更新选中的命令文件。\n#init\n" +
        JSON.stringify({ directory: picker.dataset.directory, file: file.value });
      send(picker, confirm, "选择命令文件", prompt, "请在聊天中确认选择。");
    });
  }

  function parseTemplate(template, names) {
    const parts = [];
    let offset = 0;
    for (const match of template.matchAll(/\{\?([\w.-]+):((?:[^{}]|\{[\w.-]+\})*)\}|\{([\w.-]+)\}/g)) {
      const [token, condition, body, variable] = match;
      const name = condition || variable;
      names.add(name);
      parts.push(template.slice(offset, match.index));
      parts.push(condition ? { name, body: parseTemplate(body, names) } : { name, token });
      offset = match.index + token.length;
    }
    parts.push(template.slice(offset));
    return parts;
  }

  function expand(parts, valueFor, append) {
    for (const part of parts) {
      if (typeof part === "string") {
        append(part);
      } else if (part.body) {
        if (valueFor(part.name)) expand(part.body, valueFor, append);
      } else {
        const value = valueFor(part.name);
        if (value) append(value, true);
        else append(part.token);
      }
    }
  }

  function expandedText(parts, valueFor) {
    let text = "";
    expand(parts, valueFor, part => { text += part; });
    return text;
  }

  function appendEditor(target, parts, fieldFor) {
    for (const part of parts) {
      if (typeof part === "string") {
        target.append(part);
      } else if (part.body) {
        if (!part.body.some(item => item.name === part.name)) target.append(fieldFor(part.name));
        appendEditor(target, part.body, fieldFor);
      } else {
        target.append(fieldFor(part.name));
      }
    }
  }

  function bindCommand(command, sharedFields, templateValues, refreshGroup) {
    const label = command.querySelector("h3, h4").textContent;
    const preview = command.querySelector("[data-preview]");
    const status = command.querySelector("[data-status]");
    const manual = command.querySelector("[data-manual]");
    const required = JSON.parse(command.dataset.requires);
    const names = new Set();
    const parts = parseTemplate(command.dataset.template, names);
    const local = command.querySelector("[data-local-variables]");
    const localFields = new Map(Array.from(local?.querySelectorAll("[data-variable]") ?? [], field =>
      [field.dataset.variable, field]
    ));
    const fieldFor = name => localFields.get(name) ?? sharedFields.get(name);
    const rawValueFor = name => fieldFor(name)?.value ?? templateValues.get(name) ?? "";
    const valueFor = name => rawValueFor(name).trim();
    const labelFor = name => fieldFor(name)?.closest("label").querySelector("span").textContent || name;
    let drafts = null;

    const edit = names.size ? command.querySelector('[data-action="edit"]') : null;
    const editIcon = edit?.querySelector("[data-edit-icon]");
    const saveLabel = edit?.querySelector("[data-edit-save]");

    function refresh() {
      if (drafts) {
        for (const [name, draft] of drafts) {
          const value = rawValueFor(name);
          if (value === draft.initial || draft.fields[0].value !== draft.initial) continue;
          draft.initial = value;
          for (const field of draft.fields) field.value = value;
        }
        return;
      }
      const content = document.createDocumentFragment();
      expand(parts, valueFor, (text, isVariableValue) => {
        if (isVariableValue) {
          const code = document.createElement("code");
          code.textContent = text;
          content.append(code);
        } else {
          content.append(text);
        }
      });
      preview.replaceChildren(content);
      status.textContent = "";
      manual.hidden = true;
    }

    function updateEditButton() {
      const editing = Boolean(drafts);
      const action = editing ? "保存变量" : "编辑变量";
      command.toggleAttribute("data-editing", editing);
      edit.classList.toggle("btn-primary", editing);
      edit.classList.toggle("btn-ghost", !editing);
      editIcon.hidden = editing;
      saveLabel.hidden = !editing;
      edit.dataset.tooltip = action;
      edit.setAttribute("aria-label", `${action} ${label}`);
    }

    function inlineField(name) {
      const draft = drafts.get(name) ?? { initial: rawValueFor(name), fields: [] };
      const original = fieldFor(name);
      const field = original?.cloneNode(true) ?? document.createElement("input");
      const fieldLabel = labelFor(name);
      if (!original) field.className = "form-control";
      if (field.tagName === "SELECT") {
        field.options[0].textContent = fieldLabel;
      } else {
        field.placeholder = fieldLabel;
      }
      field.value = draft.initial;
      field.setAttribute("aria-label", fieldLabel);
      draft.fields.push(field);
      drafts.set(name, draft);
      field.addEventListener("input", () => {
        for (const other of draft.fields) {
          if (other !== field) other.value = field.value;
        }
      });
      const wrapper = document.createElement("span");
      wrapper.className = "inline-variable";
      wrapper.append(field);
      return wrapper;
    }

    function startEditing(focusName) {
      drafts = new Map();
      updateEditButton();
      status.textContent = "";
      manual.hidden = true;
      preview.replaceChildren();
      appendEditor(preview, parts, inlineField);
      const first = drafts.get(focusName) ?? drafts.values().next().value;
      first.fields[0].focus();
    }

    function saveEdits() {
      for (const [name, { initial, fields }] of drafts) {
        const value = fields[0].value;
        if (value === initial) continue;
        const field = fieldFor(name);
        if (field) field.value = value;
        else templateValues.set(name, value);
      }
      drafts = null;
      updateEditButton();
      refreshGroup();
      status.textContent = "已保存变量。";
      edit.focus();
    }

    if (edit) edit.hidden = false;
    command.addEventListener("click", async event => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      if (button === edit) {
        if (drafts) saveEdits();
        else startEditing();
        return;
      }

      const missing = required.find(name => !valueFor(name));
      if (missing !== undefined) {
        if (names.has(missing)) startEditing(missing);
        else {
          const field = sharedFields.get(missing);
          if (field) {
            field.closest("details").open = true;
            field.focus();
          }
        }
        status.textContent = `请填写「${labelFor(missing)}」。`;
        return;
      }

      manual.hidden = true;
      let prompt = expandedText(parts, valueFor);
      if (button.dataset.action === "run") {
        const incrementBy = command.dataset.incrementBy;
        const reset = command.dataset.reset !== undefined;
        let amount;
        if (incrementBy) {
          amount = valueFor(incrementBy);
          const number = Number(amount);
          if (!Number.isFinite(number) || number <= 0) {
            if (names.has(incrementBy)) startEditing(incrementBy);
            status.textContent = `请为「${labelFor(incrementBy)}」输入大于 0 的数量。`;
            return;
          }
        }
        if (incrementBy || reset) {
          const request = {
            file: command.closest("[data-command-file]").dataset.commandFile,
            command: command.dataset.commandId,
            amount,
            requestId: crypto.randomUUID(),
          };
          const action = reset ? "reset" : "increment";
          prompt += `\n#${action}\n` + JSON.stringify(request);
        }
        const title = `运行「${label}」`.slice(0, 250);
        await send(command, button, title, prompt, "请在聊天中确认运行。");
        return;
      }

      try {
        await navigator.clipboard.writeText(prompt);
        status.textContent = "已复制。";
      } catch {
        const fallback = offerManual(command, prompt);
        if (document.execCommand("copy")) {
          fallback.hidden = true;
          button.focus();
          status.textContent = "已复制。";
        } else {
          status.textContent = "请复制已选中的命令。";
        }
      }
    });
    return refresh;
  }

  for (const panel of root.querySelectorAll("[data-command-file]")) {
    const shared = panel.querySelector(":scope > .command-parameters > .variables");
    const fields = new Map(Array.from(shared?.querySelectorAll("[data-variable]") ?? [], field => [field.dataset.variable, field]));
    const templateValues = new Map();
    const info = Array.from(panel.querySelectorAll("[data-group-info]"), item =>
      [item, parseTemplate(item.dataset.groupInfo, new Set())]
    );
    const rings = Array.from(panel.querySelectorAll(".group-info .info-progress-ring[data-progress-value][data-progress-max]"), ring => ({
      ring,
      value: parseTemplate(ring.dataset.progressValue, new Set()),
      max: parseTemplate(ring.dataset.progressMax, new Set()),
    }));
    const updates = Array.from(panel.querySelectorAll("[data-command]"), command =>
      bindCommand(command, fields, templateValues, refreshGroup)
    );

    function refreshGroup() {
      for (const update of updates) update();
      const valueFor = name => (fields.get(name)?.value ?? templateValues.get(name) ?? "").trim();
      for (const [item, parts] of info) item.textContent = expandedText(parts, valueFor);
      for (const { ring, value, max } of rings) {
        const current = Number(expandedText(value, valueFor));
        const target = Number(expandedText(max, valueFor));
        const fraction = Number.isFinite(current) && Number.isFinite(target) && target > 0
          ? Math.min(1, Math.max(0, current / target))
          : 0;
        ring.style.setProperty("--info-progress", `${fraction * 100}%`);
        const yellowMin = Number(ring.dataset.progressYellowMin);
        const yellowMax = Number(ring.dataset.progressYellowMax);
        if (Number.isFinite(current) && Number.isFinite(yellowMin) && Number.isFinite(yellowMax) && yellowMin <= yellowMax) {
          const color = current < yellowMin ? "red" : current <= yellowMax ? "yellow" : "green";
          ring.style.setProperty("--info-progress-color", `var(--${color})`);
        }
      }
    }

    refreshGroup();
    shared?.addEventListener("input", refreshGroup);
  }
})();
