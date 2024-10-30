import sys


def logged(func):
    def wrapper(*args, **kwargs):
        if (i := args[0].index("-o") + 1) > 0:
            with open(args[0][i], "a") as fh:
                return func(*args, fh)
        else:
            return func(*args, sys.stdout)

    return wrapper
