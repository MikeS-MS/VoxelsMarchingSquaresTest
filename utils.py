import math


def distance(start_x: int, start_y: int, end_x: int, end_y: int) -> int:
    x_sqr = math.pow(end_x - start_x, 2)
    y_sqr = math.pow(end_y - start_y, 2)
    sqrt = math.sqrt(abs(x_sqr + y_sqr))
    return int(sqrt)


def clamp(value, minimum, maximum):
    if minimum > maximum:
        minimum = maximum
    if maximum < minimum:
        maximum = minimum

    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value