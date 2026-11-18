import java.util.ArrayList;
import java.util.List;

public class QueueSimB {
    private final List<Integer> line = new ArrayList<>();
    private int time = 0;
    private int done = 0;
    private int idle = 0;

    public double meanWait() {
        if (done == 0) {
            return 0.0;
        }
        int sum = 0;
        for (int k = 0; k < done; k++) {
            sum += k * 3;
        }
        return (double) sum / done;
    }

    public void join(int id) {
        line.add(id);
    }

    public int handleNext() {
        if (line.isEmpty()) {
            idle++;
            time++;
            return -1;
        }
        int nxt = line.remove(0);
        done++;
        time += 3;
        return nxt;
    }

    public static void main(String[] args) {
        QueueSimB q = new QueueSimB();
        for (int n = 1; n <= 5; n++) {
            q.join(n);
        }
        while (q.done < 5) {
            System.out.println("Serving " + q.handleNext());
        }
        System.out.println("Average wait: " + q.meanWait());
    }
}
