import sqlite3
import json

# Connect to feedback database
conn = sqlite3.connect('secure_data/feedback.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all feedback
cursor.execute('SELECT * FROM feedback ORDER BY timestamp DESC')
rows = cursor.fetchall()

print(f"Total feedback entries in database: {len(rows)}")
print("="*80)

if rows:
    for row in rows:
        print(f"\nID: {row['id']}")
        print(f"Type: {row['feedback_type']}")
        print(f"Subject: {row['subject']}")
        print(f"Category: {row['category']}")
        print(f"Experience: {row['experience']}")
        print(f"Name: {row['name']}")
        print(f"Email: {row['email'] if row['email'] else 'N/A'}")
        print(f"Status: {row['status']}")
        print(f"Timestamp: {row['timestamp']}")
        print(f"Details: {row['details'][:100]}..." if len(row['details']) > 100 else f"Details: {row['details']}")
        print("-"*80)
else:
    print("\nNo feedback found in database!")

conn.close()
