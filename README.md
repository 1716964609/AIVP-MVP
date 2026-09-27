# AIVP-MVP

**AI-native Change Verification Platform — MVP v1**

AI Coding Agent が生成・修正するコード変更を、単に「生成できたか」ではなく、

> **安全に検証し、自動修正し、必要な場合だけ人間へ判断を戻せるか**

という観点から検証するために作成した Engineering Experiment / MVP です。

Codex CLI を Generator / Fixer、Claude Code を独立 Reviewer として利用し、Python 製の deterministic orchestrator が、AI・テスト・リスク判定・Human Gate を制御します。

---

## 1. 背景

AI Coding Agent によってコード生成速度が上がると、次のボトルネックはコードを書くことそのものではなくなります。

例えば、

- 生成コードの検証
- Code Review の負荷
- Test failure 後の修正
- 高リスク変更の判定
- AI が収束しない場合の停止条件
- 人間が介入すべき境界の定義

といった問題です。

単純に、

```text
AI generates code
        ↓
AI reviews code
```

とするだけでは不十分です。

Generator と Reviewer が同じ誤りを共有する可能性がありますし、テストが失敗したときに修正を無限に続ける危険もあります。

また、

> **コードとして正しい変更であっても、自動承認してよいとは限りません。**

Authorization、IAM、DB migration、CI/CD workflow などは、その代表例です。

そこで本MVPでは、

```text
Deterministic Verification
        +
Independent AI Review
        +
Risk Policy
        +
Human Escalation
```

を組み合わせました。

---

# 2. Architecture

```text
Human
  |
  | Task / Acceptance Criteria
  v
+----------------------------+
| Python Orchestrator        |
| Deterministic Controller   |
+----------------------------+
          |
          v
+----------------------------+
| Codex CLI                  |
| Generator / Fixer          |
+----------------------------+
          |
          v
+----------------------------+
| Deterministic Gates        |
| Test / Lint / Typecheck    |
+----------------------------+
          |
          | FAIL
          v
+----------------------------+
| Codex Fix                  |
+----------------------------+
          |
          | Re-verify
          +---------------------> Deterministic Gates

          |
          | PASS
          v
+----------------------------+
| Claude Code                |
| Independent Reviewer       |
+----------------------------+
          |
          v
+----------------------------+
| Risk Evaluation            |
| Rule + Codex + Claude      |
+----------------------------+
        /              \
       /                \
 LOW / MEDIUM        HIGH / CONFLICT
     |                     |
     v                     v
AUTO_FINISHED         HUMAN_REQUIRED
```

---

# 3. Core Design Principles

## 3.1 Generator と Reviewer を分離する

コード生成と意味的レビューを同じモデルだけで完結させません。

### Codex CLI

- Generator
- Fixer
- Final Risk Judge

### Claude Code

- Independent Semantic Reviewer

Generator と Reviewer を分離することで、一つのモデルだけに生成・修正・承認を集中させない構成にしています。

---

## 3.2 AI より先に Deterministic Gate を置く

機械的に判定できるものは、AIの判断より先に評価します。

例：

```text
compile
test
lint
typecheck
contract test
```

Verification が失敗した場合、そのfailure informationをCodexへ戻し、修正を試みます。

---

## 3.3 Fix Loop に Resource Budget を設定する

AI Agent が失敗し続けても無限に修正を繰り返さないよう、MVPでは明示的な上限を設定しています。

```text
Max Fix Iterations : 2
Codex Calls        : max 4 / run
Claude Calls       : max 3 / run
AI Timeout         : 300 sec / call
Whole Run Timeout  : 900 sec
Concurrent Runs    : 1
```

一定回数以内に収束しない場合、

```text
HUMAN_REQUIRED
```

として処理を停止します。

---

## 3.4 Code Correctness と Change Risk を分離する

コードが正しくても、その変更を自動承認してよいとは限りません。

MVPでは例えば以下を high-risk path として扱います。

```text
auth/**
security/**
db/migrations/**
infra/iam/**
.github/workflows/**
```

