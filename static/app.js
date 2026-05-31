const chatFeed = document.getElementById("chatFeed");
const traceFeed = document.getElementById("traceFeed");
const messageForm = document.getElementById("messageForm");
const messageInput = document.getElementById("messageInput");
const resetButton = document.getElementById("resetButton");
const typingIndicator = document.getElementById("typingIndicator");
let state = null;
let autoScrollChat = true;
let autoScrollTrace = true;

function renderMessage(role, text) {
  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${role}`;
  bubble.textContent = text;
  chatFeed.appendChild(bubble);
  // Only auto-scroll when the user is currently near the bottom
  if (autoScrollChat) scheduleScrollToBottom(chatFeed);
}

function renderTrace(trace) {
  const card = document.createElement("div");
  card.className = "trace-card";
  const header = document.createElement("strong");
  header.textContent = trace.title.toUpperCase();
  const meta = document.createElement("div");
  meta.className = "trace-meta";
  meta.innerHTML = `<span>${trace.type}</span><span>${trace.agent}</span><span>${new Date(trace.timestamp).toLocaleTimeString()}</span>`;
  const summary = document.createElement("p");
  summary.className = "trace-summary";
  summary.textContent = trace.summary;
  card.appendChild(header);
  card.appendChild(meta);
  card.appendChild(summary);

  if (trace.inputs || trace.outputs) {
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify({ inputs: trace.inputs, outputs: trace.outputs }, null, 2);
    card.appendChild(pre);
  }

  traceFeed.appendChild(card);
  if (autoScrollTrace) scrollToBottom(traceFeed);
}

function setTyping(visible) {
  typingIndicator.classList.toggle("hidden", !visible);
}

function isNearBottom(el, threshold = 100) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
}

function scheduleScrollToBottom(el) {
  requestAnimationFrame(() => {
    scrollToBottom(el);
  });
}

function scrollToBottom(el, smooth = true) {
  try {
    const lastChild = el.lastElementChild;
    if (lastChild) {
      lastChild.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'end' });
    } else {
      el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
    }
  } catch (e) {
    el.scrollTop = el.scrollHeight;
  }
}

// Track user scroll interactions to avoid fighting the user's manual scroll
chatFeed.addEventListener('scroll', () => {
  autoScrollChat = isNearBottom(chatFeed);
});
traceFeed.addEventListener('scroll', () => {
  autoScrollTrace = isNearBottom(traceFeed);
});

async function startScenario() {
  addLocalTrace({
    type: "operational_event",
    agent: "UI",
    title: "Starting proactive monitoring",
    summary: "Bookly is evaluating the delayed order and preparing a proactive update.",
    timestamp: new Date().toISOString(),
  });
  setTyping(true);

  try {
    const response = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    const data = await response.json();
    state = data.state;
    renderMessage("agent", data.message);
    data.traces.forEach(renderTrace);
  } catch (error) {
    renderMessage("agent", "Sorry, something went wrong when starting the demo.");
  } finally {
    setTyping(false);
  }
}

function addLocalTrace(trace) {
  renderTrace(trace);
}

messageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text || !state) return;
  renderMessage("customer", text);
  messageInput.value = "";
  setTyping(true);

  try {
    const response = await fetch("/api/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, state }),
    });
    const data = await response.json();
    state = data.state;
    renderMessage("agent", data.message);
    data.traces.forEach(renderTrace);
  } catch (error) {
    renderMessage("agent", "Sorry, I couldn’t process that message right now.");
  } finally {
    setTyping(false);
  }
});

resetButton.addEventListener("click", async () => {
  state = null;
  chatFeed.innerHTML = "";
  traceFeed.innerHTML = "";
  setTyping(false);
  await startScenario();
});

window.addEventListener("load", () => {
  setTimeout(startScenario, 4200);
});
