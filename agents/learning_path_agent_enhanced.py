"""
Learning Path Agent - Enhanced with Web Search

Uses Groq's gpt-oss-120b with browser_search tool for NEW topics:
- Automatically searches web for official documentation when needed
- Search results added to context (increases tokens but provides current info)
- Optimized prompting limits searches to 2 max via system instructions
- Only 2 modules of the gold example for lean prompt

Token usage:
- Well-known topics (no search): ~3-5K tokens
- New topics (with search): ~15-55K tokens (depends on search results)
- Quality: Uses current 2025 documentation when available
"""

import os
import json
from enum import Enum
from dotenv import load_dotenv

from groq import Groq

load_dotenv()

# LLM Configuration
LEARNING_PATH_ENHANCED_LLM_CONFIG = ("groq", "openai/gpt-oss-120b")
CLASSIFICATION_LLM_CONFIG = ("groq", "moonshotai/kimi-k2-instruct-0905")


class ExperienceLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class LearningPathAgentEnhanced:
    """Learning path generator with web search capabilities (Groq GPT-OSS-120B)."""

    def __init__(self):
        """Initialize the agent with configured Groq client."""
        self.provider = LEARNING_PATH_ENHANCED_LLM_CONFIG[0]
        self.model_name = LEARNING_PATH_ENHANCED_LLM_CONFIG[1]
        self.classification_model = CLASSIFICATION_LLM_CONFIG[1]
        self.client = self._setup_llm()
        self.total_tokens = 0  

    def _setup_llm(self):
        """Setup Groq client."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")

        return Groq(api_key=api_key)

    def _log_token_usage(self, response, call_type: str, model: str = None):
        """Log token usage from Groq response and accumulate total."""
        try:
            if hasattr(response, 'usage'):
                usage = response.usage
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
                total_tokens = usage.total_tokens

                if total_tokens > 0:
                    model_name = model or self.model_name
                    print(f"  📊 [{call_type}] {model_name}: {total_tokens} tokens (in: {input_tokens}, out: {output_tokens})")
                    self.total_tokens += total_tokens
        except Exception:
            pass

    def _classify_learning_goal_type(self, learning_goal: str) -> str:
        """
        Classify the learning goal as code-focused, concept-focused, or hybrid.
        Uses moonshotai/kimi-k2-instruct-0905 (no web search for classification).

        Returns:
            "code-focused", "concept-focused", or "hybrid"
        """
        prompt = f"""Analyze this learning goal and classify its primary focus:

Learning Goal: {learning_goal}

Classification Options:

1. **code-focused** - Learning focused on writing code, implementation details, syntax, APIs.
   Examples: "Python basics", "React hooks", "SQL queries", "REST API with Express"

2. **concept-focused** - Pure theory with NO coding/implementation required.
   Examples: "Software architecture patterns", "Distributed systems theory", "Agile methodology"

3. **hybrid** - Mix of theory AND practical implementation. Requires both understanding concepts AND coding.
   Examples: "Kubernetes", "Docker", "FastAPI", "GraphQL", "TypeScript", "Any framework/tool/protocol"

**IMPORTANT**: Frameworks, protocols, tools, and technologies are almost ALWAYS **hybrid** because you need to:
- Understand the concepts (architecture, design patterns)
- AND implement/configure/use them in code

Return ONLY a JSON object:
```json
{{
  "goal_type": "code-focused" OR "concept-focused" OR "hybrid",
  "reasoning": "Brief 1-sentence explanation"
}}
```"""

        try:
            response = self.client.chat.completions.create(
                model=self.classification_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_completion_tokens=1000
            )
            self._log_token_usage(response, "Goal Classification", self.classification_model)
            text = response.choices[0].message.content.strip()

            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            if start_idx != -1 and end_idx > 0:
                result = json.loads(text[start_idx:end_idx])
                goal_type = result.get("goal_type", "hybrid")
                print(f"  🎯 Goal type: {goal_type} - {result.get('reasoning', '')}")
                return goal_type

        except Exception as e:
            print(f"  ⚠️  Goal classification failed: {e}, defaulting to 'hybrid'")

        return "hybrid"

    def run(self, learning_goal: str, experience_level: ExperienceLevel):
        """
        Generate learning path using LLM reasoning with web search.

        Flow:
        1. Classify learning goal type (code-focused, concept-focused, hybrid)
        2. LLM uses its knowledge + browser_search to generate comprehensive learning path
        """
        print(f"\n{'='*80}")
        print(f"LEARNING PATH AGENT (ENHANCED) - {self.provider.upper()}")
        print(f"{'='*80}")
        print(f"Goal: {learning_goal}")
        print(f"Level: {experience_level.value}\n")

        print(f"  🎯 Classifying learning goal type...")
        goal_type = self._classify_learning_goal_type(learning_goal)

        print(f"\n  🤖 Generating learning path with optimized web search...\n")

        system_prompt = """You are an expert Technical Curriculum Designer (2025) who creates highly structured,
