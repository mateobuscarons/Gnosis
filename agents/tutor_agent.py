"""
Tutor Agent - Transforms resource books into personalized markdown lessons.

Autonomous agent that:
1. Receives unified resource book from Resource Agent
2. Receives challenge data and experience level
3. Generates personalized markdown lesson adapted to student's level
4. Returns ready-to-render markdown with theory, examples, and pitfalls
"""

import os
import re
import time
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

load_dotenv()

TUTOR_LLM_CONFIG = ("groq", "moonshotai/kimi-k2-instruct-0905")


def create_llm(provider: str, model_name: str):
    """Create LLM instance based on provider and model."""
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0,
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

def create_tutor_agent():
    """Initialize the Tutor Agent with configured LLM."""
    return create_llm(TUTOR_LLM_CONFIG[0], TUTOR_LLM_CONFIG[1])

def extract_core_concepts_from_lessons(previous_lessons: List[str]) -> str:
    """
    Extract core concepts sections from previous lessons to provide context.

    Args:
        previous_lessons: List of lesson markdown strings from previous challenges

    Returns:
        Extracted concepts as a formatted string
    """
    if not previous_lessons:
        return ""

    all_concepts = []

    for i, lesson in enumerate(previous_lessons, 1):
        pattern = r'## Core Concepts\s*(.*?)(?=\n##|\Z)'
        match = re.search(pattern, lesson, re.DOTALL)

        if match:
            concepts = match.group(1).strip()
            all_concepts.append(f"**Previous Challenge {i}:**\n{concepts}\n")

    if not all_concepts:
        return ""

    return "\n".join(all_concepts)

