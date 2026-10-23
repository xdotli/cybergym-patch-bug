def rotate_left(xs, k):
    if k:
        return xs[k:] + xs[:k]
    return xs
