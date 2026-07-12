const form = document.querySelector("#comic-form");
const stepsNav = document.querySelector("#steps-nav");
const uploads = document.querySelector("#uploads");
const dropzone = document.querySelector("#dropzone");
const thumbGrid = document.querySelector("#thumb-grid");
const reviewList = document.querySelector("#review");
const deleteButton = document.querySelector("#delete-project");
const statusTitle = document.querySelector("#status-title");
const statusMessage = document.querySelector("#status-message");
const progressNumber = document.querySelector("#progress-number");
const progressBar = document.querySelector("#progress-bar");
const milestones = document.querySelector("#milestones");
const previewGrid = document.querySelector("#preview-grid");
const previewTitle = document.querySelector("#preview-title");
const downloadLink = document.querySelector("#download-link");
const lightbox = document.querySelector("#lightbox");
const lightboxImage = document.querySelector("#lightbox-image");
const lightboxLabel = document.querySelector("#lightbox-label");
const lightboxRegen = document.querySelector("#lightbox-regen");

let currentProjectId = null;
let pollTimer = null;
let selectedFiles = [];
let lightboxPage = null;

const PHOTO_RE = /\.(jpg|jpeg|png|webp)$/i;

/* ---------- Session ---------- */

document.querySelector("#sign-out")?.addEventListener("click", async () => {
  await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
  window.location.href = "/login";
});

/* ---------- Wizard navigation ---------- */

function showStep(step) {
  document.querySelectorAll(".wizard-step").forEach((section) => {
    section.classList.toggle("active", Number(section.dataset.step) === step);
  });
  stepsNav.querySelectorAll("li").forEach((item) => {
    const number = Number(item.dataset.step);
    item.classList.toggle("active", number === step);
    item.classList.toggle("done", number < step);
  });
  if (step === 3) fillReview();
}

function stepIsValid(step) {
  clearFieldError();
  if (step === 1) {
    for (const id of ["recipient-name", "occasion", "event-details"]) {
      const field = document.querySelector(`#${id}`);
      if (!field.value.trim()) {
        field.focus();
        showFieldError(field, "Please fill this in first.");
        return false;
      }
    }
  }
  if (step === 2) {
    const photos = selectedFiles.filter((file) => PHOTO_RE.test(file.name));
    if (photos.length < 1 || photos.length > 8) {
      showFieldError(thumbGrid, "Please choose 1-8 photos.");
      return false;
    }
  }
  return true;
}

function showFieldError(afterElement, text) {
  const note = document.createElement("p");
  note.className = "field-error";
  note.textContent = text;
  const anchor = afterElement.closest("label") || afterElement;
  anchor.insertAdjacentElement("afterend", note);
}

function clearFieldError() {
  document.querySelectorAll(".field-error").forEach((node) => node.remove());
}

form.addEventListener("click", (event) => {
  const next = event.target.closest("[data-next]");
  if (next) {
    const from = Number(next.dataset.next) - 1;
    if (stepIsValid(from)) showStep(Number(next.dataset.next));
    return;
  }
  const back = event.target.closest("[data-back]");
  if (back) showStep(Number(back.dataset.back));
});

/* ---------- Photo selection & thumbnails ---------- */

uploads.addEventListener("change", () => {
  addFiles(Array.from(uploads.files || []));
  uploads.value = "";
});

["dragover", "dragleave", "drop"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.toggle("dragover", name === "dragover");
    if (name === "drop") addFiles(Array.from(event.dataTransfer?.files || []));
  });
});

function addFiles(files) {
  clearFieldError();
  for (const file of files) {
    const duplicate = selectedFiles.some((item) => item.name === file.name && item.size === file.size);
    if (!duplicate) selectedFiles.push(file);
  }
  renderThumbs();
}

