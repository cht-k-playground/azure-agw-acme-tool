# az-acme-tool — Development Roadmap

本文件追蹤此專案所有計畫中的 OpenSpec 變更。
每個項目對應恰好一個 `/opsx:new` → `/opsx:ff` → `/opsx:apply` → `/opsx:verify` → `/opsx:archive` 週期。

**使用方式**：
- 在目前階段選取下一個 `[ ]` 項目。
- 執行 `/opsx:new <change-name>`，再執行 `/opsx:ff` 開始。
- 僅在 `/opsx:archive` 完成後才標記為 `[x]`。
- 當另一個變更為 `in_progress` 時，不得開始新項目。
- 本文件是所有 AI Agent 執行 `/opsx:new` + `/opsx:ff` 時的首要參考來源 — 每個條目的細節即為 `proposal.md`、`design.md`、`tasks.md` 的撰寫依據。

**狀態圖例**：
- `[ ]` 尚未開始
- `[~]` 進行中（變更存在於 `openspec/changes/`）
- `[x]` 已完成（已歸檔於 `openspec/changes/archive/`）

---

## Phase 1 — Core MVP

> **目標**：一個功能完整的 CLI，能夠透過 ACME HTTP-01 驗證在 Azure Application Gateway 上簽發、更新及檢查憑證。

### 1-A：基礎設施（可並行執行）

---

- [x] `config-schema` — 定義並驗證 YAML 設定模型

  **Dependencies**：無（此為起始點）

  **實作細節**：
  - Pydantic v2 models: `AcmeConfig`、`AzureConfig`、`GatewayConfig`、`DomainConfig`
  - 驗證規則：email 格式、UUID 格式的 subscription ID、FQDN 格式、domain 格式
  - `cert_store` enum：`agw_direct` only（Key Vault 延後至 Phase 2）
  - `auth_method` enum：`default | service_principal | managed_identity`
  - `parse_config(path: Path) -> AppConfig` 公開函數 + 自訂 `ConfigError` 例外類別
  - 設定路徑預設值：`~/.config/az-acme-tool/config.yaml`
  - 單元測試覆蓋所有驗證規則（≥80% coverage）

  **Acceptance Criteria**：
  1. `parse_config()` 在讀取合法 YAML 時回傳完整型別化的 `AppConfig` 物件，且 `mypy --strict` 無錯誤。
  2. 缺少必填欄位（`acme_email`、`subscription_id`、`resource_group`）時，`parse_config()` 拋出 `ConfigError`，且錯誤訊息明確指出缺失欄位名稱。
  3. `subscription_id` 不符合 UUID 格式時，`parse_config()` 拋出 `ConfigError`。
  4. `auth_method` 設為不支援的字串時，`parse_config()` 拋出 `ConfigError`。
  5. 所有 Pydantic model 的單元測試通過，行覆蓋率 ≥80%。

---

- [x] `logging-setup` — 結構化日誌與主控台輸出基礎設施

  **Dependencies**：無（此為起始點）

  **實作細節**：
  - JSON Lines 檔案 logger → `~/.config/az-acme-tool/logs/az-acme-tool.log`
  - Rich 主控台輸出，含色彩與進度指示器（`rich.progress`、`rich.console`）
  - 日誌層級：`DEBUG`（verbose）、`INFO`（預設）、`WARNING`、`ERROR`
  - `--verbose` flag 接入 root Click group context，設定全域 log level 為 `DEBUG`
  - 公開函數：`setup_logging(verbose: bool) -> None`
  - 單元測試：驗證 JSON Lines 記錄結構、`verbose=True` 時 DEBUG 訊息出現於日誌

  **Acceptance Criteria**：
  1. 執行任何 CLI 命令後，日誌檔案以 JSON Lines 格式寫入 `~/.config/az-acme-tool/logs/az-acme-tool.log`，每行包含 `timestamp`、`level`、`message` 欄位。
  2. 未加 `--verbose` 時，DEBUG 訊息不出現在 stderr；加上 `--verbose` 後出現。
  3. `setup_logging()` 函數在 `mypy --strict` 下無型別錯誤。
  4. 測試中模擬 `rich.console.Console` 輸出，確認 INFO 訊息以非 JSON 格式印至 stderr。
  5. 單元測試行覆蓋率 ≥80%。

