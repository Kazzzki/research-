"""単線結線図の構造化データモデル"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """電気機器の種別"""
    POWER_SOURCE = "power_source"           # 受電点（商用電力）
    GENERATOR = "generator"                 # 発電機
    TRANSFORMER = "transformer"             # 変圧器（TR）
    CIRCUIT_BREAKER = "circuit_breaker"     # 遮断器（CB/VCB/ACB）
    MCCB = "mccb"                           # 配線用遮断器
    ELCB = "elcb"                           # 漏電遮断器
    FUSE = "fuse"                           # ヒューズ
    DISCONNECT_SWITCH = "disconnect_switch" # 断路器（DS）
    LOAD_BREAK_SWITCH = "load_break_switch" # 負荷開閉器（LBS）
    BUS = "bus"                             # 母線
    PANEL = "panel"                         # 分電盤
    MOTOR = "motor"                         # 電動機
    LOAD = "load"                           # 負荷（一般）
    CAPACITOR = "capacitor"                 # 進相コンデンサ（SC）
    REACTOR = "reactor"                     # リアクトル（SR）
    CT = "ct"                               # 変流器
    VT = "vt"                               # 計器用変圧器
    ZCT = "zct"                             # 零相変流器
    METER = "meter"                         # 計器（Wh/A/V）
    ARRESTER = "arrester"                   # 避雷器（LA）
    GROUNDING = "grounding"                 # 接地
    UPS = "ups"                             # 無停電電源装置
    ATS = "ats"                             # 自動切替開閉器
    OTHER = "other"                         # その他


class Severity(str, Enum):
    """指摘の重大度"""
    CRITICAL = "Critical"   # 即時対応が必要（安全に関わる）
    HIGH = "High"           # 重要な問題
    MEDIUM = "Medium"       # 改善が望ましい
    LOW = "Low"             # 軽微・参考情報


class FindingCategory(str, Enum):
    """指摘のカテゴリ"""
    CAPACITY = "capacity"               # 容量・負荷
    PROTECTION = "protection"           # 保護協調
    CODE_VIOLATION = "code_violation"    # 法規・基準違反
    GROUNDING = "grounding"             # 接地
    REDUNDANCY = "redundancy"           # 冗長性
    LABELING = "labeling"               # 表記・ラベル
    POWER_QUALITY = "power_quality"     # 電力品質
    SAFETY = "safety"                   # 安全性
    OTHER = "other"


class ElectricalComponent(BaseModel):
    """図面上の電気機器"""
    id: str = Field(description="機器の識別子（例: TR1, CB-01）")
    type: ComponentType = Field(description="機器の種別")
    name: Optional[str] = Field(default=None, description="機器名称")
    rating: Optional[str] = Field(default=None, description="定格（例: 500kVA, 100A, 200AF/150AT）")
    voltage: Optional[str] = Field(default=None, description="電圧（例: 6.6kV/210V）")
    phases: Optional[int] = Field(default=None, description="相数（1 or 3）")
    capacity_kw: Optional[float] = Field(default=None, description="容量 [kW]")
    connections_to: list[str] = Field(default_factory=list, description="接続先の機器ID")
    notes: Optional[str] = Field(default=None, description="備考")


class DiagramExtraction(BaseModel):
    """図面から抽出した構成情報"""
    title: Optional[str] = Field(default=None, description="図面タイトル")
    drawing_number: Optional[str] = Field(default=None, description="図面番号")
    voltage_levels: list[str] = Field(default_factory=list, description="使用電圧レベル（例: ['6.6kV', '210V']）")
    supply_type: Optional[str] = Field(default=None, description="受電方式（1回線受電/2回線受電/ループ等）")
    components: list[ElectricalComponent] = Field(default_factory=list, description="検出した全機器")
    topology_summary: Optional[str] = Field(default=None, description="系統構成の概要")
    annotations: list[str] = Field(default_factory=list, description="図面上の注記・凡例")


class Finding(BaseModel):
    """分析で検出した指摘事項"""
    severity: Severity
    category: FindingCategory
    title: str = Field(description="指摘の見出し")
    description: str = Field(description="詳細説明")
    recommendation: str = Field(description="推奨対応")
    reference: Optional[str] = Field(default=None, description="参照基準（例: 内線規程 3105-1）")


class CheckItem(BaseModel):
    """検証チェックリスト項目"""
    category: str
    item: str
    status: str = Field(default="未確認", description="確認状況")
    priority: Severity = Field(default=Severity.MEDIUM)


class AnalysisResult(BaseModel):
    """分析結果の全体"""
    extraction: DiagramExtraction
    findings: list[Finding] = Field(default_factory=list)
    checklist: list[CheckItem] = Field(default_factory=list)
    overall_assessment: Optional[str] = Field(default=None, description="総合評価")
