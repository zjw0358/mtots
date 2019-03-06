from mtots import test


@test.case
def test_fail():
    # This module should not be tested at all
    test.that(False)