pedagogically sound learning paths for any technical topic.

===============================================================================
WEB SEARCH RULES (CRITICAL - READ FIRST)
===============================================================================
You have access to browser_search. Use it SPARINGLY and STRATEGICALLY:

**STRICT SEARCH LIMITS:**
- **MAX 2 SEARCHES TOTAL** - You get TWO searches, that's it
- **STOP after finding basic info** - Once you have core concepts, STOP searching
- **ONE search per type**:
  1st search: "[Topic] official documentation" OR "[Topic] specification"
  2nd search: "[Topic] getting started guide" (ONLY if first search insufficient)

**WHAT TO SEARCH FOR:**
✓ Official documentation sites (docs.*, spec.*, [vendor].com/docs)
✓ Official GitHub repositories
✓ Specification documents
✗ Tutorials, blogs, Medium articles, Stack Overflow
✗ Community resources, forums
✗ Anything not official/authoritative

**WHEN TO STOP SEARCHING:**
Stop immediately once you have:
- Basic definition of what it is
- 3-5 core concepts/components
- Basic architecture or workflow
- Example use case

**EFFICIENCY RULE:**
Every search adds ~10-30K tokens. Be MINIMAL. Your training data may already be sufficient.

===============================================================================
CURRICULUM DESIGN RULES
===============================================================================
Your learning paths must be rigorous, progressive, and grounded in instructional design:
scaffolding, prerequisite sequencing, cognitive load balancing, and applied practice.

Your task is to generate a JSON learning path with 2–6 modules.

===============================================================================
INTERNAL PLANNING RULES (DO NOT SHOW)
===============================================================================
Before producing the final JSON, you MUST internally:

1. **Web Search (if needed)**: Use browser_search ONLY if topic is post-2024 or highly specialized
2. Identify all prerequisite concepts (Python knowledge can be assumed.)
3. Build a dependency graph (foundational → advanced).
4. **CRITICAL VALIDATION (Modules):**
   - **Cognitive Load:** Your #1 priority is balancing cognitive load. Modules MUST be small, focused, and cover only one MAJOR concept.
   - **Test:** Is any module twice as hard as another module? If yes, split it.
   - **Rule:** It is **ALWAYS** better to have 5-6 simple, focused modules than 3-4 dense, overloaded ones.
5. **CRITICAL VALIDATION (Topics):**
   - **Practical-First Principle:** Prioritize practical knowledge over deep, academic theory. Topics must focus on what is necessary to use the technology (the "how"), not the "deep why" that isn't required for operation.
   - **No Duplication:** Scan all module `topics`. A concept MUST NOT appear in more than one module.
   - **No Gaps:** Every prerequisite concept must be taught.
   - **No Assumed Knowledge:** No module may assume knowledge *on the topic* not taught in a *previous* module.
6. **CRITICAL VALIDATION (Hands-on):**
   - **Avoid Passivity:** Do NOT use passive tasks like "Read an article" or "Watch a video" as a `hands_on` goal.
   - Ensure hands-on use minimal, free tooling and **MUST NOT** require external accounts, paid software, or complex enterprise setup.
7. If anything violates pedagogical rules, revise internally before output.

================================================================================
LEARNER PERSONA RULES
================================================================================

**Beginner**
- Assume ZERO prior knowledge of the topic.
- Goal: *Capable* — able to perform the "hello world" equivalent independently.
- Must include foundational concepts and gentle ramp-up.
- No advanced patterns, no architecture depth.

**Intermediate**
- Assume the learner COMPLETED the full Beginner path.
- DO NOT re-teach foundational concepts.
- Goal: *Proficient* — able to build moderate projects and follow best practices.
- Focus on deeper reasoning, real-world patterns, ecosystem tools.

**Advanced**
- Assume the learner COMPLETED the full Intermediate path.
- Goal: *Authoritative* — able to design systems, reason about tradeoffs, optimize, architect, or generalize across patterns.
- Focus on advanced patterns, edge cases, performance, architecture,
  design reasoning, or research-level specifics.

================================================================================
GOAL-TYPE ADAPTATION RULES
================================================================================
You MUST tailor the *content* of the modules based on the `Goal Type`
provided in the user prompt.

**1. For `concept-focused` goals:**
   - **Topics:** Prioritize theory, principles, architecture, design patterns, and "why" explanations.
   - **Hands-on:** Tasks should be non-code or minimal-code.
   - **Goal:** The learner should be able to *explain* the topic.

