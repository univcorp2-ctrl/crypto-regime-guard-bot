# Strategy Selection Guide

ユーザーは `config/*.toml` の `strategy` を変えるだけでロジックを選べます。

```toml
[bot]
strategy = "regime_guard"
```

## 使える戦略

### `regime_guard`

デフォルト。EMA、Donchian breakout、ATR shock filter、range efficiency、z-scoreを組み合わせます。

- 上昇トレンドかつブレイクアウトなら買い。
- 急変・下落トレンドではノーポジ。
- レンジでは小さな平均回帰だけ許可。

### `ema_cross`

短期EMAが長期EMAを上回ったら買い、下回ったら売り。

向いている相場:

- きれいな上昇トレンド
- BTC/ETHなど流動性の高い銘柄

弱点:

- レンジ相場で往復ビンタになりやすい

### `donchian_trend`

過去高値を上抜けたら買い、過去安値を下抜けたら売り。

向いている相場:

- 大きなトレンド発生時
- ニュースや資金流入で継続上昇する局面

弱点:

- フェイクブレイクに弱い

### `rsi_reversion`

RSIが売られすぎなら買い、回復したら売り。

向いている相場:

- レンジ相場
- 下げすぎから反発しやすい大型銘柄

弱点:

- 本格下落トレンドでは危険。ATR shock filterで強制退出します。

### `bollinger_breakout`

ボリンジャーバンド上限をトレンド方向に抜けたら買い、中央線割れで退出。

向いている相場:

- ボラティリティ拡大
- 価格発見が続く局面

弱点:

- 髭だけの上抜けや急反落に弱い

## パラメータ変更例

```bash
python -m crypto_regime_guard.cli backtest data/sample_btc_usdt_1h.csv \
  --strategy ema_cross \
  --strategy-param fast_ema=12 \
  --strategy-param slow_ema=48
```

設定ファイルで指定する場合:

```toml
[bot]
strategy = "ema_cross"

[strategy_params]
fast_ema = 12
slow_ema = 48
target_position = 1.0
```

## どれが勝てそうか

万能戦略はありません。現実的には、以下の順で検証します。

1. BTC/ETHなど流動性の高い銘柄で複数年バックテスト。
2. 上昇・下落・レンジ・急落を含める。
3. 最適化しすぎない。
4. 紙取引でバックテストと実時間の差を確認。
5. 小額ライブで注文・手数料・スリッページを確認。

このリポの初期推奨は `regime_guard` です。理由は、トレンド・レンジ・ショックを分けて、勝てない局面で取引しない設計にしているためです。
