"""
LangGraph workflow for the challenge processing pipeline
Orchestrates all agents in a stateful, checkpointed workflow
"""

from typing import Literal
from datetime import datetime
import time

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from challenge_state import ChallengeState
from agents.tutor_agent import run_tutor_agent # type: ignore
from agents.challenge_evaluation_agents import (
    run_coding_challenge_agent,
    run_code_evaluator_agent,
    run_remediation_agent
)

def tutor_agent_node(state: ChallengeState) -> ChallengeState:
    """
    Tutor Agent Node: Creates personalized markdown lesson with context awareness

    Updates state with:
        - lesson_markdown
        - status -> "lesson_ready"
    """
    try:
        start_time = time.time()
        print(f"   ⏱️  Tutor Agent starting...")

        from database.db_operations import Database

        db = Database()
        user_id = state.get("user_id")
        module_number = state.get("module_number")
        challenge_number = state.get("challenge_number")

        past_challenges = []
        future_challenges = []
        module_context = {}

        if user_id and module_number and challenge_number:
            module_challenges = db.get_module_challenges(user_id, module_number)

            if module_challenges:
                module_context = module_challenges.get("module", {})

                all_challenges = module_challenges["challenge_roadmap"]["challenges"]

                past_challenges = [c for c in all_challenges if c["challenge_number"] < challenge_number]
                future_challenges = [c for c in all_challenges if c["challenge_number"] > challenge_number]

        result = run_tutor_agent(
            challenge_data=state["challenge_data"],
            experience_level=state["experience_level"],
            past_challenges=past_challenges,
            future_challenges=future_challenges,
            module_context=module_context
        )

        elapsed = time.time() - start_time
        print(f"   ✅ Tutor Agent completed in {elapsed:.1f}s")

        return {
            **state,
            "lesson_markdown": result["lesson_markdown"],
            "status": "lesson_ready"
        }
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"   ❌ Tutor Agent failed after {elapsed:.1f}s: {str(e)}")
        return {
            **state,
            "error": str(e),
            "error_node": "tutor_agent",
            "status": "error"
        }


def coding_challenge_agent_node(state: ChallengeState) -> ChallengeState:
    """
    Coding Challenge Agent Node: Creates the coding challenge

    Updates state with:
        - coding_challenge
        - status -> "awaiting_code"
    """
    try:
        start_time = time.time()
        print(f"   ⏱️  Coding Challenge Agent starting...")

        result = run_coding_challenge_agent(
            lesson_markdown=state["lesson_markdown"],
            challenge_data=state["challenge_data"],
            experience_level=state["experience_level"],
            learning_goal_type=state.get("learning_goal_type", "hybrid")
        )

        elapsed = time.time() - start_time
        print(f"   ✅ Coding Challenge Agent completed in {elapsed:.1f}s")

        return {
            **state,
            "coding_challenge": result["coding_challenge"],
            "status": "awaiting_code"
        }
    except Exception as e:
        elapsed = time.time() - start_time if 'start_time' in locals() else 0
        print(f"   ❌ Coding Challenge Agent failed after {elapsed:.1f}s: {str(e)}")
        return {
            **state,
            "error": str(e),
            "error_node": "coding_challenge_agent",
            "status": "error"
        }


def await_code_node(state: ChallengeState) -> ChallengeState:
    """
    Await Code Node: Interrupt point for user code submission

    This is where the graph pauses and waits for user input.
    When resumed, user_code should be populated in the state.

    Updates state with:
        - status -> "evaluating"
    """
    if not state.get("user_code"):
        return {
            **state,
            "error": "No user code submitted",
            "status": "awaiting_code"
        }

    return {
        **state,
        "status": "evaluating"
    }


def code_evaluator_node(state: ChallengeState) -> ChallengeState:
    """
    Code Evaluator Agent Node: Evaluates user submission

    Updates state with:
        - evaluation
        - attempt_count (incremented)
        - submission_history (appended)
        - status -> "passed" | "needs_remediation"
    """
    try:
        result = run_code_evaluator_agent(
            user_submission=state["user_code"],
            coding_challenge=state["coding_challenge"],
            experience_level=state["experience_level"]
        )

        attempt_count = state.get("attempt_count", 0) + 1

        submission_history = state.get("submission_history", [])
        submission_history.append({
            "attempt": attempt_count,
            "submission": state["user_code"],
            "evaluation": result["evaluation"],
            "timestamp": datetime.now().isoformat()
        })

        if result["evaluation"]["passed"]:
            status = "passed"
            completed_at = datetime.now().isoformat()
        else:
            status = "needs_remediation"
            completed_at = None

        return {
            **state,
            "evaluation": result["evaluation"],
            "attempt_count": attempt_count,
            "submission_history": submission_history,
            "status": status,
            "completed_at": completed_at
        }
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "error_node": "code_evaluator",
            "status": "error"
        }


