# RVCIMの実行可能性を高めるための改訂草案

作成日: 2026-09-04

状態: 当時の議論用草案。以下の未実装表記は作成時点のもの。F0のまま。

調査対象: `1ac0349baedde12c0ea97c16379322660b109b15`

後続の実装と検証は [v0.3結果](FEASIBILITY_V03_RESULTS.ja.md)、
[v0.4結果](SUSTAINED_V04_RESULTS.ja.md)、
[実データ会計](POWER_ACCOUNTING_RESULTS.ja.md) を参照。
ローカルbranch: `agent/feasibility-research-plan`

## 1. 改訂の中心

RVCIMを「望ましい統治原則＋警報指標」から、
**観測できる証拠を用いて、誰が、どの資源で、いつまでに、何を実行し、
失敗時にはどう戻すかを示す条件付きの意思決定手続**へ進める。

核となる洞察――「まだ安全に見えることと、制動可能であることは違う」――は残す。
変更したいのは、制動余裕のスカラー値を実行可能な制動策の代わりにしないこと。

- 正のCRは、十分な制動効果・予算・権限・権利保障を証明しない。
- 負のCRは、そのモデルと応答集合で時間順序を保証できないという結果であり、世界の不可逆性の証明ではない。
- 観測不足は危険確定でも安全確定でもない。
- 計算上の実行可能性、権限上の実行可能性、現実の効果を別々に検証する。

`make verify`は調査時に47テスト、smoke、receipt、5出力のbyte replayを通過した。
この結果はリリースの検証契約の通過であって、以下のモデル妥当性の問題を否定しない。

## 2. 既にあるものと、今回足すもの

原論文には既に事前授権、六機能分離、異議申立て、補償、解除、F0–F3の階梯がある。
「監査を追加する」「安全性を重視する」だけでは新しい改良にならない。

| 原論文の要素 | 実行可能にするための追加仕様 |
|---|---|
| 観測とモデル集合 | 観測者、単位、欠測期限、較正根拠、共通誤差、モデル採否の記録 |
| CRによる警報 | 行動別の応答時間、実効能力、適用範囲、余裕の区間、推定不能の明示 |
| 実行可能方策の存在 | 具体的な候補方策と制約判定の記録。探索失敗と不可能性を区別 |
| 事前授権・機能分離 | 実在のowner、委任範囲、資格期限、利益相反、取消権限 |
| 利得反転 | 被規制者だけでなく監督者の誘因、支援原資、予算制約、実測した選択 |
| 緊急・解除規則 | 受付先、審査期限、暫定状態、解除証拠、期限切れ後の従来手続 |
| 複数armの比較 | 同じ観測・能力条件でのtrigger比較と、実際の費用を合わせた比較 |