---

### 1-B：核心基礎設施（須在 1-A 完成後進行）

---

- [x] `azure-gateway-client` — Azure SDK 的 Application Gateway 操作封裝

  **Dependencies**：`config-schema`、`logging-setup`

  **實作細節**：
  - `AzureGatewayClient` 類別，使用 `DefaultAzureCredential`（或 SP/MI 覆寫）初始化
  - 公開方法：
    - `get_gateway(gateway_name: str) -> ApplicationGateway`
    - `upload_ssl_certificate(gateway_name: str, cert_name: str, pfx_data: bytes, password: str) -> None`
    - `add_routing_rule(gateway_name: str, rule_name: str, domain: str, backend_fqdn: str) -> None`
    - `delete_routing_rule(gateway_name: str, rule_name: str) -> None`
    - `get_listener_certificate_info(gateway_name: str, listener_name: str) -> CertInfo`
    - `update_function_app_settings(function_app_name: str, settings: dict[str, str]) -> None`
  - 暫時性 Routing Rule 命名規則：`acme-challenge-{domain_sanitized}-{unix_timestamp}`，
    其中 `domain_sanitized` 將 `.` 替換為 `-`。
    範例：`www.example.com` + timestamp `1709030400` → `acme-challenge-www-example-com-1709030400`
  - Path-based rule URL pattern：`/.well-known/acme-challenge/*`，
    指向後端池（Backend Pool），後端池指向 `acme_function_fqdn`
  - Backend HTTP Settings（for Azure Function）：
    ```json
    {
      "protocol": "Https",
      "port": 443,
      "pickHostNameFromBackendAddress": true,
      "requestTimeout": 30
    }
    ```
  - SSL Certificate 命名規則：`{domain_sanitized}-cert`，點替換為橫線。
    範例：`www.example.com` → `www-example-com-cert`
  - SSL Certificate 上傳格式：Base64 編碼的 PFX，搭配自動產生的隨機密碼（密碼僅存於記憶體，絕不寫入磁碟或日誌）
  - Listener 查找策略（UC-04 shared-cert listeners）：遍歷 AGW listeners，比對 `host_names` 欄位與目標 domain；
    找到 listener 後讀取其 `ssl_certificate` 參照名稱；所有共用該憑證名稱的 listeners 在憑證物件替換後自動更新
  - `HttpResponseError` 在每個 SDK 呼叫上顯式處理；自訂 `AzureError` 例外階層
  - 指數退避重試（max 3 次）用於 429 / 5xx 回應
  - 單元測試以 `pytest-mock` 對 `azure.mgmt.network` 與 `azure.mgmt.web` 打樁

  **Acceptance Criteria**：
  1. `upload_ssl_certificate()` 以 base64 編碼 PFX bytes 呼叫 Azure SDK，且密碼不出現在任何日誌輸出或磁碟檔案中。
  2. `add_routing_rule()` 建立的規則名稱符合 `acme-challenge-{domain_sanitized}-{unix_timestamp}` 格式，且 URL path map 包含 `/.well-known/acme-challenge/*`。
  3. Azure SDK 回傳 429 時，`AzureGatewayClient` 執行指數退避並最多重試 3 次，第 4 次後拋出 `AzureError`。
  4. `get_listener_certificate_info()` 回傳的 `CertInfo` 物件在 `mypy --strict` 下型別正確。
  5. 所有方法的單元測試通過，行覆蓋率 ≥80%，且無真實 Azure API 呼叫。

---

