"""
General test for the the `simpy.core.Environment`.

"""
# Pytest gets the parameters "env" and "log" from the *conftest.py* file


def test_stop_self(env, log):
    """Process stops itself."""
    def pem(env, log):
        while env.now < 2:
            log.append(env.now)
            yield env.timeout(1)

    env.start(pem(env, log))
    env.run(10)

    assert log == [0, 1]


def test_run_negative_until(env):
    """Test passing a negative time to run."""
    pytest.raises(ValueError, env.run, -3)


def test_run_resume(env):
    """Stopped simulation can be resumed."""
    events = [env.timeout(t) for t in (5, 10, 15)]

    env.run(until=10)
    assert events[0].processed
    assert not events[1].processed
    assert not events[2].processed
    assert env.now == 10

    env.run(until=15)
    assert events[1].processed
    assert not events[2].processed
    assert env.now == 15

    env.run()
    assert events[2].processed
    assert env.now == 15


def test_run_until_value(env):
    """Anything that can be converted to a float is a valid until value."""
    env.run(until='3.141592')
    assert env.now == 3.141592