function renderThumbs() {
  thumbGrid.innerHTML = "";
  selectedFiles.forEach((file, index) => {
    const cell = document.createElement("div");
    cell.className = "thumb";
    if (PHOTO_RE.test(file.name)) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.onload = () => URL.revokeObjectURL(img.src);
      img.alt = file.name;
      cell.append(img);
    } else {
      const chip = document.createElement("span");
      chip.className = "video-chip";
      chip.textContent = "VIDEO";
      cell.append(chip);
    }
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.title = `Remove ${file.name}`;
    remove.addEventListener("click", () => {
      selectedFiles.splice(index, 1);
      renderThumbs();
    });
    cell.append(remove);
    thumbGrid.append(cell);
  });
}

/* ---------- Review step ---------- */

function fillReview() {
  const photos = selectedFiles.filter((file) => PHOTO_RE.test(file.name)).length;
  const videos = selectedFiles.length - photos;
  const rows = [
    ["For", document.querySelector("#recipient-name").value || "—"],
    ["Relationship", document.querySelector("#relationship").value || "—"],
    ["Occasion", document.querySelector("#occasion").value || "—"],
    ["The story", truncate(document.querySelector("#event-details").value, 160) || "—"],
    ["Dedication", truncate(document.querySelector("#dedication").value, 120) || "—"],
    ["Photos", `${photos} photo${photos === 1 ? "" : "s"}${videos ? `, ${videos} video${videos === 1 ? "" : "s"}` : ""}`],
  ];
  reviewList.innerHTML = "";
  rows.forEach(([term, value]) => {
    const row = document.createElement("div");
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = value;
    row.append(dt, dd);
    reviewList.append(row);
  });
}

function truncate(text, length) {
  const clean = text.trim();
  return clean.length > length ? `${clean.slice(0, length)}…` : clean;
}

/* ---------- Submit & generation ---------- */

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  for (const step of [1, 2]) {
    if (!stepIsValid(step)) {
      showStep(step);
      return;
    }
  }
  if (!document.querySelector("#consent").checked) {
    setStatus("Almost there", "Please confirm you have permission to use the photos.", 0, true);
    return;
  }
  clearPreview();
  setBusy(true);
  try {
    setStatus("Creating project", "Saving the story details.", 5);
    const specData = await parseJson(await fetchJson("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        consent_given: true,
        recipient_name: document.querySelector("#recipient-name").value,
        relationship: document.querySelector("#relationship").value,
        occasion: document.querySelector("#occasion").value,
        event_details: document.querySelector("#event-details").value,
        dedication: document.querySelector("#dedication").value,
      }),
    }));
    currentProjectId = specData.project_id;
    deleteButton.disabled = false;

    setStatus("Uploading photos", "Saving the photos locally.", 8);
    const formData = new FormData();
    selectedFiles.forEach((file) => formData.append("files", file));
    await parseJson(await fetchJson(`/api/projects/${currentProjectId}/uploads`, { method: "POST", body: formData }));

    setStatus("Starting", "Waking up the comic artists.", 10);
    await parseJson(await fetchJson(`/api/projects/${currentProjectId}/generate`, { method: "POST" }));
    pollStatus();
  } catch (error) {
    setBusy(false);
    setStatus("Could not start", error.message, 100, true);
  }
});