- [x] `acme-client` — ACME HTTP-01 challenge 客戶端

  **Dependencies**：`config-schema`、`logging-setup`

  **實作細節**：
  - `AcmeClient` 類別，使用 `acme.client.ClientV2` 與 `josepy.JWKRSA` 作為帳號金鑰（`acme>=2.7.0`）
  - 公開方法：
    - `register_account(email: str, account_key_path: Path) -> str`
      向 ACME CA 註冊帳號，回傳帳號 URL；若 `account_key_path` 已存在則直接載入，不重新產生
    - `new_order(domains: list[str]) -> Order`
    - `get_http01_challenge(order: Order, domain: str) -> tuple[str, str]`
      回傳 `(token, key_authorization)`
    - `answer_challenge(challenge: Challenge) -> None`
    - `poll_until_valid(order: Order, timeout_seconds: int = 60, interval_seconds: int = 5) -> None`
    - `finalize_order(order: Order, csr_pem: bytes) -> Order`
    - `download_certificate(order: Order) -> str` （回傳 PEM 字串）
  - Challenge token 儲存機制：`get_http01_challenge()` 取得 token 與 key_authorization 後，
    必須透過 `AzureGatewayClient.update_function_app_settings()` 將 `ACME_CHALLENGE_RESPONSE` 寫入 Azure Function App Settings，才能呼叫 `answer_challenge()`
  - Polling 策略：呼叫 `answer_challenge()` 後，每 5 秒輪詢 ACME CA 訂單狀態，最長 60 秒；逾時則拋出 `AcmeError`
  - 指數退避重試（max 3 次，base delay 10 秒）用於暫時性錯誤
  - 自訂 `AcmeError` 例外類別
  - 單元測試以模擬 ACME CA 回應打樁

  **Acceptance Criteria**：
  1. `get_http01_challenge()` 回傳的 `(token, key_authorization)` 元組在 `mypy --strict` 下型別正確，且 key_authorization 格式符合 ACME RFC 8555 規範。
  2. `poll_until_valid()` 在模擬 CA 回傳「pending」狀態時，以 5 秒間隔輪詢；當超過 60 秒仍未驗證時拋出 `AcmeError`。
  3. ACME CA 回傳暫時性錯誤時，執行指數退避並最多重試 3 次。
  4. `download_certificate()` 回傳的字串以 `-----BEGIN CERTIFICATE-----` 開頭（有效 PEM 格式）。
  5. 所有方法的單元測試通過，行覆蓋率 ≥80%，且無真實 ACME CA 呼叫。

---

- [x] `cert-converter` — PEM → PFX 轉換與憑證工具函數

  **Dependencies**：`config-schema`、`logging-setup`

  **實作細節**：
  - `pem_to_pfx(cert_pem: str, key_pem: str, password: str) -> bytes`
  - `cert_fingerprint(cert_pem: str) -> str` （回傳 SHA-256 hex 字串）
  - `cert_expiry(cert_pem: str) -> datetime` （回傳 UTC datetime）
  - `generate_csr(domains: list[str], key_pem: str) -> bytes` （回傳 DER 格式 CSR）
  - 私鑰材料絕不寫入磁碟；所有操作在記憶體中完成
  - 使用 `cryptography` 套件
  - 單元測試使用 `cryptography` 產生的自簽憑證

  **Acceptance Criteria**：
  1. `pem_to_pfx()` 回傳可被 Python `cryptography` 套件以原始密碼解析的有效 PFX bytes。
  2. `cert_expiry()` 對已過期的測試憑證回傳過去的 datetime；對未來有效的憑證回傳未來的 datetime。
  3. `cert_fingerprint()` 對相同輸入 PEM 每次回傳相同的 SHA-256 hex 字串（確定性）。
  4. `generate_csr()` 產生的 CSR 包含所有傳入的 `domains` 作為 Subject Alternative Names。
  5. 所有函數的單元測試通過，行覆蓋率 ≥80%，且私鑰材料不出現在任何暫存檔。

---

### 1-C：CLI 命令（須在 1-B 完成後進行）

---

