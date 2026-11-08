from datetime import datetime, timezone

import pytest

from import_data.odds import odds_to_pct
from odds_source.page import read_saved_page

# Written by hand in the shape of a page saved from Oddschecker, never cut from a
# real save, which carries browser and tracking details. Four bookmakers, B1-B4.
_TEST_PAGE = "data/test_oddschecker_winner.mhtml"


def _page_with_body(tmp_path, body: str):
    """A saved page holding ``body`` as its HTML, with no odds grid of the real shape."""
    path = tmp_path / "page.mhtml"
    path.write_text(
        "From: <Saved by Blink>\n"
        "Date: Sun, 08 Nov 2026 16:01:41 GMT\n"
        "MIME-Version: 1.0\n"
        'Content-Type: multipart/related; type="text/html"; boundary="b"\n'
        "\n"
        "--b\n"
        "Content-Type: text/html\n"
        "\n"
        f"{body}\n"
        "--b--\n"
    )
    return path


def test_reads_the_race_and_when_the_page_was_saved():
    page = read_saved_page(_TEST_PAGE)

    assert page.race_name == "Test Grand Prix"
    assert page.race_start == datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)
    assert page.saved_at == datetime(2026, 11, 8, 16, 1, 41, tzinfo=timezone.utc)


def test_takes_the_winner_market_not_the_first_one_listed():
    # The podium market comes first in the page and prices Verstappen at 1/5
    assert read_saved_page(_TEST_PAGE).prices["Max Verstappen"] != "1/5"


def test_prices_a_driver_at_the_median_of_the_active_bookmakers():
    prices = read_saved_page(_TEST_PAGE).prices

    # 4/1, 9/2 and 5/1; a suspended 100/1 is not counted
    assert prices["Max Verstappen"] == "9/2"
    # An even count takes the midpoint of the middle two, 11/8 and 6/4
    assert prices["Kimi Antonelli"] == "23/16"


def test_writes_prices_the_odds_loader_reads():
    for price in read_saved_page(_TEST_PAGE).prices.values():
        assert 0.0 < odds_to_pct(price) < 1.0


def test_keeps_names_as_the_page_spells_them():
    assert "Nico Hülkenberg" in read_saved_page(_TEST_PAGE).prices


def test_drops_a_driver_priced_by_fewer_than_half_the_bookmakers(caplog):
    caplog.set_level("WARNING", logger="odds_source.page")

    prices = read_saved_page(_TEST_PAGE).prices

    # Ocon has 1 of 4 prices; Hulkenberg's 2 of 4 is half, so stays
    assert "Esteban Ocon" not in prices
    assert prices["Nico Hülkenberg"] == "150/1"
    assert "Esteban Ocon" in caplog.text


def test_raises_on_a_page_with_no_odds_grid(tmp_path):
    page = _page_with_body(tmp_path, "<html><body><p>Access denied</p></body></html>")

    with pytest.raises(ValueError, match="odds grid"):
        read_saved_page(page)


def test_raises_on_a_page_with_no_winner_market(tmp_path):
    props = (
        "{&quot;componentArgs&quot;:[0,{&quot;marketGroups&quot;:[0,{&quot;Win Markets&quot;:[1,["
        "[0,{&quot;ocMarketId&quot;:[0,222],&quot;betTypeName&quot;:[0,&quot;Podium Finish&quot;]}]"
        "]]}],&quot;oddsGrids&quot;:[0,{}]}]}"
    )
    page = _page_with_body(
        tmp_path, f'<html><body><astro-island component-export="GridGroupIsland" props="{props}">'
        "</astro-island></body></html>"
    )

    with pytest.raises(ValueError, match="Winner market"):
        read_saved_page(page)
