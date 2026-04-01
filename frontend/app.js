const $ = (id) => document.getElementById(id);

const API = `${location.origin}/api`;

const authPanel = $("auth");
const dashboard = $("dashboard");
const usernameInput = $("username");
const passwordInput = $("password");
const roleInput = $("role");
const authMsg = $("authMsg");
const signupBtn = $("signupBtn");
const loginBtn = $("loginBtn");
const logoutBtn = $("logoutBtn");
const refreshBtn = $("refreshBtn");

const welcomeTitle = $("welcomeTitle");
const welcomeCopy = $("welcomeCopy");
const roleGuide = $("roleGuide");
const createPanel = $("createPanel");
const bundleMsg = $("bundleMsg");
const bundleList = $("bundleList");
const marketStatus = $("marketStatus");

const bundleTitle = $("bundleTitle");
const serviceType = $("serviceType");
const neighborhood = $("neighborhood");
const homesCount = $("homesCount");
const targetDate = $("targetDate");
const budgetNotes = $("budgetNotes");
const bundleDescription = $("bundleDescription");
const createBundleBtn = $("createBundleBtn");

const bidsPanel = $("bidsPanel");
const bidsTitle = $("bidsTitle");
const bidsSubtitle = $("bidsSubtitle");
const bidsList = $("bidsList");
const closeBidsBtn = $("closeBidsBtn");

const openCount = $("openCount");
const bidCount = $("bidCount");
const awardCount = $("awardCount");

// Chat elements
const chatToggleBtn = $("chatToggleBtn");
const chatPanel = $("chatPanel");
const chatMessages = $("chatMessages");
const chatInput = $("chatInput");
const chatSendBtn = $("chatSendBtn");
const closeChatBtn = $("closeChatBtn");

let token = localStorage.getItem("token") || "";
let currentUser = null;
let bundles = [];
let ws = null;

function showAuth() {
  authPanel.classList.remove("hidden");
  dashboard.classList.add("hidden");
  chatToggleBtn && chatToggleBtn.classList.add("hidden");
}

function showDashboard() {
  authPanel.classList.add("hidden");
  dashboard.classList.remove("hidden");
  chatToggleBtn && chatToggleBtn.classList.remove("hidden");
}

async function callAPI(path, method = "GET", body) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch (err) {}
    throw new Error(detail);
  }
  return res.json();
}

function getRoleCopy(role) {
  if (role === "vendor") {
    return [
      "Browse open service bundles from neighborhoods and HOAs.",
      "Submit one competitive bid with price, timeline, and proposal details.",
      "Track awarded jobs and use the bid board to focus on the best-fit bundles.",
    ];
  }
  if (role === "manager") {
    return [
      "Create bulk requests on behalf of a neighborhood or HOA.",
      "Compare live vendor pricing and award the best offer.",
      "Use bundled demand to negotiate lower per-home pricing.",
    ];
  }
  return [
    "Post bundled home-service demand across multiple homes.",
    "Invite vendors to compete on one neighborhood-wide opportunity.",
    "Award the best offer once enough bids are in.",
  ];
}

function renderRoleGuide() {
  roleGuide.innerHTML = "";
  for (const step of getRoleCopy(currentUser.role)) {
    const item = document.createElement("div");
    item.className = "step";
    item.textContent = step;
    roleGuide.appendChild(item);
  }
}

function renderHeader() {
  welcomeTitle.textContent = `${currentUser.username} • ${currentUser.role}`;
  if (currentUser.role === "vendor") {
    welcomeCopy.textContent = "Compete on neighborhood bundles and win recurring bulk business.";
    createPanel.classList.add("hidden");
  } else {
    welcomeCopy.textContent = "Bundle neighborhood demand and let vendors compete for the best price.";
    createPanel.classList.remove("hidden");
  }
  renderRoleGuide();
}

function updateSummaryCards() {
  const openBundles = bundles.filter((bundle) => bundle.status === "open").length;
  const totalBids = bundles.reduce((sum, bundle) => sum + (bundle.bid_count || 0), 0);
  const awardedBundles = bundles.filter((bundle) => bundle.status === "awarded").length;
  openCount.textContent = openBundles;
  bidCount.textContent = totalBids;
  awardCount.textContent = awardedBundles;
}

function bundleActions(bundle) {
  const actions = [];
  actions.push(`<button class="secondary" data-action="view-bids" data-id="${bundle.id}">View Bids</button>`);
  if (currentUser.role === "vendor" && bundle.status === "open") {
    actions.push(`<button data-action="bid" data-id="${bundle.id}">Place Bid</button>`);
  }
  return actions.join("");
}