- [x] `cli-init` — 實作 `init` 命令

  **Dependencies**：`config-schema`、`logging-setup`、`acme-client`

  **實作細節**：
  - 產生 RSA-2048 ACME 帳號私鑰，寫入 `account_key_path`，檔案權限 `0o600`
  - 使用 `acme` + `josepy` 向 ACME CA 註冊帳號
  - `--config-template` flag：將準備好的 YAML 範本列印至 stdout（不執行任何 Azure 或 ACME 呼叫）
  - 主控台輸出格式：金鑰路徑、帳號 URL、下一步指引
  - 若 `account_key_path` 已存在，提示使用者確認是否覆寫
  - 單元測試模擬 ACME CA 與檔案系統

  **Acceptance Criteria**：
  1. 執行 `az-acme-tool init` 後，`account_key_path` 對應的檔案以 `0o600` 權限建立，且內容為有效的 PEM 格式 RSA 私鑰。
  2. 執行 `az-acme-tool init --config-template` 時，stdout 輸出包含所有必填 YAML 欄位的佔位符，且不執行任何 Azure 或 ACME 呼叫。
  3. 若 `account_key_path` 已存在，命令提示確認；測試中以 `n` 回應時，現有檔案不被覆寫。
  4. `AcmeClient.register_account()` 被呼叫一次，帳號 URL 正確列印至主控台。
  5. 單元測試行覆蓋率 ≥80%，無真實 ACME CA 呼叫。

---

- [x] `cli-issue` — 實作 `issue` 命令（協調層）

  **Dependencies**：`config-schema`、`logging-setup`、`azure-gateway-client`、`acme-client`

  **注意**：`azure-gateway-client` 與 `acme-client` 在此變更之前已完成，因此 `cli-issue` 必須針對真實的型別化介面編寫程式碼，不得使用 stub 或佔位符實作。

  **實作細節**：
  - 讀取並驗證設定；以 `--gateway` / `--domain` 篩選（均為可選）
  - Dry-run 模式（`--dry-run`）：記錄所有計畫步驟，不執行任何 Azure 或 ACME 呼叫
  - 進度輸出：每個 domain 的步驟清單 + 執行摘要
  - 委派給 `AcmeClient`（真實介面）與 `AzureGatewayClient`（真實介面）
  - 單元測試：篩選邏輯（`--gateway`/`--domain` 組合）與 dry-run 行為

  **Acceptance Criteria**：
  1. `az-acme-tool issue --dry-run` 列印所有計畫步驟至 stdout，且不呼叫任何 Azure SDK 或 ACME CA。
  2. `az-acme-tool issue --gateway my-agw` 僅處理設定中 `gateway_name == "my-agw"` 的 domains。
  3. `az-acme-tool issue --domain www.example.com` 僅處理指定 domain，即使設定中有多個 domain。
  4. 傳入不存在於設定中的 `--domain` 時，命令退出並回傳非零 exit code，且錯誤訊息清楚說明原因。
  5. 單元測試行覆蓋率 ≥80%，所有 Azure 與 ACME 呼叫以 mock 取代。

---

- [ ] `cli-renew` — 實作 `renew` 命令

  **Dependencies**：`cli-issue`、`azure-gateway-client`、`cert-converter`

  **實作細節**：
  - 透過 Azure SDK 查詢每個 AGW listener 的憑證到期日（呼叫 `get_listener_certificate_info()` 再用 `cert_expiry()`）
  - 跳過憑證到期日超過 `--days` 閾值（預設 30 天）的 domains
  - `--force` flag 略過閾值檢查，強制更新所有 domains
  - 重用 `issue` 協調邏輯執行實際的更新
  - 單元測試模擬不同到期日情境

  **Acceptance Criteria**：
  1. 憑證剩餘 35 天時，`az-acme-tool renew`（預設 `--days 30`）跳過該 domain，並在輸出中說明原因。
  2. 憑證剩餘 25 天時，`az-acme-tool renew` 觸發該 domain 的更新流程。
  3. `az-acme-tool renew --force` 對剩餘 35 天的憑證也觸發更新。
  4. `az-acme-tool renew --days 60` 對剩餘 55 天的憑證觸發更新。
  5. 單元測試行覆蓋率 ≥80%，所有 Azure 與 ACME 呼叫以 mock 取代。

