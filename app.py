"""
FastAPI Backend for Adaptive Learning OS
Exposes REST API for the complete learning workflow
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


USE_ENHANCED_LEARNING_PATH = True  
# Change this to True for web search capabilities
# Can only be done once a day MAX

if USE_ENHANCED_LEARNING_PATH:
    from agents.learning_path_agent_enhanced import LearningPathAgentEnhanced as LearningPathAgent, ExperienceLevel
    print("🔍 Using ENHANCED Learning Path Agent (with web search)")
else:
    from agents.learning_path_agent import LearningPathAgent, ExperienceLevel
    print("📚 Using STANDARD Learning Path Agent")

from agents.module_planner_agent import ModulePlannerAgent
from agents.tutor_agent import clean_mermaid_syntax

from database.db_operations import Database

from challenge_graph import (
    create_challenge_workflow,
    create_initial_state,
    get_thread_config
)

app = FastAPI(
    title="Adaptive Learning OS API",
    description="Backend API for personalized technical learning with AI agents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database(db_path="learning_system.db")
challenge_app = create_challenge_workflow(checkpointer_db_path="challenge_sessions.db")


class SetupRequest(BaseModel):
    """Initial setup request"""
    learning_goal: str
    experience_level: str 


class PathApprovalRequest(BaseModel):
    """Learning path approval/editing request"""
    learning_path: Dict[str, Any] 


class SubmissionRequest(BaseModel):
    """Code submission request"""
    code: str


class SessionResponse(BaseModel):
    """Session state response"""
    state: str 
    user_profile: Optional[Dict[str, Any]] = None
    learning_path: Optional[Dict[str, Any]] = None
    current_challenge: Optional[Dict[str, Any]] = None
    progress_summary: Optional[Dict[str, Any]] = None

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Adaptive Learning OS API",
        "version": "1.0.0"
    }


@app.get("/session", response_model=SessionResponse)
def get_session():
    """
    Load or initialize user session

    Returns:
        - new_user: No user exists, need to run setup
        - path_approval: Learning path generated, awaiting approval
        - dashboard: Learning path approved, ready to start challenges
        - challenge_active: Currently in a challenge
    """
    user = db.get_first_user_profile()
    print(f"🔍 /session: User found: {user is not None} (ID: {user['id'] if user else 'N/A'})")

    if not user:
        print(f"   → Returning state: new_user (no user)")
        return SessionResponse(
            state="new_user",
            user_profile=None,
            learning_path=None,
            current_challenge=None,
            progress_summary=None
        )

    learning_path = db.get_learning_path(user["id"])
    print(f"   Learning path found: {learning_path is not None}")

    if not learning_path:
        print(f"   → Returning state: new_user (user exists but no learning path)")
        return SessionResponse(
            state="new_user",
            user_profile=user,
            learning_path=None,
            current_challenge=None,
            progress_summary=None
        )

    module_challenges = db.get_all_module_challenges(user["id"])

    if not module_challenges:
        return SessionResponse(
            state="path_approval",
            user_profile=user,
            learning_path=learning_path,
            current_challenge=None,
            progress_summary=None
        )

    current_challenge = db.get_current_challenge(user["id"])
    progress_summary = db.get_progress_summary(user["id"])

    state = "challenge_active" if current_challenge else "dashboard"

    return SessionResponse(
        state=state,
        user_profile=user,
        learning_path=learning_path,
        current_challenge=current_challenge,
        progress_summary=progress_summary
    )


@app.post("/setup")
def setup(request: SetupRequest):
    """
    Initial setup - Generate learning path

    Process:
        1. Get or create user profile (single-user MVP)
        2. Run Learning Path Agent
        3. Save learning path to database

    Returns:
        - user_id
        - learning_path (for approval/editing)
    """
    try:
        experience_level = ExperienceLevel(request.experience_level)

        existing_user = db.get_first_user_profile()
        if existing_user:
            user_id = existing_user["id"]
            print(f"🔄 Using existing user: {user_id}")
        else:
            user_id = db.create_user_profile(
                learning_goal=request.learning_goal,
                experience_level=experience_level.value
            )

        print(f"🚀 Generating learning path for: {request.learning_goal}")
        agent = LearningPathAgent()
        learning_path_result = agent.run(request.learning_goal, experience_level)

        learning_path_data = {
            "input": {
                "learning_goal": request.learning_goal,
                "experience_level": experience_level.value
            },
            "learning_path": learning_path_result
        }

        path_id = db.save_learning_path(user_id, learning_path_data)
        print(f"✅ Learning path generated: {len(learning_path_result['modules'])} modules")
        verification = db.get_learning_path(user_id)

        return {
            "success": True,
            "user_id": user_id,
            "learning_path": learning_path_data,
            "message": f"Generated {len(learning_path_result['modules'])} modules"
        }

    except ValueError as e:
        if "Invalid experience level" in str(e) or "is not a valid ExperienceLevel" in str(e):
             raise HTTPException(status_code=400, detail=f"Invalid experience level: {request.experience_level}")
        print(f"❌ Setup failed (ValueError): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")
    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@app.post("/path/approve")
def approve_path(request: PathApprovalRequest):
    """
    Approve learning path

    Returns:
        - success
        - total_modules
        - total_challenges
    """
    try:
        user = db.get_first_user_profile()
        if not user:
            raise HTTPException(status_code=404, detail="No user profile found")

        user_id = user["id"]

        db.update_learning_path(user_id, request.learning_path)

        learning_path = request.learning_path["learning_path"]
        experience_level = request.learning_path["input"]["experience_level"]
        learning_goal_type = learning_path.get("learning_goal_type", "hybrid")
        modules = learning_path["modules"]

        print(f"\nGenerating challenges for {len(modules)} modules...")

        agent = ModulePlannerAgent()
        total_challenges = 0

        for module in modules:
            module_num = module["module_number"]
            print(f"   Module {module_num}: {module['title']}")

            challenge_roadmap = agent.run(module, experience_level, learning_goal_type)

            challenges_data = {
                "module": module,
                "experience_level": experience_level,
                "challenge_roadmap": challenge_roadmap
            }

            db.save_module_challenges(user_id, module_num, challenges_data)

            num_challenges = challenge_roadmap["total_challenges"]
            db.initialize_module_progress(user_id, module_num, num_challenges)

            total_challenges += num_challenges
            print(f"       {num_challenges} challenges created")

            if module_num < len(modules):
                print(f"      ⏳ Waiting 10 seconds before next module...")

        print(f"\n Total: {total_challenges} challenges across {len(modules)} modules")

        return {
            "success": True,
            "total_modules": len(modules),
            "total_challenges": total_challenges,
            "message": f"Learning path finalized with {total_challenges} challenges"
        }

    except Exception as e:
        print(f"❌ Path approval failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Path approval failed: {str(e)}")


@app.get("/challenge/{module_number}/{challenge_number}")
def get_challenge(module_number: int, challenge_number: int):
    """
    Get or generate challenge content

    Process:
        1. Check if lesson/challenge already cached
        2. If not, run Resource → Tutor → Challenge Agent workflow
        3. Cache results in database
        4. Return lesson + challenge for display

    Returns:
        - lesson_markdown (ready to render)
        - coding_challenge (prompt, starter_code, etc.)
        - challenge_metadata
        - progress_info
    """
    import time
    start_time = time.time()

    try:
        print(f"\n🔍 GET /challenge/{module_number}/{challenge_number}")
        user = db.get_first_user_profile()
        if not user:
            raise HTTPException(status_code=404, detail="No user profile found")

        user_id = user["id"]

        module_challenges = db.get_module_challenges(user_id, module_number)
        if not module_challenges:
            raise HTTPException(
                status_code=404,
                detail=f"Module {module_number} not found"
            )

        challenges = module_challenges["challenge_roadmap"]["challenges"]
        challenge_data = next(
            (c for c in challenges if c["challenge_number"] == challenge_number),
            None
        )

        if not challenge_data:
            raise HTTPException(
                status_code=404,
                detail=f"Challenge {challenge_number} not found in module {module_number}"
            )

        progress = db.get_challenge_progress(user_id, module_number, challenge_number)

        if progress and progress.get("lesson_markdown") and progress.get("coding_challenge_json"):
            elapsed = time.time() - start_time
            print(f"✅ Challenge loaded from cache in {elapsed:.1f}s")
            cleaned_lesson = clean_mermaid_syntax(progress["lesson_markdown"])
            return {
                "lesson_markdown": cleaned_lesson,
                "coding_challenge": progress["coding_challenge"],
                "challenge_data": challenge_data,
                "progress": {
                    "status": progress["status"],
                    "attempt_count": progress["attempt_count"]
                },
                "cached": True
            }

        print(f"⚠️  Not cached - generating challenge content...")

        learning_goal_type = "hybrid"
        learning_path = db.get_learning_path(user_id)
        if learning_path and "learning_path" in learning_path:
            learning_goal_type = learning_path.get("learning_path", {}).get("learning_goal_type", "hybrid")

        initial_state = create_initial_state(
            user_id=user_id,
            module_number=module_number,
            challenge_number=challenge_number,
            challenge_data=challenge_data,
            experience_level=module_challenges["experience_level"],
            learning_goal_type=learning_goal_type,
            max_attempts=3
        )

        session_id = initial_state["session_id"]
        thread_config = get_thread_config(session_id)

        for event in challenge_app.stream(initial_state, thread_config, stream_mode="updates"):
            for node_name, node_state in event.items():
                if isinstance(node_state, dict) and node_state.get("status") == "error":
                    print(f"      ⚠️  {node_name} error: {node_state.get('error')}")

        current_state = challenge_app.get_state(thread_config)
        state_values = current_state.values

        if "lesson_markdown" not in state_values:
            raise ValueError(f"lesson_markdown not generated. Status: {state_values.get('status')}, Error: {state_values.get('error', 'None')}")

        if not progress:
            db.create_challenge_progress(user_id, module_number, challenge_number, "in_progress")

        db.save_lesson_content(
            user_id,
            module_number,
            challenge_number,
            state_values["lesson_markdown"]
        )

        db.save_coding_challenge(
            user_id,
            module_number,
            challenge_number,
            state_values["coding_challenge"]
        )

        elapsed = time.time() - start_time
        print(f"✅ Challenge generated and cached in {elapsed:.1f}s total")
        cleaned_lesson = clean_mermaid_syntax(state_values["lesson_markdown"])

        return {
            "lesson_markdown": cleaned_lesson,
            "coding_challenge": state_values["coding_challenge"],
            "challenge_data": challenge_data,
            "progress": {
                "status": "in_progress",
                "attempt_count": 0
            },
            "cached": False
        }

    except Exception as e:
        print(f"❌ Failed to get challenge: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get challenge: {str(e)}")


@app.post("/challenge/{module_number}/{challenge_number}/submit")
def submit_challenge(module_number: int, challenge_number: int, request: SubmissionRequest):
    """
    Submit code for evaluation

    Process:
        1. Resume workflow from checkpoint
        2. Update state with submitted code
        3. Run Code Evaluator Agent
        4. If fail → run Remediation Agent
        5. Save evaluation and submission history to database

    Returns:
        - evaluation (passed, score, feedback, etc.)
        - remediation (if failed)
        - status (passed, needs_remediation)
        - attempt_count (unlimited attempts allowed)
    """
    try:
        user = db.get_first_user_profile()
        if not user:
            raise HTTPException(status_code=404, detail="No user profile found")

        user_id = user["id"]

        progress = db.get_challenge_progress(user_id, module_number, challenge_number)
        if not progress:
            raise HTTPException(
                status_code=404,
                detail=f"Challenge {module_number}.{challenge_number} not started"
            )

        if not progress.get("lesson_markdown") or not progress.get("coding_challenge"):
            raise HTTPException(
                status_code=400,
                detail="Challenge content not cached. Please load the challenge first."
            )

        session_id = f"user_{user_id}_m{module_number}_c{challenge_number}"
        thread_config = get_thread_config(session_id)

        print(f"\n📤 Evaluating submission for Module {module_number}, Challenge {challenge_number}")

        challenge_app.update_state(thread_config, {
            "user_code": request.code,
            "lesson_markdown": progress["lesson_markdown"],
            "coding_challenge": progress["coding_challenge"],
            "error": None,
            "error_node": None
        })

        for event in challenge_app.stream(None, thread_config, stream_mode="updates"):
            for node_name, node_state in event.items():
                if isinstance(node_state, dict) and node_state.get("status") == "error":
                    print(f"      ⚠️  {node_name} error: {node_state.get('error')}")

        current_state = challenge_app.get_state(thread_config)
        state_values = current_state.values

        db.record_submission(
            user_id,
            module_number,
            challenge_number,
            request.code,
            state_values["evaluation"]
        )

        if state_values["evaluation"]["passed"]:
            db.complete_challenge(user_id, module_number, challenge_number)
            db.unlock_next_challenge(user_id, module_number, challenge_number)
            print(f"   ✅ Challenge completed!")
        else:
            print(f"   ❌ Failed - Attempt {state_values['attempt_count']}")

        return {
            "evaluation": state_values["evaluation"],
            "remediation": state_values.get("remediation"),
            "status": state_values["status"],
            "attempt_count": state_values["attempt_count"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")


@app.get("/progress")
def get_progress():
    """
    Get overall progress summary with individual challenge completion status

    Returns:
        - modules (list with progress per module and individual challenge status)
        - total_completed
        - total_challenges
        - current_module
        - current_challenge
    """
    try:
        user = db.get_first_user_profile()
        if not user:
            raise HTTPException(status_code=404, detail="No user profile found")

        user_id = user["id"]

        summary = db.get_progress_summary(user_id)
        current_challenge = db.get_current_challenge(user_id)

        # Get individual challenge completion status for each module
        all_progress = db.get_all_progress(user_id)

        # Organize by module for easy lookup
        module_details = {}
        for progress_item in all_progress:
            module_num = progress_item["module_number"]
            challenge_num = progress_item["challenge_number"]

            if module_num not in module_details:
                module_details[module_num] = {}

            module_details[module_num][challenge_num] = {
                "status": progress_item["status"],
                "completed": progress_item["status"] == "completed"
            }

        for module in summary["modules"]:
            module_num = module["module_number"]
            module["challenge_details"] = module_details.get(module_num, {})

        return {
            "modules": summary["modules"],
            "total_completed": summary["total_completed"],
            "total_challenges": summary["total_challenges"],
            "current_challenge": current_challenge,
            "completion_percentage": round(
                (summary["total_completed"] / summary["total_challenges"]) * 100, 1
            ) if summary["total_challenges"] > 0 else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@app.get("/challenges/metadata")
def get_all_challenges_metadata():
    """
    Get all challenge titles and metadata for dashboard display

    Returns:
        Dictionary mapping module_number to list of challenge metadata
    """
    try:
        user = db.get_first_user_profile()
        if not user:
            raise HTTPException(status_code=404, detail="No user profile found")

        user_id = user["id"]

        all_modules = db.get_all_module_challenges(user_id)

        metadata_by_module = {}
        for module_data in all_modules:
            module_num = module_data["module_number"]
            challenges = module_data["challenges"]["challenge_roadmap"]["challenges"]

            metadata_by_module[module_num] = [
                {
                    "challenge_number": c["challenge_number"],
                    "title": c["title"],
                    "learning_objective": c.get("learning_objective", "")
                }
                for c in challenges
            ]

        return metadata_by_module

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get challenges metadata: {str(e)}")


@app.get("/challenges/cached")
def get_cached_challenges():
    """
    Get information about which challenges are already cached

    Returns:
        Dictionary mapping module_number to list of cached challenge numbers
    """
    try:
        user = db.get_first_user_profile()
        if not user:
            raise HTTPException(status_code=404, detail="No user profile found")

        user_id = user["id"]
        all_modules = db.get_all_module_challenges(user_id)

        cached_by_module = {}
        for module_data in all_modules:
            module_num = module_data["module_number"]
            challenges = module_data["challenges"]["challenge_roadmap"]["challenges"]

            cached_challenges = []
            for challenge in challenges:
                challenge_num = challenge["challenge_number"]
                progress = db.get_challenge_progress(user_id, module_num, challenge_num)

                if progress and progress.get("lesson_markdown") and progress.get("coding_challenge_json"):
                    cached_challenges.append(challenge_num)

            if cached_challenges:
                cached_by_module[module_num] = cached_challenges

        return cached_by_module

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cached challenges: {str(e)}")


@app.delete("/reset")
def reset_system():
    """
    Reset the entire system
    """
    try:
        for db_file in ["learning_system.db", "challenge_sessions.db"]:
            if os.path.exists(db_file):
                os.remove(db_file)
            wal_file = f"{db_file}-wal"
            if os.path.exists(wal_file):
                os.remove(wal_file)
            shm_file = f"{db_file}-shm"
            if os.path.exists(shm_file):
                os.remove(shm_file)

        global db, challenge_app
        db = Database(db_path="learning_system.db")
        challenge_app = create_challenge_workflow(checkpointer_db_path="challenge_sessions.db")

        return {
            "success": True,
            "message": "System reset complete"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
