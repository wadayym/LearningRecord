import os

from application import get_data_file_path


def test_get_data_file_path_uses_env_override(tmp_path, monkeypatch):
    target = tmp_path / "persisted" / "data.json"
    monkeypatch.setenv("LEARNING_RECORD_DATA_FILE", str(target))

    assert get_data_file_path() == str(target)


def test_get_data_file_path_uses_user_home_dir(monkeypatch):
    monkeypatch.delenv("LEARNING_RECORD_DATA_FILE", raising=False)
    monkeypatch.setattr('os.path.expanduser', lambda path: 'C:/Users/example')

    expected = os.path.join('C:/Users/example', 'learningrecord', 'data.json')
    assert get_data_file_path() == expected
