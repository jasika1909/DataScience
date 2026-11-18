import java.util.ArrayList;
import java.util.List;

public class QueueSimA {
    private final List<Integer> waiting = new ArrayList<>();
    private int clock = 0;
    private int served = 0;
    private int idleTime = 0;

    public void arrive(int customerId) {
        waiting.add(customerId);
    }

    public int serveNext() {
        if (waiting.isEmpty()) {
            idleTime++;
            clock++;
            return -1;
        }
        int next = waiting.remove(0);
        served++;
        clock += 3;
        return next;
    }

    public double averageWait() {
        if (served == 0) {
            return 0.0;
        }
        int total = 0;
        for (int i = 0; i < served; i++) {
            total += i * 3;
        }
        return (double) total / served;
    }

    public static void main(String[] args) {
        QueueSimA sim = new QueueSimA();
        for (int i = 1; i <= 5; i++) {
            sim.arrive(i);
        }
        while (sim.served < 5) {
            System.out.println("Serving " + sim.serveNext());
        }
        System.out.println("Average wait: " + sim.averageWait());
    }
}
