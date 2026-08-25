const tbody = document.querySelector("#record-body");
const count = document.querySelector("#record-count");
const form = document.querySelector("#manual-form");
const input = document.querySelector("#qr-text");
const message = document.querySelector("#form-message");
const status = document.querySelector("#connection-status");
const filters = document.querySelector("#history-filters");
const sortBy = document.querySelector("#sort-by");
const sortOrder = document.querySelector("#sort-order");
const sourceFilter = document.querySelector("#source-filter");
const filterMessage = document.querySelector("#filter-message");
let latestRequest = 0;

// ========================================
// 読み取り履歴の表示
// ========================================

function createRow(record) {
  const row = document.createElement("tr");

  // 入力値をHTMLとして解釈させないため、textContentを使います。
  for (const value of [record.id, record.qr_text, record.read_at]) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
  }

  const sourceCell = document.createElement("td");
  const source = document.createElement("span");
  source.className = "source";
  source.textContent = record.source;
  sourceCell.appendChild(source);
  row.appendChild(sourceCell);

  return row;
}

function renderRecords(records) {
  tbody.replaceChildren();

  if (records.length === 0) {
    const row = document.createElement("tr");
    row.id = "empty-row";
    const cell = document.createElement("td");
    cell.colSpan = 4;
    cell.textContent = "該当する読取データがありません。";
    row.appendChild(cell);
    tbody.appendChild(row);
  } else {
    for (const record of records) {
      tbody.appendChild(createRow(record));
    }
  }

  count.textContent = String(records.length);
}

async function refreshRecords() {
  const requestId = ++latestRequest;
  const params = new URLSearchParams({
    sort_by: sortBy.value,
    order: sortOrder.value,
    source: sourceFilter.value,
  });

  try {
    const response = await fetch(`/api/records?${params}`);
    if (!response.ok) {
      throw new Error(`履歴取得に失敗しました: ${response.status}`);
    }
    const records = await response.json();
    if (requestId !== latestRequest) return;

    renderRecords(records);
    filterMessage.textContent = "";
  } catch (_error) {
    if (requestId === latestRequest) {
      filterMessage.textContent =
        "履歴の更新に失敗しました。もう一度選択してください。";
    }
  }
}

filters.addEventListener("change", refreshRecords);
filters.addEventListener("submit", (event) => event.preventDefault());


// ========================================
// リアルタイム通信
// ========================================

const eventSource = new EventSource("/events");

eventSource.onopen = () => {
  status.textContent = "リアルタイム接続済み";
  status.classList.add("connected");
};

eventSource.onmessage = () => refreshRecords();

eventSource.onerror = () => {
  status.textContent = "再接続中...";
  status.classList.remove("connected");
};


// ========================================
// 手動登録
// ========================================

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  message.textContent = "登録しています...";

  const response = await fetch("/api/records", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      qr_text: input.value
    }),
  });

  if (!response.ok) {
    message.textContent =
      "登録に失敗しました。入力内容を確認してください。";
    return;
  }

  input.value = "";
  message.textContent = "登録しました。";
});


// ========================================
// ダークモード切り替え
// ========================================

const themeToggle = document.querySelector("#theme-toggle");

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const isDark = document.body.classList.toggle("dark");

    themeToggle.setAttribute(
      "aria-checked",
      String(isDark)
    );
  });
}
