const tbody = document.querySelector("#record-body");
const count = document.querySelector("#record-count");
const form = document.querySelector("#manual-form");
const input = document.querySelector("#qr-text");
const message = document.querySelector("#form-message");
const status = document.querySelector("#connection-status");

// ========================================
// 読み取り履歴に1件追加
// ========================================

function addRow(record) {
  document.querySelector("#empty-row")?.remove();

  const row = document.createElement("tr");

  // 入力値をHTMLとして解釈させないため、textContentを使います。
  for (const value of [
    record.id,
    record.qr_text,
    record.read_at,
    record.source
  ]) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
  }

  tbody.prepend(row);

  count.textContent = String(
    Number(count.textContent) + 1
  );
}


// ========================================
// リアルタイム通信
// ========================================

const eventSource = new EventSource("/events");

eventSource.onopen = () => {
  status.textContent = "リアルタイム接続済み";
  status.classList.add("connected");
};

eventSource.onmessage = (event) => {
  addRow(JSON.parse(event.data));
};

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
