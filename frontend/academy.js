"use strict";
async function loadCases() {
  const area = byId("caseArea");
  const notice = byId("academyNotice");
  area.replaceChildren();
  const version = ++caseVersion;
  notice.textContent = "Đang tải hồ sơ…";
  try {
    const data = await api("/academy/cases",{},true);
    if (version !== caseVersion || routeId() !== "academy") return;
    notice.textContent = data.cases.length ? "Chọn một hồ sơ để bắt đầu." : "Chưa có hồ sơ mô phỏng do nhóm cung cấp.";
    for (const item of data.cases) {
      area.append(action(item.title, () => openCase(item), "case-card"));
    }
  } catch (error) {
    if (version !== caseVersion) return;
    notice.textContent = error.status === 403 ? "Tài khoản chưa có quyền truy cập Academy." : "Chưa tải được danh sách hồ sơ.";
  }
}
function openCase(item) {
  let step = 0;
  let question = -1;
  let draft = "";
  const area = byId("caseArea");
  byId("academyNotice").textContent = "";
  const names = ["Tiếp nhận","Hỏi thêm","Nhận định","Đối chiếu"];
  function draw() {
    area.replaceChildren();
    const panel = element("article",null,"case-card");
    area.append(panel);
    panel.append(element("h2",item.title));
    const progress = element("p",null,"case-steps");
    names.forEach((name,index) => {
      if (index) progress.append(" · ");
      const label = element(index === step ? "b" : "span",name);
      if (step === index) label.setAttribute("aria-current","step");
      progress.append(label);
    });
    panel.append(progress,element("h3","Hồ sơ"),element("p",item.record));
    if (step === 1) {
      panel.append(element("h3","Bạn muốn hỏi thêm điều gì?"));
      item.questions.forEach((entry,index) => {
        const btn = action(entry.question, () => { question = index; draw(); panelFocus(index); }, "choice");
        btn.setAttribute("aria-pressed",String(question === index)); panel.append(btn);
      });
      if (question >= 0) panel.append(element("p",item.questions[question].answer));
    }
    if (step === 2) {
      const label = element("label","Nhận định của bạn");
      const input = element("textarea"); input.id = "caseDraft"; label.htmlFor = input.id;
      input.value = draft; input.rows = 4;
      input.oninput = () => { draft = input.value; next.disabled = !draft.trim(); };
      panel.append(label,input);
    }
    if (step === 3) panel.append(element("h3","Nhận định của bạn"),element("p",draft),element("h3","Đối chiếu với hồ sơ"),element("p",item.reference));
    if (step > 0) panel.append(action("Quay lại", () => { step--; draw(); }));
    const next = action(["Hỏi thêm","Ghi nhận định","Đối chiếu","Danh sách hồ sơ"][step],() => {
      if (step === 3) loadCases(); else {step++; draw();}
    },"primary");
    next.disabled = step === 2 && !draft.trim();
    panel.append(next);
  }
  function panelFocus(index) { area.querySelectorAll(".choice")[index]?.focus(); }
  draw();
}
byId("loadCases").onclick = loadCases;