そのため、テストがすべてPASSしていても、変更対象によってはHuman Gateへ送られます。

---

# 4. Workflow

通常の実行フローは以下です。

```text
Task
 ↓
Generate
 ↓
Deterministic Verification
 ↓
FAIL
 ↓
Fix
 ↓
Re-verify
 ↓
PASS
 ↓
Independent AI Review
 ↓
Risk Evaluation
 ↓
AUTO_FINISHED
      or
HUMAN_REQUIRED
```

---

# 5. Experimental Results

MVP v1では、異なるsuccess / failure modeを確認するために5種類の実験を行いました。

| Run | Scenario | Result |
|---|---|---|
| #001 | Low-risk small change | `AUTO_FINISHED` |
| #002 | Business logic change | `AUTO_FINISHED` |
| #002F-1 | Specification / Contract conflict | `HUMAN_REQUIRED` |
| #002F-2 | Controlled Fault Injection | `FIX → AUTO_FINISHED` |
| #003 | High-risk authorization change | `HUMAN_REQUIRED` |

---

## Run #001 — Low-risk Change

Username normalization の小規模変更。

```text
elapsed         62.845 sec
codex calls     2
claude calls    1
fix iterations  0
final risk      LOW
```

Deterministic Verification、AI Review、Risk Evaluationを通過し、

```text
AUTO_FINISHED
```

となりました。

---

## Run #002 — Business Logic Change

Member discount と maximum discount cap を追加する変更。

```text
elapsed         60.858 sec
codex calls     2
claude calls    1
fix iterations  0
final risk      LOW
```

Generatorが初回でAcceptance Criteriaを満たし、Independent Reviewerにもblocking findingはありませんでした。

---

## Run #002F-1 — Specification / Contract Conflict

Task specification と downstream contract が矛盾するケースを作成しました。

一方では、

```text
Members receive a 10% discount
```

という仕様。

一方では、

```text
subtotal < 1000 の場合は discount を適用しない
```

という外部contract。

その結果、

```text
Deterministic Gate
        ↕
Task Specification
```

の間で変更が収束しませんでした。

Resource Budget到達後、

```text
fix iterations = 2
HUMAN_REQUIRED
```

として停止しました。

この実験では、

> **AIだけでは正解を一意に決められない場合、無限修正せず人間へ判断を戻す**

というSafety Mechanismを確認しました。

---

## Run #002F-2 — Controlled Fault Injection / Autonomous Repair

Fix Loop自体を検証するため、Controlled Fault Injectionを行いました。

初回verification時に意図的なfailureを発生させています。

```text
Generate
 ↓
Unit Test PASS
 ↓
Controlled Gate FAIL
 ↓
Codex Fix
 ↓
Re-verify PASS
 ↓
Claude Review
 ↓
Risk Evaluation
 ↓
AUTO_FINISHED
```

結果：

```text
elapsed         94.381 sec
codex calls     3
claude calls    1
fix iterations  1
final risk      LOW
```

この実験によって、

```text
Detect
 ↓
Repair
 ↓
Re-verify
 ↓
Converge
```

という自動修正ループが実際に動作することを確認しました。

なお、このfailureは自然発生したバグではなく、Fix LoopのMechanicsを検証するための **Controlled Fault Injection** です。

---

## Run #003 — High-risk Authorization Change

Authorization policyを変更し、

```text
admin
superadmin
```

の双方にadmin accessを許可する変更を実施しました。

Deterministic VerificationはPASS。

Claude Reviewerにもblocking findingはありませんでした。

一方でRisk Evaluationでは、

```text
Rule Engine : HIGH
Codex Risk  : HIGH
Claude Risk : LOW
```

となりました。

Rule Engineは、

```text
auth/access.py
```

が、

```text
auth/**
```

に該当するためHIGHと判定。

Codexもauthorization policyの変更自体をhigh riskと判定しました。

最終的に、

```text
Aggregate Risk : HIGH
Large Disagreement : true
HUMAN_REQUIRED
```

となりました。