def generate_lesson_markdown(
    llm,
    challenge_data: Dict[str, Any],
    experience_level: str,
    past_challenges: list = None,
    future_challenges: list = None,
    module_context: Dict[str, Any] = None
) -> str:
    """
    Produces a personalized markdown lesson with context awareness.

    Args:
        llm: LLM instance
        challenge_data: Challenge information from module_X_challenges.json
        experience_level: "Beginner" | "Intermediate" | "Advanced"
        past_challenges: List of challenges already completed (to avoid re-teaching)
        future_challenges: List of challenges coming next (to avoid teaching prematurely)
        module_context: Module information for learning path context

    Returns:
        Markdown-formatted lesson string (ready to render)
    """
    if past_challenges is None:
        past_challenges = []
    if future_challenges is None:
        future_challenges = []
    if module_context is None:
        module_context = {}

    teaching_styles = {
        "Beginner": {
            "tone": "friendly, encouraging, and patient",
            "language": "simple terms with clear explanations of technical jargon",
            "detail_level": "step-by-step with detailed explanations",
            "analogies": "Use everyday analogies and metaphors to explain concepts",
            "assumptions": "Assume minimal prior knowledge"
        },
        "Intermediate": {
            "tone": "professional and direct",
            "language": "standard technical terminology with brief clarifications",
            "detail_level": "focused on key concepts with practical context",
            "analogies": "Use technical analogies when helpful",
            "assumptions": "Assume basic programming knowledge"
        },
        "Advanced": {
            "tone": "concise and technical",
            "language": "advanced technical terminology without over-explaining",
            "detail_level": "high-level overview with focus on nuances and edge cases",
            "analogies": "Use system-level or architectural analogies",
            "assumptions": "Assume strong programming background"
        }
    }

    style = teaching_styles.get(experience_level, teaching_styles["Beginner"])

    learning_path_context = ""
    if module_context:
        module_title = module_context.get('title', 'Current Module')
        module_desc = module_context.get('description', '')
        learning_path_context = f"""
LEARNING PATH CONTEXT:
Module: {module_title}
{module_desc}
"""

    past_context = ""
    if past_challenges:
        past_list = []
        for i, pc in enumerate(past_challenges, 1):
            past_list.append(f"  {i}. {pc['title']}: {pc['learning_objective']}")
        past_context = f"""
WHAT STUDENT ALREADY LEARNED:
{chr(10).join(past_list)}

→ These topics were already covered. Reference them when relevant, but do NOT re-teach them in detail.
→ You can briefly mention them as prerequisites (e.g., "Building on your knowledge of X...").
"""

    future_context = ""
    if future_challenges:
        future_list = []
        for i, fc in enumerate(future_challenges, 1):
            future_list.append(f"  {i}. {fc['title']}: {fc['learning_objective']}")
        future_context = f"""
WHAT WILL BE TAUGHT LATER:
{chr(10).join(future_list)}

→ Do NOT introduce or explain these topics in this lesson.
→ Focus only on what's needed for the current challenge.
"""

    prompt = f"""You are an expert technical instructor. Your task is to create a personalized lesson for a {experience_level} student.

STUDENT STYLE:
- Tone: {style['tone']}
- Language: {style['language']}
- Detail: {style['detail_level']}
- Analogies: {style['analogies']}
- Assumptions: {style['assumptions']}

LEARNING PATH CONTEXT:
{learning_path_context if learning_path_context else ''}

PAST CHALLENGES CONTENTS (Do NOT re-teach):
{past_context if past_context else "None"}

FUTURE CHALLENGES CONTENTS (Do NOT mention or teach):
{future_context if future_context else "None"}

CURRENT CHALLENGE:
- Title: {challenge_data['title']}
- Objective: {challenge_data['learning_objective']}
- Description: {challenge_data['description']}

IMPORTANT RULES:
1. Teach ONLY what is needed for this challenge.
2. Reference content you imagine were present in past challenges briefly but never repeat full explanations.
3. Do NOT introduce any concept that you think belongs to future challenges.
4. Avoid depth or complexity beyond the student’s level.

LESSON STRUCTURE (Output in pure markdown):

# {challenge_data['title']}

## Introduction
[1-2 paragraphs - Explain what this challenge is about and why it matters. Use {style['tone']} tone and {style['language']}.]

## The Core Idea
[1-2 paragraphs - Connect it to real-world applications. Explain how this concept fits into the bigger picture in one clear analogy or model. Use {style['tone']} tone and {style['language']}.]

## Core Concepts — Component Breakdown (For CONCEPTUAL CHALLENGES ONLY - Dont mention this on the lesson)
Break the main topic into its most important sub-concepts or components. This section is for explaining the "what" and "why" of the topic. Each component must:
- Contain 1–2 short sentences explaining the single sub-concept (what it is and why it matters).
- Include at most one tiny illustrative element (Mermaid diagram, 1-line table, or a one-line example). No multi-line code blocks here.
- Use only knowledge allowed by the module (past OR this challenge).

After the last component, include a short 2–3 sentence "How It Fits Together" summary that explains the relationships between these components.

If the challenge is practical (build/code), use the alternative Step-by-Step below instead.

## Step-by-Step (For PRACTICAL CHALLENGES ONLY - Dont mention this on the lesson)
If the challenge requires building or running something, break into 3–5 focused steps:
- **Step N: [Name]**
  - 1–2 short sentences: what this step adds (new concept only).
  - Show cumulative code/manifest *only if required*, with comments only for the newly added lines.
Keep each step tightly scoped. Do NOT repeat unrelated code.

IF THE CHALLENGE IS CONCEPTUAL:
- Do NOT include this section.
- Only include the "Core Concepts — Component Breakdown" section.

## Expected Results

At the end of the incremental steps, show:

- Concrete results/outputs to expect from the 'Core Concepts' OR 'Step-by-Step'.
- Any key visual indicators

## Common Pitfalls
[3-5 bullet points covering:]
- Typical mistakes at {experience_level} level
- What these errors or misunderstandings look like
- How to fix or avoid them
- Pro tips for real-world reliability

## Quick Reference and Recap
[A concise summary reinforcing key ideas — a cheat sheet or visual summary with the most important takeaways.]

---

CODE FORMATTING RULES (MANDATORY)

- Inline mentions: use backticks `like_this` for keywords, functions, variables, technical terms
- Technical specification lines: use single-line code blocks for structured data (state transitions, packet details, system calls)
- Multi-line code: use fenced code blocks with language specifier
- Tables: use GitHub Flavored Markdown table syntax for comparisons, specs, or structured information

DIAGRAMS RULES (When Valuable)

You may include Mermaid diagrams **only when they clarify the concept**.  
Use at most **one diagram per section**, and only in:

- **The Core Idea**
- **Core Concepts — Component Breakdown**
- **Step-by-Step** (practical challenges only)

MERMAID SYNTAX RULES:
- Allowed types: `flowchart`, `graph`, `sequenceDiagram`, `stateDiagram`.
- Keep diagrams **simple and readable** (4–8 nodes max).
- Use **fenced blocks**:

```mermaid
flowchart LR
    A --> B
```

STYLE RULES:
- Keep styling minimal and consistent.
- Optional: `subgraph` for grouping.
- Optional: simple `classDef` (1–2 classes max).
- Optional: small emoji in labels (e.g., `API Server 🚀`) but keep it subtle.

CONSTRAINTS:
- No custom themes.
- No excessive styling.
- No oversized diagrams.
- No multi-line explanations inside nodes.

OUTPUT RULES:
- Output ONLY markdown
- No meta-comments
- No extra explanations
- No references to this prompt

Begin the markdown lesson now:"""

    response = llm.invoke(prompt)
    lesson_markdown = response.content.strip()

    return lesson_markdown

