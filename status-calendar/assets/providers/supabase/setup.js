function renderStorageSetup(root, { mode, resume, month, provider }) {
  const dedicated = mode === "storage";

  function element(tag, classes, text) {
    const node = document.createElement(tag);
    if (classes) node.className = classes;
    if (text) node.textContent = text;
    return node;
  }

  const section = element("section", "sc-storage");
  section.setAttribute("aria-label", "云同步");
  if (dedicated) {
    section.append(
      element("h2", "", "云同步"),
      element("p", "", "连接后会打开你的云日历。如果这是第一次同步，当前设备的状态和记录会存入你选择的 Supabase 项目。")
    );
  }
  const title = "自动配置 Supabase";
  const button = element("button", dedicated ? "btn btn-primary" : "btn btn-ghost",
    dedicated ? title : "已存本机 · 开启云同步");
  button.type = "button";
  const actions = element("div", "viz-controls");
  actions.append(button);
  const message = element("p", "text-small");
  message.setAttribute("role", "status");
  const error = element("p", "text-small text-destructive");
  error.setAttribute("role", "alert");
  section.append(actions, error, message);
  root.replaceChildren(section);

  button.addEventListener("click", async event => {
    if (!event.isTrusted || button.disabled) return;
    message.textContent = "";
    error.textContent = "";
    if (provider !== "supabase" || !["month", "configure"].includes(resume) ||
        !/^\d{4}-(0[1-9]|1[0-2])$/.test(month)) {
      error.textContent = "请重新打开日历，再开启云同步。";
      return;
    }
    button.disabled = true;
    try {
      const request = { action: "auto_connect", provider, resume, month };
      const prompt = "用 $status-calendar 自动配置 Supabase 云同步。\n" + JSON.stringify(request);
      await window.openai.sendFollowUpMessage({ title, prompt });
      message.textContent = "请在聊天中确认自动配置请求。";
    } catch {
      error.textContent = "当前聊天未能发起请求。可重试，或在聊天中输入「自动配置 Supabase」。";
    } finally {
      button.disabled = false;
    }
  });
}