---

- [x] `cli-status` — 實作 `status` 命令

  **Dependencies**：`azure-gateway-client`、`cert-converter`

  **實作細節**：
  - 透過 Azure SDK 從每個 AGW listener 取得 SSL 憑證 metadata
  - 資料來源：呼叫 `get_listener_certificate_info()` 取得 PFX 資料，再用 `cert_expiry()` 解析到期日
  - 計算剩餘天數；標記在 30 天內到期的憑證
  - 輸出格式：
    - `table`（預設，使用 Rich）— 欄位：`Gateway | Listener | Domain | Expiry Date | Days Remaining | Status`
    - `json` — 陣列，每個物件包含：`gateway`（str）、`resource_group`（str）、`listener`（str）、`domain`（str）、`expiry_date`（ISO 8601 字串）、`days_remaining`（int）、`status`（`"valid"` / `"expiring_soon"` / `"expired"`）
    - `yaml`
  - Status 判斷邏輯：
    - `✅ Valid`（`valid`）：剩餘 >30 天
    - `⚠️  Expiring Soon`（`expiring_soon`）：剩餘 ≤30 天且 >0 天
    - `❌ Expired`（`expired`）：剩餘 ≤0 天
  - 單元測試：到期日計算、三種輸出格式

  **Acceptance Criteria**：
  1. `az-acme-tool status` 以 Rich table 輸出，欄位順序為 `Gateway | Listener | Domain | Expiry Date | Days Remaining | Status`。
  2. `az-acme-tool status --output json` 輸出符合上述 JSON schema 的有效 JSON，可被 `json.loads()` 解析。
  3. 剩餘 31 天的憑證顯示 `✅ Valid`（JSON: `"valid"`）；剩餘 29 天顯示 `⚠️  Expiring Soon`（JSON: `"expiring_soon"`）；剩餘 -1 天顯示 `❌ Expired`（JSON: `"expired"`）。
  4. `az-acme-tool status --output yaml` 輸出有效 YAML，`expiry_date` 為 ISO 8601 格式字串。
  5. 單元測試行覆蓋率 ≥80%，所有 Azure SDK 呼叫以 mock 取代。

---

- [ ] `cli-cleanup` — 實作 `cleanup` 命令

  **Dependencies**：`azure-gateway-client`

  **實作細節**：
  - 透過名稱前綴 `acme-challenge-` 識別每個 AGW URL path maps 中的孤立規則
  - 不加 `--all`：顯示已找到規則的編號清單，逐一提示確認後再移除
  - 加 `--all`：不提示，移除所有匹配規則
  - 輸出：每條被移除的規則名稱列印至 stdout
  - 單元測試模擬 Azure SDK 回應

  **Acceptance Criteria**：
  1. `az-acme-tool cleanup`（不加 `--all`）顯示所有 `acme-challenge-` 前綴規則的編號清單，並對每條規則個別提示確認。
  2. `az-acme-tool cleanup --all` 移除所有 `acme-challenge-` 前綴規則，不顯示任何確認提示。
  3. 沒有匹配規則時，命令輸出「No orphaned ACME challenge rules found.」並以 exit code 0 退出。
  4. `delete_routing_rule()` 僅對規則名稱以 `acme-challenge-` 開頭的規則呼叫。
  5. 單元測試行覆蓋率 ≥80%，所有 Azure SDK 呼叫以 mock 取代。

---

### 1-D：Azure Function Responder（須在 1-B 完成後進行）

---

