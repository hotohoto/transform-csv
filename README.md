# transform-csv

A python script to transform a CSV file.

## Usage

Execute `transform-csv.py` like below to window fields as `XXX_T-1, XXX_T-0, XXX_T+1, XXX_T+2, XXX_T+3`.

```bash
./transform-csv.py methane.csv methane.windowed.csv 2 3
```

You can choose a transform to apply for each field interactively like below.

```
Configure fields settings: [w] Window  [d] Drop  [k] Keep  [ENTER] Proceed  [q] Quit
[d] Time
[w] CO2
[w] Methane
```

Additional features:

- cached fields setting

Requirements:

- Python 3.7 or higher
- pandas
