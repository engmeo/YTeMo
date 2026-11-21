"use strict";
const byId = (id) => document.getElementById(id);
const cfg = window.YTEMO_CONFIG;
const topics = [
  ["Chi phí khám chữa bệnh", "chi-phi", "Tôi đang lo chi phí khám chữa bệnh quá cao."],
  ["Chăm sóc người thân", "cham-soc-nguoi-than", "Tôi đang chăm sóc người thân tại nhà và không biết bắt đầu từ đâu."],
  ["Phòng bệnh", "phong-benh", "Tôi muốn phòng bệnh nhưng không biết cần theo dõi điều gì."],
  ["Ý tưởng công nghệ", "y-tuong-cong-nghe", "Tôi có một ý tưởng thiết bị y tế giá rẻ."]
];
const pages = [...document.querySelectorAll("main > .page")];
let client, clientTask, user, register = false, authBusy = false, nextPage = "assistant";
let thread = null, chatVersion = 0, chatBusy = false, queuedText = "", caseVersion = 0;
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function action(label, fn, className) {
  const button = element("button", label, className);
  button.type = "button";
  button.addEventListener("click", fn);
  return button;
}
function go(page) { location.hash = page; }
function routeId() { return new URLSearchParams(location.search).get("auth") === "recovery" ? "reset" : location.hash.slice(1) || "home"; }
function professional() { return user?.app_metadata?.ytemo_role === "professional"; }
function historyKey() { return "ytm_conversation_" + user.id; }
function setUser(next) {
  if (user?.id !== next?.id) {
    chatVersion++; caseVersion++;
    thread = null; chatBusy = false;
    byId("message").value = ""; byId("messages").replaceChildren(); byId("caseArea").replaceChildren();
    byId("chatNotice").textContent = ""; byId("profileNotice").textContent = "";
    updateChatControls();
  }
  user = next;
  byId("account").querySelector("span").textContent = user ? "Tài khoản" : "Đăng nhập";
  byId("accountEmail").textContent = user?.email || "";
  byId("academyLink").hidden = !professional();
}
async function api(path, options = {}, authenticated = false) {
  const headers = new Headers(options.headers);
  if (authenticated) {
    const { data, error } = await client.auth.getSession();
    if (error || !data.session || data.session.user.id !== user?.id) throw new Error("Phiên đã hết hạn. Hãy đăng nhập lại.");
    headers.set("Authorization", "Bearer " + data.session.access_token);
  }
  const response = await fetch(cfg.apiBase.replace(/\/$/, "") + path, { ...options, headers });
  if (!response.ok) {
    const err = new Error(response.status === 403 ? "Tài khoản chưa có quyền chuyên nghiệp." :
      response.status === 401 ? "Phiên đã hết hạn. Hãy đăng nhập lại." : "Chưa thể kết nối. Hãy thử lại.");
    err.status = response.status;
    throw err;
  }
  return response.json();
}
function connect() {
  if (clientTask) return clientTask;
  clientTask = (async () => {
    const settings = await api("/public-config");
    const {createClient} = await import("https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm");
    const auth = createClient(settings.supabase_url, settings.supabase_publishable_key);
    client = auth;
    auth.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY") {
        setUser(session?.user || null);
        // Defer routing until Supabase finishes consuming the callback URL.
        setTimeout(() => { history.replaceState(null, "", location.pathname + "?auth=recovery#reset"); render(); }, 0);
        return;
      }
      if (authBusy) return;
      const previous = user?.id;
      setUser(session?.user || null);
      if (previous !== user?.id || (event === "TOKEN_REFRESHED" && routeId() === "academy" && !professional())) setTimeout(render, 0);
    });
    const { data, error } = await auth.auth.getSession();
    if (error) throw error;
    setUser(data.session?.user || null);
    return auth;
  })().catch(error => { clientTask = null; throw error; });
  return clientTask;
}
let routeVersion = 0;
async function render() {
  const version = ++routeVersion;
  let page = routeId();
  if (!pages.some(node => node.id === page)) page = "home";
  const privatePage = ["assistant","academy","profile"].includes(page);
  if (privatePage && !user) {
    nextPage = page;
    try { await connect(); } catch { /* The login form offers retry on submit. */ }
    if (version !== routeVersion) return;
    if (!user) { location.replace("#login"); return; }
  }
  if (page === "academy" && !professional()) { location.replace("#profile"); return; }
  if (page === "login" && user) { location.replace("#profile"); return; }
  for (const section of pages) section.hidden = section.id !== page;
  document.querySelectorAll(".navlinks a").forEach(link => {
    if (link.hash === "#" + page) link.setAttribute("aria-current","page"); else link.removeAttribute("aria-current");
  });
  byId("mainNav").classList.remove("open"); byId("menu").setAttribute("aria-expanded","false");
  byId("content").focus({preventScroll:true}); window.scrollTo(0,0);
  if (page === "login") updateAuth();
  if (page === "reset") prepareReset();
  if (page === "assistant") {
    if (queuedText) { byId("message").value = queuedText; queuedText = ""; }
    if (thread === null && !chatBusy && !byId("messages").childElementCount) restoreChat();
  }
  if (page === "academy") loadCases();
}
function updateAuth() {
  byId("login").classList.toggle("is-register", register);
  byId("toggleRegister").textContent = register ? "Đã có tài khoản? Đăng nhập" : "Chưa có tài khoản? Tạo tài khoản";
  byId("submitAuth").textContent = register ? "Tạo tài khoản" : "Đăng nhập";
  byId("authTitle").textContent = register ? "Bắt đầu cùng Y Tế Mở" : "Chào mừng bạn trở lại";
  byId("authIntro").textContent = register ? "Tạo tài khoản để bắt đầu cuộc trò chuyện đầu tiên." : "Đăng nhập để tiếp tục cuộc trò chuyện của bạn.";
  byId("authStep").textContent = register ? "MỘT KHỞI ĐẦU MỚI" : "TÀI KHOẢN CỦA BẠN";
  byId("password").autocomplete = register ? "new-password" : "current-password";
  byId("email").autocomplete = register ? "email" : "username";
  byId("passwordHint").hidden = byId("signupNote").hidden = !register;
  byId("forgotLink").hidden = register;
}
byId("showPassword").onclick = () => {
  const visible = byId("password").type === "password";
  byId("password").type = visible ? "text" : "password";
  byId("showPassword").textContent = visible ? "Ẩn" : "Hiện";
  byId("showPassword").setAttribute("aria-pressed", String(visible));
};
byId("toggleRegister").onclick = () => {
  if (authBusy) return;
  register = !register;
  byId("authNotice").textContent = "";
  byId("emailConfirmation").hidden = true;
  byId("password").value = "";
  byId("password").type = "password";
  byId("showPassword").textContent = "Hiện";
  byId("showPassword").setAttribute("aria-pressed", "false");
  updateAuth(); byId("authTitle").focus();
};
byId("authForm").onsubmit = async e => {
  e.preventDefault();
  if (authBusy) return;
  const signup = register;
  byId("emailConfirmation").hidden = true;
  const form = byId("authForm");
  const credentials = { email:byId("email").value.trim(), password:byId("password").value };
  authBusy = true;
  Array.from(form.elements).forEach(control => control.disabled = true);
  byId("authNotice").textContent = "Đang xử lý…";
  try {
    const auth = (await connect()).auth;
    const {data, error} = signup ? await auth.signUp(credentials) : await auth.signInWithPassword(credentials);
    if (error) {
      byId("authNotice").textContent = signup ? "Chưa đăng ký được. Kiểm tra email, mật khẩu và thử lại." : "Chưa đăng nhập được. Kiểm tra email và mật khẩu.";
      return;
    }
    byId("password").value = "";
    if (!data.session) {
      register = false; updateAuth();
      byId("emailConfirmation").hidden = false;
      byId("authNotice").textContent = "Yêu cầu đã được xử lý. Xem hướng dẫn xác nhận email bên dưới."; return;
    }
    setUser(data.user); register = false; byId("authNotice").textContent = "";
    go(nextPage === "academy" && !professional() ? "profile" : nextPage);
  } catch { byId("authNotice").textContent = "Chưa kết nối được dịch vụ đăng nhập. Bạn có thể thử lại."; }
  finally { authBusy = false; Array.from(form.elements).forEach(control => control.disabled = false); updateAuth(); }
};
let recoveryBusy = false, resetBusy = false;
byId("forgotLink").onclick = () => { byId("recoveryEmail").value = byId("email").value; };
byId("forgotForm").onsubmit = async event => {
  event.preventDefault(); if (recoveryBusy) return;
  recoveryBusy = true; byId("sendRecovery").disabled = true;
  byId("recoveryNotice").textContent = "Đang gửi yêu cầu…";
  try {
    const auth = (await connect()).auth;
    const target = new URL(location.pathname, location.origin);
    target.searchParams.set("auth", "recovery");
    const {error} = await auth.resetPasswordForEmail(byId("recoveryEmail").value.trim(), {redirectTo:target.href});
    if (error) throw error;
    byId("recoveryNotice").textContent = "Nếu email này có tài khoản, bạn sẽ nhận được liên kết đặt lại mật khẩu. Hãy kiểm tra cả thư mục thư rác.";
  } catch { byId("recoveryNotice").textContent = "Chưa gửi được yêu cầu. Hãy thử lại sau ít phút."; }
  finally { recoveryBusy = false; byId("sendRecovery").disabled = false; }
};
async function prepareReset() {
  if (resetBusy || byId("resetForm").hidden) return;
  byId("resetFields").disabled = true;
  try {
    const auth = (await connect()).auth;
    const {data,error} = await auth.getSession();
    if (routeId() !== "reset") return;
    if (error || !data.session) throw new Error("No session");
    byId("resetIntro").textContent = "Chọn mật khẩu riêng cho tài khoản của bạn.";
    byId("resetFields").disabled = false;
  } catch {
    if (routeId() === "reset") byId("resetIntro").textContent = "Liên kết chưa xác thực được hoặc đã hết hạn. Kiểm tra kết nối và yêu cầu liên kết mới nếu cần.";
  }
}
byId("confirmPassword").oninput = () => byId("confirmPassword").setCustomValidity("");
byId("newPassword").oninput = () => byId("confirmPassword").setCustomValidity("");
byId("showNewPassword").onclick = () => {
  const visible = byId("newPassword").type === "password";
  for (const id of ["newPassword", "confirmPassword"]) byId(id).type = visible ? "text" : "password";
  byId("showNewPassword").textContent = visible ? "Ẩn mật khẩu" : "Hiện mật khẩu";
  byId("showNewPassword").setAttribute("aria-pressed", String(visible));
};
byId("resetForm").onsubmit = async event => {
  event.preventDefault(); if (resetBusy) return;
  if (byId("newPassword").value !== byId("confirmPassword").value) {
    byId("confirmPassword").setCustomValidity("Hai mật khẩu chưa khớp.");
    byId("confirmPassword").reportValidity(); return;
  }
  resetBusy = true; byId("resetFields").disabled = true;
  byId("resetNotice").textContent = "Đang lưu mật khẩu…";
  try {
    const {error} = await (await connect()).auth.updateUser({password:byId("newPassword").value});
    if (error) throw error;
    byId("newPassword").value = byId("confirmPassword").value = "";
    byId("resetForm").hidden = true; byId("retryRecovery").hidden = true;
    byId("resetDone").hidden = false;
    byId("resetIntro").textContent = "Đã đổi mật khẩu. Từ lần đăng nhập tiếp theo, hãy dùng mật khẩu mới.";
    history.replaceState(null, "", location.pathname + "#reset");
  } catch { byId("resetNotice").textContent = "Chưa đổi được mật khẩu. Hãy chọn mật khẩu mạnh hơn hoặc yêu cầu liên kết mới nếu liên kết đã hết hạn."; }
  finally { resetBusy = false; byId("resetFields").disabled = false; }
};
byId("account").onclick = () => { nextPage = "assistant"; go(user ? "profile" : "login"); };
byId("menu").onclick = () => {
  const open = byId("mainNav").classList.toggle("open");
  byId("menu").setAttribute("aria-expanded",String(open));
};
byId("logout").onclick = async () => {
  try {
    const {error} = await client.auth.signOut({scope:"local"});
    if (error) throw error;
    setUser(null); queuedText = ""; nextPage = "assistant"; go("home");
  } catch { byId("profileNotice").textContent = "Chưa đăng xuất được. Hãy thử lại."; }
};
for (const [label, icon, prompt] of topics) {
  for (const id of ["topics","quick"]) {
    const btn = action(label, () => {
      if (id === "topics") { queuedText = prompt; go("assistant"); }
      else { byId("message").value = prompt; byId("message").focus(); }
    }, "topic");
    const img = element("img"); img.src = "assets/icons/" + icon + ".svg"; img.alt = ""; btn.prepend(img);
    byId(id).append(btn);
  }
}
function addMessage(text, role) {
  const list = byId("messages");
  list.append(element("p",text,"msg " + role));
  list.scrollTop = list.scrollHeight;
}
function updateChatControls() {
  byId("send").disabled = byId("newChat").disabled = chatBusy;
  byId("message").readOnly = chatBusy;
  byId("quick").querySelectorAll("button").forEach(btn => btn.disabled = chatBusy);
}
async function restoreChat() {
  thread = localStorage.getItem(historyKey());
  if (!thread) return;
  const version = ++chatVersion;
  chatBusy = true; updateChatControls();
  try {
    const data = await api("/conversations/" + encodeURIComponent(thread) + "/messages",{},true);
    if (version !== chatVersion) return;
    for (const msg of data.messages) addMessage(msg.content,msg.sender_type === "user" ? "user" : "assistant");
  } catch (err) {
    if (version !== chatVersion) return;
    if (err.status === 404) { thread = null; localStorage.removeItem(historyKey()); }
    else byId("chatNotice").textContent = "Chưa tải được lịch sử. Hãy tải lại trang hoặc bắt đầu cuộc mới.";
  } finally { if (version === chatVersion) { chatBusy = false; updateChatControls(); } }
}
byId("chatForm").onsubmit = async e => {
  e.preventDefault();
  const draft = byId("message");
  const text = draft.value.trim();
  if (!text || !user || chatBusy) return;
  const version = ++chatVersion;
  chatBusy = true; updateChatControls(); byId("chatNotice").textContent = "Đang xử lý tin nhắn…";
  try {
    const result = await api("/chat", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,conversation_id:thread})},true);
    if (version !== chatVersion) return;
    if (!result.reply || !result.conversation_id) throw new Error();
    thread = result.conversation_id; localStorage.setItem(historyKey(),thread);
    addMessage(text,"user"); addMessage(result.reply,"assistant"); draft.value = ""; byId("chatNotice").textContent = "";
  } catch {
    if (version === chatVersion) byId("chatNotice").textContent = "Chưa nhận được trả lời. Câu hỏi vẫn ở ô nhập. Kiểm tra lịch sử trước khi gửi lại.";
  } finally { if (version === chatVersion) { chatBusy = false; updateChatControls(); if (routeId()==="assistant") draft.focus(); } }
};
byId("newChat").onclick = () => {
  if (!user || chatBusy) return;
  chatVersion++; thread = null; localStorage.removeItem(historyKey());
  byId("messages").replaceChildren(); byId("message").value = ""; byId("chatNotice").textContent = ""; byId("message").focus();
};
function displayPhoto(url, host) {
  if (!url || !host) return;
  const img = new Image();
  img.alt = "";
  img.onload = () => { host.replaceChildren(img); host.hidden = false; };
  img.src = url;
}
displayPhoto(cfg.homePhoto,byId("coverPhoto")); displayPhoto(cfg.communityPhoto,byId("teamPhoto"));
// Only public editorial content animates; forms and chat stay stable.
const motionQuery = matchMedia("(prefers-reduced-motion: reduce)");
const motionItems = [...document.querySelectorAll("#home .hero-copy > *, #home .art, #home .topic-block h2, #topics .topic, #system .page-hero > *, #system .agent-card, #research .page-hero > *, #research .research-card, #projects .page-hero > *, #projects .project-row, #community .page-hero > *, #community .role")];
let motionObserver;
function setupMotion() {
  motionObserver?.disconnect();
  motionItems.forEach(node => { node.classList.remove("motion-item", "in-view"); });
  if (motionQuery.matches || !("IntersectionObserver" in window)) return;
  motionObserver = new IntersectionObserver(entries => {
    for (const entry of entries) entry.target.classList.toggle("in-view", entry.isIntersecting);
  }, {threshold:0, rootMargin:"0px 0px -12px 0px"});
  motionItems.forEach((node, index) => {
    node.classList.add("motion-item");
    node.style.setProperty("--reveal-delay", (index % 4) * 45 + "ms");
    motionObserver.observe(node);
  });
}
setupMotion(); motionQuery.addEventListener("change", setupMotion);
let scrollScheduled = false;
window.addEventListener("scroll", () => {
  if (scrollScheduled) return;
  scrollScheduled = true;
  requestAnimationFrame(() => {
    document.querySelector(".mast").classList.toggle("is-scrolled", scrollY > 24);
    scrollScheduled = false;
  });
}, {passive:true});
window.addEventListener("hashchange", () => {
  // Explicit navigation ends the recovery route; tokens are consumed by connect first.
  if (new URLSearchParams(location.search).get("auth") === "recovery" && !location.hash.includes("access_token") && location.hash !== "#reset") history.replaceState(null, "", location.pathname + location.hash);
  render();
});
render();
connect().catch(() => {});