**2. For `code-focused` goals:**
   - **Topics:** Prioritize syntax, APIs, library functions, implementation patterns, and "how" explanations.
   - **Hands-on:** Tasks MUST be practical coding.
   - **Goal:** The learner should be able to *build* with the topic.

**3. For `hybrid` goals:**
   - This is the default. Maintain a balanced mix of conceptual `topics` and practical `hands_on` coding tasks.
   - **Goal:** The learner should be able to *explain* and *build*.

================================================================================
OUTPUT FORMAT & QUALITY EXAMPLE
================================================================================

**GOLD STANDARD EXAMPLE** (Kubernetes Beginner - showing 2 of 5 modules):

```json
{
  "learning_goal": "Understand core Kubernetes concepts, deploy and manage containerized applications, and gain practical skills to build simple projects.",
  "learning_goal_type": "hybrid",
  "modules": [
    {
      "module_number": 1,
      "title": "Foundations: From Container to Pod",
      "description": "Introduces the 'why' of Kubernetes and its most fundamental unit, the Pod. We then trace how a Pod is brought to life by the core components.",
      "topics": [
        "What is a container? (Docker basics)",
        "Why Kubernetes? (The need for orchestration)",
        "**The Pod:** The smallest deployable unit",
        "**The Node:** The worker machine that runs Pods",
        "**Tracing a Pod's Life:** How components interact (API Server, Scheduler, Kubelet)"
      ],
      "hands_on": [
        "Install Docker and run a simple Nginx container.",
        "Install Minikube and `kubectl`.",
        "Run your first Pod imperatively (`kubectl run ...`).",
        "Inspect the Pod's status (`kubectl describe pod`)."
      ]
    },
    {
      "module_number": 2,
      "title": "Declarative Management with Deployments",
      "description": "Learn the 'right' way to manage applications using declarative YAML manifests and Deployments for self-healing and rolling updates.",
      "topics": [
        "Declarative (YAML) vs. Imperative commands",
        "Problem: Why not just create Pods directly?",
        "**Deployments:** The controller for stateless applications",
        "**ReplicaSets:** How Deployments manage Pod replicas",
        "Rolling Updates and Rollbacks"
      ],
      "hands_on": [
        "Write a YAML manifest for a 3-replica Nginx Deployment.",
        "Apply the manifest (`kubectl apply -f ...`).",
        "Perform a rolling update by changing the image tag.",
        "Perform a rollback using `kubectl rollout undo`."
      ]
    },
    {...}
  ],
  "reasoning": "Pod-first approach: **Module 1** introduces the Pod as the central 'thing' you want to run, then introduces architecture components *in context*—getting that Pod running. **Module 2** builds on this by introducing Deployments as the *correct* way to manage Pods. Progressive dependencies ensure solid foundation."
}
```

This is just an ideal example to showcase the level of detail, granularity, cognitive load and ideal progression.
Do not copy exact contents or structure from the example. Draft new ideal output for each unique learning goal and type. 

**REQUIRED STRUCTURE:**

```json
{
  "learning_goal": "string",
  "learning_goal_type": "code-focused | concept-focused | hybrid",
  "modules": [ /* 2-6 modules */ ],
  "reasoning": "string"
}
```
================================================================================
FINAL BEHAVIOR
================================================================================

- Use internal planning but NEVER reveal it.
- Ensure modules progress logically.
- Ensure no duplication.
- Ensure hands-on is aligned with topics.
- Ensure strict JSON correctness.
- Output ONLY the JSON. No text before/after.
- Ensure expert-level pedagogy.
- Use 2025 best practices.

Your #1 priority is:
A clear, progressive, dependency-driven learning path that a real learner can follow."""

        user_prompt = f"""Create a comprehensive learning path for:

Learning Goal: {learning_goal}
Experience Level: {experience_level.value}
Goal Type: {goal_type}

**Search Strategy Reminder:**
- IF this is a new/niche topic (post-2024), use browser_search for official docs
- MAX 2 searches total
- STOP once you have basic info
- Then generate the JSON learning path