この実験から、

> **Code Correctness ≠ Change Risk**

であることを確認しました。

コードとして正しいことと、自動承認してよいことは別問題です。

---

# 6. Human Review

自動処理を継続できない場合、OrchestratorはHuman Review Packetを生成します。

例：

```text
Human Review Required

Task
Deterministic Verification
Blocking AI Findings
Risk Evaluation
Changed Files
Resource Usage

Human Decision:
[ ] Accept change
[ ] Request another manual change
[ ] Reject / revert
```

狙いは、人間がすべての変更を最初からレビューすることではありません。

人間には、

> **AI / Policyだけでは安全に判断できない変更**

を集中して判断してもらいます。

---

# 7. Risk Model

現在のMVPでは、

```text
LOW
MEDIUM
HIGH
```

という単一のrisk scoreを使用しています。

しかしRun #003では、

```text
Claude : LOW
Codex  : HIGH
Rule   : HIGH
```

と評価が分かれました。

これは、各Reviewerが異なる種類のRiskを見ている可能性があります。

例えば、

```text
Correctness Risk
Security Sensitivity
Business Impact
Blast Radius
Reversibility
```

です。

そのため次のバージョンでは、Riskを単一scalarではなくmulti-dimensional modelとして扱うことが設計候補になります。

---

# 8. Repository Structure

```text
AIVP-MVP/
├── aivp_orchestrator_v1.py
├── README.md
├── aivp-config.example.json
├── task.example.json
│
├── config/
│   ├── aivp-config.json
│   ├── aivp-config-fault.json
│   ├── aivp-config-fault2.json
│   ├── task-low.json
│   ├── task-medium.json
│   ├── task-high.json
│   ├── task-fault-002f.json
│   └── task-fault-002f2.json
│
└── scripts/
    ├── pricing_contract_gate.py
    └── pricing_fault_once_gate.py
```

Raw experiment logsはローカル保存とし、repositoryには含めていません。

---

# 9. Requirements

本MVPでは以下を利用します。

```text
Python 3
Git
Codex CLI
Claude Code
```

Codex CLI / Claude Codeは事前にauthentication済みである必要があります。

---

# 10. Example

```bash
python3 aivp_orchestrator_v1.py \
  --repo /path/to/target-repository \
  --task ./config/task-low.json \
  --config ./config/aivp-config.json \
  --reports ./reports \
  --yes
```

Runごとに以下のようなartifactが生成されます。

```text
metrics.json
events.json
status.json
final.diff.txt
rule-risk.json
codex-risk.json
claude-review-*.json
human-review.md
```

---

# 11. Scope

本repositoryは、

> **Engineering Experiment / MVP**

です。

Production-readyなAI delivery platformではありません。

現在MVPのscope外としている主な論点：

- GitHub Pull Request integration
- Multi-repository orchestration
- Parallel execution
- Secrets management
- Model outage handling
- Flaky test handling
- Prompt injection mitigation
- Cost accounting
- Artifact signing
- Fine-grained permission boundary
- Production observability
- Large-scale organizational adoption
- Platform adoption metrics

---

# 12. What I Learned

本MVPから得られた主要な知見：

1. AI-generated codeでもDeterministic Verificationは重要
2. GeneratorとReviewerは分離した方がよい
3. AI Fix Loopには明示的なResource Budgetが必要
4. Specification ConflictはAIだけで解決すべきではない
5. Code CorrectnessとChange Riskは別概念
6. High-risk changeは、実装品質に問題がなくてもHuman Gateへ送る必要がある
7. Riskは単一scoreではなくmulti-dimensional modelへ発展させる余地がある

---

# 13. Status

```text
AIVP-MVP v1
Status: Experiment Complete
```

MVPとして予定していた主要なsuccess / failure pathの検証は完了しました。

この段階では機能追加そのものより、

```text
Hypothesis
 ↓
Implementation
 ↓
Experiment
 ↓
Evidence
 ↓
Learning
 ↓
Next Design
```

というEngineering Cycleの整理を重視しています。