def remediation_agent_node(state: ChallengeState) -> ChallengeState:
    """
    Remediation Agent Node: Provides progressive hints on failure

    Updates state with:
        - remediation
        - status -> "awaiting_code" (ready for retry)
        - user_code -> None (clear for next attempt)
    """
    try:
        result = run_remediation_agent(
            evaluation=state["evaluation"],
            coding_challenge=state["coding_challenge"],
            user_submission=state["user_code"],
            attempt_count=state["attempt_count"]
        )

        return {
            **state,
            "remediation": result["remediation"],
            "status": "awaiting_code",
            "user_code": None 
        }
    except Exception as e:
        return {
            **state,
            "error": str(e),
            "error_node": "remediation_agent",
            "status": "error"
        }


def route_evaluation(state: ChallengeState) -> Literal["complete", "retry"]:
    """
    Decides what happens after code evaluation

    Routes to:
        - "complete": Challenge passed
        - "retry": Failed, provide remediation and allow retry (infinite attempts)
    """

    if state.get("error"):
        print(f"      → Routing: retry (had error, allowing retry)")
        return "retry"

    if state.get("evaluation", {}).get("passed", False):
        print(f"      → Routing: complete (passed)")
        return "complete"

    attempt_count = state.get("attempt_count", 0)
    print(f"      → Routing: retry (attempt {attempt_count}, unlimited attempts)")
    return "retry"


def create_challenge_workflow(checkpointer_db_path: str = "challenge_sessions.db"):
    """
    Creates the compiled LangGraph workflow for challenge processing

    Args:
        checkpointer_db_path: Path to SQLite database for checkpointing

    Returns:
        Compiled StateGraph application
    """

    workflow = StateGraph(ChallengeState)

    workflow.add_node("tutor_agent", tutor_agent_node)
    workflow.add_node("coding_challenge_agent", coding_challenge_agent_node)
    workflow.add_node("await_code", await_code_node)
    workflow.add_node("code_evaluator", code_evaluator_node)
    workflow.add_node("remediation_agent", remediation_agent_node)

    workflow.set_entry_point("tutor_agent")

    workflow.add_edge("tutor_agent", "coding_challenge_agent")
    workflow.add_edge("coding_challenge_agent", "await_code")
    workflow.add_edge("await_code", "code_evaluator")

    workflow.add_conditional_edges(
        "code_evaluator",
        route_evaluation,
        {
            "complete": END,
            "retry": "remediation_agent"
        }
    )

    workflow.add_edge("remediation_agent", "await_code")

    import sqlite3
    conn = sqlite3.connect(checkpointer_db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["await_code"]
    )

    return app


def create_initial_state(
    user_id: int,
    module_number: int,
    challenge_number: int,
    challenge_data: dict,
    experience_level: str,
    learning_goal_type: str = "hybrid",
    max_attempts: int = 3
) -> ChallengeState:
    """
    Creates initial state for starting a new challenge

    Args:
        user_id: User ID from database
        module_number: Module number (1-indexed)
        challenge_number: Challenge number (1-indexed)
        challenge_data: Challenge metadata from module challenges JSON
        experience_level: Beginner, Intermediate, or Advanced
        learning_goal_type: code-focused, concept-focused, or hybrid
        max_attempts: Maximum allowed attempts (default: 3)

    Returns:
        Initial ChallengeState
    """
    session_id = f"user_{user_id}_m{module_number}_c{challenge_number}"

    return {
        "user_id": user_id,
        "module_number": module_number,
        "challenge_number": challenge_number,
        "challenge_data": challenge_data,
        "experience_level": experience_level,
        "learning_goal_type": learning_goal_type,
        "max_attempts": max_attempts,
        "session_id": session_id,
        "started_at": datetime.now().isoformat(),
        "attempt_count": 0,
        "submission_history": [],
        "status": "creating_lesson"
    }


def get_thread_config(session_id: str) -> dict:
    """
    Creates LangGraph thread configuration for a session

    Args:
        session_id: Unique session identifier

    Returns:
        Config dict with thread_id
    """
    return {
        "configurable": {
            "thread_id": session_id
        }
    }