function winningBidMarkup(bundle) {
  if (!bundle.winning_bid) return "";
  return `
    <div class="winning-banner">
      Winner: <strong>${bundle.winning_bid.vendor}</strong> at $${bundle.winning_bid.amount.toFixed(2)}
      for ${bundle.winning_bid.timeline_days} days
    </div>
  `;
}

function renderBundles() {
  updateSummaryCards();
  if (!bundles.length) {
    bundleList.innerHTML = `<div class="empty-state">No bundles yet. Post the first neighborhood service request.</div>`;
    marketStatus.textContent = "";
    return;
  }

  marketStatus.textContent = `${bundles.length} bundles loaded`;
  bundleList.innerHTML = bundles
    .map(
      (bundle) => `
        <article class="bundle-card">
          <div class="bundle-head">
            <div>
              <span class="pill ${bundle.status}">${bundle.status}</span>
              <h4>${bundle.title}</h4>
              <p class="soft">${bundle.service_type} • ${bundle.neighborhood}</p>
            </div>
            <div class="price-box">
              <span>Lowest bid</span>
              <strong>${bundle.lowest_bid != null ? `$${bundle.lowest_bid.toFixed(2)}` : "No bids yet"}</strong>
            </div>
          </div>
          <p>${bundle.description}</p>
          <div class="bundle-meta">
            <span>${bundle.homes_count} homes</span>
            <span>Target: ${bundle.target_date}</span>
            <span>Posted by ${bundle.created_by}</span>
            <span>${bundle.bid_count} bids</span>
          </div>
          ${bundle.budget_notes ? `<div class="note">Budget notes: ${bundle.budget_notes}</div>` : ""}
          ${winningBidMarkup(bundle)}
          <div class="bundle-actions">
            ${bundleActions(bundle)}
          </div>
        </article>
      `
    )
    .join("");
}

async function loadBundles() {
  const data = await callAPI("/bundles");
  bundles = data.bundles;
  renderBundles();
}

async function loadMe() {
  currentUser = await callAPI("/me");
  renderHeader();
}

function closeBidsPanel() {
  bidsPanel.classList.add("hidden");
  bidsList.innerHTML = "";
}

async function showBids(bundleId) {
  const bundle = bundles.find((item) => item.id === bundleId);
  const data = await callAPI(`/bundles/${bundleId}/bids`);

  bidsPanel.classList.remove("hidden");
  bidsTitle.textContent = `Bids for ${data.bundle_title}`;
  bidsSubtitle.textContent = `${data.bids.length} vendor offers`;

  if (!data.bids.length) {
    bidsList.innerHTML = `<div class="empty-state">No bids submitted yet.</div>`;
    return;
  }

  bidsList.innerHTML = data.bids
    .map((bid) => {
      const awardButton =
        data.can_award && bundle.status === "open"
          ? `<button data-action="award" data-bundle-id="${bundleId}" data-bid-id="${bid.id}">Award Bid</button>`
          : "";
      return `
        <div class="bid-card">
          <div class="bid-top">
            <div>
              <h4>${bid.vendor}</h4>
              <p class="soft">${bid.timeline_days} days • ${bid.status}</p>
            </div>
            <strong>$${bid.amount.toFixed(2)}</strong>
          </div>
          <p>${bid.proposal}</p>
          <div class="bundle-actions">
            ${awardButton}
          </div>
        </div>
      `;
    })
    .join("");
}

function promptForBid(bundle) {
  const amount = window.prompt(`Bid amount for "${bundle.title}"`, "");
  if (!amount) return null;
  const timeline = window.prompt("Timeline in days", "7");
  if (!timeline) return null;
  const proposal = window.prompt("Short proposal", "");
  if (!proposal) return null;
  return {
    amount: Number(amount),
    timeline_days: Number(timeline),
    proposal,
  };
}

async function submitBid(bundleId) {
  const bundle = bundles.find((item) => item.id === bundleId);
  const bid = promptForBid(bundle);
  if (!bid) return;
  if (!Number.isFinite(bid.amount) || !Number.isFinite(bid.timeline_days)) {
    window.alert("Please enter valid numeric values for price and timeline.");
    return;
  }
  await callAPI(`/bundles/${bundleId}/bids`, "POST", bid);
  await loadBundles();
  await showBids(bundleId);
}

async function awardBid(bundleId, bidId) {
  await callAPI(`/bundles/${bundleId}/award/${bidId}`, "POST");
  await loadBundles();
  await showBids(bundleId);
}

function connectWS() {
  if (ws) ws.close();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);
      if (["bundle_created", "bid_created", "bundle_awarded"].includes(data.type)) {
        await loadBundles();
      }
      // Show chat messages broadcast from other users
      if (data.type === "chat_message") {
        appendChatMessage(data.payload.username, data.payload.message, false);
      }
      if (data.type === "bot_reply") {
        appendChatMessage("🤖 Assistant", data.payload.reply, false, true);
      }
    } catch (err) {}
  };
}

