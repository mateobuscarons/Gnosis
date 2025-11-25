"""
Database operations for Adaptive Learning OS
Handles all CRUD operations for user profiles, learning paths, module challenges, and progress tracking
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    """SQLite database manager for the learning system"""

    def __init__(self, db_path: str = "learning_system.db"):
        """
        Initialize database connection and create tables

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.schema_path = Path(__file__).parent / "schema.sql"
        self._init_database()

    def _init_database(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            with open(self.schema_path, 'r') as f:
                conn.executescript(f.read())
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # Wait up to 30 seconds for locks
            isolation_level='IMMEDIATE'  # Acquire locks immediately to prevent conflicts
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')  # Faster writes while still safe
        return conn

    def create_user_profile(self, learning_goal: str, experience_level: str) -> int:
        """
        Create a new user profile

        Args:
            learning_goal: What the user wants to learn
            experience_level: Beginner, Intermediate, or Advanced

        Returns:
            User ID of created profile
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO user_profile (learning_goal, experience_level)
                   VALUES (?, ?)""",
                (learning_goal, experience_level)
            )
            conn.commit()
            return cursor.lastrowid

    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user profile by ID

        Args:
            user_id: User ID

        Returns:
            User profile dict or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_profile WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_first_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Get the first (and typically only) user profile
        Useful for single-user MVP

        Returns:
            User profile dict or None if no users exist
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM user_profile ORDER BY id LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def update_user_last_active(self, user_id: int):
        """Update user's last_active timestamp"""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE user_profile SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            conn.commit()


    def save_learning_path(self, user_id: int, path_data: Dict[str, Any]) -> int:
        """
        Save learning path for a user

        Args:
            user_id: User ID
            path_data: Full learning path output from Learning Path Agent

        Returns:
            Learning path ID
        """
        path_json = json.dumps(path_data, indent=2)
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO learning_path (user_id, path_json) VALUES (?, ?)",
                (user_id, path_json)
            )
            conn.commit()
            return cursor.lastrowid

    def get_learning_path(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get learning path for a user

        Args:
            user_id: User ID

        Returns:
            Learning path dict or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT path_json FROM learning_path WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                (user_id,)
            ).fetchone()
            return json.loads(row['path_json']) if row else None

    def update_learning_path(self, user_id: int, path_data: Dict[str, Any]):
        """
        Update existing learning path for a user

        Args:
            user_id: User ID
            path_data: Updated learning path data
        """
        path_json = json.dumps(path_data, indent=2)
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE learning_path
                   SET path_json = ?, created_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND id = (
                       SELECT id FROM learning_path WHERE user_id = ? ORDER BY id DESC LIMIT 1
                   )""",
                (path_json, user_id, user_id)
            )
            conn.commit()

    def save_module_challenges(self, user_id: int, module_number: int, challenges_data: Dict[str, Any]) -> int:
        """
        Save challenges for a specific module

        Args:
            user_id: User ID
            module_number: Module number (1-indexed)
            challenges_data: Full module challenges from Module Planner Agent

        Returns:
            Module challenges ID
        """
        challenges_json = json.dumps(challenges_data, indent=2)
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO module_challenges (user_id, module_number, challenges_json)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id, module_number) DO UPDATE SET challenges_json = excluded.challenges_json""",
                (user_id, module_number, challenges_json)
            )
            conn.commit()
            return cursor.lastrowid

    def get_module_challenges(self, user_id: int, module_number: int) -> Optional[Dict[str, Any]]:
        """
        Get challenges for a specific module

        Args:
            user_id: User ID
            module_number: Module number

        Returns:
            Module challenges dict or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT challenges_json FROM module_challenges WHERE user_id = ? AND module_number = ?",
                (user_id, module_number)
            ).fetchone()
            return json.loads(row['challenges_json']) if row else None

    def get_all_module_challenges(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all module challenges for a user

        Args:
            user_id: User ID

        Returns:
            List of module challenges dicts
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT module_number, challenges_json FROM module_challenges WHERE user_id = ? ORDER BY module_number",
                (user_id,)
            ).fetchall()
            return [
                {
                    'module_number': row['module_number'],
                    'challenges': json.loads(row['challenges_json'])
                }
                for row in rows
            ]


    def create_challenge_progress(
        self,
        user_id: int,
        module_number: int,
        challenge_number: int,
        status: str = 'not_started'
    ) -> int:
        """
        Create a new challenge progress entry

        Args:
            user_id: User ID
            module_number: Module number
            challenge_number: Challenge number within module
            status: not_started, in_progress, or completed

        Returns:
            Challenge progress ID
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO challenge_progress
                   (user_id, module_number, challenge_number, status)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, module_number, challenge_number) DO NOTHING""",
                (user_id, module_number, challenge_number, status)
            )
            conn.commit()
            return cursor.lastrowid

    def get_challenge_progress(
        self,
        user_id: int,
        module_number: int,
        challenge_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get progress for a specific challenge

        Args:
            user_id: User ID
            module_number: Module number
            challenge_number: Challenge number

        Returns:
            Challenge progress dict or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM challenge_progress
                   WHERE user_id = ? AND module_number = ? AND challenge_number = ?""",
                (user_id, module_number, challenge_number)
            ).fetchone()

            if not row:
                return None

            progress = dict(row)
            if progress['coding_challenge_json']:
                progress['coding_challenge'] = json.loads(progress['coding_challenge_json'])
            if progress['last_evaluation_json']:
                progress['last_evaluation'] = json.loads(progress['last_evaluation_json'])
            return progress

    def update_challenge_status(
        self,
        user_id: int,
        module_number: int,
        challenge_number: int,
        status: str
    ):
        """
        Update challenge status

        Args:
            user_id: User ID
            module_number: Module number
            challenge_number: Challenge number
            status: locked, in_progress, or completed
        """
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE challenge_progress
                   SET status = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND module_number = ? AND challenge_number = ?""",
                (status, user_id, module_number, challenge_number)
            )
            conn.commit()

    def save_lesson_content(
        self,
        user_id: int,
        module_number: int,
        challenge_number: int,
        lesson_markdown: str
    ):
        """
        Cache lesson content from Tutor Agent

        Args:
            user_id: User ID
            module_number: Module number
            challenge_number: Challenge number
            lesson_markdown: Lesson content in markdown format
        """
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE challenge_progress
                   SET lesson_markdown = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND module_number = ? AND challenge_number = ?""",
                (lesson_markdown, user_id, module_number, challenge_number)
            )
            conn.commit()

    def save_coding_challenge(
        self,
        user_id: int,
        module_number: int,
        challenge_number: int,
        coding_challenge: Dict[str, Any]
    ):
        """
        Cache coding challenge from Coding Challenge Agent

        Args:
            user_id: User ID
            module_number: Module number
            challenge_number: Challenge number
            coding_challenge: Challenge data dict
        """
        challenge_json = json.dumps(coding_challenge, indent=2)
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE challenge_progress
                   SET coding_challenge_json = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND module_number = ? AND challenge_number = ?""",
                (challenge_json, user_id, module_number, challenge_number)
            )
            conn.commit()

    def record_submission(
        self,
        user_id: int,
        module_number: int,
        challenge_number: int,
        submission: str,
        evaluation: Dict[str, Any]
    ):
        """
        Record a code submission and its evaluation

        Args:
            user_id: User ID
            module_number: Module number
            challenge_number: Challenge number
            submission: User's submitted code
            evaluation: Evaluation result from Code Evaluator Agent
        """
        evaluation_json = json.dumps(evaluation, indent=2)
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE challenge_progress
                   SET last_submission = ?,
                       last_evaluation_json = ?,
                       attempt_count = attempt_count + 1,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND module_number = ? AND challenge_number = ?""",
                (submission, evaluation_json, user_id, module_number, challenge_number)
            )
            conn.commit()

    def complete_challenge(
        self,
        user_id: int,
        module_number: int,
        challenge_number: int
    ):
        """
        Mark a challenge as completed

        Args:
            user_id: User ID
            module_number: Module number
            challenge_number: Challenge number
        """
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE challenge_progress
                   SET status = 'completed',
                       completed_at = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_id = ? AND module_number = ? AND challenge_number = ?""",
                (user_id, module_number, challenge_number)
            )
            conn.commit()

    def get_module_progress(self, user_id: int, module_number: int) -> List[Dict[str, Any]]:
        """
        Get progress for all challenges in a module

        Args:
            user_id: User ID
            module_number: Module number

        Returns:
            List of challenge progress dicts
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM challenge_progress
                   WHERE user_id = ? AND module_number = ?
                   ORDER BY challenge_number""",
                (user_id, module_number)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_all_progress(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get progress for all challenges across all modules

        Args:
            user_id: User ID

        Returns:
            List of all challenge progress dicts
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM challenge_progress
                   WHERE user_id = ?
                   ORDER BY module_number, challenge_number""",
                (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_current_challenge(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the current in-progress challenge, or the first incomplete challenge

        Args:
            user_id: User ID

        Returns:
            Challenge progress dict or None if all completed
        """
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM challenge_progress
                   WHERE user_id = ? AND status = 'in_progress'
                   ORDER BY module_number, challenge_number
                   LIMIT 1""",
                (user_id,)
            ).fetchone()

            if not row:
                row = conn.execute(
                    """SELECT * FROM challenge_progress
                       WHERE user_id = ? AND status = 'not_started'
                       ORDER BY module_number, challenge_number
                       LIMIT 1""",
                    (user_id,)
                ).fetchone()

            return dict(row) if row else None


    def initialize_module_progress(self, user_id: int, module_number: int, num_challenges: int):
        """
        Create progress entries for all challenges in a module
        All challenges start as accessible (not_started)

        Args:
            user_id: User ID
            module_number: Module number
            num_challenges: Total number of challenges in module
        """
        with self._get_connection() as conn:
            for i in range(1, num_challenges + 1):
                conn.execute(
                    """INSERT INTO challenge_progress
                       (user_id, module_number, challenge_number, status)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(user_id, module_number, challenge_number) DO NOTHING""",
                    (user_id, module_number, i, 'not_started')
                )
            conn.commit()

    def unlock_next_challenge(self, user_id: int, module_number: int, current_challenge: int) -> bool:
        """
        Legacy method - no longer needed as all challenges are accessible

        Args:
            user_id: User ID
            module_number: Module number
            current_challenge: Just completed challenge number

        Returns:
            Always returns True
        """
        return True

    def get_progress_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get overall progress summary for dashboard

        Args:
            user_id: User ID

        Returns:
            Progress summary with counts by module and status
        """
        with self._get_connection() as conn:
            summary = conn.execute(
                """SELECT
                       module_number,
                       COUNT(*) as total,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                       SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                       SUM(CASE WHEN status = 'not_started' THEN 1 ELSE 0 END) as not_started
                   FROM challenge_progress
                   WHERE user_id = ?
                   GROUP BY module_number
                   ORDER BY module_number""",
                (user_id,)
            ).fetchall()

            return {
                'modules': [dict(row) for row in summary],
                'total_completed': sum(row['completed'] for row in summary),
                'total_challenges': sum(row['total'] for row in summary)
            }
