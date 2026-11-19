# WP2 — Scenario Trade-off Analysis
## Implementation Specification v1.0

**Status:** Approved Design Baseline — Implementation Pending  
**Priority Cohort Policy:** Fixed Reference Cohort  
**Dependency:** WP1 Root Cause Investigation  
**Target:** Existing Streamlit Planning Decision Support Application

---

## 1. Objective

建立 Reference vs. Candidate 的 Scenario Trade-off Analysis，讓使用者能夠比較不同規劃情境下的服務水準、未滿足需求、Backlog、Lost Sales 與產能負荷。

WP2 的核心問題：

1. Candidate 相較於 Reference，整體營運結果有什麼變化？
2. 指定優先產品群組的服務水準是否改善？
3. 其他產品是否因此承受更大的服務損失？
4. 服務、Backlog、Lost Sales 與 Workload 之間存在什麼 Trade-off？
5. 哪些結果可以公平比較？哪些只能作描述性比較？

**重要原則：WP2 是比較分析功能，不是新的 Planning Engine，也不負責產生新的 Scenario。**

## 2. Scope

### Included

- Reference / Candidate 明確選擇。
- Scenario Trade-off Comparison。
- Fixed Priority Cohort。
- Complementary Product Group。
- All / Selected / Complementary 三組比較。
- Service、Backlog、Lost Sales、Workload 指標。
- Metric-level Comparability Validation。
- Comparison Context、Metric Results、Evidence References。
- CSV Export。
- USER_DATA 與 SYNTHETIC_DEMO 支援。
- 與 WP1 Root Cause Investigation 的整合。

### Excluded

- 新增 Scenario Generator 或 What-if Controls。
- 跨 Run 比較及 Canonical Replay。
- 修改 Planning、Allocation、Inventory、KPI 核心計算公式。
- 自動調整 Product Priority。
- Optimization、Preferred Action 或推薦最佳方案。
- 新的 Composite Score。
- AI-generated Recommendations。
- Power BI 或 Dashboard 全面改版。

**MVP 限制：第一版只支援同一個已發布 sequential_v1 Run 內的兩個明確 Scenario。**

---

## 3. Reference / Candidate Selection

使用者必須明確指定：

- Reference Scenario：比較基準。
- Candidate Scenario：待評估方案。

兩者必須屬於相同的 Published Run。

### Comparison Direction

所有 Delta 統一採用：

`Delta = Candidate - Reference`

解讀方式：

| Metric | Delta 為正 | Delta 為負 |
|---|---|---|
| Fulfilled Quantity | 增加 | 減少 |
| Service Level | 改善 | 惡化 |
| Backlog | 增加 | 減少 |
| Lost Sales | 增加 | 減少 |
| Allocated Workload | 增加 | 減少 |
| Unmet Workload | 增加 | 減少 |

注意：Delta 的正負不直接代表好壞，必須依照 Metric 的商業意義解讀。

---

## 4. Priority Cohort — Fixed Reference Policy

### 4.1 Core Rule

Cohort Membership 必須固定依據 Reference Scenario 的 `Planning_Priority` 決定。

Candidate Scenario 的 Priority 變化不得改變既有 Cohort Membership。

例如：

| Product | Reference Priority | Candidate Priority | Priority 3 Cohort |
|---|---:|---:|---|
| Product A | 3 | 3 | Selected |
| Product B | 3 | 1 | Selected |
| Product C | 1 | 3 | Complement |
| Product D | 2 | 2 | Complement |

假設使用者選擇 Priority 3：

- Product A、B 永遠屬於 Selected Cohort。
- Product C、D 屬於 Complement。
- Product B 的 Priority 變化另外標示為 `Priority Changed`。
- 不得將 Product B 移出 Selected Cohort。
- 不得依 Candidate Priority 重新計算 Selected Cohort。

### 4.2 Cohort Definition

先建立兩側共同且明確指定的產品 Universe：

`U = Common Product Universe`

Selected Cohort：

`C = {p ∈ U | Reference Planning Priority(p) ∈ Selected Priorities}`

Complement：

`U - C`

必須符合：

1. Selected 與 Complement 互斥。
2. Selected 與 Complement 的聯集等於 U。
3. 不得因資料缺漏而默默縮小 Universe。
4. 不得以 ABC Class、Risk Ranking 或 Top N 取代 Planning Priority。
5. 空 Cohort 必須顯示 Empty / N/A，不得產生虛假的 0%。

