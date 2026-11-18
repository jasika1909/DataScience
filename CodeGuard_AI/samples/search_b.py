# Same behaviour as search_a.py: while loop, expanded assignments, new order
def summarise(items):
    total = 0
    idx = 0
    while idx < len(items):
        total = total + items[idx]
        idx = idx + 1
    mean = total / len(items)
    top = items[0]
    for element in items:
        if element > top:
            top = element
    hits = 0
    for element in items:
        if element == top:
            hits = hits + 1
    print("avg", mean)
    print("max", top)
    print("count", hits)
    return top, hits, mean


numbers = [4, 9, 2, 9, 7]
summarise(numbers)
