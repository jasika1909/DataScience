public class Search {
    static double analyse(int[] numbers) {
        int largest = numbers[0];
        for (int value : numbers) {
            if (value > largest) {
                largest = value;
            }
        }
        int count = 0;
        for (int value : numbers) {
            if (value == largest) {
                count++;
            }
        }
        int total = 0;
        for (int i = 0; i < numbers.length; i++) {
            total += numbers[i];
        }
        double average = (double) total / numbers.length;
        System.out.println("max " + largest);
        System.out.println("count " + count);
        System.out.println("avg " + average);
        return average;
    }

    public static void main(String[] args) {
        int[] data = {4, 9, 2, 9, 7};
        analyse(data);
    }
}
