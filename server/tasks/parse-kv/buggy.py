def parse_kv(s):
    out = {}
    for part in s.split():
        key, value = part.split("=", 1)[0], part.split("=", 1)[0]
        out[key] = value
    return out
