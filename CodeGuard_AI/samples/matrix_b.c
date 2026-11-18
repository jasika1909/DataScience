#include <stdio.h>

#define SIZE 3

void show(int grid[SIZE][SIZE]) {
    for (int r = 0; r < SIZE; r++) {
        for (int q = 0; q < SIZE; q++) {
            printf("%d ", grid[r][q]);
        }
        printf("\n");
    }
}

void product(int x[SIZE][SIZE], int y[SIZE][SIZE], int out[SIZE][SIZE]) {
    for (int r = 0; r < SIZE; r++) {
        for (int q = 0; q < SIZE; q++) {
            out[r][q] = 0;
            for (int t = 0; t < SIZE; t++) {
                out[r][q] += x[r][t] * y[t][q];
            }
        }
    }
}

int main(void) {
    int x[SIZE][SIZE] = {{1, 2, 3}, {4, 5, 6}, {7, 8, 9}};
    int y[SIZE][SIZE] = {{9, 8, 7}, {6, 5, 4}, {3, 2, 1}};
    int out[SIZE][SIZE];
    product(x, y, out);
    show(out);
    return 0;
}
