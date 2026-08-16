# 情境規劃專案面試筆記

## 為什麼既有 Control Tower 還不夠？

既有 Control Tower 已能用 DataCo 資料與 Power BI 監控需求、庫存、產能及服務風險，但主要回答「現在發生了什麼」。規劃者還需要回答「如果需求上升或產能下降，應如何分配有限產能，以及服務水準會如何變化」，因此加入 Scenario Planning。

## 為什麼使用 Plant × Product × Week？

週是適合這個 MVP 的規劃週期；Plant 代表共享產能池與瓶頸；Product 代表需求、優先順序與服務取捨。這個 Level 3 粒度足以展示產能分配、瓶頸識別和 Scenario 比較，也不會引入即時或多層級規劃的額外複雜度。

## 為什麼先使用 ABC 優先順序與規則式分配？

目前沒有可直接使用的利潤或策略價值資料，因此使用既有 ABC 分類作為透明代理：A、B、C 對應 3、2、1。每個 `Scenario × Plant × Week` 使用共享產能池，先考慮庫存，再依優先順序、淨需求和產品 ID 分配。這套規則可重現、容易驗證，也能清楚解釋高優先與低優先產品的服務取捨。

## 為什麼初期不做 OR 最佳化？

線性規劃或混合整數規劃需要更完整的成本、交期、替代工廠、物料限制和明確的最佳化目標。兩週 MVP 應先完成正確、可驗證、可說明的 deterministic planning engine；OR solver 是未來擴充，不應在資料假設不足時增加不必要的複雜度。

## 這個專案展現哪些規劃能力？

專案展示如何從既有監控資料建立 Planning Snapshot、定義 Baseline/Demand Surge/Capacity Disruption 情境、在共享產能限制下依優先順序分配、計算 backlog 與 service level，並把服務惡化追溯到需求或產能限制。這表示專案已從 monitoring/diagnosis 延伸到 planning/simulation/decision support。

## 如何說明架構與未來 AI？

面試時可說明資料先進入 Planning Data Layer，再建立 Planning Snapshot，Scenario Generator 產生情境，Allocation Engine 進行規則式分配，Performance Evaluation 計算 KPI，Decision Support 提供解釋，最後輸出到 Power BI。未來 AI 可協助用自然語言建立情境、說明結果、進行根因解釋或提供知識檢索；但 AI 應建立在已驗證的 deterministic engine 上，不取代核心商業規則。
