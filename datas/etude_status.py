import csv

CSV_PATH = "events_propres.csv"


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        values = {row["status"] for row in csv.DictReader(f)}
    print(f"Nombre de valeurs possibles pour la métadonnée status : {len(values)}")


if __name__ == "__main__":
    main()