- [ ] `azure-function-responder` — Azure Function HTTP-01 challenge 回應器

  **Dependencies**：`config-schema`、`logging-setup`

  **位置**：`azure-function/` 目錄於 repo 根目錄

  **實作細節**：
  - Runtime：Python 3.11
  - Trigger：HTTP trigger，route 為 `/.well-known/acme-challenge/{token}`
  - 邏輯：讀取 `ACME_CHALLENGE_RESPONSE` 環境變數，以 `text/plain` content type 回傳其值
  - 若 `ACME_CHALLENGE_RESPONSE` 未設定或為空，回傳 HTTP 404
  - 必要 App Settings：`ACME_CHALLENGE_RESPONSE`（由 CLI 在 challenge 流程中設定）
  - CLI 側整合：`AzureGatewayClient.update_function_app_settings()` 使用 `azure-mgmt-web` SDK 更新 App Settings
  - 部署設定：`azure-function/host.json`、`azure-function/function_app.py`、`azure-function/requirements.txt`
  - 單元測試：模擬 HTTP trigger，驗證正確的 `text/plain` 回應與 404 行為

  **Acceptance Criteria**：
  1. HTTP GET `/.well-known/acme-challenge/TOKEN` 在 `ACME_CHALLENGE_RESPONSE` 設為 `TOKEN.KEY_AUTH` 時，回傳 HTTP 200，body 為 `TOKEN.KEY_AUTH`，Content-Type 為 `text/plain`。
  2. `ACME_CHALLENGE_RESPONSE` 未設定時，回傳 HTTP 404。
  3. `AzureGatewayClient.update_function_app_settings()` 成功呼叫 `azure-mgmt-web` SDK 更新 App Settings，且不將 key_authorization 值寫入日誌。
  4. `azure-function/function_app.py` 通過 `ruff` lint 檢查，且 `mypy --strict` 無錯誤。
  5. 單元測試行覆蓋率 ≥80%，且無真實 Azure Function 部署。

---

### 1-E：端對端串接（須在 1-C 與 1-D 全部完成後進行）

---

- [ ] `issue-flow-core` — 單一 domain 的完整 14 步 ACME 流程實作

  **Dependencies**：`cli-issue`、`cli-renew`、`cli-status`、`cli-cleanup`、`azure-function-responder`、`cert-converter`

  **實作範疇**：僅涵蓋單一 domain、單一 gateway 的 happy path（14 步），不包含批次並行處理。

  **14 步流程（精確定義）**：
  1. 讀取設定 + 解析目標 domain
  2. 建立 ACME order（`new_order`）
  3. 取得 HTTP-01 challenge（`get_http01_challenge`）→ 回傳 token + key_authorization
  4. 更新 Azure Function App Settings，寫入 key_authorization（`ACME_CHALLENGE_RESPONSE`）
  5. 在 AGW 建立暫時性 Path-based Routing Rule（`add_routing_rule`，含 `/.well-known/acme-challenge/*` path map）
  6. 通知 ACME CA 準備就緒（`answer_challenge`）
  7. 輪詢 ACME CA 直到驗證通過（最長 60 秒，5 秒間隔）
  8. Finalize order（`finalize_order`，含 CSR）
  9. 下載憑證 PEM（`download_certificate`）
  10. 將 PEM 轉換為 PFX（`pem_to_pfx`，使用隨機產生的密碼，僅存於記憶體）
  11. 上傳 PFX 至 AGW 作為 SSL Certificate 物件（`upload_ssl_certificate`，命名規則：`{domain_sanitized}-cert`）
  12. 尋找所有使用舊憑證名稱的 listeners
  13. 更新每個 listener 以參照新憑證
  14. 刪除暫時性 Routing Rule（`delete_routing_rule`）

  **Listener 自動發現（UC-04）**：遍歷 AGW listeners，比對 `host_names` 欄位與目標 domain；找到後讀取其 `ssl_certificate` 參照名稱；所有共用該憑證名稱的 listeners 皆更新。

  **Acceptance Criteria**：
  1. 對單一 domain 執行完整流程後，AGW 上存在命名為 `{domain_sanitized}-cert` 的 SSL Certificate 物件，且對應 listener 已更新參照。
  2. 步驟 14（刪除暫時性 Routing Rule）即使在步驟 7-13 發生例外時仍會被執行（finally block 或等效機制）。
  3. PFX 的隨機密碼不出現在任何日誌輸出或磁碟檔案中。
  4. 單元測試模擬所有 14 步，確認每步驟的呼叫順序與參數正確。
  5. 【手動驗證】使用 Let's Encrypt Staging 環境與真實 Azure Application Gateway 執行端對端測試，確認完整 14 步流程通過。此項目不在自動化 CI 範疇內。