deleteButton.addEventListener("click", async () => {
  if (!currentProjectId) return;
  await fetch(`/api/projects/${currentProjectId}`, { method: "DELETE" });
  currentProjectId = null;
  deleteButton.disabled = true;
  downloadLink.classList.add("hidden");
  clearPreview();
  setMilestones(-1);
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
  const failed = status.status === "failed";
  const message = failed ? (status.error || status.message || "") : (status.message || "");
  setStatus(titleFor(status), message, status.progress || 0, failed);
  updateMilestones(status);
  if (data.manifest) renderPreview(data.manifest);
  if (status.status === "complete" || failed) {
    setBusy(false);
    return;
  }
  pollTimer = window.setTimeout(pollStatus, 1300);
}

function titleFor(status) {
  if (status.status === "complete") return "The comic is ready!";
  if (status.status === "failed") return "Something went wrong";
  return "Making the comic";
}

/* ---------- Milestones ---------- */

function updateMilestones(status) {
  if (status.status === "complete") {
    setMilestones(4);
    return;
  }
  if (status.status !== "running") return;
  const progress = status.progress || 0;
  if (progress < 30) setMilestones(0);
  else if (progress < 38) setMilestones(1);
  else if (progress < 95) setMilestones(2);
  else setMilestones(3);
}

function setMilestones(activeIndex) {
  milestones.querySelectorAll("li").forEach((item, index) => {
    item.classList.toggle("done", index < activeIndex);
    item.classList.toggle("active", index === activeIndex);
  });
}

/* ---------- Preview & lightbox ---------- */

function renderPreview(manifest) {
  previewGrid.classList.remove("empty");
  previewGrid.innerHTML = "";
  if (manifest.title) previewTitle.textContent = `“${manifest.title}”`;
  downloadLink.href = manifest.download_url;
  downloadLink.classList.remove("hidden");
  manifest.pages.forEach((page) => {
    const card = document.createElement("article");
    card.className = "page-card";
    card.dataset.page = page.page_number;
    const img = document.createElement("img");
    img.src = `${page.image_url}?t=${Date.now()}`;
    img.alt = `Page ${page.page_number}: ${page.title}`;
    img.addEventListener("click", () => openLightbox(page, img.src));
    const footer = document.createElement("footer");
    const label = document.createElement("span");
    label.textContent = pageLabel(page);
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Redraw";
    button.addEventListener("click", () => regeneratePage(page.page_number));
    footer.append(label, button);
    card.append(img, footer);
    previewGrid.append(card);
  });
}

function pageLabel(page) {
  if (page.kind === "cover") return "Cover";
  if (page.kind === "end") return "End page";
  return `Page ${page.page_number}`;
}

function openLightbox(page, src) {
  lightboxPage = page;
  lightboxImage.src = src;
  lightboxLabel.textContent = `${pageLabel(page)} — ${page.title}`;
  lightbox.showModal();
}

document.querySelector("#lightbox-close").addEventListener("click", () => lightbox.close());
lightbox.addEventListener("click", (event) => {
  if (event.target === lightbox) lightbox.close();
});
lightboxRegen.addEventListener("click", () => {
  if (!lightboxPage) return;
  lightbox.close();
  regeneratePage(lightboxPage.page_number);
});

async function regeneratePage(pageNumber) {
  if (!currentProjectId) return;
  setBusy(true);
  document.querySelector(`.page-card[data-page="${pageNumber}"]`)?.classList.add("regenerating");
  setStatus("Redrawing", `Drawing page ${pageNumber} again.`, 60);
  setMilestones(2);
  try {
    await parseJson(await fetchJson(`/api/projects/${currentProjectId}/pages/${pageNumber}/regenerate`, { method: "POST" }));
    pollStatus();
  } catch (error) {
    setBusy(false);
    setStatus("Could not redraw", error.message, 100, true);
  }
}

/* ---------- Helpers ---------- */

function clearPreview() {
  if (pollTimer) window.clearTimeout(pollTimer);
  renderEmptyPreview();
  previewTitle.textContent = "Your pages will appear here";
  downloadLink.classList.add("hidden");
}

function renderEmptyPreview() {
  previewGrid.className = "preview-grid";
  previewGrid.innerHTML = "";
  const labels = ["Cover", "Page 2", "Page 3", "Page 4", "Page 5", "Page 6", "Page 7", "The End"];
  labels.forEach((label, index) => {
    const ghost = document.createElement("div");
    ghost.className = "ghost-page";
    const number = document.createElement("span");
    number.className = "ghost-num";
    number.textContent = index + 1;
    const caption = document.createElement("span");
    caption.textContent = label;
    ghost.append(number, caption);
    previewGrid.append(ghost);
  });
}

renderEmptyPreview();

function setBusy(isBusy) {
  document.querySelector("#create-button").disabled = isBusy;
}

function setStatus(title, message, progress, isError = false) {
  statusTitle.textContent = title;
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
  progressNumber.textContent = `${progress}%`;
  progressBar.style.width = `${progress}%`;
}

async function parseJson(response) {
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Please sign in first.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    if (Array.isArray(detail)) throw new Error(detail.map((item) => item.msg).join(" "));
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
