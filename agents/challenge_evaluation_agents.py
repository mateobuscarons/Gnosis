"""
Challenge, Evaluation, and Remediation Agents - Complete Flow

This module contains three interconnected agents that form the challenge-submission-feedback loop:
1. Coding Challenge Agent - Creates pedagogically optimized challenges
2. Code Evaluator Agent - Evaluates submissions without execution
3. Remediation Agent - Provides progressive hints on failure

Flow: Challenge → User Submission → Evaluation → Pass/Fail → (if fail) Remediation → Retry
"""

import os
import json
import re
import time
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

load_dotenv()

CHALLENGE_LLM_CONFIG = ("groq", "llama-3.3-70b-versatile")

EVALUATOR_LLM_CONFIG = ("groq", "llama-3.3-70b-versatile")

REMEDIATION_LLM_CONFIG = ("groq", "llama-3.3-70b-versatile")


def create_llm(provider: str, model_name: str):
    """Create LLM instance based on provider and model."""
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0,
            max_output_tokens=4000,
        )
    elif provider == "groq":
        return ChatGroq(
            model=model_name,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0,
            max_tokens=8000,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

def log_token_usage(response, call_type: str, provider: str, model_name: str):
    """Log token usage from LLM response (only for gpt-oss-120b)."""
    if "gpt-oss-120b" not in model_name:
        return

    try:
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if provider == "groq" and hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if isinstance(metadata, dict) and 'token_usage' in metadata:
                usage = metadata['token_usage']
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)

        elif provider == "gemini" and hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            input_tokens = getattr(usage, 'input_tokens', 0) or getattr(usage, 'prompt_tokens', 0)
            output_tokens = getattr(usage, 'output_tokens', 0) or getattr(usage, 'completion_tokens', 0)
            total_tokens = getattr(usage, 'total_tokens', 0) or (input_tokens + output_tokens)

        if total_tokens > 0:
            print(f"  📊 [{call_type}] {model_name}: {total_tokens} tokens (in: {input_tokens}, out: {output_tokens})")
    except Exception:
        pass

def create_challenge_llm():
    """Initialize Coding Challenge Agent LLM with configured model."""
    return create_llm(CHALLENGE_LLM_CONFIG[0], CHALLENGE_LLM_CONFIG[1])

def create_evaluator_llm():
    """Initialize Code Evaluator Agent LLM with configured model."""
    return create_llm(EVALUATOR_LLM_CONFIG[0], EVALUATOR_LLM_CONFIG[1])

def create_remediation_llm():
    """Initialize Remediation Agent LLM with configured model."""
    return create_llm(REMEDIATION_LLM_CONFIG[0], REMEDIATION_LLM_CONFIG[1])

