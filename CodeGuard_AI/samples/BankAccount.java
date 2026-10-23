public class BankAccount {
    private final String owner;
    private double balance;

    public BankAccount(String owner, double opening) {
        this.owner = owner;
        this.balance = opening;
    }

    public void deposit(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Deposit must be positive");
        }
        balance += amount;
    }

    public boolean withdraw(double amount) {
        if (amount > balance) {
            return false;
        }
        balance -= amount;
        return true;
    }

    public String statement() {
        return owner + " has " + String.format("%.2f", balance);
    }

    public static void main(String[] args) {
        BankAccount acct = new BankAccount("Nila", 100.0);
        acct.deposit(50.5);
        System.out.println(acct.withdraw(500.0));
        System.out.println(acct.statement());
    }
}
