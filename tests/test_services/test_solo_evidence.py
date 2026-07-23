from services.solo_evidence import SoloClearEvidence, validate


def test_verify_solo_presence_valid():
    evidence = SoloClearEvidence(
        scoreboard_lines=["The Catacombs (F7)", "Time Elapsed: 03m 49s", "Solo"],
        tablist_lines=["[537] Mamadal", "Party (1)"],
    )
    result = validate(evidence, 229000)
    assert result.passed
    assert not result.failures


def test_verify_solo_presence_invalid_scoreboard():
    evidence = SoloClearEvidence(
        scoreboard_lines=["The Catacombs (F7)", "Time Elapsed: 04m 41s", "[B] Bubbleh DEAD"],
        tablist_lines=["[232] wtjwtj", "Party (1)"],
    )
    result = validate(evidence, 281000)
    assert not result.passed
    assert any("scoreboard lines do not contain Solo or Party (1)" in f for f in result.failures)
