import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name='levels.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY,
                      xp INTEGER DEFAULT 0,
                      level INTEGER DEFAULT 1,
                      last_message_time INTEGER)''')
        
        # Create weekly_leaderboard table
        c.execute('''CREATE TABLE IF NOT EXISTS weekly_leaderboard
                     (week_start TEXT PRIMARY KEY,
                      top_users TEXT)''')
        
        conn.commit()
        conn.close()
    
    def get_user_level(self, user_id):
        """Get user's current XP and level"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return result or (0, 1)
    
    def update_user_xp(self, user_id, xp_gain):
        """Update user's XP and level"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # Get current XP and level
        c.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        
        if result:
            current_xp, current_level = result
            new_xp = current_xp + xp_gain
        else:
            current_xp, current_level = 0, 1
            new_xp = xp_gain
        
        # Calculate new level
        new_level = current_level
        while new_xp >= self.xp_for_level(new_level):
            new_level += 1
        
        # Update or insert user data
        c.execute('''INSERT OR REPLACE INTO users (user_id, xp, level, last_message_time)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, new_xp, new_level, int(datetime.now().timestamp())))
        
        conn.commit()
        conn.close()
        return new_xp, new_level, current_level
    
    def xp_for_level(self, level):
        """Calculate XP needed for a level"""
        return 5 * (level ** 2) + 50 * level + 100
    
    def get_top_users(self, limit=10):
        """Get top users by level and XP"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT user_id, level, xp FROM users ORDER BY level DESC, xp DESC LIMIT ?', (limit,))
        result = c.fetchall()
        conn.close()
        return result
    
    def save_weekly_leaderboard(self, top_users):
        """Save current week's leaderboard"""
        conn = self.get_connection()
        c = conn.cursor()
        week_start = datetime.now().strftime('%Y-%W')
        c.execute('''INSERT OR REPLACE INTO weekly_leaderboard (week_start, top_users)
                     VALUES (?, ?)''',
                  (week_start, json.dumps(top_users)))
        conn.commit()
        conn.close()
    
    def get_current_leaderboard(self):
        """Get current week's leaderboard"""
        conn = self.get_connection()
        c = conn.cursor()
        week_start = datetime.now().strftime('%Y-%W')
        c.execute('SELECT top_users FROM weekly_leaderboard WHERE week_start = ?', (week_start,))
        result = c.fetchone()
        conn.close()
        return json.loads(result[0]) if result else None
    
    def get_user_rank(self, user_id):
        """Get user's rank in the server"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # Get all users ordered by level and XP
        c.execute('SELECT user_id FROM users ORDER BY level DESC, xp DESC')
        users = c.fetchall()
        
        # Find user's position
        rank = next((i + 1 for i, (uid,) in enumerate(users) if uid == user_id), None)
        
        conn.close()
        return rank
    
    def get_user_stats(self, user_id):
        """Get detailed user statistics"""
        conn = self.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT xp, level FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        
        if result:
            xp, level = result
            next_level_xp = self.xp_for_level(level)
            progress = (xp / next_level_xp) * 100
            rank = self.get_user_rank(user_id)
            
            stats = {
                'level': level,
                'xp': xp,
                'next_level_xp': next_level_xp,
                'progress': progress,
                'rank': rank
            }
        else:
            stats = {
                'level': 1,
                'xp': 0,
                'next_level_xp': self.xp_for_level(1),
                'progress': 0,
                'rank': None
            }
        
        conn.close()
        return stats 