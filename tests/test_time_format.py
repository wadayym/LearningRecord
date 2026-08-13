from application import format_minutes


def test_format_minutes_1h30m():
    assert format_minutes(90) == "1時間30分"


def test_format_minutes_under_hour():
    assert format_minutes(30) == "0時間30分"


def test_format_minutes_zero():
    assert format_minutes(0) == "0時間0分"
