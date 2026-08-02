# iPAS AI 應用規劃師 2026 600 題大滿貫 AI 教學與微調指南 (AI Teaching Guide)

> **版本**: v2.04 Complete (2026 最新公告試題整合)  
> **適用對象**: LLM Agent 提示工程、RAG 向量檢索庫、AI 輔導教案自動生成、題目自動解析與微調

---

## 1. 系統架構與題庫分佈矩陣 (600 題大滿貫)

本題庫包含 **初級 300 題 + 中級 300 題** 共 600 題實戰公告試題，結構完全對齊經濟部 iPAS 官方考試大綱。

| 科目代碼 | 能力鑑定級別 | 科目名稱 | 題目數量 | 資料來源與試題標籤 | 權限/範疇焦點 |
| --- | --- | --- | --- | --- | --- |
| **A1** | **初級 (Junior)** | 人工智慧基礎概論 | 150 題 | 114年第四梯次 + 115年第二次試題 | AI 定義、ML/DL 基本概念、資料隱私與倫理規範 |
| **A2** | **初級 (Junior)** | 生成式 AI 應用與規劃 | 150 題 | 114年第四梯次 + 115年第二次試題 | LLM 原理、Prompt 工程、RAG 與 Fine-tuning、No/Low Code 導入 |
| **B1** | **中級 (Intermediate)** | 人工智慧技術應用與規劃 | 100 題 | 114年公告試題 + 115年第一次試題 | 企業 AI 架構規劃、Agentic Workflow、概念漂移與資料漂移、XAI 可解釋性 |
| **B2** | **中級 (Intermediate)** | 大數據處理分析與應用 | 100 題 | 114年公告試題 + 115年第一次試題 | 大數據 5V 特性、Pandas/SQL 實做、特徵工程與離群值處理、資料管道治理 |
| **B3** | **中級 (Intermediate)** | 機器學習技術與應用 | 100 題 | 114年公告試題 + 115年第一次試題 | 模型演算法細節 (SVM, Random Forest, CNN, ResNet, PyTorch 梯度裁剪, Autoencoder) |

---

## 2. 核心考點知識樹與解題邏輯 (Taxonomy & Core Logic)

### 2.1 初級 (Junior Level) 核心重點
- **A1 人工智慧基礎概論**:
  - **監督式學習 (Supervised)** vs **非監督式 (Unsupervised)** vs **強化學習 (RL)** vs **半監督式 (Semi-supervised)**。
  - **指標判讀**: 召回率 Recall (防止漏報) vs 精確率 Precision (防止誤報) vs F1-score vs Accuracy。
  - **AI 倫理與基本法**: 隱私去識別化 (MD5 雜湊 vs 隨機化編號)、可解釋性、去偏見性、人身安全。
- **A2 生成式 AI 應用與規劃**:
  - **Prompt Engineering**: Role, Task, Context, Output format, Few-shot prompting, Chain of Thought (CoT)。
  - **RAG (檢索增強生成)** vs **Fine-tuning (微調)**: 企業內部文件滾動更新選 RAG，特定風格格式/專業領域術語選 Fine-tuning。
  - **Low-Code / Agentic Coding**: AutoML 核心優勢，Vibe Coding 彈性與維護性比較。

### 2.2 中級 (Intermediate Level) 核心重點
- **B1 人工智慧技術應用與規劃**:
  - **概念漂移 (Concept Drift)**: 輸入特徵分布未變，但目標關係變了（如疫情後消費行為改變）。
  - **資料漂移 (Data Drift)**: 輸入特徵分布發生變化（如新增行動裝置端用戶群）。
  - **XAI 可解釋性工具**: LIME (區域黑箱代理模型)、SHAP (Shapley 值特徵貢獻)、Saliency Map (熱度著色圖)。
- **B2 大數據處理分析與應用**:
  - **特徵工程**: Feature Cross (特徵交叉)、One-hot encoding vs Label encoding (避免無序類別產生不當大小排序概念)。
  - **資料時間依賴性**: 時間序列資料**絕不能使用標準 K-fold** 隨機分割，必須使用時間序列分割 (TimeSeriesSplit) 避免未來資訊洩漏。
- **B3 機器學習技術與應用**:
  - **深度學習與訓練瓶頸**: Loss 變成 `NaN` (梯度爆炸，使用 Gradient Clipping 梯度裁剪)， overfitting 過擬合處置 (Dropout, Early Stopping, Regularization)。
  - **神經網路架構**: CNN (影像物件分類)、LSTM (長序列依賴)、ResNet (殘差連接解決深層梯度消失)、Autoencoder (異常檢測自編碼)。

---

## 3. Prompt Engineering 指南: AI 家教 / 試題生成 System Prompt

若要將本題庫資料融入 AI 家教對話或自動解題 agent，建議使用以下系統提示詞（System Prompt）：

```markdown
You are an expert iPAS AI Application Planner (iPAS AI應用規劃師) Master Tutor.
Your goal is to guide students to master both Junior (初級 A1, A2) and Intermediate (中級 B1, B2, B3) certification exams.

When answering user questions or explaining exam items:
1. Provide the exact correct option letter and description.
2. Explain the fundamental technical concept (e.g. why RAG is better than Fine-tuning for real-time document updates).
3. Identify potential traps in wrong options.
4. Relate the problem to real-world industrial scenarios (financial fraud detection, AOI optical inspection, medical diagnosis).
5. Output structured Markdown with Key Takeaways and Memory Mnemonic.
```

---

## 4. 題庫 CSV 數據整合規格

資料庫全量備份檔案位於 [`official_sources/questions.csv`](file:///d:/ai-antigravity/ipas-aiap/official_sources/questions.csv)。

### 欄位說明
1. `編號`: 唯一識別碼 (A1-001 ~ A1-150, A2-001 ~ A2-150, B1-001 ~ B1-100, B2-001 ~ B2-100, B3-001 ~ B3-100)
2. `分類`: 科目分類 (`A1`, `A2`, `B1`, `B2`, `B3`)
3. `題號`: 原始題號 (001 ~ 050)
4. `文件名稱`: 出處官方試題 PDF 檔名
5. `題目`: 題幹全文
6. `選項1` ~ `選項4`: 標準選項內容 (1), (2), (3), (4)
7. `正確答案`: 數值標記 (`1`, `2`, `3`, `4`)
