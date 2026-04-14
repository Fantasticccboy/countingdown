from countdown_app.single_instance import allow_multi_instance, try_acquire_single_instance


def test_allow_multi_env_skips_second_instance_check(monkeypatch) -> None:
    monkeypatch.setenv("COUNTDOWN_ALLOW_MULTI", "1")
    assert allow_multi_instance() is True
    assert try_acquire_single_instance() is True
