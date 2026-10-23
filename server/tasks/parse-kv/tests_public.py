from buggy import *  # noqa: F401,F403
assert parse_kv('') == {}
assert parse_kv('k=k') == {'k': 'k'}
