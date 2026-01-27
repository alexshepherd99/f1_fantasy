import pytest

from linear.strategy_odds import odds_to_pct


def test_odds_to_pct():
    assert odds_to_pct("100/1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("100:1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("100-1") == pytest.approx(0.01, abs=0.001)
    assert odds_to_pct("10/2") == pytest.approx(0.2, abs=0.001)
    assert odds_to_pct("9/4") == pytest.approx(0.4444, abs=0.0001)

    with pytest.raises(ValueError):
        odds_to_pct("0/100")
    with pytest.raises(ValueError):
        odds_to_pct("100/0")
    with pytest.raises(ValueError):
        odds_to_pct("1/100")
    with pytest.raises(ValueError):
        odds_to_pct("100")
    with pytest.raises(ValueError):
        odds_to_pct("/")
    with pytest.raises(ValueError):
        odds_to_pct("/1")
    with pytest.raises(ValueError):
        odds_to_pct("100/")
    with pytest.raises(ValueError):
        odds_to_pct("100/100/100")
    with pytest.raises(ValueError):
        odds_to_pct("string")
