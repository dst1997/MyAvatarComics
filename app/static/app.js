const form = document.querySelector("#comic-form");
const uploads = document.querySelector("#uploads");
const uploadCount = document.querySelector("#upload-count");
const deleteButton = document.querySelector("#delete-project");
const statusTitle = document.querySelector("#status-title");
const statusMessage = document.querySelector("#status-message");
const progressNumber = document.querySelector("#progress-number");
const progressBar = document.querySelector("#progress-bar");
const previewGrid = document.querySelector("#preview-grid");
const downloadLink = document.querySelector("#download-link");

let currentProjectId = null;
let pollTimer = null;

uploads.addEventListener("change", () => {
  const files = Array.from(uploads.files || []);
  const photos = files.filter((file) => /\.(jpg|jpeg|png|webp)$/i.test(file.name)).length;
  const videos = files.length - photos;
  uploadCount.textContent = `${photos} photo${photos === 1 ? "" : "s"}${videos ? `, ${videos} video${videos === 1 ? "" : "s"}` : ""} selected.`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearPreview();
  setBusy(true);
  try {
    const files = Array.from(uploads.files || []);
    const photoCount = files.filter((file) => /\.(jpg|jpeg|png|webp)$/i.test(file.name)).length;
    if (photoCount < 1 || photoCount > 8) {
      throw new Error("Please choose 1-8 photos before generating.");
    }
    setStatus("Creating project", "Saving the project details.", 8);
    const specResponse = await fetchJson("/api/projects", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        consent_given: document.querySelector("#consent").checked,
        recipient_name: document.querySelector("#recipient-name").value,
        relationship: document.querySelector("#relationship").value,
        occasion: document.querySelector("#occasion").value,
        event_details: document.querySelector("#event-details").value,
        dedication: document.querySelector("#dedication").value,
      }),
    });
    const specData = await parseJson(specResponse);
    currentProjectId = specData.project_id;
    deleteButton.disabled = false;

    setStatus("Uploading media", "Saving uploads locally.", 18);
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    await parseJson(await fetchJson(`/api/projects/${currentProjectId}/uploads`, {method: "POST", body: formData}));

    setStatus("Generating", "The comic generator is starting.", 24);
    await parseJson(await fetchJson(`/api/projects/${currentProjectId}/generate`, {method: "POST"}));
    pollStatus();
  } catch (error) {
    setBusy(false);
    setStatus("Could not start", error.message, 100, true);
  }
});

deleteButton.addEventListener("click", async () => {
  if (!currentProjectId) return;
  await fetch(`/api/projects/${currentProjectId}`, {method: "DELETE"});
  currentProjectId = null;
  deleteButton.disabled = true;
  downloadLink.classList.add("hidden");
  clearPreview();
  setStatus("Deleted", "Project files were removed from local storage.", 0);
});

async function pollStatus() {
  if (!currentProjectId) return;
  let data;
  try {
    data = await parseJson(await fetchJson(`/api/projects/${currentProjectId}/status`));
  } catch (error) {
    setBusy(false);
    setStatus("Connection lost", error.message, 100, true);
    return;
  }
  const status = data.status;
  const message = status.status === "failed" ? (status.error || status.message || "") : (status.message || "");
  setStatus(status.status, message, status.progress || 0, status.status === "failed");
  if (data.manifest) {
    renderPreview(data.manifest);
  }
  if (status.status === "complete" || status.status === "failed") {
    setBusy(false);
    return;
  }
  pollTimer = window.setTimeout(pollStatus, 1300);
}

function renderPreview(manifest) {
  previewGrid.classList.remove("empty");
  previewGrid.innerHTML = "";
  const previewTitle = document.querySelector("#preview-title");
  if (previewTitle && manifest.title) previewTitle.textContent = manifest.title;
  downloadLink.href = manifest.download_url;
  downloadLink.classList.remove("hidden");
  manifest.pages.forEach((page) => {
    const card = document.createElement("article");
    card.className = "page-card";
    const img = document.createElement("img");
    img.src = `${page.image_url}?t=${Date.now()}`;
    img.alt = `Comic page ${page.page_number}: ${page.title}`;
    const footer = document.createElement("footer");
    const label = document.createElement("span");
    label.textContent = `Page ${page.page_number}`;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Regenerate";
    button.addEventListener("click", () => regeneratePage(page.page_number));
    footer.append(label, button);
    card.append(img, footer);
    previewGrid.append(card);
  });
}

async function regeneratePage(pageNumber) {
  if (!currentProjectId) return;
  setBusy(true);
  setStatus("Regenerating", `Rendering page ${pageNumber} again.`, 80);
  await parseJson(await fetchJson(`/api/projects/${currentProjectId}/pages/${pageNumber}/regenerate`, {method: "POST"}));
  pollStatus();
}

function clearPreview() {
  if (pollTimer) window.clearTimeout(pollTimer);
  previewGrid.className = "preview-grid empty";
  previewGrid.innerHTML = "<p>Generated pages will appear here.</p>";
}

function setBusy(isBusy) {
  form.querySelector("button[type='submit']").disabled = isBusy;
}

function setStatus(title, message, progress, isError = false) {
  statusTitle.textContent = title;
  statusMessage.textContent = message;
  statusMessage.style.color = isError ? "#b91c1c" : "";
  progressNumber.textContent = `${progress}%`;
  progressBar.style.width = `${progress}%`;
}

async function parseJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg).join(" "));
    }
    throw new Error(detail || "Request failed.");
  }
  return data;
}

async function fetchJson(url, options = {}) {
  try {
    return await fetch(url, options);
  } catch (error) {
    throw new Error("Cannot reach the local app server. Keep the Uvicorn terminal running and reopen http://127.0.0.1:8000/.");
  }
}