---

- [ ] `issue-flow-batch` — 多 domain 並行處理、失敗隔離與批次摘要報告

  **Dependencies**：`issue-flow-core`

  **實作細節**：
  - 並行處理：使用 `asyncio` 或 `concurrent.futures.ThreadPoolExecutor(max_workers=3)`，最多同時處理 3 個 domains
  - 失敗隔離：domain X 失敗時記錄錯誤並繼續處理 domain X+1，不中斷整批作業
  - 摘要輸出：
    ```
    Total: N | Succeeded: S | Failed: F | Duration: Xs
    ```
    失敗的 domains 列出名稱與錯誤原因
  - 在 `cli-issue` 協調層中整合批次邏輯（取代原本的序列處理）
  - 整合測試使用 Let's Encrypt Staging + 模擬 AGW SDK 呼叫

  **Acceptance Criteria**：
  1. 處理 5 個 domains 時，日誌顯示最多 3 個 domains 同時進行（並行度 ≤3）。
  2. 第 2 個 domain 在步驟 7 發生 `AcmeError` 時，第 3、4、5 個 domains 仍繼續處理。
  3. 批次完成後輸出包含 `Total`、`Succeeded`、`Failed`、`Duration` 四個數值，且數字加總正確（`Succeeded + Failed == Total`）。
  4. 失敗 domain 的錯誤訊息出現在最終摘要中，包含 domain 名稱與例外訊息。
  5. 單元測試行覆蓋率 ≥80%，至少包含「全部成功」與「部分失敗」兩種情境；端對端批次流程為【手動驗證】，不在自動化 CI 範疇內。

---

## Phase 2 — Enterprise Extensions

> **目標**：Key Vault 整合、自動排程與可觀測性。
> 在所有 Phase 1 項目標記為 `[x]` 之前，不得開始 Phase 2 項目。

---

- [ ] `keyvault-cert-store` — Azure Key Vault 作為替代憑證儲存

  **Dependencies**：`issue-flow-batch`（Phase 1 全部完成）

  **實作細節**：
  - `cert_store: key_vault` 支援於 config schema
  - 每個 domain 新增 `key_vault_name` + `key_vault_secret_name` 欄位
  - `KeyVaultCertStore` 類別使用 `azure-keyvault-certificates`
  - `HttpResponseError` 處理與指數退避重試（與 `AzureGatewayClient` 一致）
  - 單元測試模擬 Key Vault SDK

  **Acceptance Criteria**：
  1. 設定 `cert_store: key_vault` 後，`parse_config()` 要求 `key_vault_name` 欄位存在，否則拋出 `ConfigError`。
  2. `KeyVaultCertStore.store_certificate()` 以正確的 secret name 呼叫 Azure Key Vault SDK。
  3. Key Vault SDK 回傳 429 時，執行指數退避重試，最多 3 次。
  4. `KeyVaultCertStore` 在 `mypy --strict` 下無型別錯誤。
  5. 單元測試行覆蓋率 ≥80%，無真實 Key Vault 呼叫。

---

- [ ] `renewal-scheduler` — 自動排程更新

  **Dependencies**：`cli-renew`（Phase 1 全部完成）

  **實作細節**：
  - `schedule` 子命令（或 cron 相容設計）
  - 設定 YAML 中可設定 `renew_before_days`
  - 冪等性：在排程中重複執行不產生副作用
  - 單元測試排程邏輯

  **Acceptance Criteria**：
  1. `az-acme-tool schedule --once` 執行單次更新檢查後退出，exit code 0。
  2. 設定中 `renew_before_days: 45` 時，`schedule` 命令使用 45 天作為更新閾值。
  3. 多次執行 `schedule` 不重複簽發已在有效期內的憑證（冪等性）。
  4. 命令在 `mypy --strict` 下無型別錯誤。
  5. 單元測試行覆蓋率 ≥80%。

