const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = { ...options.headers };
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = "Bearer " + token;
  const response = await fetch(API_BASE_URL + path, { ...options, headers });
  const raw = await response.text();
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch { data = raw; }
  if (!response.ok) {
    const error = new Error(data?.detail || ("HTTP " + response.status));
    error.status = response.status; error.data = data; throw error;
  }
  return data;
}

const json = (method, body) => ({ method, body: JSON.stringify(body) });

export const API = {
  health: () => apiRequest("/health"),
  root: () => apiRequest("/"),
  publicConfig: () => apiRequest("/public-config"),
  conversationMessages: id => apiRequest("/conversations/" + encodeURIComponent(id) + "/messages"),
  chat: body => apiRequest("/chat", json("POST", body)),
  listAgentTasks: () => apiRequest("/agent/tasks"),
  createAgentTask: body => apiRequest("/agent/tasks", json("POST", body)),
  getAgentTask: id => apiRequest("/agent/tasks/" + encodeURIComponent(id)),
  resumeAgentTask: id => apiRequest("/agent/tasks/" + encodeURIComponent(id) + "/resume", json("POST", {})),
  initializeCompanion: body => apiRequest("/companion/initialize", json("POST", body)),
  getCompanion: () => apiRequest("/companion"),
  updateConsent: body => apiRequest("/companion/consent", json("PUT", body)),
  getContext: () => apiRequest("/companion/context"),
  addContext: body => apiRequest("/companion/context", json("POST", body)),
  deleteContext: id => apiRequest("/companion/context/" + encodeURIComponent(id), { method: "DELETE" }),
  listNeeds: () => apiRequest("/companion/needs"),
  createNeed: body => apiRequest("/companion/needs", json("POST", body)),
  updateNeed: (id, body) => apiRequest("/companion/needs/" + encodeURIComponent(id), json("PATCH", body)),
  followUp: body => apiRequest("/companion/follow-up", json("POST", body)),
  evaluateProactive: body => apiRequest("/companion/proactive/evaluate", json("POST", body)),
  listProposals: () => apiRequest("/companion/proactive/proposals"),
  updateProposal: (id, body) => apiRequest("/companion/proactive/proposals/" + encodeURIComponent(id), json("PATCH", body))
};