def generate_coding_challenge(
    llm: ChatGoogleGenerativeAI,
    lesson_markdown: str,
    challenge_data: Dict[str, Any],
    experience_level: str,
    learning_goal_type: str = "hybrid"
) -> Dict[str, Any]:
    """
    Creates a pedagogically optimized challenge based on the lesson.

    Autonomously decides whether the challenge should be:
    - Code-based (write/complete code)
    - Conceptual (explain, analyze, diagram)

    Args:
        llm: Gemini LLM instance
        lesson_markdown: Full lesson from Tutor Agent
        challenge_data: Challenge metadata (learning_objective, description)
        experience_level: Student's level
        learning_goal_type: code-focused, concept-focused, or hybrid (helps inform decision)

    Returns:
        Dictionary with challenge details, format, success criteria, and hints bank
    """

    prompt = f"""You are a pedagogical expert creating a learning challenge based on a technical lesson.
Your job is to transform a lesson into ONE high-quality assessment challenge that tests understanding through **active recall, application, and real-world scenario transfer**.

---------------------------------------------------------------------------
## LESSON CONTENT:
{lesson_markdown}

## CHALLENGE CONTEXT:
Learning Objective: {challenge_data['learning_objective']}
Description: {challenge_data['description']}
Student Level: {experience_level}
Learning Goal Type: {learning_goal_type}
---------------------------------------------------------------------------

# 🎯 YOUR TASK
Analyze the lesson and create ONE specific, testable challenge that effectively assesses understanding of the learning objective.

The challenge must:
1. Require **active recall** (no copy/paste from the lesson).
2. Require **application to a NEW scenario**, not a mutation of the lesson example.
3. Be **real-world**, practical, and level-appropriate.
4. Be **non-trivial**, requiring reasoning or construction.
5. Stay tightly aligned with the *specific learning objective*, not the entire lesson.
6. Remain strictly within the learner’s **current conceptual scope** — do NOT introduce tools, workflows, architectures, or multi-component systems that were NOT taught in the lesson.

---------------------------------------------------------------------------

# 🔒 LEARNING SCOPE GUARDRAIL (IMPORTANT)
To maintain instructional alignment:

- The challenge MUST test the SAME cognitive skill as the learning objective.
- The challenge MUST involve ONLY concepts directly taught in the lesson.
- The challenge MUST NOT introduce:
  - New technologies (e.g., docker-compose, Kubernetes, Databases, caching layers)
  - Multi-service architectures
  - Multi-environment pipelines
  - System design considerations not included in the lesson
  - Tools, flags, workflows, abstractions not taught

You may change the scenario, but not the conceptual level.

Example:
If the lesson taught “what containers are + docker build/run/images,”  
the challenge can apply these concepts to a **new application**,  
but MUST NOT require container orchestration, multi-service stacks, volumes, networks, or databases.

---------------------------------------------------------------------------

# 🧠 SCENARIO TRANSFORMATION RULE
You MUST generate a scenario that is meaningfully different from the lesson example.

Minimal acceptable transformation:
- New application purpose
- New operational context
- New constraints or goals
- At least 3 elements must differ

You may NOT simply:
- Change image names
- Change labels or ports while keeping the pattern
- Retell the same scenario with surface-level changes

BUT the scenario must still:
- Fit the learning objective
- Stay within the conceptual boundaries of the lesson (NO scope creep)

---------------------------------------------------------------------------

# 🎯 CRITICAL DECISION: CHALLENGE FORMAT
Choose the format that BEST tests THIS learning objective:

**"code" challenge**
- For implementing or constructing something using syntax, logic, or configuration.
- Ideal for objectives requiring creation of artifacts.

**"conceptual" challenge**
- For understanding, reasoning, debugging, or analysis.
- Ideal for objectives involving conceptual correctness or design rationale.

Choose whichever yields the **highest assessment quality** for THIS learning objective.

---------------------------------------------------------------------------

# 🧩 CODE CHALLENGE DESIGN STRATEGY

Your job is to provide **just enough structure** to reduce friction but **never leak the solution**.

## 🚨 TWO DISTINCT MODES: PROGRAMMING vs CONFIGURATION
Follow these rules:

### 1. PROGRAMMING CHALLENGES (Python, JS, SQL, Bash, algorithms)
Allowed scaffolding:
- Function signatures
- Imports
- TODO markers **inside** functions/classes

Rules:
- NEVER include working examples of the solution.
- NEVER outline the logic.
- ONLY scaffold the environment.

### 2. CONFIGURATION CHALLENGES (YAML, Kubernetes, Terraform, JSON, INI)
Configuration structure **IS the solution**, so:

🚫 NEVER provide:
- Keys
- Nesting
- Indentation
- Placeholder values
- Partial manifest skeletons

✅ Provide only:
# File: <filename>.yaml
# TODO 1: ...
# TODO 2: ...
# TODO 3: ...

Nothing else.

---------------------------------------------------------------------------

# 🧩 CONCEPTUAL CHALLENGE DESIGN STRATEGY

Conceptual challenges must:
- Be scenario-driven
- Require application
- Use 2–3 focused aspects max
- Avoid broad, open-ended prompts

Prefer:
- Analyze a situation
- Apply a concept to a realistic scenario
- Debug reasoning
- Choose between alternatives

Avoid:
- "Explain everything"
- Multi-part essays

---------------------------------------------------------------------------

# 🟦 OUTPUT FORMAT (STRICT)
Return ONLY valid JSON.
Escape all quotes and newlines.

{{
  "challenge_format": "code" OR "conceptual",
  "challenge_prompt": "Clear description of what the student must do",
  "starter_code": "Scaffold ONLY if code challenge; null for conceptual",
  "expected_approach": "Thinking steps WITHOUT listing syntax, YAML keys, or full logic",
  "success_criteria": [
    "Specific requirement 1",
    "Specific requirement 2",
    "Specific requirement 3"
  ],
  "hints_bank": [
    "Level 1 hint: General nudge",
    "Level 2 hint: More targeted direction",
    "Level 3 hint: Nearly gives the answer"
  ]
}}

---------------------------------------------------------------------------

# 🔍 FINAL SELF-CHECK BEFORE RETURNING JSON

The model must verify:

1. The challenge is aligned with the learning objective **AND** remains within lesson scope.
2. The scenario is NEW, non-trivial, and NOT a mutation of the lesson example.
3. If challenge_format = "conceptual": starter_code = null.
4. If challenge_format = "code" AND configuration-related:
   - starter_code contains ONLY filename + TODO lines.
   - No YAML keys, values, or structure appear anywhere.
5. expected_approach does NOT reveal specific syntax, keys, or the solution.
6. success_criteria refer ONLY to observable aspects of the student's answer.
7. No contradictions, no scope creep, and no introduction of new technologies.

If any violation occurs → regenerate the entire output to comply.

---------------------------------------------------------------------------

Generate the challenge now:"""

    response = llm.invoke(prompt)
    response_text = response.content.strip()

    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        challenge = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"      ⚠️  coding_challenge_agent error: {e}")
        print(f"      Attempting to fix common JSON issues...")

        try:
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            challenge = json.loads(response_text)
            print(f"      ✓ JSON fixed and parsed successfully")
        except json.JSONDecodeError as e2:
            print(f"      ❌ JSON parsing still failed: {e2}")
            print(f"      Raw response (first 500 chars):\n{response_text[:500]}")
            raise Exception(f"Failed to parse JSON from LLM response: {e2}")

    return challenge

