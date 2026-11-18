#include <iostream>
#include <vector>

class IntStack {
public:
    void push(int value) {
        data.push_back(value);
    }

    int pop() {
        if (data.empty()) {
            return -1;
        }
        int top = data.back();
        data.pop_back();
        return top;
    }

    bool empty() const {
        return data.empty();
    }

private:
    std::vector<int> data;
};

int main() {
    IntStack s;
    for (int i = 0; i < 5; i++) {
        s.push(i * i);
    }
    while (!s.empty()) {
        std::cout << s.pop() << std::endl;
    }
    return 0;
}
