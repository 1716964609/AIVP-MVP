# AIVP-MVP v1 技術実験報告書

## 1. 概要

AIVP（AI-native Change Verification Platform）MVP v1 は、AI Coding Agent が生成したコード変更に対して、

- どこまで自動検証できるか
- 失敗時にどこまで自動修復できるか
- どの条件で人間へEscalateすべきか
- AI Agentの実行回数や時間をどう制御するか

を検証するために構築したローカル実験用MVPです。

本MVPでは、

- Codex CLI：Generator / Fixer / Risk Judge
- Claude Code：Independent Reviewer
- Git / Unit Test / External Gate：Deterministic Verification
- Python Orchestrator：Workflow Controller
- Human：High-risk / Ambiguous Change の最終判断

という責務分離を採用しています。

目的は「完全自律開発」を作ることではありません。

AIVPが検証したいのは、

> AIにどこまで任せ、どこから人間へ戻すべきか

というAI-native software deliveryにおけるControl Problemです。

---

## 2. 背景

Coding Agentのコード生成能力が高まるほど、今後は「コードを書く速度」だけではなく、

- Review
- Verification
- Risk Assessment
- Repair Loop
- Human Escalation
- Resource Control

が重要になると考えました。

AIが大量のコードを生成できても、人間がすべてのDiffを従来通り確認するのであれば、Review側が新しいボトルネックになります。

一方、

「AIが書いたコードを別のAIにレビューさせればよい」

だけでは十分とは限りません。

Model同士が異なるSpecificationを重視したり、コードのCorrectnessとChange Riskを異なる観点で評価したりする可能性があるためです。

そこでAIVPでは、Generator・Reviewer・Deterministic Gate・Humanの責務を分離し、最終的なWorkflow制御を非AIのOrchestratorへ持たせました。

---

## 3. 検証範囲

### 対象

- AIによるコード生成
- AIによるbounded repair
- Unit Test等のDeterministic Verification
- Independent AI Review
- Rule-based Risk Assessment
- AI-based Risk Assessment
- Human Escalation
- Resource Budget
- Experiment Logging

### 対象外

以下はMVP v1では扱いません。

- Autonomous Merge
- Production Deployment
- GitHub App Integration
- Multi-repository orchestration
- Kubernetes / EKS Integration
- Argo CD Integration
- RAG
- Parallel Multi-Agent execution
- Production-grade Security Boundary
- Formal Correctness Guarantee

AIVP-MVP v1 は Production-ready Platform ではなく、ローカル実験用Prototypeです。

---

## 4. アーキテクチャ

    Human
      |
      v
    Task / Acceptance Criteria
      |
      v
    Python Orchestrator
      |
      +--> Codex CLI
      |      Generator / Fixer
      |
      +--> Deterministic Verification
      |      Unit Test / External Gate
      |
      +--> Claude Code
      |      Independent Reviewer
      |
      +--> Risk Evaluation
      |      Rule Engine
      |      Codex Risk Judge
      |      Claude Risk Assessment
      |
      v
    AUTO_FINISHED
    or
    HUMAN_REQUIRED

### Python Orchestrator

OrchestratorはAI Agentではありません。

以下をdeterministicに制御します。

- 実行順序
- Fix iteration
- Resource Budget
- Verification Loop
- Risk Aggregation
- Exit Condition
- Human Gate生成

### Codex CLI

Codexには以下を担当させます。

- Initial Implementation
- Bounded Fix
- Final Risk Judgment

### Claude Code

Claude Codeは独立Reviewerとして使用します。

- Semantic Review
- Blocking Finding検出
- Independent Risk Assessment

GeneratorとReviewerを同一モデル・同一役割にせず、独立性を持たせています。

### Deterministic Gate

AI判断だけに依存しないため、

- Unit Test
- External Contract Gate
- Explicit Pass / Fail

を使用します。

### Human

以下の場合は人間へEscalateします。

- High-risk Change
- Specification Ambiguity
- Model / Policy Disagreement
- Blocking Finding
- Fix Budget Exhaustion

---

## 5. Resource Budget

AI Agentに無制限の試行を許可しないため、MVP v1では以下を上限としました。

| Resource | Limit |
|---|---:|
| Fix iterations | 2 |
| Codex calls / run | 4 |
| Claude calls / run | 3 |
| AI call timeout | 300 sec |
| Whole run timeout | 900 sec |
| Concurrent runs | 1 |

終了条件はAI自身ではなくOrchestratorが決定します。

---

## 6. Risk Engine

