from datetime import datetime

import pytz
import pytest

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


def test_advance_active_session_fills_missing_category_in_existing_record():
    data = {
        'records': {
            '2026-08-14': {'english': 30},
        },
        'active_session': {
            'type': 'piano',
            'start_time': '2026-08-14T10:00:00+09:00',
            'last_checkpoint_time': '2026-08-14T10:00:00+09:00',
        },
    }

    now = JST.localize(datetime(2026, 8, 14, 10, 1))

    result = advance_active_session(data, now)

    assert result['records']['2026-08-14'] == {
        'english': 30,
        'piano': 60,
    }


@pytest.mark.parametrize('session_type', [None, 'unknown'])
def test_advance_active_session_defaults_unknown_type_to_piano(session_type):
    data = {
        'records': {},
        'active_session': {
            'type': session_type,
            'start_time': '2026-08-14T10:00:00+09:00',
            'last_checkpoint_time': '2026-08-14T10:00:00+09:00',
        },
    }

    now = JST.localize(datetime(2026, 8, 14, 10, 1))

    result = advance_active_session(data, now)

    assert result['records']['2026-08-14'] == {'english': 0, 'piano': 60}
    assert result['active_session']['type'] == 'piano'


def test_start_rejects_unknown_session_type():
    from application import app

    response = app.test_client().post('/start', data={'type': 'unknown'})

    assert response.status_code == 400
