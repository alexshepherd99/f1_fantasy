from scripts.select_starting_team import select_starting_team


def test_select_starting_team():
    team = select_starting_team(2025, 99.9)
    assert str(team) == "(ALB@WIL,ALO@AST,BEA@HAA,OCO@HAA,STR@AST)(FER,MCL)"
