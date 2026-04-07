"""Markdown形式のレポート生成"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .prompts import REPORT_HEADER_TEMPLATE
from .schemas import AnalysisResult, Severity


def _severity_icon(severity: Severity) -> str:
    """重大度に応じたマーカーを返す。"""
    return {
        Severity.CRITICAL: "[!!!]",
        Severity.HIGH: "[!!]",
        Severity.MEDIUM: "[!]",
        Severity.LOW: "[-]",
    }.get(severity, "[-]")


def generate_report(
    result: AnalysisResult,
    source_filename: str,
    model: str,
) -> str:
    """AnalysisResultからMarkdownレポートを生成する。"""
    lines: list[str] = []

    # ヘッダー
    lines.append(REPORT_HEADER_TEMPLATE.format(
        filename=source_filename,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        model=model,
    ))

    # 1. システム概要
    ext = result.extraction
    lines.append("## 1. システム概要\n")
    if ext.title:
        lines.append(f"**図面タイトル**: {ext.title}\n")
    if ext.drawing_number:
        lines.append(f"**図面番号**: {ext.drawing_number}\n")
    if ext.voltage_levels:
        lines.append(f"**電圧レベル**: {', '.join(ext.voltage_levels)}\n")
    if ext.supply_type:
        lines.append(f"**受電方式**: {ext.supply_type}\n")
    if ext.topology_summary:
        lines.append(f"\n{ext.topology_summary}\n")

    # 2. 機器一覧
    lines.append("\n## 2. 機器一覧\n")
    if ext.components:
        lines.append("| No. | ID | 種別 | 名称 | 定格 | 電圧 | 相数 | 接続先 | 備考 |")
        lines.append("|-----|----|------|------|------|------|------|--------|------|")
        for i, comp in enumerate(ext.components, 1):
            lines.append(
                f"| {i} "
                f"| {comp.id} "
                f"| {comp.type.value} "
                f"| {comp.name or '-'} "
                f"| {comp.rating or '-'} "
                f"| {comp.voltage or '-'} "
                f"| {comp.phases or '-'} "
                f"| {', '.join(comp.connections_to) if comp.connections_to else '-'} "
                f"| {comp.notes or '-'} |"
            )
    else:
        lines.append("機器情報を抽出できませんでした。\n")

    # 注記
    if ext.annotations:
        lines.append("\n### 図面注記\n")
        for ann in ext.annotations:
            lines.append(f"- {ann}")

    # 3. 指摘事項
    lines.append("\n## 3. 指摘事項\n")
    if result.findings:
        # 重大度順にソート
        severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}
        sorted_findings = sorted(result.findings, key=lambda f: severity_order.get(f.severity, 9))

        for i, finding in enumerate(sorted_findings, 1):
            icon = _severity_icon(finding.severity)
            lines.append(f"### {i}. {icon} {finding.title}")
            lines.append(f"- **重大度**: {finding.severity.value}")
            lines.append(f"- **カテゴリ**: {finding.category.value}")
            lines.append(f"- **内容**: {finding.description}")
            lines.append(f"- **推奨対応**: {finding.recommendation}")
            if finding.reference:
                lines.append(f"- **参照基準**: {finding.reference}")
            lines.append("")
    else:
        lines.append("特筆すべき指摘事項はありませんでした。\n")

    # 4. 検証チェックリスト
    lines.append("## 4. 検証チェックリスト\n")
    if result.checklist:
        current_category = None
        for item in result.checklist:
            if item.category != current_category:
                current_category = item.category
                lines.append(f"\n### {current_category}\n")
            priority_mark = _severity_icon(item.priority)
            lines.append(f"- [ ] {priority_mark} {item.item}")
        lines.append("")
    else:
        lines.append("チェックリストを生成できませんでした。\n")

    # 5. 総合評価
    lines.append("## 5. 総合評価\n")
    if result.overall_assessment:
        lines.append(result.overall_assessment)
    else:
        lines.append("総合評価を生成できませんでした。")

    lines.append("\n---\n*本レポートはAIによる自動分析結果です。最終判断は有資格の電気技術者が行ってください。*\n")

    return "\n".join(lines)


def save_report(
    result: AnalysisResult,
    source_filename: str,
    model: str,
    output_dir: str | Path = "sld-reports",
) -> Path:
    """レポートを生成してファイルに保存する。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_text = generate_report(result, source_filename, model)

    stem = Path(source_filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"analysis_{stem}_{timestamp}.md"

    output_path.write_text(report_text, encoding="utf-8")
    return output_path
