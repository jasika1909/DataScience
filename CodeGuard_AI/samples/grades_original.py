"""Simple grade book used to demonstrate similarity detection."""


class GradeBook:
    def __init__(self):
        self.students = {}

    def add_student(self, name):
        if name in self.students:
            raise ValueError("student already exists")
        self.students[name] = []

    def add_grade(self, name, grade):
        if grade < 0 or grade > 100:
            raise ValueError("grade out of range")
        self.students[name].append(grade)

    def average(self, name):
        grades = self.students[name]
        if not grades:
            return 0.0
        total = 0
        for grade in grades:
            total += grade
        return total / len(grades)

    def top_student(self):
        best_name = None
        best_avg = -1
        for name in self.students:
            avg = self.average(name)
            if avg > best_avg:
                best_avg = avg
                best_name = name
        return best_name, best_avg

    def report(self):
        lines = []
        for name in sorted(self.students):
            avg = self.average(name)
            lines.append(name + ": " + str(round(avg, 2)))
        return "\n".join(lines)


def main():
    book = GradeBook()
    for student in ["Asha", "Ravi", "Meera"]:
        book.add_student(student)
    book.add_grade("Asha", 91)
    book.add_grade("Asha", 84)
    book.add_grade("Ravi", 72)
    book.add_grade("Meera", 88)
    print(book.report())
    print(book.top_student())


if __name__ == "__main__":
    main()