def run_tutor_agent(
    challenge_data: Dict[str, Any],
    experience_level: str = "Beginner",
    past_challenges: List[Dict[str, Any]] = None,
    future_challenges: List[Dict[str, Any]] = None,
    module_context: Dict[str, Any] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Main entry point for Tutor Agent.
    Suitable for use as a LangGraph node.

    Args:
        challenge_data: Challenge information from module_X_challenges.json
        experience_level: Student's experience level
        past_challenges: List of challenges already completed (for context)
        future_challenges: List of challenges coming next (to avoid teaching prematurely)
        module_context: Module information for learning path context
        verbose: If True, print progress messages (default: False)

    Returns:
        Dictionary with lesson_markdown for display and next agents
    """

    print(f"      📚 Tutor Agent: Creating lesson for '{challenge_data['title']}'")
    if past_challenges:
        print(f"         Context: {len(past_challenges)} past challenges")
    if future_challenges:
        print(f"         Future: {len(future_challenges)} upcoming challenges")

    llm = create_tutor_agent()

    t1 = time.time()
    lesson_markdown = generate_lesson_markdown(
        llm,
        challenge_data,
        experience_level,
        past_challenges=past_challenges,
        future_challenges=future_challenges,
        module_context=module_context
    )
    print(f"         ⏱️  Lesson generation: {time.time()-t1:.1f}s ({len(lesson_markdown)} chars, {lesson_markdown.count('##')} sections)")

    return {
        "lesson_markdown": lesson_markdown,
        "challenge_data": challenge_data,
        "experience_level": experience_level
    }


def main():
    """Local testing function - configure module and challenge below."""
    import json
    from pathlib import Path
    from datetime import datetime

    # ========== CONFIGURATION ==========
    MODULE_NUMBER = 3
    CHALLENGE_NUMBER = 5
    # ===================================

    print("\n" + "="*80)
    print("TUTOR AGENT - LOCAL TEST")
    print("="*80)
    print(f"\n📋 Configuration:")
    print(f"   Module: {MODULE_NUMBER}")
    print(f"   Challenge: {CHALLENGE_NUMBER}")

    script_dir = Path(__file__).parent
    module_file = script_dir / f"module_{MODULE_NUMBER}_challenges.json"

    if not module_file.exists():
        print(f"\n❌ Error: {module_file} not found!")
        print("Run module_planner_agent.py first to generate challenge files.")
        return

    try:
        with open(module_file, "r") as f:
            module_data = json.load(f)

        experience_level = module_data["experience_level"]
        module_info = module_data.get("module", {})
        challenges = module_data["challenge_roadmap"]["challenges"]

        if CHALLENGE_NUMBER < 1 or CHALLENGE_NUMBER > len(challenges):
            print(f"❌ Invalid challenge number. Module has {len(challenges)} challenges.")
            return

        challenge_data = challenges[CHALLENGE_NUMBER - 1]

        print(f"\n✅ Loaded challenge:")
        print(f"   Title: {challenge_data['title']}")
        print(f"   Objective: {challenge_data['learning_objective']}")
        print(f"   Experience Level: {experience_level}")

    except Exception as e:
        print(f"\n❌ Error loading module file: {e}")
        return

    past_challenges = challenges[:CHALLENGE_NUMBER - 1] if CHALLENGE_NUMBER > 1 else []
    future_challenges = challenges[CHALLENGE_NUMBER:] if CHALLENGE_NUMBER < len(challenges) else []

    print(f"\n📊 Learning Path Context:")
    print(f"   Module: {module_info.get('title', 'N/A')}")
    print(f"   Past Challenges: {len(past_challenges)}")
    print(f"   Future Challenges: {len(future_challenges)}")

    print(f"\n{'='*80}")
    print("GENERATING LESSON")
    print("="*80)

    try:
        llm = create_tutor_agent()

        lesson_markdown = generate_lesson_markdown(
            llm,
            challenge_data,
            experience_level,
            past_challenges=past_challenges,
            future_challenges=future_challenges,
            module_context=module_info
        )

        print(f"\n✅ Lesson generated:")
        print(f"   Length: {len(lesson_markdown)} chars")
        print(f"   Sections: {lesson_markdown.count('##')} headers")
        print(f"   Code blocks: {lesson_markdown.count('```')//2}")

        output_file = script_dir / f"lesson_module{MODULE_NUMBER}_ch{CHALLENGE_NUMBER}.md"

        metadata = f"""<!--
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Module: {MODULE_NUMBER} - {module_info.get('title', 'N/A')}
Challenge: {CHALLENGE_NUMBER} / {len(challenges)}
Title: {challenge_data['title']}
Experience Level: {experience_level}
Past Challenges: {len(past_challenges)}
Future Challenges: {len(future_challenges)}
LLM: {TUTOR_LLM_CONFIG[0]} - {TUTOR_LLM_CONFIG[1]}
-->

"""

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(metadata + lesson_markdown)

        print(f"\n💾 Saved to: {output_file.name}")
        print(f"\n{'='*80}\n")

    except Exception as e:
        print(f"\n❌ Error generating lesson: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
