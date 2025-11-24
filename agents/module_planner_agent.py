"""
Module Planner Agent - Micro-Curriculum Designer

Takes a module and breaks it down into 5-8 progressive micro-challenges.
Uses LLM reasoning (Groq).
"""

import os
import json
import time
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# LLM Configuration - Change model here
MODULE_PLANNER_LLM_CONFIG = ("groq", "moonshotai/kimi-k2-instruct-0905")

class ModulePlannerAgent:
    """Breaks down a module into 5-8 progressive micro-challenges."""

    def __init__(self):
        """Initialize the agent with configured Groq LLM."""
        self.provider = MODULE_PLANNER_LLM_CONFIG[0]
        self.model_name = MODULE_PLANNER_LLM_CONFIG[1]
        self.llm = self._setup_llm()

    def _setup_llm(self):
        """Setup Groq LLM."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")

        return ChatGroq(
            model=self.model_name,
            groq_api_key=api_key,
            temperature=0.0,
            max_tokens=8000,
        )

    def _log_token_usage(self, response, call_type: str):
        """Log token usage from LLM response."""
        try:
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0

            if hasattr(response, 'response_metadata'):
                metadata = response.response_metadata
                if isinstance(metadata, dict) and 'token_usage' in metadata:
                    usage = metadata['token_usage']
                    input_tokens = usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', 0)

            if total_tokens > 0:
                print(f"  📊 [{call_type}] {self.model_name}: {total_tokens} tokens (in: {input_tokens}, out: {output_tokens})")
        except Exception:
            pass

    def run(self, module: dict, experience_level: str, learning_goal_type: str = "hybrid",
            past_modules: list = None, future_modules: list = None):
        """
        Generate micro-challenge roadmap for a module.

        Args:
            module: Module dict from learning path output
            experience_level: User's experience level
            learning_goal_type: Overall learning goal type (code-focused, concept-focused, hybrid)
            past_modules: List of modules *before* this one (knowledge to assume)
            future_modules: List of modules *after* this one (knowledge to avoid)

        Returns:
            Challenge roadmap with 5-8 progressive learning milestones
        """
        if past_modules is None:
            past_modules = []
        if future_modules is None:
            future_modules = []
        print(f"\n{'='*80}")
        print(f"MODULE PLANNER AGENT - {self.provider.upper()}")
        print(f"{'='*80}")
        print(f"Module: {module['title']}")
        print(f"Level: {experience_level}")
        print(f"Goal Type: {learning_goal_type}\n")

        system_prompt = """You are an expert Micro-Curriculum Designer for technical education.

Your task:
Create 5–8 progressive micro-challenges for ONE module of a learning path.

These challenges feed into other agents (materials, tutors, coding challenge generator, evaluator, remediation). Your output must be structured, specific, and actionable.

=====================================================
CORE RULES
=====================================================

1. Purpose
- Your primary goal is to create a challenge for **every single item** in the module's `Topics to include` list.
- The `Hands-on goals` are practical challenges that MUST be slotted into the roadmap *after* their prerequisite topics are taught.
- You MAY combine 1-2 very closely related topics into a single challenge, but you MUST NOT omit any.

2. Progression
- 5–8 challenges.
- Challenge numbering = learning progression.
- **A conceptual challenge MUST always come before a practical challenge that depends on it.**
- Use ONLY knowledge from:
   - past modules
   - prior challenges in this module
- DO NOT use any knowledge from future modules.

3. Challenge Design
Each challenge must have:
- A specific, actionable title.
- One clear, testable learning objective.
- A concise 2–3 sentence description explaining what the learner must do or understand.

4. Types of Challenges Allowed
- Practical steps (“Build X”, “Run Y”)
- Conceptual explanation (“Explain Z’s role”)
- Design reasoning (“Design a flow for …”)
- Integration (“Combine A and B to achieve C”)

5. Quality Checklist
Ensure:
- Logical sequence
- **A challenge exists for EVERY topic in the `Topics` list**
- **Hands-on goals are placed *after* their prerequisite topics**
- No dependency on future modules
- Clear, specific, testable objectives

=====================================================
OUTPUT FORMAT (STRICT)
=====================================================

Output ONLY this JSON wrapped in:
```json
{
  "module_title": "string",
  "module_number": 1,
  "total_challenges": 7,
  "challenges": [
    {
      "challenge_number": 1,
      "title": "string",
      "learning_objective": "string",
      "description": "string"
    }
  ],
  "progression_notes": "3–4 sentences summarizing how the challenges build toward the module’s hands-on outcomes."
}
```
"""

        user_prompt = f"""

Design 5–8 progressive micro-challenges for this module.

=====================================================
CONTEXT FOR THIS MODULE
=====================================================

Past modules (knowledge the learner already has):
{json.dumps(past_modules, indent=2) if past_modules else "[] - First module. No prior TOPIC knowledge."}

Future modules (DO NOT use or teach these concepts):
{json.dumps(future_modules, indent=2) if future_modules else "[] - Last module."}

