"""単線結線図の分析エンジン

Claude Vision APIを使い、3段階のパイプラインで図面を解析する。
Phase 1: 機器・構成の抽出
Phase 2: 問題点・確認事項の分析
Phase 3: レポート生成
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Optional

from anthropic import Anthropic

from .prompts import ANALYSIS_PROMPT, EXTRACTION_PROMPT
from .schemas import AnalysisResult, CheckItem, DiagramExtraction, Finding


def load_image_as_base64(file_path: Path) -> tuple[str, str]:
    """画像ファイルをBase64エンコードし、media_typeとともに返す。

    大きな画像は長辺1568pxにリサイズする（Claude Vision最適サイズ）。
    """
    suffix = file_path.suffix.lower()
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    if suffix not in media_type_map:
        raise ValueError(f"未対応の画像形式: {suffix} (対応形式: {', '.join(media_type_map.keys())})")

    media_type = media_type_map[suffix]

    # Pillowでリサイズ
    try:
        from PIL import Image
        import io

        img = Image.open(file_path)
        max_dim = 1568
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buffer = io.BytesIO()
        fmt = "PNG" if suffix == ".png" else "JPEG"
        img.save(buffer, format=fmt)
        image_data = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    except ImportError:
        # Pillow未インストール時はそのまま読み込み
        raw = file_path.read_bytes()
        image_data = base64.standard_b64encode(raw).decode("utf-8")

    return image_data, media_type


def extract_json_from_response(text: str) -> dict:
    """Claude応答テキストからJSON部分を抽出してパースする。"""
    # ```json ... ``` ブロックを探す
    match = re.search(r"```json\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # ```なしのJSONブロックを探す
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))

    raise ValueError("応答からJSONを抽出できませんでした")


class SLDAnalyzer:
    """単線結線図分析パイプライン"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def _call_vision(self, image_b64: str, media_type: str, prompt: str) -> str:
        """Claude Vision APIを呼び出し、テキスト応答を返す。"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        return response.content[0].text

    def phase1_extract(self, image_b64: str, media_type: str) -> DiagramExtraction:
        """Phase 1: 図面から機器・構成を抽出する。"""
        print("  [Phase 1] 図面の読み取り・機器抽出中...")
        raw_response = self._call_vision(image_b64, media_type, EXTRACTION_PROMPT)

        try:
            data = extract_json_from_response(raw_response)
            extraction = DiagramExtraction(**data)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  警告: JSON解析に失敗、テキスト応答を直接使用します: {e}")
            extraction = DiagramExtraction(
                topology_summary=raw_response,
                annotations=["※ 構造化抽出に失敗。テキスト応答を参照してください。"],
            )
            extraction._raw_response = raw_response

        print(f"  [Phase 1] 完了: {len(extraction.components)}個の機器を検出")
        return extraction

    def phase2_analyze(
        self, image_b64: str, media_type: str, extraction: DiagramExtraction
    ) -> tuple[list[Finding], list[CheckItem], str]:
        """Phase 2: 抽出結果に基づき問題点を分析する。"""
        print("  [Phase 2] 問題点・確認事項の分析中...")

        extraction_json = extraction.model_dump_json(indent=2, exclude_none=True)
        analysis_prompt = ANALYSIS_PROMPT.format(extraction_json=extraction_json)

        raw_response = self._call_vision(image_b64, media_type, analysis_prompt)

        try:
            data = extract_json_from_response(raw_response)
            findings = [Finding(**f) for f in data.get("findings", [])]
            checklist = [CheckItem(**c) for c in data.get("checklist", [])]
            overall = data.get("overall_assessment", "")
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  警告: JSON解析に失敗: {e}")
            findings = []
            checklist = []
            overall = raw_response

        print(f"  [Phase 2] 完了: {len(findings)}件の指摘、{len(checklist)}件のチェック項目")
        return findings, checklist, overall

    def analyze(self, file_path: str | Path) -> AnalysisResult:
        """図面ファイルを分析し、結果を返す。"""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        print(f"分析開始: {file_path.name}")
        print("-" * 50)

        # 画像読み込み
        image_b64, media_type = load_image_as_base64(file_path)

        # Phase 1: 抽出
        extraction = self.phase1_extract(image_b64, media_type)

        # Phase 2: 分析
        findings, checklist, overall = self.phase2_analyze(
            image_b64, media_type, extraction
        )

        print("-" * 50)
        print("分析完了")

        return AnalysisResult(
            extraction=extraction,
            findings=findings,
            checklist=checklist,
            overall_assessment=overall,
        )
