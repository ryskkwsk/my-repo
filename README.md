# FX 自動売買ツール（OANDA v20 / デモ口座向け）

移動平均クロス戦略をベースにした、FX 自動売買のスターターキットです。
**バックテスト → デモ口座での自動売買** までを段階的に進められる構成になっています。

> ⚠️ **まずはデモ(practice)口座で。** 本番資金の運用は、デモで十分に検証してから。
> 自動売買は「戦略の良し悪し」より「壊れないコード」と「リスク管理」が9割です。

---

## 全体ロードマップ

```
Step 0  OANDAデモ口座開設 → APIトークン + アカウントID取得   ← 手動
Step 1  接続確認（残高・価格が取れる）                         scripts/check_connection.py
Step 2  ヒストリカルデータ取得                                 fx_bot/data/
Step 3  戦略ロジック（移動平均クロス）                         fx_bot/strategies/
Step 4  バックテストで検証 ★最重要                             fx_bot/backtest/
Step 5  デモ口座でライブ発注                                   fx_bot/live/
Step 6  リスク管理（損切り・ロット・自動停止）                 fx_bot/risk/
Step 7  常時稼働＋ログ/通知                                    （今後）
```

現状 **Step 1〜6 の土台が動く状態**です。トークンが無くても Step 3〜4
（戦略＋バックテスト）は合成データで動かして確認できます。

## セットアップ

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # もしくは: pip install -r requirements.txt
```

## Step 0: OANDA デモ口座（手動）

1. [OANDA](https://www.oanda.com/) でデモ口座を開設（無料・即日）
2. 管理画面の「APIアクセスの管理」から **パーソナルアクセストークン** を発行
3. **アカウントID**（例 `101-009-1234567-001`）を控える

```bash
cp .env.example .env
# .env を編集して OANDA_API_TOKEN と OANDA_ACCOUNT_ID を設定
```

> `.env` は `.gitignore` 済み。トークンは絶対にコミットしないこと。

## Step 1: 接続確認

```bash
python scripts/check_connection.py
```

口座残高と現在値が表示されれば成功。トークン未設定なら案内メッセージが出ます。

## Step 3〜4: バックテスト（トークン不要でも動作）

```bash
# トークンがあれば OANDA 実データ、無ければ合成データで実行
python -m fx_bot.backtest.run_backtest --instrument USD_JPY --fast 20 --slow 50

# 出力例:
# ===== バックテスト結果 =====
# 総リターン      : +X.XX%
# 勝率            : XX.X%
# プロフィットファクター: X.XX
# 最大ドローダウン: XX.XX%
```

主なオプション: `--granularity H1` `--count 3000` `--balance 1000000` `--spread-pips 0.8`

## Step 5: デモ口座でライブ運用

```bash
# まずは発注せずシグナルだけ確認（強く推奨）
python -m fx_bot.live.runner --dry-run

# 挙動に納得したらデモ発注（OANDA_ENV=practice のときのみ動作）
python -m fx_bot.live.runner --poll 60
```

## テスト

```bash
pytest
```

## ディレクトリ構成

```
fx_bot/
├── config/       設定（.env 読み込み）
├── instruments.py pip 計算などの共通ユーティリティ
├── data/         ヒストリカルデータ取得（OANDA / 合成フォールバック）
├── strategies/   戦略（base + 移動平均クロス。差し替え可能）
├── backtest/     バックテストエンジン + CLI
├── risk/         リスク管理（ロット計算・SL/TP・1日損失上限）
├── broker/       OANDA v20 API ラッパー
└── live/         デモ口座ライブ運用ループ
scripts/          接続確認などの実行スクリプト
tests/            pytest
```

## 設計上のポイント

- **未来を見ない**: バックテストは「バー i で判断、i+1 の始値で執行」。
- **戦略は差し替え可能**: `Strategy` を継承すれば同じ基盤で検証・運用できる。
- **リスク管理を独立層に**: ポジションサイズは常に「資金 × リスク% ÷ 損切り幅」。

## 今後の拡張候補

- 戦略追加（ボリンジャーバンド逆張り、ブレイクアウト）とパラメータ最適化
- ウォークフォワード検証（過学習の検出）
- ログ永続化・稼働監視・アラート通知（Slack / メール）
- 複数通貨ペア対応、口座通貨換算の厳密化

## 免責

本コードは学習・検証用です。自動売買には損失リスクが伴います。
本番運用は自己責任で、必ずデモで十分に検証してから行ってください。