Generate the learning path as JSON."""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    max_completion_tokens=3072,
                    top_p=1,
                    reasoning_effort="low",
                    stream=False,
                    stop=None,
                    tools=[{"type": "browser_search"}]
                )

                self._log_token_usage(response, "Learning Path Generation")

                # Detect if web search was used (high input tokens indicate search results in context)
                usage = response.usage
                estimated_prompt_tokens = 4000  # Rough estimate of our prompts
                if usage.prompt_tokens > estimated_prompt_tokens * 3:
                    print(f"  🔍 Web search was used (high input tokens suggest search results included)")

                learning_path = self._extract_json(response.choices[0].message.content)

                # Print total token usage summary
                print(f"\n{'─'*80}")
                print(f"📊 TOTAL TOKEN USAGE SUMMARY")
                print(f"{'─'*80}")
                print(f"  Goal Classification: {self.total_tokens - response.usage.total_tokens:,} tokens")
                print(f"  Learning Path Gen: {response.usage.total_tokens:,} tokens")
                print(f"  TOTAL: {self.total_tokens:,} tokens")
                print(f"{'─'*80}\n")

                return learning_path

            except (ValueError, json.JSONDecodeError) as e:
                if attempt < max_retries - 1:
                    print(f"  🔄 Retry {attempt + 1}/{max_retries - 1} due to JSON error...")
                    import time
                    time.sleep(2)
                else:
                    print(f"  ❌ All retries exhausted")
                    raise e
            except Exception as e:
                if "429" in str(e) or "Resource exhausted" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 15
                        print(f"  ⏳ Rate limit hit - waiting {wait_time} seconds...")
                        import time
                        time.sleep(wait_time)
                    else:
                        print(f"  ❌ Rate limit retries exhausted")
                        raise e
                else:
                    raise e

    def _extract_json(self, text: str):
        """Extract JSON from LLM response wrapped in markdown."""
        text = text.strip()

        start_marker = "```json"
        end_marker = "```"

        start_idx = text.find(start_marker)
        if start_idx == -1:
            start_marker = "```"
            start_idx = text.find(start_marker)
            if start_idx == -1:
                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parsing error: {e}")
                    print(f"Response (first 500 chars): {text[:500]}")
                    raise ValueError(f"Invalid JSON response: {str(e)}")

        end_idx = text.rfind(end_marker, start_idx + len(start_marker))

        if end_idx == -1:
            raise ValueError(f"No closing '```' found for JSON block: {text[:200]}...")

        json_str = text[start_idx + len(start_marker) : end_idx].strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"  Attempting to repair JSON...")

            try:
                import re
                repaired = re.sub(r',\s*}', '}', json_str)
                repaired = re.sub(r',\s*]', ']', repaired)

                result = json.loads(repaired)
                print(f"  ✅ JSON repaired successfully")
                return result
            except:
                print(f"  ❌ Repair failed")
                print(f"  JSON around error position {e.pos}:")
                start = max(0, e.pos - 100)
                end = min(len(json_str), e.pos + 100)
                print(f"  ...{json_str[start:end]}...")
                raise ValueError(f"Invalid JSON in code block: {str(e)}")


def print_learning_path(path: dict):
    """Pretty print learning path."""
    print(f"\n{'='*80}")
    print(f"LEARNING PATH")
    print(f"{'='*80}\n")

    print(f"📚 {path['learning_goal']}")
    print(f"📊 Modules: {len(path['modules'])}")

    print(f"\n{'─'*80}")
    print("MODULES:")
    print(f"{'─'*80}")
    for module in path['modules']:
        print(f"\n[{module['module_number']}] {module['title']}")
        print(f"    📝 {module['description']}")

    print(f"\n{'─'*80}")
    print("REASONING:")
    print(f"{'─'*80}")
    print(path.get('reasoning', 'N/A'))
    print()


def main():
    """Main function with terminal input."""
    print("\n" + "="*80)
    print("ADAPTIVE LEARNING OS - LEARNING PATH AGENT (ENHANCED)")
    print("="*80)

    print("\nLet's create your learning path!\n")

    learning_goal = input("What do you want to learn?\n> ").strip()

    print("\nWhat's your experience?")
    print("1. Beginner")
    print("2. Intermediate")
    print("3. Advanced")
    level_choice = input("> ").strip()

    level_map = {
        "1": ExperienceLevel.BEGINNER,
        "2": ExperienceLevel.INTERMEDIATE,
        "3": ExperienceLevel.ADVANCED,
    }
    experience_level = level_map.get(level_choice, ExperienceLevel.INTERMEDIATE)

    print(f"\nUsing LLM: {LEARNING_PATH_ENHANCED_LLM_CONFIG[0]} - {LEARNING_PATH_ENHANCED_LLM_CONFIG[1]}")

    try:
        agent = LearningPathAgentEnhanced()
        result = agent.run(learning_goal, experience_level)

        print_learning_path(result)

        output_file = "learning_path_output.json"
        with open(output_file, "w") as f:
            json.dump({
                "input": {
                    "learning_goal": learning_goal,
                    "experience_level": experience_level.value
                },
                "learning_path": result
            }, f, indent=2)

        print(f"\n✅ Results saved to: {output_file}")
        print("📦 This output will be used as input for the Module Planner Agent.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("\n⚠️  No .env file found!")
        print("Create .env with:")
        print("  GROQ_API_KEY=your_key")
        exit(1)

    main()
