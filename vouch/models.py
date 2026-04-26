from dataclasses import dataclass, field
from typing import List, Literal, Optional


Risk = Literal["high", "med", "low"]
Confidence = Literal["confident", "uncertain", "guess"]
Decision = Literal["accept", "reject"]


@dataclass
class RawHunk:
    id: str
    file: str
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    header: str
    body: str


@dataclass
class SemanticHunk:
    id: str
    intent: str
    files: List[str]
    raw_hunk_ids: List[str]
    merged_diff: str


@dataclass
class Analysis:
    id: str
    risk: Risk
    risk_reason: str
    confidence: Confidence
    summary_ko: str


@dataclass
class ReviewItem:
    semantic: SemanticHunk
    analysis: Analysis
    decision: Optional[Decision] = None
    reject_reason: Optional[str] = None
