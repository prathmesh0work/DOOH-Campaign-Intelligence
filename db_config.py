import os
import mysql.connector
from dotenv import load_dotenv
from clean_data import add_calculated_metrics

load_dotenv()

def get_connection():
	return mysql.connector.connect(
			host=os.getenv("DB_HOST"),
        	port=os.getenv("DB_PORT"),
        	user=os.getenv("DB_USER"),
        	password=os.getenv("DB_PASSWORD"),
        	database=os.getenv("DB_NAME")
        )

def fetch_campaigns_from_db():
	conn = get_connection()
	cursor = conn.cursor(dictionary=True)

	cursor.execute("SELECT * from campaigns")
	db_rows = cursor.fetchall()

	cursor.close()
	conn.close()

	rows =[]
	for db_row in db_rows:
		rows.append({
			"Campaign_Name":db_row["campaign_name"],
			"City":db_row["city"],
			"Industry":db_row["industry"],
			"Screen_ID":db_row["screen_id"],
			"Date":db_row["campaign_date"].strftime("%Y-%m-%d"),
			"revenue":float(db_row["revenue"]),
			"ad_spend":float(db_row["ad_spend"]),
			"Impressions":db_row["impressions"],
			"Clicks":db_row["clicks"],
			"Hours_Booked":float(db_row["hours_booked"]),
			"Hours_Committed":float(db_row["hours_committed"])
		})
	rows = add_calculated_metrics(rows)
	return rows
def insert_campaigns(clean_rows):
	conn = get_connection()
	cursor = conn.cursor()

	insert_query = """
			INSERT INTO campaigns
			(campaign_name,city,industry,screen_id,campaign_date,revenue,ad_spend,clicks,impressions,hours_booked,hours_committed)
			values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
		"""
	row_inserted = 0
	for row in clean_rows:
		values = (
			row["Campaign_Name"],
			row["City"],
			row["Industry"],
			row["Screen_ID"],
			row["Date"],
			row["revenue"],
			row["ad_spend"],
			row["Clicks"],
			row["Impressions"],
			row["Hours_Booked"],
			row["Hours_Committed"],
		)
		cursor.execute(insert_query,values)
		row_inserted += 1
	conn.commit()
	cursor.close()
	conn.close()
	
	return row_inserted


	
