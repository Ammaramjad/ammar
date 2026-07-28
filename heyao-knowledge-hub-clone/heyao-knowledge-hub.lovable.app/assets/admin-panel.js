const STORAGE_KEY = "fycc_admin_config_v1";
const DEFAULT_RESOURCE = "articles";

const refs = {
  baseUrl: document.getElementById("baseUrl"),
  token: document.getElementById("token"),
  resource: document.getElementById("resource"),
  customResource: document.getElementById("customResource"),
  itemId: document.getElementById("itemId"),
  payload: document.getElementById("payload"),
  status: document.getElementById("status"),
  listBody: document.getElementById("listBody"),
  countValue: document.getElementById("countValue"),
  lastActionValue: document.getElementById("lastActionValue"),
  selectedResourceValue: document.getElementById("selectedResourceValue")
};

function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    const parsed = JSON.parse(raw);
    refs.baseUrl.value = parsed.baseUrl || "";
    refs.token.value = parsed.token || "";
    refs.resource.value = parsed.resource || DEFAULT_RESOURCE;
    refs.customResource.value = parsed.customResource || "";
  } catch (error) {
    showStatus("Failed to restore saved admin settings.", true);
  }
}

function saveConfig() {
  const payload = {
    baseUrl: refs.baseUrl.value.trim(),
    token: refs.token.value.trim(),
    resource: refs.resource.value,
    customResource: refs.customResource.value.trim()
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function getResourcePath() {
  if (refs.resource.value === "custom") {
    const custom = refs.customResource.value.trim();
    if (!custom) {
      throw new Error("Custom endpoint path is required.");
    }
    return custom.replace(/^\/+|\/+$/g, "");
  }
  return refs.resource.value;
}

function getHeaders() {
  const headers = {
    "Content-Type": "application/json"
  };
  const token = refs.token.value.trim();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

function getBaseUrl() {
  const baseUrl = refs.baseUrl.value.trim().replace(/\/+$/, "");
  if (!baseUrl) {
    throw new Error("API base URL is required.");
  }
  return baseUrl;
}

function showStatus(message, isError = false, isSuccess = false) {
  refs.status.className = "status";
  if (isError) {
    refs.status.classList.add("error");
  }
  if (isSuccess) {
    refs.status.classList.add("success");
  }
  refs.status.textContent = message;
}

function setLastAction(label) {
  refs.lastActionValue.textContent = label;
  refs.selectedResourceValue.textContent = refs.resource.value === "custom"
    ? refs.customResource.value.trim() || "(custom)"
    : refs.resource.value;
}

function safeParsePayload() {
  const raw = refs.payload.value.trim();
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error("JSON payload format is invalid.");
  }
}

function renderRows(items) {
  refs.listBody.innerHTML = "";
  if (!Array.isArray(items) || items.length === 0) {
    refs.listBody.innerHTML = "<tr><td colspan='3'>No data found.</td></tr>";
    refs.countValue.textContent = "0";
    return;
  }
  refs.countValue.textContent = String(items.length);

  const keys = ["id", "title", "name"];
  items.forEach((item, index) => {
    const key = keys.find((candidate) => item && Object.prototype.hasOwnProperty.call(item, candidate));
    const idValue = key ? item[key] : `row-${index + 1}`;
    const nameValue = item?.title || item?.name || item?.subject || "(no title)";
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(String(idValue ?? ""))}</td>
      <td>${escapeHtml(String(nameValue ?? ""))}</td>
      <td><pre>${escapeHtml(JSON.stringify(item, null, 2))}</pre></td>
    `;
    refs.listBody.appendChild(row);
  });
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function request(method, path, body) {
  const baseUrl = getBaseUrl();
  const endpoint = `${baseUrl}/${path}`;
  const options = {
    method,
    headers: getHeaders()
  };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(endpoint, options);
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (error) {
    data = text;
  }

  if (!response.ok) {
    const reason = typeof data === "string" ? data : JSON.stringify(data);
    throw new Error(`Request failed (${response.status}): ${reason}`);
  }
  return data;
}

async function listItems() {
  try {
    saveConfig();
    const resourcePath = getResourcePath();
    showStatus("Loading data...");
    const result = await request("GET", resourcePath);
    const items = Array.isArray(result) ? result : result?.data || [];
    renderRows(items);
    setLastAction("Listed");
    showStatus(`Loaded ${items.length} item(s).`, false, true);
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function createItem() {
  try {
    saveConfig();
    const resourcePath = getResourcePath();
    const body = safeParsePayload();
    showStatus("Creating item...");
    await request("POST", resourcePath, body);
    setLastAction("Created");
    showStatus("Item created successfully.", false, true);
    await listItems();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function updateItem() {
  try {
    saveConfig();
    const resourcePath = getResourcePath();
    const id = refs.itemId.value.trim();
    if (!id) {
      throw new Error("Item ID is required for update.");
    }
    const body = safeParsePayload();
    showStatus("Updating item...");
    await request("PUT", `${resourcePath}/${encodeURIComponent(id)}`, body);
    setLastAction("Updated");
    showStatus("Item updated successfully.", false, true);
    await listItems();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function deleteItem() {
  try {
    saveConfig();
    const resourcePath = getResourcePath();
    const id = refs.itemId.value.trim();
    if (!id) {
      throw new Error("Item ID is required for deletion.");
    }
    showStatus("Deleting item...");
    await request("DELETE", `${resourcePath}/${encodeURIComponent(id)}`);
    setLastAction("Deleted");
    showStatus("Item deleted successfully.", false, true);
    await listItems();
  } catch (error) {
    showStatus(error.message, true);
  }
}

document.getElementById("saveConfig").addEventListener("click", () => {
  saveConfig();
  showStatus("Configuration saved in this browser.", false, true);
});
document.getElementById("listItems").addEventListener("click", listItems);
document.getElementById("createItem").addEventListener("click", createItem);
document.getElementById("updateItem").addEventListener("click", updateItem);
document.getElementById("deleteItem").addEventListener("click", deleteItem);
document.getElementById("resource").addEventListener("change", () => {
  refs.selectedResourceValue.textContent = refs.resource.value;
});

loadConfig();
setLastAction("Ready");
