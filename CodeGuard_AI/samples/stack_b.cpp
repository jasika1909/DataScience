#include <iostream>
#include <vector>

class NumberStack {
public:
    void push(int v) {
        items.push_back(v);
    }

    int pop() {
        if (items.empty()) {
            return -1;
        }
        int t = items.back();
        items.pop_back();
        return t;
    }

    bool empty() const {
        return items.empty();
    }

private:
    std::vector<int> items;
};

int main() {
    NumberStack st;
    for (int n = 0; n < 5; n++) {
        st.push(n * n);
    }
    while (!st.empty()) {
        std::cout << st.pop() << std::endl;
    }
    return 0;
}