根拠: [論文の制度設計](../paper/nashs_cage_rvcim_v0_2.tex#L718)、
[研究仮説と階梯](../paper/nashs_cage_rvcim_v0_2.tex#L955)。
GitHubの行番号リンクは調査commitを固定して使うこと。

## 3. 現行コードで確認した、先に直すべき点

### 3.1 評価用の真値が閉ループへ戻る

`run_episode`では `hidden_reserve → truth_mode → false_positive/false_negative`
の結果が、backlash、trust、institution、次のpolicy schedulingへ戻る。
該当箇所: `simulation/rvcim_sim.py:1037–1084` および `947–950`。

真の境界を知らない設計である一方、誤警報の「正解」は即座に社会反応へ伝わる。
別の観測経路を明示してモデル化するなら正当化し得るが、
現状では、その経路・遅延・誤差がない。

再現確認: master seed 7、episode 3の環境を固定し、true_boundaryだけ0.87と1.13に変更。
t=38ではpressure、observation、estimated CR、requested/active modeが完全一致し、
両方とも不可逆域の外にあるのにtrustが分岐した。t=39にはpolicyも分岐した。

**改訂:** controller、社会主体の観測、評価器を分離する。
真値はplantと評価器に閉じ、社会反応はそれぞれの観測履歴から生じさせる。
同じ許可された情報履歴と同じ乱数なら同じ判断になるという不変条件をテストする。
真の物理状態が実際に観測を変えることまで禁止するものではない。

### 3.2 「回復可能性」が到達可能性計算になっていない

`estimate_reserve`の `recoverability` は
`logistic((reserve + 0.25 * exit_estimate) / 4.5)`。
これは滑らかなproxyであり、論文の「実行可能な方策の下で安全域へ戻る最悪モデル確率」
を計算していない（コード615–629、論文531–544）。

**改訂:** 当面はproxyをproxyと明示する。
その後、小さな有限モデルで、具体的な行動列・資源・遅延を使う到達可能性判定を別に実装する。
較正なしに0–1の値を「回復確率」と呼ばない。

### 3.3 物理応答遅延が実際のplantにない

`biophysical_response_lag` は推定応答時間に加算されるが、
`update_world`のpolicy効果には遅延キューがない
（コード596、882–895）。

同一state/actionでlag=0と100を比べると、plantの全更新状態が完全一致した。
推定応答時間だけが2.94336から114.94336へ変化した。

**改訂:** 要求、承認、作動、実効化を別の状態として保持し、
plantの効果発現にも遅延を反映する。推定だけ遅くなるケースと、
物理効果そのものが遅くなるケースを分けて試験する。

### 3.4 4群比較はtrigger効果の識別になっていない

既定のarmはcoupling、audit、anti_capture、justice_buffer、速度、
モデル数、policy/support targetsなどを同時に変更する（コード223–295）。
財政・人員・監査工数の明示的なbudgetはない。

**改訂:** 「同じ能力でtriggerだけ変更」と
「費用と能力のtrade-offを含む制度bundle比較」を別の実験にする。
同じArmSpecは同じ能力パラメータであって、実測した同一予算ではない。

### 3.5 反復する戦略的captureの耐性はまだ試していない

captureは固定されたactor profileと現在のpolicyから生成される。
攻撃の学習・攻撃経路の選択・攻撃費用の上限はモデル化されていない。
防御係数を上げれば有効captureが下がる式の確認だけでは、
適応的な攻撃者にも防御が持続することの検証にならない
（コード689–696、752–760、論文961–963）。

**改訂:** 資源上限を持つ攻撃者に、metric操作・遅延・規則変更などの
明示的な選択肢を与える。固定攻撃と適応攻撃を分け、
防御側の資源と監督者自身の逸脱誘因も含めて比較する。
最初から高性能な学習器は必要なく、小さな行動集合の列挙でもよい。

## 4. 小さな反証実験の結果

既定config、master seed 7、64 episodes。
各episodeの環境・乱数を共通にし、
`full_rvcim`の全ArmSpecを保ったまま `trigger`だけを
`reserve`から `threshold`へ変更した。
既定nominal armも参考として同じ環境で実行した。

| 条件 | 不可逆域への進入 |
|---|---:|
| 既定nominal bundle | 64 / 64 |
| 既定full RVCIM（reserve trigger） | 40 / 64 |
| fullと同じ能力設定＋threshold trigger | 20 / 64 |

paired比較ではreserve側だけ成功2、threshold側だけ成功22、同結果40。
rootと独立subtaskで同じ結果を再現した。

また既定full reserveのnormal要求は **0 / 4,608 steps**。
モデル境界の幅0.24が固定uncertainty thresholdの0.18を常に超えるため、
この設定では正常時へ戻る要求が生成されない。
committed referenceには、全期間の `min_hidden_cr > 0` にもかかわらず
不可逆域へ入ったfull RVCIM episodeが2件ある。
CRの圧力境界proxyが全てのbiosphere/制度/justice制約を表していないことと整合する。

**解釈の限界:** 既存toyの診断であり、post-hocな1設定の比較。
thresholdの一般的優位、reserve理論の反証、政策効果の推定ではない。
真値フィードバック等の既存モデル問題を残したままの結果である。
次の実験では修正済みモデルと未使用のseed・条件で再評価する。

再実行コード（repo root、Python 3.10以上、ファイル書込みなし）:

```python
import dataclasses
from pathlib import Path
from simulation import rvcim_sim as sim

cfg = sim.load_config(Path("simulation/configs/minimal.json"))
full = sim.ARM_SPECS["full_rvcim"]
arms = {
    "nominal": sim.ARM_SPECS["nominal_trigger"],
    "reserve": full,
    "matched_threshold": dataclasses.replace(full, trigger="threshold"),
}
counts = dict.fromkeys(arms, 0)
wins = losses = ties = normal = steps = 0
for episode in range(64):
    env = sim.sample_environment(
        cfg, sim.stable_seed(7, "environment", episode), episode
    )
    result = {}
    for name, arm in arms.items():
        outcome, trace = sim.run_episode(cfg, arm, env, collect_trace=True)
        result[name] = outcome.irreversible_entry
        counts[name] += outcome.irreversible_entry
        if name == "reserve":
            normal += sum(row.requested_mode == 0 for row in trace)
            steps += len(trace)
    a, b = result["reserve"], result["matched_threshold"]
    wins += a < b
    losses += a > b
    ties += a == b
print(counts)
print(wins, losses, ties, normal, steps)
```

機械可読の結果は [feasibility_probe_results.json](feasibility_probe_results.json)。

## 5. 理論改訂案: 行動別の条件付き実行可能性

### 5.1 観測可能な情報から始める

意思決定時点の情報を `I_t` とする。
含めるのは観測履歴、発行済みの権限、利用可能な資源、pending action、
モデル・規則版、証拠の有効期限。隠れた真値は含めない。

状態・モデルの候補集合 `B_t` をこの情報から作る。
集合の外に真のモデルがある可能性や共通誤差を、
モデル数が多いという理由だけで消さない。

### 5.2 時間余裕を行動に結び付ける

行動候補aに対して

```text
CR_t(a) = L_exit(I_t, baseline) - U_effect(I_t, a)
```

とする。baselineには、既に進行中の行動と何もしない場合の動態も含める。
`U_effect`は命令を出すまでではなく、必要な効果を確認するまでの時間。
観測・審査・予算執行・作動・物理応答を含む。
baselineと行動の効果が途中から相互作用する場合、差だけではなく全軌道を評価する。

簡単な反例: 境界まで10日、装置の起動まで2日でも、
装置の能力が不足して悪化が止まらなければ、CR=8日は安全の証明にならない。

### 5.3 時間順序についてだけ言える条件付き命題

同じ情報I_tの下、全モデルについて

```text
P(T_exit < L | I_t) <= alpha_exit
P(T_effect > U | I_t) <= alpha_effect
U < L
```

が成立するなら、union boundから

```text
P(T_exit <= T_effect | I_t) <= alpha_exit + alpha_effect
```

となる。二つの時間の独立性は不要。
ただし、これは時間順序だけの主張であり、効果の十分性・権利保障・その後の安全性は別である。
数値を分位点として出力するだけでは上の被覆条件は成立しない。
真のモデルの集合外リスクもこの式で自動的には扱われない。
繰返し判断の全期間保証には別のrisk accountingが必要。

### 5.4 「具体策と根拠」を返す

各候補について、有限horizon内の軌道と次を一緒に提出する。

1. 観測証拠と、その鮮度・不確かさ・適用範囲。
2. 起動から実効化までのaction sequenceと各時刻の制約。
3. 人員・予算・監査・支援・復旧費用の上限と原資。
4. 実行権限、委任期限、別担当の異議審査、利益相反。
5. 守るべき非代替的な権利・分配制約。平均値で相殺しない。
6. 停止・代替策・解除の条件と、適用期間末の状態。

これは**条件付き実行可能性記録**であって、
署名や権限の真正性、現実の安全性を自己証明するcertificateではない。
有限個のシナリオでPASSしただけなら「そのシナリオ集合で制約を満たした」とのみ言う。
horizon外の継続安全性には、別途backup方策や終端条件の正当化が必要。

判定はmodeとは別軸にする。

| 判定 | 意味 |
|---|---|
| `model_feasible` | 指定した情報・モデル・期間・制約の中で具体的な候補が成立 |
| `insufficient_evidence` | 欠測、古い観測、較正不足、権限・費用の未確認等で判定不能 |
| `no_admissible_candidate` | 調べた候補に適格なものがない。世界全体で不可能とは言わない |
| `known_constraint_violation` | 特定の候補が明示的な権利・資源・安全条件に違反 |

`model_feasible`だけで実行しない。
実行側には別途、現時点で有効な授権と範囲チェックを要求する。
UNKNOWNを非常権限の自動付与にも、危険な現状の放置の免罪符にも使わない。
不明時は未承認行動を控え、事前承認された限定措置と期限付きの人間の判断へ戻す。

## 6. 最小の運用実証（対象は仮置き）

最初の候補は、内部向けソフトウェア／AI機能の可逆な変更管理。
観測→判断→実行→復旧の時刻と工数を取れるためである。
これは気候統治の検証ではなく、制御と制度の接続部分の工学実証である。
適用対象は利用者と相談して確定する。

### 範囲

- 一つの非重要な内部機能、同意した参加者、承認済みの非機密データに限定。
- 初期はshadow。提案だけ記録し、実システムの操作権限を持たせない。
- データ削除、外部送信、恒久的schema変更、金銭・人事・医療等の重要判断は対象外。
- 限定実操作への移行は別の承認事項。この草案は承認を与えない。

### 作成する7つの仕様

| 仕様 | 最小内容 |
|---|---|
| pilot charter | 対象、授権、参加者、rights floor、予算、終了条件 |
| role/authority matrix | 実行者、取消者、監査者、異議担当、利益相反 |
| indicator dictionary | 観測値、単位、データ源、有効期限、欠測時の扱い |
| action state machine | 提案、審査、pending、active、停止、解除 |
| decision event log | evidence ID、規則版、候補、理由、各時刻、費用 |
| appeal/release register | 申立て、受付期限、暫定状態、解除根拠、補償 |
| preregistered evaluation | 比較条件、成功・失敗基準、hold-out、分析手順 |

被規制者には期限のある審査、復旧支援、早期申告への不利益禁止を用意する。
監督側にも担当時間と予算、誤停止の訂正経路を用意する。
停止件数・承認件数を成果指標にしない。
これらが「得」になるかは、費用表だけではなく行動と負担の実測で判断する。
制度を採用・維持する主体自身の参加条件を満たせなければ、導入案を改める。

### 終了・解除

- 範囲逸脱、権限不備、復旧失敗、重大な予期せぬ不利益、負担上限超過でpilotを止める。
- 欠測ではモデル判断を棄権。無期限凍結にも、自動承認にも移らない。
- 暫定権限の期限切れは、権限終了と承認済みの従来手続への復帰。
- 異議申立てそのものを罰しない。
- shadowでは因果的な利得反転や安全性優越は測れない。測れるのは観測・提案・工数・応答可能性。

## 7. 実装・検証を分けた進め方

### 第1段階: 実験の妥当性を直す

- 真値とcontrollerの境界を分離し、情報不変性テストを追加。
- 作動・効果発現の遅延をplantへ実装。
- recoverability proxyの名称と主張を修正。
- uncertaintyによる永久precautionと解除規則の相互作用を試験。
- 旧参照結果を上書きして隠さず、別model versionの結果として保存。

### 第2段階: RVCIMに有利でない比較を先に定める

- 同じ観測、初期状態、能力、乱数でtriggerだけを入れ替える。
- 次に監査・支援・速度を一つずつ変えるablationを行う。
- 明示した費用モデルの下で同一budgetのtrade-offを比較する。
- 単純閾値＋hysteresisも基準に含める。
- 初期化用seed/条件と最終評価用seed/条件を分け、閾値を後から合わせない。
- closer boundary、共通誤差、観測欠落、作動失敗、長遅延、資源枯渇、解除不能を含める。
- 不可逆進入だけでなく、誤停止、非常状態の継続、負担集中、費用、見逃し、復旧を併記する。
- 「勝った」だけでなく、どの条件で優位が消えるかを主要結果として保存する。

### 第3段階: 小さな有限モデルで実行可能性記録を計算する

物理状態、pending action、実効能力、budgetを含む小さな状態空間を使う。
既知の正解を列挙できるtoyで、solver結果と全探索を比較する。
観測不能・予算不足・能力不足・正のCRでも危険な例・可逆な代替案を固定テストにする。
この段階でも現実の安全証明にはならない。

### 第4段階: 狭い領域のshadowへ

owner、データ、権限、費用、異議、解除、評価計画を確定してから開始する。
較正・識別・held-out妥当性がないままF1を名乗らない。
shadowの運用確認だけでF2/F3の要件を満たしたことにしない。

**最初の実装単位としては第1段階を推奨する。**
証明を増やす前に、理論が実際には持てない情報や資源を使っていない実験系を作る。
この草案ではrelease本体・論文PDF・参照fixtureを変更していない。

## 8. 既存研究との接続と、新規性の置き所

安全フィルタは、提案された入力が制約内で使えるかを検査し、
必要に応じて安全側の入力へ変更するという構成を持つ。
この「警報値だけでなく候補行動を検査する」構成は参考になる。
物理制御での保証を、制度や社会へ移せるという主張ではない。
[Wabersich & Zeilinger, predictive safety filter](https://arxiv.org/abs/1812.05506)

DAPPは、単一の遠い目標だけでなく、行動の系列、切替条件、
monitoring、費用・便益、将来の選択肢をまとめて設計する。
RVCIMも具体的なpathwayを要求する形にすると接続しやすい。
[Deltares, Dynamic Adaptive Policy Pathways](https://www.deltares.nl/en/expertise/areas-of-expertise/sea-level-rise/dynamic-adaptive-policy-pathways)

従って、新規性を「制約を使う」「監査する」「適応的に変える」だけに置かない。
RVCIM固有の検証対象を、
**制動余裕の維持と、制度の捕捉・遅延・利得反転を、
同じ観測可能な閉ループで扱うと何が追加で可能になるか**
へ絞る。この追加価値は今後の比較実験で検証する仮説である。