### 4.3 User Interface

使用者可選擇一個或多個 Reference Priority，例如：

- Priority 1
- Priority 2
- Priority 3

預設不應偷偷指定某個 Priority 作為優先產品群組；必須清楚呈現使用者目前選擇。

### 4.4 Priority Change Indicator

Cohort Membership Table 至少包含：

| Field | Description |
|---|---|
| Product Card Id | Product identifier |
| Reference Priority | Reference Planning Priority |
| Candidate Priority | Candidate Planning Priority |
| Cohort Membership | Selected / Complement |
| Priority Changed | True / False |

Priority Changed 的判斷：

`Reference Priority != Candidate Priority`

若任一側 Priority 缺漏或無法對應，必須顯示資料問題，不得自行推定。

---

## 5. Comparison Groups

每個 Metric 至少支援以下三種比較群組：

| Group | Definition |
|---|---|
| ALL | Universe U 中所有產品 |
| SELECTED | 固定的 Reference Priority Cohort |
| COMPLEMENT | Universe 中不屬於 Selected 的其他產品 |

所有群組均使用同一個 Reference / Candidate、Plant Scope 與 Planning Horizon。

不得讓三組使用不同的產品範圍或不同的比較基準。

---

## 6. KPI and Metric Definitions

### 6.1 Service

**Weekly Service Level**

`SUM(Fulfilled_Current_Qty) / SUM(Scenario_Qualified_Demand)`

- Fulfillment Basis：CURRENT_WEEK_COHORT
- 以加總後的 Numerator / Denominator 計算。
- 不可直接平均各產品或各週的 Service Rate。
- 不可將本週對過去 Backlog 的 Fulfillment 混入本週需求服務率。

**Horizon Service Level**

`SUM(Fulfilled_Current_Qty + Fulfilled_Horizon_Backlog_Qty) / SUM(Scenario_Qualified_Demand)`

- Fulfillment Basis：HORIZON_ORIGIN_COHORT
- 不包含 Opening-origin Fulfillment。
- MVP 使用完整 Planning Horizon。
- 不得透過切割 Allocation Rows 自行推算不完整 Horizon 的服務率。

### 6.2 Backlog

使用共同 Horizon 結束時的 Terminal Backlog。

計算原則：

1. 先取得每個 Plant × Product 的期末 Backlog。
2. 再依 Cohort / Universe 聚合。
3. 不可把不同週的 Backlog 加總。
4. 不可將不同產品的期末存量與跨週流量混為一談。
5. 必須保留 Opening-origin 與 Horizon-origin 的區別。

### 6.3 Lost Sales

以原生產品 × Plant × Week Grain 的 Lost Sales Flow 加總。

不可將 Lost Sales 與 Backlog 合併成單一 KPI。

特別注意：

**LOST_SALES Policy 下 Backlog = 0，不代表 Service Level 改善。**

### 6.4 Workload

支援：

- Allocated Workload
- Unmet Workload
- Plant Capacity Pool Context

Workload 使用產品層級 Allocation Rows 聚合。

Shared Capacity 必須使用唯一的 Scenario × Plant × Week Capacity Pool 計算，不能因為多個產品引用同一個 Pool 而重複計算。

如果顯示 Utilization：

`SUM(Allocated Workload) / SUM(Available Capacity)`

分子與分母必須使用相同的 Plant × Week Scope。

不得把 Shared Plant Utilization 命名為 Cohort Utilization。

如果不同 Scenario 的 Workload Factor 或校準定義不相容，該 Workload Delta 必須標示為不可比較。

---

## 7. Comparability Validation

每個 Metric 必須獨立判斷可比較性。

### Status

| Status | Meaning |
|---|---|
| COMPARABLE | 可以進行正式 Delta 比較 |
| DESCRIPTIVE_ONLY | 可並列呈現，但不能視為受控比較或判定優劣 |
| BLOCKED | 無法進行有效比較 |

### Required Checks

