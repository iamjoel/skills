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
        directory.setCustomValidity("请输入命令文件地址。");
        directory.reportValidity();
        return;
      }
      settings.querySelector("[data-manual]").hidden = true;
      const prompt = "用 $chat-actions 保存命令文件地址并显示 #ls。\n#setting save\n" +
        JSON.stringify({ directory: value });
      send(settings, save, "保存命令文件地址", prompt, "请在聊天中确认保存。");
    }

    save.addEventListener("click", saveDirectory);
    directory.addEventListener("input", () => directory.setCustomValidity(""));
    directory.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.isComposing) save.click();
    });
  }

  function expand(template, values) {
    return template
      .replace(/\{\?([\w.-]+):((?:[^{}]|\{[\w.-]+\})*)\}/g, (_, name, body) => values.get(name) ? body : "")
      .replace(/\{([\w.-]+)\}/g, (token, name) => values.get(name) || token);
  }

  for (const panel of root.querySelectorAll('[role="tabpanel"]')) {
    const fields = new Map(Array.from(panel.querySelectorAll("[data-variable]"), field => [field.dataset.variable, field]));
    const commands = panel.querySelectorAll("[data-command]");
    const values = () => new Map(Array.from(fields, ([name, field]) => [name, field.value.trim()]));

    function refresh() {
      const current = values();
      for (const command of commands) {
        command.querySelector("[data-preview]").textContent = expand(command.dataset.template, current);
        command.querySelector("[data-status]").textContent = "";
        command.querySelector("[data-manual]").hidden = true;
      }
    }

    panel.addEventListener("input", refresh);
    refresh();

    panel.addEventListener("click", async event => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const command = button.closest("[data-command]");
      const status = command.querySelector("[data-status]");
      const current = values();
      const missing = JSON.parse(command.dataset.requires).find(name => !current.get(name));
      if (missing !== undefined) {
        const field = fields.get(missing);
        const label = field?.closest("label").querySelector("span").textContent || missing;
        status.textContent = `请填写「${label}」。`;
        field?.focus();
        return;
      }

      command.querySelector("[data-manual]").hidden = true;
      const prompt = expand(command.dataset.template, current);
      if (button.dataset.action === "run") {
        const title = `运行「${command.querySelector("h3").textContent}」`.slice(0, 250);
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
  }
})();
