from dataclasses import dataclass, field
from typing import List, Optional, Tuple

CLOCK_TOLERANCE_MS = 10_000
TICK_TOLERANCE = 200
TICKS_PER_SECOND = 20.0

MIN_PLAUSIBLE_TIME_MS = {
    "F7": 60_000,
    "M7": 60_000,
}
DEFAULT_MIN_PLAUSIBLE_TIME_MS = 30_000
MAX_NORMAL_SCORE_TOTAL = 305


@dataclass
class ScoreComponents:
    skill: int = 0
    explore: int = 0
    time: int = 0
    bonus: int = 0
    total: int = 0

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["ScoreComponents"]:
        if not isinstance(data, dict):
            return None
        return cls(
            skill=int(data.get("skill", 0) or 0),
            explore=int(data.get("explore", 0) or 0),
            time=int(data.get("time", 0) or 0),
            bonus=int(data.get("bonus", 0) or 0),
            total=int(data.get("total", 0) or 0),
        )

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "explore": self.explore,
            "time": self.time,
            "bonus": self.bonus,
            "total": self.total,
        }


@dataclass
class SoloClearEvidence:
    player: str = ""
    uuid: str = ""
    floor: str = ""
    time: str = ""
    secrets: int = 0
    puzzles: List[str] = field(default_factory=list)
    prince: bool = False
    mimic: bool = False
    needs_verification: bool = False

    scoreboard_lines: List[str] = field(default_factory=list)
    tablist_lines: List[str] = field(default_factory=list)
    score_components: Optional[ScoreComponents] = None
    dungeon_enter_tick: int = -1
    clear_trigger_tick: int = -1
    client_clock_enter: int = 0
    client_clock_clear: int = 0
    mojang_server_id: str = ""
    map_data: Optional[dict] = None

    @classmethod
    def from_request(cls, body: dict) -> "SoloClearEvidence":
        return cls(
            player=str(body.get("player", "")),
            uuid=str(body.get("uuid", "")),
            floor=str(body.get("floor", "")),
            time=str(body.get("time", "")),
            secrets=int(body.get("secrets", 0) or 0),
            puzzles=list(body.get("puzzles", []) or []),
            prince=bool(body.get("prince", False)),
            mimic=bool(body.get("mimic", False)),
            needs_verification=bool(body.get("needs_verification", False)),
            scoreboard_lines=list(body.get("scoreboard_lines", []) or []),
            tablist_lines=list(body.get("tablist_lines", []) or []),
            score_components=ScoreComponents.from_dict(body.get("score_components")),
            dungeon_enter_tick=int(body.get("dungeon_enter_tick", -1) or -1),
            clear_trigger_tick=int(body.get("clear_trigger_tick", -1) or -1),
            client_clock_enter=int(body.get("client_clock_enter", 0) or 0),
            client_clock_clear=int(body.get("client_clock_clear", 0) or 0),
            mojang_server_id=str(body.get("mojang_server_id", "")),
            map_data=body.get("map_data") or None,
        )

    def has_extended_evidence(self) -> bool:
        return bool(
            self.scoreboard_lines
            or self.tablist_lines
            or self.score_components
            or self.mojang_server_id
        )


@dataclass
class ValidationResult:
    passed: bool = True
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_outlier: bool = False

    def fail(self, reason: str) -> None:
        self.passed = False
        self.failures.append(reason)

    def warn(self, reason: str) -> None:
        self.warnings.append(reason)


def verify_score_formula(evidence: SoloClearEvidence) -> Tuple[bool, List[str]]:
    components = evidence.score_components
    if not components:
        return True, []
    expected = components.skill + components.explore + components.time + components.bonus
    if components.total != expected:
        return False, [
            f"score formula mismatch: total={components.total} != skill+explore+time+bonus={expected}"
        ]
    return True, []


def verify_clock_consistency(evidence: SoloClearEvidence, claimed_time_ms: int) -> Tuple[bool, List[str]]:
    failures: List[str] = []
    if claimed_time_ms < 0:
        return True, []
    if evidence.client_clock_enter > 0 and evidence.client_clock_clear > 0:
        wall_delta = evidence.client_clock_clear - evidence.client_clock_enter
        if wall_delta < claimed_time_ms - CLOCK_TOLERANCE_MS:
            failures.append(
                f"wall clock delta {wall_delta}ms shorter than claimed {claimed_time_ms}ms (-{CLOCK_TOLERANCE_MS}ms tol)"
            )
    if evidence.dungeon_enter_tick >= 0 and evidence.clear_trigger_tick >= 0:
        tick_delta = evidence.clear_trigger_tick - evidence.dungeon_enter_tick
        expected_ticks = claimed_time_ms / 1000.0 * TICKS_PER_SECOND
        if tick_delta < expected_ticks - TICK_TOLERANCE:
            failures.append(
                f"tick delta {tick_delta} shorter than expected {expected_ticks:.0f} (-{TICK_TOLERANCE} tol)"
            )
    return (not failures), failures


def verify_plausibility(evidence: SoloClearEvidence, claimed_time_ms: int) -> Tuple[bool, List[str]]:
    warnings: List[str] = []
    floor = evidence.floor.upper()
    floor_min = MIN_PLAUSIBLE_TIME_MS.get(floor, DEFAULT_MIN_PLAUSIBLE_TIME_MS)
    if 0 < claimed_time_ms < floor_min:
        warnings.append(
            f"claimed time {claimed_time_ms}ms below plausible floor for {floor} ({floor_min}ms)"
        )
    if evidence.score_components and evidence.score_components.total > MAX_NORMAL_SCORE_TOTAL:
        warnings.append(
            f"score total {evidence.score_components.total} exceeds normal max ({MAX_NORMAL_SCORE_TOTAL})"
        )
    return (not warnings), warnings


def validate(evidence: SoloClearEvidence, claimed_time_ms: int) -> ValidationResult:
    result = ValidationResult()

    ok, fails = verify_score_formula(evidence)
    if not ok:
        for f in fails:
            result.fail(f"score: {f}")

    ok, fails = verify_clock_consistency(evidence, claimed_time_ms)
    if not ok:
        for f in fails:
            result.fail(f"clock: {f}")

    ok, warns = verify_plausibility(evidence, claimed_time_ms)
    if not ok:
        result.is_outlier = True
        for w in warns:
            result.warn(f"plausibility: {w}")

    return result