- Reference / Candidate 是否明確存在。
- Run 與 Scenario 是否有效。
- Schema Version 是否支援。
- Product Universe 是否完整。
- Product / Plant Coverage 是否一致。
- Planning Horizon 是否一致。
- Metric Definition 是否一致。
- Output Grain 是否一致。
- Quantity Unit 是否一致。
- Fulfillment Basis 是否一致。
- Backlog Policy 是否相容。
- Opening State、Receipts、Priority、Eligibility、Capacity Basis 是否有差異。
- 必要資料是否缺漏或存在重複 Key。

### Missing Data

- 不得將缺漏資料自動填為 0。
- 不得默默使用兩側交集代替原定 Universe。
- 不得以最後一個有資料的 Week 取代缺漏的 Horizon Endpoint。
- 分母為 0 時，Rate 必須是 N/A。
- 不可比較時，Delta 必須是 N/A，並提供具體 Reason。

若 Run 或 Artifact Integrity Validation 失敗，應拒絕該 Run，而不是只顯示警告後繼續產生可信度不足的比較結果。

---

## 8. Backlog Policy Differences

預設要求兩側使用相同 Backlog Policy。

如果兩側不同，例如：

`CARRY_FORWARD → LOST_SALES`

應標示：

`POLICY_CONTRAST`

允許：

- 並列呈現兩側 Service。
- 並列呈現兩側 Terminal Backlog。
- 並列呈現兩側 Lost Sales。
- 顯示 Policy Difference。
- 在符合 Metric Definition 的情況下提供描述性 Delta。

不允許：

- 宣稱 Candidate 勝出。
- 將 Backlog 降低視為 Service 改善。
- 將 Backlog 與 Lost Sales 合併。
- 將 Policy Contrast 當作受控的 Allocation Improvement。
- 基於不同 Policy 的結果直接產生 Preferred Action。

其他重要輸入若有變化，也必須記錄並依 Metric 影響範圍降低比較等級或阻擋比較。

---

## 9. Proposed Data Structure

實作應採用小型、可測試的 Pure Function Interface。

建議介面：

`compare_published_results(reference, candidate, scope) -> ComparisonResult`

### 9.1 Input

Reference 與 Candidate 各自包含：

- Validated Manifest
- Published Sequential Output Tables
- Run_ID
- Scenario
- Schema_Version
- Data_Mode
- Backlog_Policy

Scope 包含：

- Product Universe
- Plant Scope
- Planning Horizon
- Selected Priorities
- Cohort Basis
- Metric IDs
- Output Grain

### 9.2 ComparisonResult

至少包含：

**context**

- Comparison_ID
- Reference Run_ID / Scenario
- Candidate Run_ID / Scenario
- Reference / Candidate Backlog Policy
- Scope
- Comparability Summary

**cohort_membership**

- Product Card Id
- Reference Priority
- Candidate Priority
- Cohort Membership
- Priority Changed

**metrics**

- Comparison_ID
- Cohort_ID
- Metric_ID
- Aggregation_Level
- Plant_ID（適用時）
- Order_Date（適用時）
- Unit
- Fulfillment_Basis
- Reference Value
- Candidate Value
- Reference Numerator / Denominator
- Candidate Numerator / Denominator
- Delta
- Delta Unit
- Comparability Status
- Reason

**evidence_refs**

- Side
- Run_ID
- Scenario
- Artifact Name / Path / Hash
- Native Grain
- Key / Filter
- Provenance
- Metric Definition Reference

### 9.3 Architecture Rules

- Loader 負責 IO、Manifest、Hash、Schema 與資料驗證。
- Comparison Function 僅處理已驗證的 DataFrames。
- Comparison Function 不應直接執行新的 Planning Simulation。
- 優先重用既有 KPI、Product Horizon Aggregation 與 WP1 Investigation Helpers。
- 不建立大型 Allocation × Ledger × Receipts Join。
- 不修改原有 WP1 Evidence Export 的語意。
- Comparison Export 必須額外標示 Reference / Candidate、Comparison_ID 與 Scope。
- 保留原始 Run / Scenario Identity。
- 輸出排序必須 deterministic。
- 不得修改或污染輸入 DataFrames。

---

## 10. UI Requirements

新增 Scenario Trade-off Analysis 區域或 Tab。

建議操作順序：

1. 選擇 Reference Scenario。
2. 選擇 Candidate Scenario。
3. 選擇 Reference Priority Cohort。
4. 確認固定 Cohort Membership。
5. 檢視 Priority Changes。
6. 檢視 All / Selected / Complement Trade-offs。
7. 檢視 Comparability Status 與 Reasons。
8. 下載 Comparison CSV。