Module Number: {module['module_number']}
Title: {module['title']}
Description: {module['description']}
Learner Level: {experience_level}

Topics to include (conceptual foundations):
{json.dumps(module['topics'], indent=2)}

Hands-on goals (practical outcomes to achieve):
{json.dumps(module['hands_on'], indent=2)}

=====================================================
INSTRUCTIONS
=====================================================

Create 5–8 challenges that:
- Follow the rules from the system prompt.
- **First, create a challenge for EACH topic** in the `Topics to include` list.
- **Second, weave the `Hands-on goals`** into the list, placing them *after* their prerequisite conceptual challenges.
- Logically order the final list to create a smooth learning ramp.

Return ONLY the JSON described in the system prompt.
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(messages)
                self._log_token_usage(response, "Challenge Roadmap Generation")
                challenge_roadmap = self._extract_json(response.content)
                return challenge_roadmap
            except ValueError as e:
                if attempt < max_retries - 1:
                    print(f"   🔄 Retry {attempt + 1}/{max_retries - 1} due to JSON error...")
                    time.sleep(2)
                else:
                    print(f"   ❌ All retries exhausted")
                    raise e
            except Exception as e:
                if "429" in str(e) or "Resource exhausted" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 15
                        print(f"   ⏳ Rate limit hit - waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"   ❌ Rate limit retries exhausted")
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
            print(f"   Attempting to repair JSON...")

            try:
                # Try using json_repair library if available
                try:
                    from json_repair import repair_json
                    result = repair_json(json_str)
                    print(f"   ✅ JSON repaired successfully using json_repair library")
                    return json.loads(result) if isinstance(result, str) else result
                except ImportError:
                    # Fallback to manual repair
                    import re

                    repaired = json_str

                    # Fix trailing commas
                    repaired = re.sub(r',\s*}', '}', repaired)
                    repaired = re.sub(r',\s*]', ']', repaired)

                    # Try to fix unescaped quotes within strings
                    # This is a heuristic approach - look for patterns like: "text"more text"
                    # and replace inner quotes with escaped quotes
                    def fix_quotes_in_strings(match):
                        full_match = match.group(0)
                        # Replace unescaped quotes inside the string value
                        # Keep the outer quotes, escape inner ones
                        return full_match.replace('"', '\\"').replace('\\"', '"', 1).replace('\\"', '"', 1)[::-1].replace('"', '\\"', 1)[::-1]

                    # More aggressive: try to escape quotes that appear inside code/backtick blocks
                    # Pattern: find strings that contain backticks with quotes inside
                    def escape_quotes_in_backticks(text):
                        result = []
                        in_string = False
                        in_backtick = False
                        escape_next = False
                        i = 0

                        while i < len(text):
                            char = text[i]

                            if escape_next:
                                result.append(char)
                                escape_next = False
                                i += 1
                                continue

                            if char == '\\':
                                result.append(char)
                                escape_next = True
                                i += 1
                                continue

                            if char == '"' and not in_backtick:
                                in_string = not in_string
                                result.append(char)
                            elif char == '`' and in_string:
                                in_backtick = not in_backtick
                                result.append(char)
                            elif char == '"' and in_backtick and in_string:
                                # Escape quotes inside backticks
                                result.append('\\')
                                result.append(char)
                            else:
                                result.append(char)

                            i += 1

                        return ''.join(result)

                    repaired = escape_quotes_in_backticks(repaired)

                    result = json.loads(repaired)
                    print(f"   ✅ JSON repaired successfully")
                    return result
            except Exception as repair_error:
                print(f"   ❌ Repair failed: {repair_error}")
                print(f"   JSON around error position {e.pos}:")
                start = max(0, e.pos - 100)
                end = min(len(json_str), e.pos + 100)
                print(f"   ...{json_str[start:end]}...")

                # Save problematic JSON for debugging
                debug_file = "debug_json_error.txt"
                with open(debug_file, "w") as f:
                    f.write(f"Original Error: {e}\n")
                    f.write(f"Error Position: {e.pos}\n\n")
                    f.write("Full JSON String:\n")
                    f.write(json_str)
                print(f"   💾 Full JSON saved to {debug_file} for debugging")

                raise ValueError(f"Invalid JSON in code block: {str(e)}")

def print_challenge_roadmap(roadmap: dict):
    """Pretty print challenge roadmap."""
    print(f"\n{'='*80}")
    print(f"CHALLENGE ROADMAP")
    print(f"{'='*80}\n")

    print(f"📚 Module: {roadmap['module_title']}")
    print(f"📊 Total Challenges: {roadmap['total_challenges']}")

    print(f"\n{'─'*80}")
    print("CHALLENGES:")
    print(f"{'─'*80}")

    for i, challenge in enumerate(roadmap['challenges'], 1):
        # Validate required fields
        if 'challenge_number' not in challenge:
            print(f"\n⚠️  Warning: Challenge {i} missing 'challenge_number' field")
            challenge['challenge_number'] = i

        if 'title' not in challenge:
            print(f"\n⚠️  Warning: Challenge {i} missing 'title' field")
            challenge['title'] = f"Challenge {i}"

        if 'learning_objective' not in challenge:
            print(f"\n⚠️  Warning: Challenge {i} missing 'learning_objective' field")
            print(f"    Available fields: {list(challenge.keys())}")
            challenge['learning_objective'] = challenge.get('description', 'No objective provided')

        print(f"\n[Challenge {challenge['challenge_number']}] {challenge['title']}")
        print(f"    🎯 Objective: {challenge['learning_objective']}")

        # Optionally show description if it exists and differs from objective
        if 'description' in challenge and challenge['description'] != challenge['learning_objective']:
            print(f"    📝 Description: {challenge['description']}")

    print(f"\n{'─'*80}")
    print("PROGRESSION:")
    print(f"{'─'*80}")
    print(roadmap.get('progression_notes', 'N/A'))
    print()

def main():
    """Main function - loads learning path and lets user select a module."""
    print("\n" + "="*80)
    print("ADAPTIVE LEARNING OS - MODULE PLANNER AGENT")
    print("="*80)

    # Load learning path output
    try:
        with open("learning_path_output.json", "r") as f:
            learning_path_data = json.load(f)
    except FileNotFoundError:
        print("\n❌ Error: learning_path_output.json not found!")
        print("Run learning_path_agent.py first to generate a learning path.")
        return

    learning_path = learning_path_data["learning_path"]
    experience_level = learning_path_data["input"]["experience_level"]

    print(f"\nLearning Goal: {learning_path['learning_goal']}")
    print(f"Experience Level: {experience_level}")
    print(f"\nAvailable Modules ({len(learning_path['modules'])}):")

    for module in learning_path['modules']:
        print(f"  {module['module_number']}. {module['title']}")

    # Ask if user wants to process one module or all modules
    print("\nHow many modules do you want to process?")
    print("1. Single module (select which one)")
    print("2. All modules sequentially")
    mode_choice = input("> ").strip()

    print(f"\nUsing LLM: {MODULE_PLANNER_LLM_CONFIG[0]} - {MODULE_PLANNER_LLM_CONFIG[1]}")

    # Determine which modules to process
    modules_to_process = []

    if mode_choice == "2":
        # Process all modules
        modules_to_process = learning_path['modules']
        print(f"\n📋 Processing all {len(modules_to_process)} modules sequentially...")
    else:
        # Process single module (default)
        module_choice = input(f"\nSelect module number (1-{len(learning_path['modules'])}): ").strip()

        try:
            module_num = int(module_choice)
            selected_module = next(
                (m for m in learning_path['modules'] if m['module_number'] == module_num),
                None
            )

            if not selected_module:
                print(f"❌ Invalid module number: {module_num}")
                return

            modules_to_process = [selected_module]
        except ValueError:
            print(f"❌ Invalid input: {module_choice}")
            return

    # Process each module
    try:
        agent = ModulePlannerAgent()

        # Rate limiting: Track request times for Groq (max 2 requests per minute)
        request_times = []
        max_requests_per_minute = 2

        for idx, selected_module in enumerate(modules_to_process, 1):
            # Rate limiting: Ensure we don't exceed max requests per minute
            if len(request_times) >= max_requests_per_minute:
                # Check the oldest request in our window
                oldest_request = request_times[0]
                time_since_oldest = time.time() - oldest_request

                if time_since_oldest < 60:
                    # Need to wait before making next request
                    wait_time = 60 - time_since_oldest
                    print(f"\n⏳ Rate limit protection: Waiting {wait_time:.1f}s before next request...")
                    time.sleep(wait_time)

                # Remove the oldest request from tracking
                request_times.pop(0)

            if len(modules_to_process) > 1:
                print(f"\n{'='*80}")
                print(f"Processing Module {idx}/{len(modules_to_process)}")
                print(f"{'='*80}")

            current_module_number = selected_module['module_number']

            past_modules = [
                m for m in learning_path['modules']
                if m['module_number'] < current_module_number
            ]

            future_modules = [
                m for m in learning_path['modules']
                if m['module_number'] > current_module_number
            ]

            result = agent.run(
                selected_module,
                experience_level,
                learning_path.get('learning_goal_type', 'hybrid'),
                past_modules=past_modules,
                future_modules=future_modules
            )

            request_times.append(time.time())

            print_challenge_roadmap(result)

            output_file = f"module_{current_module_number}_challenges.json"
            with open(output_file, "w") as f:
                json.dump({
                    "module": selected_module,
                    "experience_level": experience_level,
                    "challenge_roadmap": result
                }, f, indent=2)

            print(f"\n✅ Results saved to: {output_file}")

            if len(modules_to_process) > 1 and idx < len(modules_to_process):
                print(f"\n⏭️  Moving to next module...")

        if len(modules_to_process) > 1:
            print(f"\n{'='*80}")
            print(f"✅ All {len(modules_to_process)} modules processed successfully!")
            print(f"{'='*80}")

        print("📦 Output files can be used as input for the Resource & Tutor Agents.")

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
