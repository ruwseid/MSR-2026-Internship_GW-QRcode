# インターンシップ課題：QRコード受付アプリ

FastAPI、OpenCV、Jinja2、CSVを使った最小構成のサンプルです。カメラでQRコードを読み取るとCSVへ保存し、ブラウザへリアルタイム表示します。

## 1. 必要なもの

- Python 3.12
- uv
- QRコードを読み取る場合はWebカメラ

uvのインストール方法は公式ドキュメントを参照してください。

- https://docs.astral.sh/uv/getting-started/installation/

## 2. 起動方法

展開したフォルダ内で次を実行します。

```bash
uv sync
uv run uvicorn app.main:app --reload
```

このプロジェクトはWindows環境を考慮し、uvのインストール方式を `copy` に設定しています。

ブラウザで http://127.0.0.1:8000 を開きます。終了するときはターミナルで `Ctrl + C` を押します。

カメラを開けない場合でもサーバは起動します。画面上部の手動登録欄で動作を確認できます。

## 3. データ保存先

読取結果は `data/records.csv` にUTF-8（BOM付き）で保存されます。Excelから直接開くこともできます。

| 列 | 内容 |
|---|---|
| id | 連番 |
| qr_text | QRコードの内容 |
| read_at | 読取日時（日本時間） |
| source | `camera` または `manual` |

## 4. 処理の流れ

1. FastAPI起動時にバックグラウンドのカメラスレッドを開始する
2. OpenCVの `QRCodeDetector` でフレームを読み取る
3. 読取結果を `data/records.csv` へ保存する
4. Server-Sent Events（SSE）で接続中のブラウザへ通知する
5. JavaScriptが一覧の先頭へ新しい行を追加する
6. 画面を再読込した場合は、FastAPIがCSV全件を読みJinja2でHTMLを生成する

## 5. ファイル構成

```text
app/
  main.py          FastAPIの画面・API・SSE
  camera.py        OpenCVのバックグラウンド処理
  csv_store.py     CSVの読み書き
  events.py        ブラウザへの非同期通知
  models.py        データ構造
  config.py        設定値
  templates/       Jinja2のHTML
  static/          CSSとJavaScript
data/              CSV保存先
tests/             最小限の自動テスト
```

## 6. カメラ番号の変更

外付けカメラなどを使う場合は `app/config.py` の `CAMERA_DEVICE_INDEX` を `1`、`2` などへ変えてください。

## 7. テスト

```bash
uv run pytest
```

## 8. 改修・拡張例

### 基礎

1. 一覧へ「備考」列を追加する
2. QRコード内容による検索機能を追加する
3. CSVをダウンロードするボタンを追加する

### 発展

1. 同じQRコードの重複登録ルールを変更する
2. カメラの稼働状態を画面へ表示する
3. CSVをSQLiteへ置き換える
4. 認証を追加し、登録者を記録する

## 9. 注意事項

- CSVは小規模な開発向けです。複数プロセスから同時に書き込む本番システムにはDBを使ってください。
- `uvicorn` の `--workers` は指定せず、1プロセスで実行してください。複数プロセスにすると各プロセスがカメラを開こうとします。
- QRコードには個人情報や機密情報を入れないでください。
