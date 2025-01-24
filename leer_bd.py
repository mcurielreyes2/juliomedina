from sqlalchemy import create_engine, text
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Create a connection to the database engine
engine = create_engine(DATABASE_URL)

# Query data from the `feedback` table and save to JSON
try:
    with engine.connect() as connection:
        # Execute the query
        query = text("SELECT * FROM feedback;")
        result = connection.execute(query)

        # Convert result to a list of dictionaries using `row._mapping`
        feedback_data = [dict(row._mapping) for row in result]

        # Save the data to a JSON file
        output_file = "feedback.json"
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(feedback_data, json_file, ensure_ascii=False, indent=4)

        print(f"Data successfully saved to {output_file}")

except Exception as e:
    print(f"Error while querying the `feedback` table: {e}")
