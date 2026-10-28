# ZEN Prospector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan in the current session.

**Goal:** 標準Prospectorで左右ZENと右PMW3610を使う追加ファーム構成を用意し、通常構成とともにビルド検証する。

**Architecture:** ZMK v0.3-zenを維持し、Prospectorを親機、左右ZENを子機にする。右PMW3610の生入力を既存チャネル0で送り、親機で方向・レイヤー・スクロールを一度だけ処理する。左通常子機と物理レイアウトは再利用する。

**Tech Stack:** ZMK v0.3-zen / Zephyr 3.5、BMP Boost、Seeed XIAO nRF52840、Prospectorモジュール77a852293532879c992847e01db27abe4f94fa9f、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-10-28-zen-prospector-design.md`（ユーザー承認済み）

## Global Constraints

- 既存の通常版・診断版・他センサー版のビルドと動作設定を保つ。
- ZMKはE24-GHの`v0.3-zen`。分割子機の広告開始を再試行する修正を保持する。
- 右PMW3610は400CPI。方向は現行版と同じ。キー配線と割当は変えない。
- マウスレイヤー1の500ms維持、打鍵後200msの誤発動抑制、スクロールレイヤー4と現行倍率を親機側でも維持する。
- 初期版は固定輝度50。照度センサーとタッチには依存しない。
- USB Studioと画面の共存を検証する。入らない場合に黙って機能を落とさない。
- 実機の設定消去・書き込み・ペアリングは自動実行しない。
- 実機未確認の項目は未実施として報告する。

## Review Focus

- 同じ右入力へローカルと親機の両方で変換が適用され、90度補正やスクロール倍率が二重にならないこと。
- 全ての右端キーを含む共有マトリクスと物理レイアウトが通常版と一致し、右子機の列オフセット7が保たれること。
- 右子機に親機専用のStudio・電池取得設定が残らず、ドングルは子機2台を扱えること。
- Prospectorの画面・USB・StudioがRAMとスタックに収まり、BMP専用GPIO・電池ドライバーがドングルへ混入しないこと。
- リセット対象と左→右のペアリング順、保存設定の消去、通常版への復帰手順が実機のボード別に正しいこと。

---

### Task 1: Prospector用ファーム構成と移行手順を追加する

**Files:**
- Modify: `config/west.yml`, `build.yaml`
- Modify: `boards/shields/zen/Kconfig.shield`, `boards/shields/zen/Kconfig.defconfig`, `boards/shields/zen/zen.dtsi`
- Create: `boards/shields/zen/zen_transform.dtsi`, `boards/shields/zen/zen_dongle.overlay`, `boards/shields/zen/zen_dongle.conf`
- Create: `snippets/split-peripheral/snippet.yml`, `snippets/split-peripheral/split-peripheral.conf`
- Create: `snippets/input-split-listener-right-trackball-pmw3610/snippet.yml`, `snippets/input-split-listener-right-trackball-pmw3610/input-split-listener-right-trackball-pmw3610.overlay`
- Modify: `README.md`
- Test: 既存 `.github/workflows/build.yml` と、追加する `build.yaml` の構成。

**Interfaces:**
- Consumes: `zen_physical_layout`、`zen_transform`、`pointing_device`、`pointing_device_split`のチャネル0、`config/keymap.keymap`、既存の左右ビルド。
- Produces: `zen_dongle`、`split-peripheral`、`input-split-listener-right-trackball-pmw3610`。
- Artifacts: `zen_prospector_central.uf2`、`zen_right_trackball_pmw3610_peripheral.uf2`、`settings_reset-seeeduino_xiao_ble-zmk.uf2`。既存左通常版を使用する。

- [ ] **Step 1: 新構成のビルドケースを先に定義する。**

`build.yaml`に標準Prospector、右PMW子機、XIAO設定リセットの3構成を追加する。
実装前にGitHub Actionsで実行し、未定義の`zen_dongle`または`split-peripheral`を理由に失敗することを確認する。
これは実コンパイラーを使う構成統合テストであり、設定文字列をなぞるだけの単体テストは追加しない。

Run: `gh workflow run build.yml --repo ebisu3/zen-firmware --ref codex/add-prospector-dongle`
Expected: 新親機または右子機が未定義シールド/snippetでFAIL。既存版への変更はない。

- [ ] **Step 2: 共通レイアウトと依存を追加する。**

`zen_transform`を共通dtsiへ移し、従来のGPIOを含まないドングルoverlayから共有する。
Prospectorモジュールを指定コミットで追加する。既存のZMKとセンサー依存を変更しない。

Expected: 既存のマトリクス値・物理キー順が変わらず、ドングルはmock kscanを使用する。

- [ ] **Step 3: 右子機と親機の入力処理を追加する。**

右子機は既存`input-split`で生入力を送る。親機専用設定をsnippetで無効化する。
親機はチャネル0を受け、XY_SWAP、スクロール時XY_SWAP|Y_INVERT、倍率1/20、
レイヤー1・500ms・require-prior-idle-ms200を適用する。子機では入力リスナーを有効化しない。

Expected: 右子機はセンサーあり・親機役なし、ドングルは子機2台・右入力受信あり。

- [ ] **Step 4: 画面とUSB Studioを設定する。**

標準Prospector adapterをドングルに適用し、固定輝度50・照度センサー無効・USB Studioを設定する。
ドングルにBMP Boost専用の電池・起動トリガー設定を継承しない。

Expected: 画面とStudioが同一ファームで有効。RAM/FLASHのリンクが成功する。

- [ ] **Step 5: READMEの選択・移行・復帰手順を書く。**

3台で使うUF2を明示し、全台の保存設定消去、BMPとXIAOのリセット実行の違い、
左→右のペアリング、Prospectorなしでは入力できないこと、元の右親機への復帰を記す。
設定消去はペアリング情報とStudio設定を消すことを明記する。

- [ ] **Step 6: 全構成の実ビルドと生成設定を確認する。**

Run: `git diff --check`
Expected: PASS。

Run: `gh run view <green-run-id> --repo ebisu3/zen-firmware --json headSha,conclusion,jobs`
Expected: 対象コミットで既存10構成と追加3構成が全てsuccess。

生成DTS/KconfigでReview Focusの各項目を確認する。通常右・左は基準ビルドと共有変換を比較する。
ドングルの子機数2・画面・Studio・固定輝度、右子機のチャネル0・400CPI・列オフセット7・
ローカルリスナー無効を検証する。UF2ヘッダー・ブロック数・終端マジックとメモリー使用量を確認する。

- [ ] **Step 7: 全ブランチの独立レビューを行う。**

設計・本計画・Review Focus・生成設定・差分を新しいレビュアーに渡す。
重要指摘があれば再現と修正を行い、必要なビルドを再実行する。

- [ ] **Step 8: 結果を記録してファームを渡す。**

成功したCIのUF2をダウンロードし、右子機・Prospector親機・両ボードのリセットの場所を示す。
実機は未検証として残す。mainへのpush/merge、実機の設定消去は行わない。

**Commits:** 最初は追加ビルドケースと設計・計画をコミットしてREDを確認する。
次に実装とREADMEをまとめてコミットしてGREENを確認する。修正が必要なら対象を絞った追加コミットにする。

**Completion command:** 台帳の検証スクリプトから`gh run view`のSHA・全job結果と、生成UF2の検査結果を確認する。
実機確認は完了条件に混ぜず、未実施として報告する。
