from external_data.fastf1_common import get_cache_filename


def test_get_cache_filename():
    def dummy_func():
        pass
    
    assert get_cache_filename(
        dummy_func,
        (),
        {}
    ) == "cache_dummy_func.pkl"

    assert get_cache_filename(
        dummy_func,
        (100,),
        {}
    ) == "cache_dummy_func_100.pkl"

    assert get_cache_filename(
        dummy_func,
        (100, 200),
        {}
    ) == "cache_dummy_func_100_200.pkl"

    assert get_cache_filename(
        dummy_func,
        (),
        {"a": 99}
    ) == "cache_dummy_func_a-99.pkl"

    assert get_cache_filename(
        dummy_func,
        (),
        {"a": 99, "b": 88}
    ) == "cache_dummy_func_a-99_b-88.pkl"

    assert get_cache_filename(
        dummy_func,
        (100, 200),
        {"a": 99, "b": 88}
    ) == "cache_dummy_func_100_200_a-99_b-88.pkl"
