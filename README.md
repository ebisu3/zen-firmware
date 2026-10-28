# ZEN ファームウェア

ZEN用のファームウェアを作成するためのリポジトリです。

GitHubに慣れていない方でも、リポジトリをforkして、Keymap Editorでキー配置を編集し、GitHub Actionsでファームウェアを作成できます。

## はじめに読むもの

詳しい手順は以下のガイドにまとめています。

- [ZEN ファームウェア案内](https://e24-gh.github.io/zen/firmware.html)

## このリポジトリでできること

- ZEN用ファームウェアのビルド
- Keymap Editorでのキー配置編集
- GitHub ActionsからのUF2ファイル作成

## 作成されるファームウェア

GitHub Actionsで作成される `firmware` というzipファイルには、以下のUF2ファイルが含まれます。

- 設定リセット用UF2ファイル
- `zen_right_trackball_pmw3610_central.uf2`
- `zen_right_trackball_pmw3610_central_usb_logging.uf2`（右手のUSBログ診断用。電池の測定値を5秒ごとに出力）
- `zen_right_trackball_paw3222_central.uf2`
- `zen_right_trackpad_central.uf2`
- `zen_left_peripheral.uf2`
- `zen_left_peripheral_usb_logging.uf2`（左手のUSBログ診断用。電池の測定値を5秒ごとに出力）
- `zen_left_trackball_pmw3610_peripheral.uf2`
- `zen_left_trackball_paw3222_peripheral.uf2`
- `zen_left_trackpad_peripheral.uf2`
- `zen_right_trackball_pmw3610_peripheral.uf2`（Prospector接続用の右手子機）
- `zen_prospector_central.uf2`（標準Prospector用の親機）
- `settings_reset-seeeduino_xiao_ble-zmk.uf2`（Prospectorの保存設定リセット用）

通常使用するファイルは以下です。

- 右手: `zen_right_trackball_pmw3610_central.uf2`
- 左手: `zen_left_peripheral.uf2`

右手にPAW3222やTrackpadを使用する場合は、それぞれ名前に対応する右手用UF2ファイルを使用します。

左手にTrackballやTrackpadを使用する場合は、以下を使用します。

- 左手PMW3610: `zen_left_trackball_pmw3610_peripheral.uf2`
- 左手PAW3222: `zen_left_trackball_paw3222_peripheral.uf2`
- 左手Trackpad: `zen_left_trackpad_peripheral.uf2`

標準構成では、右手はPMW3610用、左手は `zen_left_peripheral.uf2` を使用してください。

無線接続がうまくいかない場合や、別のファームウェアから切り替える場合は、先に設定リセット用のUF2ファイルを使います。

## 最短手順

1. このリポジトリを自分のGitHubアカウントへforkします
2. Keymap Editorでforkしたリポジトリを開きます
3. 必要に応じてキー配置を編集して保存します
4. GitHub Actionsでファームウェアがbuildされるのを待ちます
5. `firmware` のダウンロードボタンからzipファイルをダウンロードします
6. 右手と左手の対応コントローラへUF2ファイルを書き込みます
7. PCやMacの接続設定から `ZEN` として接続します

## 対象

このリポジトリは、PMW3610トラックボール版を標準構成とし、左右それぞれでPAW3222およびTrackpadを使用する構成にも対応しています。

## Prospectorを使う構成

標準Prospector（Seeed Studio XIAO nRF52840と1.69インチ画面）向けに、
Prospectorを親機、左右のZENを子機にする追加構成を用意しています。
通常の右手親機版も引き続きビルドされます。

```text
左ZEN ── Bluetooth ──┐
                     ├── Prospector ── USB ── PC / Mac
右ZEN ── Bluetooth ──┘
```

Prospector接続で今回対象とするのは、右PMW3610トラックボールと左通常キーの構成です。
右手の400CPI、方向変換、マウスレイヤー・スクロール設定は通常版と揃えています。
マウスレイヤーの切り替えはProspector側で行います。
画面はレイヤー番号、左右の電池残量・接続状態を表示し、初期設定は固定輝度50です。
照度センサーとタッチ操作は使用しません。

### 使用するファイル

| 書き込み先 | 通常動作用UF2 | 保存設定リセット用UF2 |
| --- | --- | --- |
| Prospector / XIAO nRF52840 | `zen_prospector_central.uf2` | `settings_reset-seeeduino_xiao_ble-zmk.uf2` |
| 右ZEN / BMP Boost | `zen_right_trackball_pmw3610_peripheral.uf2` | `settings_reset-bmp_boost-zmk.uf2` |
| 左ZEN / BMP Boost | `zen_left_peripheral.uf2` | `settings_reset-bmp_boost-zmk.uf2` |

右手のファイル名は`peripheral`で終わるものを選んでください。
`zen_right_trackball_pmw3610_central.uf2`は従来の、右手をPCへ直接接続する構成用です。

### 初回の書き込みとペアリング

切り替える前に、通常構成で左右のキー入力と電池駆動が安定していることを確認してください。
**保存設定をリセットすると、Bluetoothのペアリング情報とZMK Studioで保存した設定が消えます。**
必要なキーマップは先に控えてください。

1. 3台とも保存設定をリセットします。この時点では他のZENを電源OFFにして、
   意図せず再ペアリングしないようにします。
   - **BMP Boost：** 電源OFFでUSB接続して`BLEMICROPRO`ドライブへBMP用リセットUF2をコピーします。
     USBを外し、電源ONにしてからUSBをつなぎ、リセット用ファームを実行します。
     UF2をコピーしただけで、電源OFFのままにしないでください。
   - **Prospector：** USB接続してリセットボタンを素早く2回押し、出現したドライブへXIAO用リセットUF2をコピーします。
     コピー後に再起動したリセット用ファームを実行させます。
2. 3台のリセットが終わったら、表の通常動作用UF2を書き込みます。
   BMP BoostはUSBを外して電源OFFからブートローダーへ入り直し、
   XIAOはリセットボタンを2回押してブートローダーへ入り直します。
3. ProspectorをUSBでPC / Macへ接続し、親機を起動します。
4. **左ZENだけを先に電源ON**にして、画面で左側の接続を確認します。
5. 次に右ZENを電源ONにして、右側の接続を確認します。
   電池表示の左右は子機がペアリングされた順なので、左→右の順で接続してください。
6. 左右の全列、トラックボールの上下左右、マウスクリック、スクロールを確認します。

PC / MacとはUSBで接続するため、この構成でZENをMacのBluetooth設定からペアリングする必要はありません。
ZMK Studioでキー配置を編集するときは、USB接続したProspectorを選択してください。

この構成では、左右のZENはProspectorを介して入力を送ります。
Prospectorを外すと、右手子機のUSBをPCへつないでも通常の右手親機版の代わりにはなりません。

### 従来の右手親機構成へ戻す

1. 左右の保存設定を、上記のBMP Boost用リセット手順で初期化します。
   Prospectorも別の構成で再利用する場合は、その保存設定も初期化してください。
2. 右手に`zen_right_trackball_pmw3610_central.uf2`、左手に`zen_left_peripheral.uf2`を書き込みます。
3. ProspectorをPCから外し、右手をUSB接続して左右の入力を確認します。
4. MacとBluetooth接続する場合は、Macに残った以前のZENの登録を削除してから再ペアリングします。

Prospector構成のファームのビルド・設定確認と実機確認は別です。
実機では、画面表示、電池駆動、無線再接続、キーとトラックボール、Studio接続の確認が必要です。

参考：

- [Prospector公式モジュール](https://github.com/carrefinho/prospector-zmk-module)
- [ZMK公式のドングル構成](https://zmk.dev/docs/hardware-integration/dongle)

## うまく接続できない場合

無線接続がうまくいかない場合は、以下を試してください。

1. PCやMacの接続設定から `ZEN` を削除します
2. 設定リセット用のUF2ファイルを書き込みます
3. USBを外します
4. ZENの電源を入れます
5. もう一度通常ファームウェアを書き込みます
6. 接続設定から `ZEN` を再接続します

## ライセンス

MIT