def run_coding_challenge_agent(
    lesson_markdown: str,
    challenge_data: Dict[str, Any],
    experience_level: str = "Intermediate",
    learning_goal_type: str = "hybrid",
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for Coding Challenge Agent.

    Returns:
        Dictionary with challenge details ready for UI display
    """

    print(f"      🎯 Coding Challenge Agent: Creating challenge for '{challenge_data['title']}'")
    print(f"         Level: {experience_level}, Type: {learning_goal_type}")

    llm = create_challenge_llm()

    t1 = time.time()
    challenge = generate_coding_challenge(
        llm,
        lesson_markdown,
        challenge_data,
        experience_level,
        learning_goal_type
    )
    print(f"         ⏱️  Challenge generation: {time.time()-t1:.1f}s (format: {challenge['challenge_format']}, {len(challenge['success_criteria'])} criteria)")

    return {
        "coding_challenge": challenge,
        "lesson_markdown": lesson_markdown,
        "challenge_data": challenge_data,
        "experience_level": experience_level
    }

def evaluate_submission(
    llm: ChatGoogleGenerativeAI,
    user_submission: str,
    coding_challenge: Dict[str, Any],
    experience_level: str
) -> Dict[str, Any]:
    """
    Evaluates user submission without code execution.

    Uses LLM reasoning to assess correctness against success criteria.
    Works for both code and conceptual submissions.

    Args:
        llm: LLM instance
        user_submission: Student's code or written response
        coding_challenge: Challenge details from Coding Challenge Agent
        experience_level: Student's level

    Returns:
        Evaluation dictionary with pass/fail and detailed feedback
    """

    challenge_format = coding_challenge['challenge_format']

    prompt = f"""You are an expert technical evaluator assessing a student's submission.

CHALLENGE DETAILS:
Format: {challenge_format}
Prompt: {coding_challenge['challenge_prompt']}

SUCCESS CRITERIA:
{chr(10).join(f"- {criterion}" for criterion in coding_challenge['success_criteria'])}

EXPECTED APPROACH:
{coding_challenge['expected_approach']}

STUDENT'S SUBMISSION:
{user_submission}

YOUR TASK:
Evaluate the submission WITHOUT executing code. Use your reasoning to assess correctness.

**EVALUATION CRITERIA:**
1. **Correctness** - Does it meet all success criteria?
2. **Code Quality** (if code) - Proper syntax, structure, best practices?
3. **Completeness** - Are all requirements addressed?

**EVALUATION GUIDELINES:**

**For CODE challenges:**
- Analyze logic, check imports, verify approach matches expected solution
- Look for syntax errors, logic flaws, missing components
- Be specific: Point to exact lines or sections with issues

**For CONCEPTUAL challenges:**
- Accept MULTIPLE valid explanations - there's rarely one "right answer"
- Check if core concepts are understood, even if explanation differs from expected approach
- Evaluate depth, accuracy, clarity, and use of examples
- Don't penalize different but valid perspectives or explanation styles
- Focus on whether they demonstrate understanding, not whether they used exact wording

**General Guidelines:**
- Be constructive: Identify what works AND what doesn't
- Consider {experience_level} level (be appropriately lenient/strict)
- For Beginners: More lenient, focus on core understanding
- For Advanced: Expect nuanced explanations, edge cases, production concerns

**OUTPUT FORMAT:**
Return ONLY a JSON object:

{{
  "passed": true/false,
  "score": 0-100,
  "errors": ["Specific issue 1", "Specific issue 2"],
  "feedback": "Overall assessment paragraph explaining what's right and what's wrong",
  "what_worked": ["Positive aspect 1", "Positive aspect 2"],
  "what_needs_work": ["Issue 1 with location", "Issue 2 with location"],
}}

**IMPORTANT:**
- If submission fully meets all success criteria → passed: true
- If missing any critical requirement → passed: false
- Be specific in errors (e.g., "Missing StrOutputParser import" not "Missing import")
- Score reflects both correctness and quality
- Always include at least one "what_worked" (encourage learning)

Evaluate the submission now:"""

    response = llm.invoke(prompt)
    response_text = response.content.strip()

    # Extract JSON from markdown code blocks if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    # Try to parse JSON with error handling
    try:
        evaluation = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"      ⚠️  evaluation_agent error: {e}")
        print(f"      Attempting to fix common JSON issues...")

        try:
            # Remove any trailing commas before } or ]
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            evaluation = json.loads(response_text)
            print(f"      ✓ JSON fixed and parsed successfully")
        except json.JSONDecodeError as e2:
            print(f"      ❌ JSON parsing still failed: {e2}")
            print(f"      Raw response (first 500 chars):\n{response_text[:500]}")
            raise Exception(f"Failed to parse JSON from LLM response: {e2}")

    return evaluation

def run_code_evaluator_agent(
    user_submission: str,
    coding_challenge: Dict[str, Any],
    experience_level: str = "Intermediate",
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for Code Evaluator Agent.

    Returns:
        Dictionary with evaluation results
    """

    if verbose:
        print(f"📊 Code Evaluator Agent: Evaluating submission...")
        print(f"   Challenge format: {coding_challenge['challenge_format']}")

    llm = create_evaluator_llm()

    evaluation = evaluate_submission(
        llm,
        user_submission,
        coding_challenge,
        experience_level
    )

    if verbose:
        print(f"   Result: {'✅ PASSED' if evaluation['passed'] else '❌ FAILED'}")
        print(f"   Score: {evaluation['score']}/100")
        print(f"   Errors found: {len(evaluation['errors'])}")
        print("✅ Code Evaluator Agent complete")

    return {
        "evaluation": evaluation,
        "coding_challenge": coding_challenge,
        "user_submission": user_submission,
        "experience_level": experience_level
    }

def generate_remediation(
    llm: ChatGoogleGenerativeAI,
    evaluation: Dict[str, Any],
    coding_challenge: Dict[str, Any],
    attempt_count: int,
    user_submission: str
) -> Dict[str, Any]:
    """
    Provides progressive hints based on attempt count.

    Level 1 (attempt 1): General direction
    Level 2 (attempt 2): Point to specific issue
    Level 3 (attempt 3+): Nearly give answer

    Args:
        llm: LLM instance
        evaluation: Evaluation results from Code Evaluator
        coding_challenge: Original challenge with hints bank
        attempt_count: Number of attempts (determines hint level)
        user_submission: Student's failed submission

    Returns:
        Remediation dictionary with targeted hint and encouragement
    """
    hint_level = min(attempt_count, 3)

    prompt = f"""You are a supportive coding tutor providing remediation after a failed submission.

CHALLENGE:
{coding_challenge['challenge_prompt']}

STUDENT'S SUBMISSION:
{user_submission}

EVALUATION RESULTS:
Passed: {evaluation['passed']}
Score: {evaluation['score']}/100
Errors: {', '.join(evaluation['errors'])}
What Needs Work: {', '.join(evaluation['what_needs_work'])}

ATTEMPT COUNT: {attempt_count}
HINT LEVEL: {hint_level}/3

HINTS BANK (for guidance):
{chr(10).join(f"Level {i+1}: {hint}" for i, hint in enumerate(coding_challenge['hints_bank']))}

YOUR TASK:
Provide targeted remediation at Level {hint_level} specificity:
- **Level 1**: General direction, encourage thinking
- **Level 2**: Point to specific issue or missing element
- **Level 3**: Nearly give the solution (but don't write it for them)

**REMEDIATION PRINCIPLES:**
1. Be encouraging (they're learning!)
2. Build on what they got right
3. Guide, don't solve
4. Progressive disclosure (respect hint level)

**OUTPUT FORMAT:**
Return ONLY a JSON object:

{{
  "hint_level": {hint_level},
  "targeted_hint": "Specific hint at level {hint_level} that addresses the main error",
  "encouragement": "Positive, motivating message about what they got right",
  "key_concept_reminder": "Brief reminder of the lesson concept they need to apply"
}}

**EXAMPLES:**

Level 1 Response:
- targeted_hint: "Think about the flow of data through your chain. What component processes the LLM's output?"
- encouragement: "Great job setting up the LLM and prompt! Your structure is on the right track."

Level 2 Response:
- targeted_hint: "You're missing the StrOutputParser component. Check the lesson's 'Incremental Build-Up' section, Step 3."
- encouragement: "Your chain logic is correct! You're very close - just missing one component."

Level 3 Response:
- targeted_hint: "Add this after your llm: `from langchain_core.output_parsers import StrOutputParser` and include it in your chain: `chain = prompt | llm | StrOutputParser()`"
- encouragement: "You've almost got it! Just need to add the output parser to convert the response to a string."

Generate remediation now:"""

    response = llm.invoke(prompt)
    response_text = response.content.strip()

    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    try:
        remediation = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"      ⚠️  remediation_agent error: {e}")
        print(f"      Attempting to fix common JSON issues...")

        try:
            response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            remediation = json.loads(response_text)
            print(f"      ✓ JSON fixed and parsed successfully")
        except json.JSONDecodeError as e2:
            print(f"      ❌ JSON parsing still failed: {e2}")
            print(f"      Raw response (first 500 chars):\n{response_text[:500]}")
            raise Exception(f"Failed to parse JSON from LLM response: {e2}")

    return remediation

def run_remediation_agent(
    evaluation: Dict[str, Any],
    coding_challenge: Dict[str, Any],
    user_submission: str,
    attempt_count: int = 1,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for Remediation Agent.

    Returns:
        Dictionary with remediation guidance
    """

    if verbose:
        print(f"💡 Remediation Agent: Generating hint (attempt {attempt_count})...")
        hint_level = min(attempt_count, 3)
        print(f"   Hint level: {hint_level}/3")

    llm = create_remediation_llm()

    remediation = generate_remediation(
        llm,
        evaluation,
        coding_challenge,
        attempt_count,
        user_submission
    )

    if verbose:
        print(f"   Hint provided: {remediation['targeted_hint']}")
        print("✅ Remediation Agent complete")

    return {
        "remediation": remediation,
        "evaluation": evaluation,
        "coding_challenge": coding_challenge,
        "attempt_count": attempt_count
    }
 