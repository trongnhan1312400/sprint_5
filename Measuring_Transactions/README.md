# Measuring Transactions
The testing is done through python scripts calling into Libindy to send the transactions.
The measurement of transactions per second is done be getting the epoch time stamp from the first transaction that was sent and subtracting it from the epoch time stamp of the last transaction that was sent. The difference in the time stamps gives you the total number of seconds. 
Dividing the total transactions by the total seconds of what was committed to the ledger gives the number of transactions per second.

This Python script currently requires python 3.5.


# How to run

```
Step 1: Get the number of transactions
syntax: python3.5  measuring_transactions.py -c

e.g.: return 18500
```

```
Step 2: run the test.
```

```
Step 3. Calculate the transactions per minute
python3.5  measuring_transactions.py -n 18500
```