// ── Chat ────────────────────────────────────────────────────────────────────

function appendChatMessage(sender, text, isMine = false, isBot = false) {
  const wrap = document.createElement("div");
  wrap.className = `chat-msg ${isMine ? "mine" : ""} ${isBot ? "bot" : ""}`;
  wrap.innerHTML = `
    <span class="chat-sender">${sender}</span>
    <span class="chat-bubble">${text}</span>
  `;
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
  const el = chatMessages.querySelector(".typing-indicator");
  if (el) el.remove();
}

function showTypingIndicator() {
  removeTypingIndicator();
  const wrap = document.createElement("div");
  wrap.className = "chat-msg bot typing-indicator";
  wrap.innerHTML = `<span class="chat-sender">🤖 Assistant</span><span class="chat-bubble">Thinking<span class="dots"><span>.</span><span>.</span><span>.</span></span></span>`;
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChatMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";

  appendChatMessage(currentUser.username, text, true);

  try {
    const data = await callAPI("/chat", "POST", { message: text });
    if (data.reply) {
      removeTypingIndicator();
      appendChatMessage("🤖 Assistant", data.reply, false, true);
    }
  } catch (err) {
    removeTypingIndicator();
    appendChatMessage("⚠️ Error", err.message, false, true);
  }
}

if (chatToggleBtn) {
  chatToggleBtn.onclick = () => {
    chatPanel.classList.toggle("hidden");
    if (!chatPanel.classList.contains("hidden")) {
      chatInput.focus();
    }
  };
}

if (closeChatBtn) {
  closeChatBtn.onclick = () => chatPanel.classList.add("hidden");
}

if (chatSendBtn) {
  chatSendBtn.onclick = sendChatMessage;
}

if (chatInput) {
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  // Show typing indicator when user is typing a question
  chatInput.addEventListener("input", () => {
    if (chatInput.value.trim().endsWith("?")) {
      showTypingIndicator();
    } else {
      removeTypingIndicator();
    }
  });
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

async function bootstrapApp() {
  if (!token) {
    showAuth();
    return;
  }

  try {
    await loadMe();
    await loadBundles();
    connectWS();
    showDashboard();
  } catch (err) {
    token = "";
    localStorage.removeItem("token");
    showAuth();
  }
}

signupBtn.onclick = async () => {
  try {
    const data = await callAPI("/signup", "POST", {
      username: usernameInput.value.trim(),
      password: passwordInput.value,
      role: roleInput.value,
    });
    token = data.token;
    localStorage.setItem("token", token);
    authMsg.textContent = "";
    await bootstrapApp();
  } catch (err) {
    authMsg.textContent = err.message;
  }
};

loginBtn.onclick = async () => {
  try {
    const data = await callAPI("/login", "POST", {
      username: usernameInput.value.trim(),
      password: passwordInput.value,
    });
    token = data.token;
    localStorage.setItem("token", token);
    authMsg.textContent = "";
    await bootstrapApp();
  } catch (err) {
    authMsg.textContent = err.message;
  }
};

logoutBtn.onclick = () => {
  token = "";
  currentUser = null;
  localStorage.removeItem("token");
  if (ws) ws.close();
  closeBidsPanel();
  chatPanel && chatPanel.classList.add("hidden");
  showAuth();
};

refreshBtn.onclick = async () => {
  await loadBundles();
};

createBundleBtn.onclick = async () => {
  try {
    await callAPI("/bundles", "POST", {
      title: bundleTitle.value.trim(),
      service_type: serviceType.value.trim(),
      neighborhood: neighborhood.value.trim(),
      homes_count: Number(homesCount.value),
      target_date: targetDate.value.trim(),
      description: bundleDescription.value.trim(),
      budget_notes: budgetNotes.value.trim(),
    });
    bundleMsg.textContent = "Bundle posted successfully.";
    bundleTitle.value = "";
    serviceType.value = "";
    neighborhood.value = "";
    homesCount.value = "";
    targetDate.value = "";
    bundleDescription.value = "";
    budgetNotes.value = "";
    await loadBundles();
  } catch (err) {
    bundleMsg.textContent = err.message;
  }
};

bundleList.onclick = async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  const action = button.dataset.action;
  const bundleId = Number(button.dataset.id);
  if (action === "view-bids") await showBids(bundleId);
  if (action === "bid") await submitBid(bundleId);
};

bidsList.onclick = async (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  if (button.dataset.action === "award") {
    await awardBid(Number(button.dataset.bundleId), Number(button.dataset.bidId));
  }
};

closeBidsBtn.onclick = closeBidsPanel;

bootstrapApp();