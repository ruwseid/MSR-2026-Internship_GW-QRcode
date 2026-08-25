const tbody = document.querySelector("#record-body");
const count = document.querySelector("#record-count");
const form = document.querySelector("#manual-form");
const input = document.querySelector("#qr-text");
const message = document.querySelector("#form-message");
const status = document.querySelector("#connection-status");

// 受け取った1件を一覧の先頭へ追加します。
function addRow(record) {
  document.querySelector("#empty-row")?.remove();
  const row = document.createElement("tr");

  // innerHTMLへ入力値を直接入れるとXSSの原因になるため、textContentを使います。
  for (const value of [record.id, record.qr_text, record.read_at, record.source]) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.appendChild(cell);
  }
  tbody.prepend(row);
  count.textContent = String(Number(count.textContent) + 1);
}

// FastAPIのSSEエンドポイントへ常時接続し、新規データを待ちます。
const eventSource = new EventSource("/events");
eventSource.onopen = () => {
  status.textContent = "リアルタイム接続済み";
  status.classList.add("connected");
};
eventSource.onmessage = (event) => addRow(JSON.parse(event.data));
eventSource.onerror = () => {
  status.textContent = "再接続中...";
  status.classList.remove("connected");
};

// 手動登録フォームからJSONをPOSTします。登録結果自体はSSE経由で表へ届きます。
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "登録しています...";
  const response = await fetch("/api/records", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ qr_text: input.value }),
  });
  if (!response.ok) {
    message.textContent = "登録に失敗しました。入力内容を確認してください。";
    return;
  }
  input.value = "";
  message.textContent = "登録しました。";
});

