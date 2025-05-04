const START_WEBHOOK = "http://localhost:13371/meet-start";
const END_WEBHOOK = "http://localhost:13371/meet-end";

function toast(text, isError = false) {
  document.getElementById("__meet_toast")?.remove();

  const node = document.createElement("div");
  node.id = "__meet_toast";
  node.textContent = text;

  Object.assign(node.style, {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    background: isError ? "rgba(200, 50, 50, 0.95)" : "rgba(60, 60, 60, 0.9)",
    color: "#fff",
    padding: "12px 18px",
    borderRadius: "8px",
    fontSize: "14px",
    zIndex: 9999999,
    opacity: 1,
    transition: "opacity 0.3s ease 2.7s"
  });

  document.body.appendChild(node);
  setTimeout(() => (node.style.opacity = 0), 10);
  setTimeout(() => node.remove(), 3000);
}

function pingWebhook(url, successMsg, failMsg) {
  fetch(url, { method: "POST" })
    .then(response => {
      if (!response.ok) {
        return response.text().then(msg => { throw new Error(msg); });
      }
      toast(successMsg);
    })
    .catch(err => toast(failMsg + (err.message ? ": " + err.message : ""), true));
}

function isInMeeting() {
  return Boolean(document.querySelector('div[data-meeting-id]'));
}

// JOIN
function onJoinMeeting() {
  pingWebhook(START_WEBHOOK, "Recording started", "Failed to start recording");
}

// LEAVE
function onLeaveMeeting() {
  pingWebhook(END_WEBHOOK, "Recording ended", "Failed to stop recording");
}

// Initial check: if already inside a meeting
if (isInMeeting()) {
  onJoinMeeting();
}

// Watch for user clicking "Join now" or transitioning into meeting
const observer = new MutationObserver(() => {
  if (isInMeeting() && !window.__meetRecordingStarted) {
    window.__meetRecordingStarted = true;
    onJoinMeeting();
  }
});
observer.observe(document.body, { childList: true, subtree: true });

// Handle hangup or page close
window.addEventListener("beforeunload", () => {
  if (window.__meetRecordingStarted) {
    onLeaveMeeting();
  }
});

// Hook into Leave call button
const leaveObserver = new MutationObserver(() => {
  const leaveBtn = document.querySelector(
    '[aria-label^="Leave call"], [data-tooltip^="Leave call"]'
  );
  if (leaveBtn && !leaveBtn.__toastBound) {
    leaveBtn.__toastBound = true;
    leaveBtn.addEventListener("click", () => {
      if (window.__meetRecordingStarted) {
        onLeaveMeeting();
        window.__meetRecordingStarted = false;
      }
    });
  }
});
leaveObserver.observe(document.documentElement, { childList: true, subtree: true });
