"""
State schema for the LangGraph challenge workflow
Defines the complete state structure used across all agent nodes
"""

from typing import TypedDict, List, Dict, Any, Optional


class ChallengeState(TypedDict, total=False):
    """
    State schema for the challenge processing pipeline

    This state flows through the entire LangGraph workflow,
    being updated by each agent node as the challenge progresses.
    """

    module_number: int  # Module number
    challenge_number: int  # Challenge number within module 
    challenge_data: Dict[str, Any]  # Challenge metadata from 
    experience_level: str  # Beginner, Intermediate, or Advanced
    learning_goal_type: str  # code-focused, concept-focused, or hybrid

    unified_resource_book: str  # Resource Agent output (structured text book)
    lesson_markdown: str  # Tutor Agent output (MARKDOWN format)
    coding_challenge: Dict[str, Any]  # Coding Challenge Agent output
    evaluation: Dict[str, Any]  # Code Evaluator Agent output
    remediation: Dict[str, Any]  # Remediation Agent output

    user_code: str  # User's submitted code
    attempt_count: int  # Number of submission attempts
    submission_history: List[Dict[str, Any]]  # List of {submission, evaluation, timestamp}

    status: str  
                 # "gathering_resources" | "lesson_ready" | "awaiting_code" |
                 # "evaluating" | "passed" | "needs_remediation"
    max_attempts: int # optional

    session_id: str  # Unique session identifier for checkpointing
    user_id: int  # User ID from database
    started_at: str  
    completed_at: Optional[str] 

    error: Optional[str]  
    error_node: Optional[str] 
