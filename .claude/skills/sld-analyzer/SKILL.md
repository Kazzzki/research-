---
name: sld-analyzer
user-invocable: true
description: |
  電気設備の単線結線図（SLD）を読み込み、系統構成の抽出・問題点の検出・
  検証チェックリストの生成を行う図面分析ツール。
  Use when asked to "単線結線図を分析して", "電気図面をチェックして",
  "SLDをレビューして", "結線図の問題点を洗い出して", "electrical diagram review".
  Args: <file_path> - 分析対象の単線結線図ファイルパス（画像添付時は省略可）
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
  - Agent
---

# 単線結線図（SLD）分析ツール v1

> **免責事項**: 本ツールはAIによるスクリーニングであり、有資格の電気技術者の判断を代替するものではありません。
> 最終的な設計判断は電気主任技術者等の有資格者が行ってください。

## 概要

電気設備の単線結線図（Single Line Diagram）画像を入力として受け取り、
Claude Vision APIの画像認識を活用して以下を自動実行する：

1. **機器・構成の抽出** - 変圧器、遮断器、母線、負荷等の識別
2. **問題点の分析** - 容量・保護協調・法規適合・安全性の観点
3. **レポート生成** - 指摘事項とチェックリストのMarkdown出力

## 使い方

### CLIとして実行

```bash
# リポジトリルートから
pip install -r tools/sld_analyzer/requirements.txt
python -m tools.sld_analyzer.cli <図面ファイル> [--output-dir sld-reports/] [--model claude-sonnet-4-20250514]
```

### Claude Code内で使用

ユーザーが単線結線図の画像ファイルを提供した場合：

1. ファイルをReadツールで読み込む（画像ファイルのマルチモーダル読み取り）
2. 以下の3段階パイプラインで分析を実行する

## Phase 1: 機器・構成の抽出

画像を読み取り、以下の電気機器を識別する（JIS C 0617準拠の図記号）：

| カテゴリ | 機器 |
|---------|------|
| 受電・電源 | 受電点、発電機（G）、UPS、ATS |
| 変圧器 | TR（単相/三相）、一次/二次電圧、容量[kVA] |
| 開閉・保護 | CB/VCB/ACB、MCCB、ELCB、DS、LBS、ヒューズ |
| 母線・配電 | 母線（Bus）、分電盤、フィーダ |
| 計測・保護 | CT、VT/PT、ZCT、保護継電器（OCR/GR/DGR/UVR） |
| 負荷 | 電動機（M）、一般負荷、コンデンサ（SC）、リアクトル（SR） |
| その他 | 避雷器（LA）、接地、電力量計 |

抽出結果は構造化して、各機器のID・種別・定格・電圧・接続先を記録する。

## Phase 2: 問題点分析

以下の8つの観点で図面を評価する：

### 2.1 容量・負荷 (capacity)
- 変圧器容量 vs 接続負荷の整合性（需要率考慮）
- 変圧器利用率: 80%超→警告、100%超→重大
- 電圧降下: 幹線2%以下、分岐3%以下、全体4%以下（内線規程）

### 2.2 保護協調 (protection)
- 全分岐回路の過電流保護装置の有無
- 上位CB > 下位CBの容量関係
- 遮断器の定格遮断容量 vs 想定短絡電流
- カスケード遮断の適切性

### 2.3 接地保護 (grounding)
- ELCB設置要否（水回り・屋外等）
- 接地種別の適切性（B種/C種/D種）
- ZCT設置位置

### 2.4 法規・基準 (code_violation)
- 電気設備技術基準（電技）
- 内線規程（JEAC 8001）
- 消防法（非常用電源・耐火配線）
- 建築基準法（非常照明・排煙）

### 2.5 冗長性・信頼性 (redundancy)
- 防災負荷の電源冗長性
- 単一障害点の有無
- 母線連絡遮断器
- 非常用発電機と切替方式

### 2.6 電力品質 (power_quality)
- 進相コンデンサ（力率改善）
- 高調波対策（直列リアクトル）
- 不平衡負荷

### 2.7 表記・ラベル (labeling)
- 機器定格の記載漏れ
- 配線サイズの記載
- 行先表示の明確さ

### 2.8 安全性 (safety)
- 主幹遮断器の設置
- 断路器操作手順の安全性
- 避雷器の設置（高圧受電時）

## Phase 3: レポート生成

Markdownレポートを生成し `sld-reports/` に保存する：

1. **システム概要** - 受電方式・電圧レベル・系統構成
2. **機器一覧** - テーブル形式
3. **指摘事項** - 重大度順（Critical > High > Medium > Low）
4. **検証チェックリスト** - カテゴリ別チェックボックス
5. **総合評価** - 全体所見

## Pythonモジュール構成

```
tools/sld_analyzer/
  __init__.py       # パッケージ定義
  __main__.py       # python -m 実行エントリ
  cli.py            # CLI引数解析
  analyzer.py       # 分析パイプライン（Claude Vision API）
  prompts.py        # プロンプトテンプレート（電気工学知識埋め込み）
  schemas.py        # Pydanticデータモデル
  report.py         # Markdownレポート生成
  requirements.txt  # 依存パッケージ
```