### High-risk Pathの例

    auth/**
    security/**
    db/migrations/**
    infra/iam/**
    .github/workflows/**

### Dangerous Patternの例

    DROP TABLE
    DELETE FROM
    AdministratorAccess
    iam:PassRole

### Risk Source

MVP v1では以下の3系統を利用します。

1. Rule Engine
2. Codex Risk Judge
3. Claude Risk Assessment

以下のような場合はHuman Gateへ送ります。

- Rule = HIGH
- Codex = HIGH
- Claude = HIGH
- Large Disagreement
- Blocking Findingが残存
- Fix Budget Exhaustion

---

## 7. 実験一覧

| Run | Scenario | Result | Elapsed | Codex Calls | Claude Calls | Fix Iterations |
|---|---|---|---:|---:|---:|---:|
| #001 | Low-risk Username Normalization | AUTO_FINISHED | 62.845 sec | 2 | 1 | 0 |
| #002 | Medium Business Logic | AUTO_FINISHED | 60.858 sec | 2 | 1 | 0 |
| #002F-1 | Specification / Contract Conflict | HUMAN_REQUIRED | 136.032 sec | 3 | 1 | 2 |
| #002F-2 | Controlled Fault Injection | AUTO_FINISHED | 94.381 sec | 3 | 1 | 1 |
| #003 | High-risk Authorization Change | HUMAN_REQUIRED | 50.638 sec | 2 | 1 | 0 |

---

## 8. Run #001 — Low-risk Change

### 目的

Username Normalizationを変更し、

    "  Alice  "

を、

    "alice"

へ正規化する変更を実装しました。

### 結果

- Deterministic Test：PASS
- Claude Blocking Finding：なし
- Final Risk：LOW
- Fix Iteration：0
- Result：AUTO_FINISHED

### Metrics

    elapsed_seconds: 62.845
    codex_calls: 2
    claude_calls: 1
    fix_iterations: 0
    final_risk: low

Low-risk Changeに対する基本的な自動完了経路を確認しました。

---

## 9. Run #002 — Medium Business Logic

### 目的

Pricing Logicに以下を実装しました。

- Member：10% Discount
- Maximum Discount：2,000
- Non-member：変更なし
- Negative subtotal：Error

### 結果

- Deterministic Test：PASS
- Claude Blocking Finding：なし
- Final Risk：LOW
- Fix Iteration：0
- Result：AUTO_FINISHED

### Metrics

    elapsed_seconds: 60.858
    codex_calls: 2
    claude_calls: 1
    fix_iterations: 0
    final_risk: low

単純な文字列処理だけでなく、Business Logicを含む変更でも自動経路が成立することを確認しました。

---

## 10. Run #002F-1 — Specification / Contract Conflict

### このExperimentの位置付け

このRunは、

「Codexがバグを修正できなかった」

ことを示す実験ではありません。

TaskとExternal Contractの間に矛盾を持たせ、一意な正解が存在しない状態でAIVPが安全に停止できるかを確認しました。

### Conflict

Task：

    Member receives 10% discount

External Contract：

    No discount below 1000

### Round 0

- Unit Test：PASS
- Contract Gate：FAIL

CodexはContractを満たすためにThresholdを追加しました。

### Round 1

- Unit Test：PASS
- Contract Gate：PASS

しかしClaudeは、

    threshold >= 1000 is an unauthorized business rule

としてMAJOR Findingを返しました。

CodexはTaskの明示仕様を優先し、Thresholdを削除しました。

### Round 2

- Unit Test：PASS
- Contract Gate：FAIL

ここでFix Budgetを使い切ったため、

    HUMAN_REQUIRED

として終了しました。

### Metrics

    elapsed_seconds: 136.032
    codex_calls: 3
    claude_calls: 1
    fix_iterations: 2
    final_risk: unknown

### 観察

問題はAIの能力不足ではなく、Specification Source同士のConflictです。

このような場合にAIへ無理やり一方を選ばせるのではなく、Human DecisionへEscalateすることを確認しました。

---

## 11. Run #002F-2 — Controlled Fault Injection

### このExperimentの位置付け

このFaultはProduction環境で自然発生したBugではありません。

Detect → Repair → Re-verifyの制御ループを検証するために、一度だけ意図的にDefectを注入しました。

### Flow

    Generate
      |
      v
    Unit Test PASS
      |
      v
    Controlled Fault Injection
      |
      v
    Gate FAIL
      |
      v
    Codex Repair
      |
      v
    Unit Test PASS
      |
      v
    Controlled Gate PASS
      |
      v
    Claude Review
      |
      v
    Risk Evaluation
      |
      v
    AUTO_FINISHED

### 結果

- Fault Detection：成功
- Autonomous Repair：実行
- Re-verification：PASS
- Blocking Finding：なし
- Final Risk：LOW
- Result：AUTO_FINISHED

### Metrics

    elapsed_seconds: 94.381
    codex_calls: 3
    claude_calls: 1
    fix_iterations: 1
    final_risk: low

### 観察

Bounded Autonomous Repair Loopが実際に成立することを確認しました。

---

## 12. Run #003 — High-risk Authorization Change

### 目的

Authorization Policyを変更し、

    admin

に加えて、

    superadmin

にもAdmin AreaへのAccessを許可しました。

### Verification

- Deterministic Test：PASS
- Claude Finding：なし

コードのCorrectnessだけを見れば問題ありませんでした。

### Risk Assessment

    Rule Engine : HIGH
    Codex       : HIGH
    Claude      : LOW

Claudeは、

- 変更が小さい
- Pure Function
- Test済み
- Blocking Findingなし

という観点からLOWと評価しました。

一方、

Rule Engineは `auth/**` をHigh-risk Pathと判定し、CodexはAuthorization Policyそのものの変更としてHIGHと評価しました。

### Result

    HUMAN_REQUIRED

### Metrics

    elapsed_seconds: 50.638
    codex_calls: 2
    claude_calls: 1
    fix_iterations: 0
    final_risk: high

---

## 13. 主要な発見 — Code Correctness != Change Risk

Run #003から得られた重要な観察は、

    Code Correctness
    !=
    Change Risk

という点です。

変更が、

- Syntactically Correct
- Logically Correct
- Fully Tested
- Reviewer Findingなし

であっても、自動承認してよいとは限りません。

特に、

- Authorization
- IAM
- Database Migration
- CI/CD Workflow
- Security Policy

のような変更では、Correctnessとは別にRiskを考える必要があります。

---

## 14. Human Gate

AIVPでは `HUMAN_REQUIRED` をFailureとして扱いません。

安全なTermination Pathの一つです。

Human Review Packetには、

- Deterministic Verification Result
- AI Findings
- Risk Assessment
- Model Disagreement
- Escalation Reason

を含めます。

人間は最終的に、

    Accept
    Request Manual Change
    Reject

などの判断を行います。

---

## 15. Limitations

### Small Experimental Repository

実験は小規模なPython Repositoryで実施しています。

Large MonorepoやComplex Dependency Graphでの性能は未検証です。

### Model Dependence

Generator / Reviewer / Risk Judgeの結果はModel Behaviorへ依存します。

### No Production Integration

GitHub Merge、CI/CD、Deployment、Production Environmentとは統合していません。

### No Security Boundary

AIVP自体をSecurity Sandboxとして利用することはできません。

### Controlled Fault

Run #002F-2のFaultは人工的に注入したものです。

### Limited Risk Taxonomy

v1では主に、

    LOW
    MEDIUM
    HIGH

という一次元のRisk Classificationを使用しています。

---

## 16. v1.1に向けたRisk Modelの改善案

Run #003では、CodexとClaudeが異なる観点からRiskを評価していました。

そのため、Riskを単一のLOW / MEDIUM / HIGHへ押し込むのではなく、例えば以下のDimensionへ分解する余地があります。

- Correctness Risk
- Security Sensitivity
- Business Impact
- Blast Radius
- Reversibility

例：

    Correctness Risk     : LOW
    Security Sensitivity : HIGH
    Business Impact      : MEDIUM
    Blast Radius         : MEDIUM
    Reversibility        : HIGH

これにより、Model間のDifferenceを単純な「意見の不一致」ではなく、異なるRisk Dimensionの評価として扱える可能性があります。

---

## 17. Reproducibility

公開Repositoryには以下を含めます。

- Orchestrator
- Example Configuration
- Task Definitions
- External Contract Gate
- Controlled Fault Gate

Fault Experiment用Configでは、公開用Placeholderとして、

    /path/to/AIVP_MVP_v1

を使用しています。

再現する場合は、Clone先のAbsolute Pathへ置換してください。

以下は公開Repositoryには含めません。

- Raw Experiment Logs
- Local Machine Paths
- Session Metadata
- Private Runtime Data

---

## 18. 今回分かったこと

5つのExperimentから、少なくともMVPレベルでは以下を確認できました。

1. Low / Medium-risk Changeは自動完了できる
2. Temporary FaultはBounded Repairできる
3. Specification ConflictはAIだけで決定すべきではない
4. Code CorrectnessとChange Riskは別概念である
5. Human GateはFailureではなくSafe Termination Pathとして設計できる
6. AI Agent自身ではなくControllerがResourceとExit Conditionを管理することに意味がある

---

## 19. 結論

AIVP-MVP v1では、

    Generate
      ↓
    Verify
      ↓
    Repair
      ↓
    Re-verify
      ↓
    Independent Review
      ↓
    Risk Assessment
      ↓
    AUTO_FINISHED
    or
    HUMAN_REQUIRED

というBounded Workflowを構築しました。

本MVPはProduction-ready Platformではありません。

一方で、

> AIにコードを書かせることだけではなく、  
> どこまでAIに任せ、どこから人間へ戻すのか

というAI-native software deliveryのControl Problemを検証する小規模Experimentとして、当初の目的は達成できたと考えています。

---

## Status

    AIVP-MVP v1
    Experiment Complete
    Public Experimental Release
