from contextlib import suppress

with suppress(ValueError):
    int("not a number")

print("This still runs because the ValueError was suppressed.")



