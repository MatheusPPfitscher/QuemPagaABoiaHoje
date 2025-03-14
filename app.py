from flask import Flask, request, render_template, redirect, url_for, send_from_directory
import sqlite3
from datetime import datetime
import logging



app = Flask(__name__)
logging.basicConfig(filename='app.log', level=logging.INFO)
# Initialize SQLite database
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        buyer TEXT NOT NULL,
        type TEXT NOT NULL,
        value REAL NOT NULL
    )
''')
conn.commit()

@app.route('/favicon.png')
def favicon():
    return send_from_directory('static', 'favicon.png', mimetype='image/png')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        date = request.form['date']
        buyer = request.form['buyer']
        entry_type = request.form['type']
        value = request.form['value']
        
        # Ensure the date is in YYYY-MM-DD format
        date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        
        # Insert data into SQLite
        c.execute('''
            INSERT INTO entries (date, buyer, type, value) 
            VALUES (?, ?, ?, ?)
        ''', (date, buyer, entry_type, value))
        conn.commit()
        
        # Redirect to prevent form resubmission
        return redirect(url_for('index'))
    
    # Fetch the latest entry for each type based on date
    c.execute('''
        SELECT buyer, date, value, type FROM entries 
        WHERE type = 'Dinner' 
        ORDER BY date DESC 
        LIMIT 1
    ''')
    last_dinner = c.fetchone()
    
    c.execute('''
        SELECT buyer, date, value, type FROM entries 
        WHERE type = 'Lunch' 
        ORDER BY date DESC 
        LIMIT 1
    ''')
    last_lunch = c.fetchone()

    # Fetch the last 10 entries sorted by date
    c.execute('''
        SELECT buyer, date, type FROM entries 
        ORDER BY date DESC 
        LIMIT 10
    ''')
    last_10_entries = c.fetchall()

    # Pass current date to the template in YYYY-MM-DD format
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('index.html', last_dinner=last_dinner, last_lunch=last_lunch, current_date=current_date, last_10_entries=last_10_entries)

if __name__ == '__main__':
    app.run(host='::', port=5000)
