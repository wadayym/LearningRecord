from datetime import datetime

import pytz

from application import advance_active_session

JST = pytz.timezone('Asia/Tokyo')


def test_advance_active_session_adds_only_unrecorded_seconds():
    data = {
        'records': {},
        'active_session': {
            'type': 'english',
            'start_time': '2026-08-14T23:00:00+09:00',
            'last_checkpoint_time': '2026-08-14T23:00:00+09:00',
        },
    }

    now = JST.localize(datetime(2026, 8, 14, 23, 30))

    result = advance_active_session(data, now)

    assert result['records']['2026-08-14']['english'] == 1800.0
    assert result['active_session']['last_checkpoint_time'] == now.isoformat()
    assert result['active_session']['start_time'] == '2026-08-14T23:00:00+09:00'


def test_advance_active_session_splits_across_midnight_without_double_counting():
    data = {
        'records': {},
        'active_session': {
            'type': 'english',
            'start_time': '2026-08-14T23:30:00+09:00',
            'last_checkpoint_time': '2026-08-14T23:30:00+09:00',
        },
    }

    now = JST.localize(datetime(2026, 8, 15, 0, 15))

    result = advance_active_session(data, now)

    assert result['records']['2026-08-14']['english'] == 1800.0
    assert result['records']['2026-08-15']['english'] == 900.0
    assert result['active_session']['last_checkpoint_time'] == now.isoformat()
