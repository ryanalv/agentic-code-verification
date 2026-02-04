from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ReviewResult:
    """Entidade que representa o resultado de uma revisão técnica."""
    approved: bool
    score: float
    feedback: str
    hallucinations: List[str] = field(default_factory=list)
    quality_feedback: str = ""
