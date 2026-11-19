(() => {
  "use strict";

  function render(container, initialSnapshot, { onConfigure, saveDays }) {
    let snapshot = initialSnapshot;
    const now = new Date();
    let month = new Date(now.getFullYear(), now.getMonth(), 1);
    const section = document.createElement("section");
    section.className = "sc-month";
    const nav = document.createElement("nav");
    nav.className = "month-navigation";
    nav.setAttribute("aria-label", "月历导航");
    const view = document.createElement("div");
    const notice = document.createElement("p");
    notice.setAttribute("role", "status");
    section.append(nav, view, notice);
    container.replaceChildren(section);

    function addButton(text, action, label) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = text;
      if (label) button.setAttribute("aria-label", label);
      button.addEventListener("click", action);
      nav.append(button);
    }

    function move(offset) {
      month.setMonth(month.getMonth() + offset);
      notice.textContent = "";
      draw();
    }

    function draw() {
      const key = month.getFullYear() + "-" + String(month.getMonth() + 1).padStart(2, "0");
      window.renderStatusMonth(view, { ...snapshot, month: key }, async (date, entries) => {
        const controls = Array.from(nav.querySelectorAll("button"));
        for (const control of controls) control.disabled = true;
        try {
          snapshot = await saveDays(date, entries);
          draw();
          view.querySelector('[data-date="' + date + '"]')?.focus();
          notice.textContent = entries.length ? "已保存当天记录。" : "已清空当天记录。";
        } finally {
          for (const control of controls) control.disabled = false;
        }
      });
    }

    addButton("‹", () => move(-1), "上个月");
    addButton("本月", () => {
      const today = new Date();
      month = new Date(today.getFullYear(), today.getMonth(), 1);
      move(0);
    });
    addButton("›", () => move(1), "下个月");
    addButton("配置状态", onConfigure);
    draw();
  }

  window.StatusMonth = { render };
})();
