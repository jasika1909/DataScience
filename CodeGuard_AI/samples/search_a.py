def analyse(numbers):
    largest = numbers[0]
    for value in numbers:
        if value > largest:
            largest = value
    count = 0
    for value in numbers:
        if value == largest:
            count += 1
    total = 0
    for i in range(len(numbers)):
        total += numbers[i]
    average = total / len(numbers)
    print("max", largest)
    print("count", count)
    print("avg", average)
    return largest, count, average


data = [4, 9, 2, 9, 7]
analyse(data)