---

- [ ] `webhook-notifications` — 操作後 webhook 通知

  **Dependencies**：`issue-flow-batch`（Phase 1 全部完成）

  **實作細節**：
  - 設定 YAML 中新增可選的 `notifications` 區段
  - 目標：通用 HTTP webhook（Teams / Slack 相容格式）
  - 事件：`certificate_issued`、`certificate_renewed`、`certificate_failed`
  - 單元測試模擬 HTTP 客戶端

  **Acceptance Criteria**：
  1. 設定 `notifications.webhook_url` 後，成功簽發憑證時發送 HTTP POST 至該 URL，body 包含 `event: "certificate_issued"` 與 domain 名稱。
  2. 未設定 `notifications` 時，不發送任何 HTTP 請求（通知功能完全可選）。
  3. Webhook 端點回傳非 2xx 時，記錄警告但不中斷主流程。
  4. Webhook 請求不包含任何憑證私鑰或密碼材料。
  5. 單元測試行覆蓋率 ≥80%，無真實 HTTP 呼叫。

---

- [ ] `revoke-command` — 實作 `revoke` 命令

  **Dependencies**：`acme-client`、`azure-gateway-client`（Phase 1 全部完成）

  **實作細節**：
  - 透過 ACME CA 撤銷憑證
  - 從 AGW 移除對應的 SSL Certificate 物件
  - 任何破壞性操作前顯示確認提示
  - 單元測試模擬 ACME + Azure SDK

  **Acceptance Criteria**：
  1. `az-acme-tool revoke --domain www.example.com` 顯示確認提示，以 `n` 回應時不執行任何 ACME 或 Azure 呼叫。
  2. 確認後，`AcmeClient` 的撤銷方法與 `AzureGatewayClient` 的刪除憑證方法各被呼叫一次。
  3. ACME CA 回傳撤銷失敗時，命令以非零 exit code 退出並顯示錯誤原因。
  4. 命令在 `mypy --strict` 下無型別錯誤。
  5. 單元測試行覆蓋率 ≥80%，無真實 ACME CA 或 Azure 呼叫。

---

## 跨越所有階段的要求（Cross-Cutting Constraints）

以下不是獨立的變更項目，而是每個變更都必須滿足的約束條件。Agent 在撰寫任何變更的 `design.md` 時必須明確說明這些約束如何被遵守：

- **型別標注**：所有公開函數與方法必須具備完整的型別標注；`mypy --strict` 必須無錯誤。
- **程式碼品質**：每個變更後 `ruff`（linter）與 `mypy --strict`（型別檢查）必須乾淨；不得在未於 `design.md` 中說明理由的情況下停用 linter 規則。
- **格式化**：使用 `black --line-length 100`。
- **測試覆蓋率**：每個變更後 `src/az_acme_tool/` 的行覆蓋率必須維持 **≥80%**。
- **安全性**：任何 committed 程式碼或測試 fixtures 中不得出現 secrets、私鑰或憑證材料。私鑰檔案必須以 `0o600` 權限建立。任何層級的日誌均不得記錄 secrets。
- **例外處理**：使用結構化例外 — 每個模組定義自訂例外類別。所有 Azure SDK 呼叫必須顯式處理 `HttpResponseError`。ACME 操作必須實作指數退避重試（最多 3 次）。
- **依賴管理**：新的 runtime 依賴加入 `pyproject.toml` 的 `[project.dependencies]`；開發依賴加入 `[project.optional-dependencies] dev`；主應用程式不使用 `requirements.txt`。**例外**：`azure-function/requirements.txt` 是唯一被允許的 `requirements.txt`，由 Azure Functions runtime 部署所需，與 `pyproject.toml` 分開維護，不由 uv 管理。
