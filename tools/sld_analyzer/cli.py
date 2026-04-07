"""単線結線図分析ツール - コマンドラインインターフェース

Usage:
    python -m tools.sld_analyzer.cli <input_file> [options]

Examples:
    python -m tools.sld_analyzer.cli diagram.png
    python -m tools.sld_analyzer.cli diagram.jpg --output-dir ./reports
    python -m tools.sld_analyzer.cli diagram.png --model claude-opus-4-20250514
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import SLDAnalyzer
from .report import save_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="単線結線図（SLD）分析ツール - 電気図面をAIで自動解析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
対応形式:
  画像: PNG, JPG/JPEG, GIF, WebP

出力:
  Markdown形式の分析レポート（機器一覧・指摘事項・チェックリスト）
        """,
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="分析対象の単線結線図ファイルパス",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="sld-reports",
        help="レポート出力ディレクトリ（デフォルト: sld-reports/）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="使用するClaudeモデル（デフォルト: claude-sonnet-4-20250514）",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Anthropic APIキー（未指定時は環境変数 ANTHROPIC_API_KEY を使用）",
    )

    args = parser.parse_args(argv)
    input_path = Path(args.input_file)

    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {input_path}", file=sys.stderr)
        return 1

    supported_ext = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    if input_path.suffix.lower() not in supported_ext:
        print(
            f"エラー: 未対応のファイル形式: {input_path.suffix}\n"
            f"対応形式: {', '.join(sorted(supported_ext))}",
            file=sys.stderr,
        )
        return 1

    try:
        analyzer = SLDAnalyzer(api_key=args.api_key, model=args.model)
        result = analyzer.analyze(input_path)
        output_path = save_report(
            result=result,
            source_filename=input_path.name,
            model=args.model,
            output_dir=args.output_dir,
        )
        print(f"\nレポートを保存しました: {output_path}")
        return 0

    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
