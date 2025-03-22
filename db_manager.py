import sqlite3
from typing import List, Tuple


class DBManager:
    def __init__(self, db_name: str = "cinema_bot.db"):
        self.connection = sqlite3.connect(db_name)
        self._create_tables()

    def _create_tables(self):
        with self.connection:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    query TEXT,
                    movie_title TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS movie_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    movie_title TEXT,
                    user_id TEXT,
                    count INTEGER DEFAULT 1,
                    UNIQUE(movie_title, user_id)
                )
            """)

    def save_search(self, user_id: str, query: str, movie_title: str):
        with self.connection:
            self.connection.execute("""
                INSERT INTO search_history (user_id, query, movie_title)
                VALUES (?, ?, ?)
            """, (user_id, query, movie_title))

    def get_search_history(self, user_id: str) -> List[Tuple[str, str]]:
        with self.connection:
            return self.connection.execute("""
                SELECT query, movie_title
                FROM search_history
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (user_id,)).fetchall()

    def increment_movie_stat(self, user_id: str, movie_title: str):
        with self.connection:
            cursor = self.connection.execute("""
                SELECT count
                FROM movie_stats
                WHERE movie_title = ? AND user_id = ?
            """, (movie_title, user_id))
            row = cursor.fetchone()
            if row:
                self.connection.execute("""
                    UPDATE movie_stats
                    SET count = count + 1
                    WHERE movie_title = ? AND user_id = ?
                """, (movie_title, user_id))
            else:
                self.connection.execute("""
                    INSERT INTO movie_stats (movie_title, user_id, count)
                    VALUES (?, ?, 1)
                """, (movie_title, user_id))

    def get_movie_stats(self, user_id: str) -> List[Tuple[str, int]]:
        with self.connection:
            return self.connection.execute("""
                SELECT movie_title, count
                FROM movie_stats
                WHERE user_id = ?
                ORDER BY count DESC
                LIMIT 10
            """, (user_id,)).fetchall()

    def close(self):
        self.connection.close()
