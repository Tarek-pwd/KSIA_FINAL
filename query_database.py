import psycopg2
from psycopg2 import sql
import json
import os
from datetime import datetime, date
from decimal import Decimal
import uuid  # For generating unique IDs

# --- Database Connection Details ---
DB_NAME = "HR_db_New"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = 5433

conn = None  # Initialize conn to None for proper error handling
cur = None   # Initialize cur to None

def execute_query(sql_query):
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        print("🔹 Executing query:\n", sql_query)
        cur.execute(sql_query)
        rows = cur.fetchall()
        
        if not rows:
            return 'I dont know the answer, Please check your database'
        
        print("✅ Results:")
        for row in rows:
            print(row)
        
        final_data = []
        for idx, row in enumerate(rows):
            row_data = []
            for elem in row:
                # Fixed: Use (datetime, date) instead of (datetime.datetime, datetime.date)
                if isinstance(elem, (datetime, date)):
                    elem = elem.strftime('%Y-%m-%d')
                elif isinstance(elem, Decimal):
                    elem = float(elem)
                elif elem is None:
                    elem = 'NULL'
                else:
                    elem = str(elem)
                row_data.append(elem)
            
            # Only add row numbers if there are multiple rows

            print("the current row is >> ",row)
            row_string = str(row[0])
            for i in range(1,len(row)):
                print(f"type of {row[i]} is {type(row[i])} ")
                if isinstance(row[i],str):
                    row_string += " " + str(row[i])
                else:
                    row_string += " | " + str(row[i])

                
            if len(rows) > 1:
                final_data.append(f"{idx + 1}. {row_string}")
            else:
                final_data.append(row_string)
        
        # Join with newlines instead of returning a list
        return '\n'.join(final_data)
        
    except Exception as e:
        print("❌ Error:", e)
        return f"Error: {str(e)}"
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# Example usage:
# query = "SELECT e.first_name, e.last_name FROM employees e WHERE e.first_name = 'Michael' AND e.last_name = 'Mcclain';"
# results = execute_query(query)
# print(results)