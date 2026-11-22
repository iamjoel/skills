(() => {
  const root = document.getElementById("__ROOT__");

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

  function expand(parts, valueFor) {
    let text = "";
    for (const part of parts) {
      if (typeof part === "string") {
        text += part;
      } else if (part.body) {
        if (valueFor(part.name)) text += expand(part.body, valueFor);
      } else {
        text += valueFor(part.name) || part.token;
      }
    }
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

  function bindCommand(command, sharedFields) {
    const label = command.querySelector("h3").textContent;
    const preview = command.querySelector("[data-preview]");
    const status = command.querySelector("[data-status]");
    const manual = command.querySelector("[data-manual]");
    const required = JSON.parse(command.dataset.requires);
    const names = new Set();
    const parts = parseTemplate(command.dataset.template, names);
    const saved = new Map();
    const rawValueFor = name => saved.get(name) ?? sharedFields.get(name)?.value ?? "";
    const valueFor = name => rawValueFor(name).trim();
    const labelFor = name => sharedFields.get(name)?.closest("label").querySelector("span").textContent || name;
    let drafts = null;

    const edit = names.size ? document.createElement("button") : null;
    if (edit) {
      edit.type = "button";
      edit.className = "btn";
      edit.dataset.action = "edit";
      command.querySelector(".command-actions").prepend(edit);
    }

    function refresh() {
      if (drafts) return;
      preview.textContent = expand(parts, valueFor);
      status.textContent = "";
      manual.hidden = true;
    }

    function updateEditButton() {
      command.toggleAttribute("data-editing", Boolean(drafts));
      edit.classList.toggle("btn-primary", Boolean(drafts));
      edit.textContent = drafts ? "保存" : "编辑变量";
      edit.setAttribute("aria-label", `${drafts ? "保存变量" : "编辑变量"} ${label}`);
    }

    function inlineField(name) {
      const draft = drafts.get(name) ?? { initial: rawValueFor(name), fields: [] };
      const original = sharedFields.get(name);
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
        if (value !== initial) saved.set(name, value);
      }
      drafts = null;
      updateEditButton();
      refresh();
      status.textContent = "已保存变量。";
      edit.focus();
    }

    if (edit) updateEditButton();
    refresh();
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
        else sharedFields.get(missing)?.focus();
        status.textContent = `请填写「${labelFor(missing)}」。`;
        return;
      }

      manual.hidden = true;
      const prompt = expand(parts, valueFor);
      if (button.dataset.action === "run") {
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
    const shared = panel.querySelector(".variables");
    const fields = new Map(Array.from(shared?.querySelectorAll("[data-variable]") ?? [], field => [field.dataset.variable, field]));
    const updates = Array.from(panel.querySelectorAll("[data-command]"), command => bindCommand(command, fields));
    shared?.addEventListener("input", () => updates.forEach(update => update()));
  }
})();
