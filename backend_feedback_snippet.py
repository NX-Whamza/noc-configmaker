
# ========================================
# FEEDBACK SYSTEM
# ========================================
FEEDBACK_DB = 'feedback.db'

def init_feedback_db():
    """Initialize feedback database"""
    try:
        conn = sqlite3.connect(FEEDBACK_DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS feedback
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user TEXT,
                      message TEXT,
                      rating INTEGER,
                      status TEXT,
                      date TEXT)''')
        conn.commit()
        conn.close()
        safe_print("[DATABASE] Feedback database initialized")
    except Exception as e:
        safe_print(f"[ERROR] Failed to init feedback DB: {e}")

# Initialize on startup
init_feedback_db()

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback"""
    try:
        data = request.json
        user = data.get('user', 'Anonymous')
        message = data.get('message', '')
        rating = data.get('rating', 0)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
            
        conn = sqlite3.connect(FEEDBACK_DB)
        c = conn.cursor()
        c.execute("INSERT INTO feedback (user, message, rating, status, date) VALUES (?, ?, ?, ?, ?)",
                  (user, message, rating, 'new', get_cst_datetime_string()))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Feedback received'})
    except Exception as e:
        safe_print(f"[ERROR] Feedback submission failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/feedback', methods=['GET'])
def get_admin_feedback():
    """Get all feedback for admin dashboard"""
    try:
        conn = sqlite3.connect(FEEDBACK_DB)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM feedback ORDER BY date DESC")
        rows = c.fetchall()
        conn.close()
        
        feedback_list = []
        for row in rows:
            feedback_list.append({
                'id': row['id'],
                'user': row['user'],
                'message': row['message'],
                'rating': row['rating'],
                'status': row['status'],
                'date': row['date']
            })
            
        return jsonify(feedback_list)
    except Exception as e:
        safe_print(f"[ERROR] Failed to fetch feedback: {e}")
        return jsonify({'error': str(e)}), 500
