# Marks register - same logic, different identifiers and comments


class MarksRegister:
    def __init__(self):
        self.pupils = {}

    def enroll(self, pupil):
        if pupil in self.pupils:
            raise ValueError("student already exists")
        self.pupils[pupil] = []

    def record(self, pupil, mark):
        if mark < 0 or mark > 100:
            raise ValueError("grade out of range")
        self.pupils[pupil].append(mark)

    def mean(self, pupil):
        marks = self.pupils[pupil]
        if not marks:
            return 0.0
        acc = 0
        for mark in marks:
            acc += mark
        return acc / len(marks)

    def best_pupil(self):
        winner = None
        winner_mean = -1
        for pupil in self.pupils:
            m = self.mean(pupil)
            if m > winner_mean:
                winner_mean = m
                winner = pupil
        return winner, winner_mean

    def summary(self):
        rows = []
        for pupil in sorted(self.pupils):
            m = self.mean(pupil)
            rows.append(pupil + ": " + str(round(m, 2)))
        return "\n".join(rows)


def run():
    register = MarksRegister()
    for kid in ["Asha", "Ravi", "Meera"]:
        register.enroll(kid)
    register.record("Asha", 91)
    register.record("Asha", 84)
    register.record("Ravi", 72)
    register.record("Meera", 88)
    print(register.summary())
    print(register.best_pupil())


if __name__ == "__main__":
    run()
