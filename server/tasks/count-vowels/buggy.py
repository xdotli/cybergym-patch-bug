def count_vowels(s):
    n = 0
    for ch in s:
        if ch in "aeio":
            n += 1
    return n
