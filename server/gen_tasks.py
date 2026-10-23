#!/usr/bin/env python3
"""Generate the cybergym_patch_bug tasks: buggy module + public tests + hidden
tests + a reference fix. Self-test at generation time: hidden tests must FAIL
on the buggy module and PASS on the reference fix; public tests must PASS on
both. Hidden tests and the reference never enter the agent's workspace."""
import os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks")

SPECS = [
    {
        "task_id": "sum-upto",
        "brief": "sum_upto(n) must return the sum 1 + 2 + ... + n inclusive.",
        "buggy": '''def sum_upto(n):
    total = 0
    for i in range(1, n):
        total += i
    return total
''',
        "fixed": '''def sum_upto(n):
    total = 0
    for i in range(1, n + 1):
        total += i
    return total
''',
        "public": "assert sum_upto(0) == 0\n",
        "hidden": "assert sum_upto(4) == 10\nassert sum_upto(100) == 5050\n",
        "hidden_fails_on_buggy": "sum_upto(4) == 7 != 10",
    },
    {
        "task_id": "average-float",
        "brief": "average(xs) must return the arithmetic mean as a float (xs is non-empty).",
        "buggy": '''def average(xs):
    s = 0
    for x in xs:
        s += x
    return s // len(xs)
''',
        "fixed": '''def average(xs):
    s = 0
    for x in xs:
        s += x
    return s / len(xs)
''',
        "public": "assert average([4]) == 4.0\nassert average([2, 4, 6]) == 4.0\n",
        "hidden": "assert average([1, 2]) == 1.5\nassert average([1, 2, 4]) == 7 / 3\n",
    },
    {
        "task_id": "clip-upper",
        "brief": "clip(v, lo, hi) must clamp v into the closed range [lo, hi].",
        "buggy": '''def clip(v, lo, hi):
    if v < lo:
        return lo
    return v
''',
        "fixed": '''def clip(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v
''',
        "public": "assert clip(1, 0, 5) == 1\nassert clip(-3, 0, 5) == 0\n",
        "hidden": "assert clip(9, 0, 5) == 5\nassert clip(5, 0, 5) == 5\n",
    },
    {
        "task_id": "parse-kv",
        "brief": "parse_kv(s) must parse 'a=1 b=2' into {'a': '1', 'b': '2'} (tokens split on spaces, keys/values on the first '=').",
        "buggy": '''def parse_kv(s):
    out = {}
    for part in s.split():
        key, value = part.split("=", 1)[0], part.split("=", 1)[0]
        out[key] = value
    return out
''',
        "fixed": '''def parse_kv(s):
    out = {}
    for part in s.split():
        key, value = part.split("=", 1)
        out[key] = value
    return out
''',
        "public": "assert parse_kv('') == {}\nassert parse_kv('k=k') == {'k': 'k'}\n",
        "hidden": "assert parse_kv('a=1 b=2') == {'a': '1', 'b': '2'}\nassert parse_kv('path=/tmp/f name=a=b') == {'path': '/tmp/f', 'name': 'a=b'}\n",
    },
    {
        "task_id": "count-vowels",
        "brief": "count_vowels(s) must count every lowercase vowel (a, e, i, o, u) in the string.",
        "buggy": '''def count_vowels(s):
    n = 0
    for ch in s:
        if ch in "aeio":
            n += 1
    return n
''',
        "fixed": '''def count_vowels(s):
    n = 0
    for ch in s:
        if ch in "aeiou":
            n += 1
    return n
''',
        "public": 'assert count_vowels("date") == 2\nassert count_vowels("big dog") == 2\nassert count_vowels("rhythm") == 0\n',
        "hidden": 'assert count_vowels("queue") == 4\nassert count_vowels("university") == 4\n',
    },
    {
        "task_id": "rotate-left",
        "brief": "rotate_left(xs, k) must rotate the list left by k positions (k >= 0), without mutating the input.",
        "buggy": '''def rotate_left(xs, k):
    if k:
        return xs[k:] + xs[:k]
    return xs
''',
        "fixed": '''def rotate_left(xs, k):
    if not xs:
        return []
    k = k % len(xs)
    return xs[k:] + xs[:k]
''',
        "public": "assert rotate_left([1, 2, 3, 4], 1) == [2, 3, 4, 1]\n",
        "hidden": "src = [1, 2, 3]\nr = rotate_left(src, 0)\nr.append(99)\nassert src == [1, 2, 3], 'k=0 must return a new list'\nassert rotate_left([1, 2], 2) == [1, 2]\nassert rotate_left(src, 5) == [3, 1, 2]\n",
    },
]


def run_tests(module_source, tests_source):
    namespace = {}
    exec(module_source, namespace)
    try:
        exec(tests_source, namespace)
        return True, None
    except AssertionError as exc:
        return False, f"assertion failed: {exc}"


def main():
    import json
    for spec in SPECS:
        task = spec["task_id"]
        base = os.path.join(HERE, task)
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "buggy.py"), "w") as h:
            h.write(spec["buggy"])
        with open(os.path.join(base, "tests_public.py"), "w") as h:
            h.write("from buggy import *  # noqa: F401,F403\n" + spec["public"])
        with open(os.path.join(base, "hidden_tests.py"), "w") as h:
            h.write(spec["hidden"])
        with open(os.path.join(base, "reference_fix.py"), "w") as h:
            h.write(spec["fixed"])
        with open(os.path.join(base, "challenge.txt"), "w") as h:
            h.write(
                f"{spec['brief']}\n\n"
                "buggy.py implements it with a bug: its public tests (tests_public.py) pass,\n"
                "but hidden requirements do not. Submit the FULL corrected module source as\n"
                "your final answer: the server imports it and runs the hidden tests.\n"
                "You can test locally: python3 tests_public.py\n"
                "A fix that special-cases the hidden tests is impossible to write blindly:\n"
                "think about what the specification above demands.\n"
            )
        ok_public_buggy, err = run_tests(spec["buggy"], "from buggy import *  # noqa\n".replace("from buggy import *", "") + spec["public"])
        ok_public_fixed, _ = run_tests(spec["fixed"], spec["public"])
        ok_hidden_buggy, _ = run_tests(spec["buggy"], spec["hidden"])
        ok_hidden_fixed, _ = run_tests(spec["fixed"], spec["hidden"])
        assert ok_public_buggy, f"{task}: public tests must pass on buggy code"
        assert ok_public_fixed, f"{task}: public tests must pass on the reference fix"
        assert not ok_hidden_buggy, f"{task}: hidden tests must FAIL on buggy code"
        assert ok_hidden_fixed, f"{task}: hidden tests must PASS on the reference fix"
        print(f"{task}: self-test OK (public passes on both, hidden fails only on buggy)")
    index = {
        "env": "cybergym-patch-bug",
        "description": "Defensive fixing: each task has a buggy module whose public tests pass; the hidden tests encode the specification the bug breaks. The submitted module source is imported and graded server-side.",
        "tasks": [{"task_id": s["task_id"], "split": "train", "verify": "hidden-tests"} for s in SPECS],
    }
    with open(os.path.join(HERE, "index.json"), "w") as h:
        json.dump(index, h, indent=2)
    print("tasks generated")


if __name__ == "__main__":
    main()
