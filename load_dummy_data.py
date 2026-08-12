import pandas as pd
from clean_data import clean_data
from db_config import get_connection
from db_config import insert_campaigns

def load_csv_to_database(csv_path):
    table = pd.read_csv(csv_path)
    raw_rows = table.to_dict('records')

    cleaning_result = clean_data(raw_rows)
    clean_rows = cleaning_result["rows"]
    log = cleaning_result["log"]

    print(f"cleaned {log['final_rows']} rows out of {log['total_rows']} original rows.")

    row_inserted = insert_campaigns(clean_rows)
    print(f"Inserted {row_inserted} rows into the campaigns table")

if __name__ == "__main__":
    load_csv_to_database("dummy_dataset.csv")