### Summary View

至少呈現：

- Reference / Candidate Context
- Comparison Scope
- Selected Priority Cohort
- Priority Changed Product Count
- Service Level Delta
- Terminal Backlog Delta
- Lost Sales Delta
- Allocated Workload Delta
- Unmet Workload Delta
- Comparability Status

### Detailed View

提供：

- All Products
- Selected Cohort
- Complement
- Product-level Membership
- Priority Changes
- Metric-level Reasons
- Evidence References

應保留 WP1 Root Cause Investigation 的既有操作流程，不得因新增 WP2 而破壞其功能。

---

## 11. Testing Requirements

### A. Reference / Candidate

- 明確選擇不同 Scenario。
- 驗證 Delta 方向為 Candidate − Reference。
- 不可自動猜測 Reference。
- 不可將 Scenario 名稱或第一筆資料當成預設基準。

### B. Fixed Cohort

- Reference Priority 決定 Cohort。
- Candidate Priority 改變不得移動產品。
- Priority Changed Indicator 正確。
- Selected 與 Complement 互斥。
- Selected + Complement = Universe。
- 空 Cohort 正確顯示 N/A。
- Priority 缺漏時不能靜默分類。

### C. Aggregation

- Rate 使用加總後 Numerator / Denominator。
- Zero Denominator → N/A。
- Backlog 使用 Terminal Balance。
- 不可跨週加總 Stock。
- Shared Capacity 不得重複計算。
- 不可混合不同 Grain。
- 不可混合不同 Quantity Units。

### D. Policy / Comparability

- 相同 Policy 的可比較結果。
- 不同 Policy 的 POLICY_CONTRAST。
- 不同 Policy 不得產生 Winner 判定。
- Missing Product / Week 必須明確處理。
- 不相容的 Workload Factor 必須阻擋對應 Delta。
- Invalid Run / Artifact 必須拒絕。

### E. Integrity

- String IDs 不得被轉成錯誤數值。
- Evidence 不得產生 Join Fanout。
- Input DataFrames 不得被修改。
- Comparison 結果排序 deterministic。
- CSV Export 保留 Comparison Context。

### F. Data Modes

所有主要流程都必須在：

- USER_DATA
- SYNTHETIC_DEMO

兩種模式下測試。

### G. Regression

- WP1 Product → Plant → Week 正常。
- WP1 Plant → Week → Product 正常。
- WP1 Evidence Export 正常。
- Phase 1 CSV Upload 正常。
- Phase 2 Planning Risk Summary 正常。
- 不改變既有 Planning / Allocation / Inventory / KPI 結果。

---

## 12. Acceptance Criteria

WP2 可視為完成，必須同時滿足：

1. 使用者能明確選擇 Reference 與 Candidate。
2. Fixed Reference Cohort 正確運作。
3. Candidate Priority 變化只產生標示，不改變 Cohort Membership。
4. All / Selected / Complement 三組比較結果正確。
5. Service、Backlog、Lost Sales、Workload 的計算遵守定義。
6. Shared Capacity 不會被重複計算。
7. 每個 Metric 都有 Comparability Status 與必要理由。
8. Missing Data 不會被當作 0。
9. CSV 匯出具有完整比較脈絡與 Evidence Reference。
10. USER_DATA 與 SYNTHETIC_DEMO 都能使用。
11. WP1 與既有流程 Regression Tests 全部通過。
12. 不修改 Planning Engine、Allocation、Inventory 或既有 KPI 公式。

---

## 13. Implementation Boundary

本規格核准的是 WP2 的設計基準，不代表已授權 Codex 修改程式碼。

實作前應先確認：

- 目前 WP1 Worktree 狀態。
- 目前 Published Artifact Schema。
- 現有 KPI 與 Aggregation Helper 的實際可重用範圍。
- WP1 與 WP2 的 UI 整合位置。

實作採分階段方式，先完成 Comparison Data Model、Pure Comparison Logic、Tests，再整合 UI 與 Export。

**Main Agent 負責所有程式修改、測試與整合。Subagents 僅可執行獨立 Read-only Analysis，不得與 Main Agent 同時修改程式碼。**

不自動 Commit 或 Push。必須經過獨立驗收與明確授權後才可發布。
