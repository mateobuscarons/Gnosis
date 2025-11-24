"""
Learning Path Agent - Simple and Direct

Uses LLM reasoning (Groq) to generate structured learning paths.
"""

import os
import json
from enum import Enum
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# LLM Configuration
TEMPERATURE = 0.0
CURRENT = False

if CURRENT:
    LEARNING_PATH_LLM_CONFIG = ("groq", "moonshotai/kimi-k2-instruct-0905")
else:
    LEARNING_PATH_LLM_CONFIG = ("groq", "openai/gpt-oss-20b")

class ExperienceLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"

class LearningPathAgent:
    """Learning path generator using LLM reasoning (Groq)."""

    def __init__(self):
        """Initialize the agent with configured Groq LLM."""
        self.provider = LEARNING_PATH_LLM_CONFIG[0]
        self.model_name = LEARNING_PATH_LLM_CONFIG[1]
        self.llm = self._setup_llm()

    def _setup_llm(self):
        """Setup Groq LLM."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")

        return ChatGroq(
            model=self.model_name,
            groq_api_key=api_key,
            temperature=TEMPERATURE,
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

    def _classify_learning_goal_type(self, learning_goal: str) -> str:
        """
        Classify the learning goal as code-focused, concept-focused, or hybrid.

        Returns:
            "code-focused", "concept-focused", or "hybrid"
        """
        prompt = f"""Analyze this learning goal and classify its primary focus:

Learning Goal: {learning_goal}

Classification Options:
1. **code-focused** - Learning that involves MAINLY code and no abstract concepts.

2. **concept-focused** - Learning that involves MAINLY theory or abstract concepts. No code nor configuration necessary to fully learn it. 

3. **hybrid** - Significant mix of both implementation and conceptual understanding. Both theory / abstract and coding needed. 

Return ONLY a JSON object:
```json
{{
  "goal_type": "code-focused" OR "concept-focused" OR "hybrid",
  "reasoning": "Brief 1-sentence explanation"
}}
```"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            self._log_token_usage(response, "Goal Classification")
            text = response.content.strip()

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
        Generate learning path using LLM reasoning.

        Flow:
        1. Classify learning goal type (code-focused, concept-focused, hybrid)
        2. LLM uses its knowledge to generate comprehensive learning path
        """
        print(f"\n{'='*80}")
        print(f"LEARNING PATH AGENT - {self.provider.upper()}")
        print(f"{'='*80}")
        print(f"Goal: {learning_goal}")
        print(f"Level: {experience_level.value}\n")

        print(f"  🎯 Classifying learning goal type...")
        goal_type = self._classify_learning_goal_type(learning_goal)

        print(f"\n  🤖 Generating learning path...\n")

        system_prompt = """You are an expert Technical Curriculum Designer (2025) who creates highly structured,
pedagogically sound learning paths for any technical topic.

Your learning paths must be rigorous, progressive, and grounded in instructional design:
scaffolding, prerequisite sequencing, cognitive load balancing, and applied practice.

Your task is to generate a JSON learning path with 2–6 modules.

===============================================================================
INTERNAL PLANNING RULES (DO NOT SHOW)
===============================================================================
Before producing the final JSON, you MUST internally:

1. Identify all prerequisite concepts (Python knowledge can be assumed.)
2. Build a dependency graph.
3. **CRITICAL VALIDATION (Modules):**
   - **Cognitive Load:** Your #1 priority is balancing cognitive load. Modules MUST be small, focused, and cover only one MAJOR concept.
   - **Test:** Is any module twice as hard as another module? If yes, split it.
   - **Rule:** It is **ALWAYS** better to have 5-6 simple, focused modules than 3-4 dense, overloaded ones.
4. **CRITICAL VALIDATION (Topics):**
   - **Practical-First Principle:** Prioritize practical knowledge over deep, academic theory. Topics must focus on what is necessary to use the technology (the "how"), not the "deep why" that isn't required for operation.
   - **No Duplication:** Scan all module `topics`. A concept MUST NOT appear in more than one module.
   - **No Gaps:** Every prerequisite concept must be taught.
   - **No Assumed Knowledge:** No module may assume knowledge *on the topic* not taught in a *previous* module.
5. **CRITICAL VALIDATION (Hands-on):**
   - **Avoid Passivity:** Do NOT use passive tasks like "Read an article" or "Watch a video" as a `hands_on` goal.
   - Ensure hands-on use minimal, free tooling and **MUST NOT** require external accounts, paid software, or complex enterprise setup.
6. If anything violates pedagogical rules, revise internally before output.

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
OUTPUT FORMAT (STRICT)
================================================================================

Output ONLY a JSON object
wrapped inside a single ```json code block.

Follow EXACTLY this structure:

```json
{
  "learning_goal": "string",
  "learning_goal_type": "code-focused | concept-focused | hybrid",
  "modules": [
    {
      "module_number": 1,
      "title": "string",
      "description": "string",
      "topics": ["string", "string"],
      "hands_on": ["string", "string"]
    }
  ],
  "reasoning": "Brief explanation of the learning path structure and why this ordering."
}
```

Do NOT include anything outside the JSON.
Do NOT add or remove fields.
Do NOT wrap the JSON in text.
Do NOT copy content or structure from example.

================================================================================
PERFECT EXAMPLE (Kubernetes for Beginner)
================================================================================

You should use this example as your gold standard for structure, pedagogy, knowledge dependency and module granularity.

{
  "learning_goal": "To understand core Kubernetes concepts from the ground up, deploy and manage containerized applications, and gain practical skills to build simple projects without constant hand-holding.",
  "learning_goal_type": "hybrid",
  "modules": [
    {
      "module_number": 1,
      "title": "Foundations: From Container to Pod",
      "description": "This module introduces the 'why' of Kubernetes and its most fundamental unit, the Pod. We will then trace how a Pod is brought to life by the core components of the cluster.",
      "topics": [
        "What is a container? (Docker basics)",
        "Why Kubernetes? (The need for orchestration)",
        "**The Pod:** The smallest deployable unit in Kubernetes",
        "**The Node:** The worker machine that runs Pods",
        "**The Control Plane:** The 'brain' of the cluster",
        "**Tracing a Pod's Life:** How components interact (API Server, etcd, Scheduler, Kubelet, Container Runtime)",
        "Introduction to `kubectl`: The command-line tool"
      ],
      "hands_on": [
        "Install Docker and run a simple Nginx container.",
        "Install Minikube (or Kind) and `kubectl`.",
        "Interact with the cluster (`kubectl cluster-info`, `kubectl get nodes`).",
        "Run your first Pod imperatively (`kubectl run ...`).",
        "Inspect the Pod's status and events (`kubectl get pod`, `kubectl describe pod`)."
      ]
    },
    {
      "module_number": 2,
      "title": "Declarative Management with Deployments",
      "description": "Learn the 'right' way to manage applications using declarative YAML manifests and Deployments, which provide self-healing and rolling updates for your Pods.",
      "topics": [
        "Declarative (YAML) vs. Imperative (`kubectl run`)",
        "YAML Basics for Kubernetes manifests",
        "Problem: Why not just create Pods directly?",
        "**Deployments:** The controller for managing stateless applications",
        "**ReplicaSets:** How Deployments manage Pod replicas",
        "Rolling Updates and Rollbacks"
      ],
      "hands_on": [
        "Write a YAML manifest for a 3-replica Nginx Deployment.",
        "Apply the manifest (`kubectl apply -f ...`) and inspect the objects (`kubectl get deployment,replicaset,pod`).",
        "Perform a rolling update by changing the container image tag in the YAML.",
        "Perform a rollback using `kubectl rollout undo`."
      ]
    },
    {
      "module_number": 3,
      "title": "Exposing Applications with Services",
      "description": "Understand how to make applications accessible both within and outside the Kubernetes cluster using various Service types.",
      "topics": [
        "Kubernetes Services: Abstracting Pods for stable access",
        "Service Types: ClusterIP, NodePort, LoadBalancer",
        "Service Discovery within Kubernetes (DNS-based)",
        "Basic networking: Pod IP vs. Service IP"
      ],
      "hands_on": [
        "Create a ClusterIP Service to expose the web Deployment internally.",
        "Deploy a temporary 'test' Pod and use `kubectl exec` to curl the Service by its name.",
        "Modify the Service to be type NodePort and access it from your host machine's browser."
      ]
    },
    {
      "module_number": 4,
      "title": "Configuration, Storage, and Resource Management",
      "description": "This module covers how to manage application configuration, handle persistent data, and allocate resources efficiently.",
      "topics": [
        "ConfigMaps: Managing non-sensitive configuration data",
        "Secrets: Securely managing sensitive data (e.g., API keys, passwords)",
        "Volumes: Ephemeral vs. Persistent Storage concepts",
        "PersistentVolumeClaims (PVCs) and PersistentVolumes (PVs) basics",
        "Resource Requests and Limits for CPU and Memory"
      ],
      "hands_on": [
        "Create a ConfigMap and inject its data as environment variables into a Deployment.",
        "Create a Secret and mount it as a file into a Pod; use `kubectl exec` to verify it exists.",
        "Deploy an application (e.g., a simple database) that uses a PersistentVolumeClaim to store data."
      ]
    },
    {
      "module_number": 5,
      "title": "Enhancing Reliability and Introduction to Packaging",
      "description": "Learn how to make applications more robust with health checks and basic scaling, and get an introduction to Helm for packaging applications.",
      "topics": [
        "Liveness Probes: Detecting and restarting unhealthy containers",
        "Readiness Probes: Controlling traffic to ready containers",
        "Horizontal Pod Autoscaler (HPA): Basic concepts",
        "Introduction to Helm: The package manager for Kubernetes"
      ],
      "hands_on": [
        "Add Liveness and Readiness probes to your Deployment manifest and apply the change.",
        "Create an HPA for your Deployment.",
        "Install Helm and deploy a simple application (e.g., a database) using a public Helm chart."
      ]
    }
  ],
  "reasoning": "This learning path is structured to fix a common pedagogical flaw. **Module 1** introduces the `Pod` as the central, concrete 'thing' a user wants to run. It then introduces the architecture components (Scheduler, Kubelet) *in the context of their job*, which is to get that `Pod` running. **Module 2** builds on this by introducing the declarative `Deployment` as the *correct* way to manage Pods. This 'Pod-first' approach provides a strong foundation. **Module 3** (Services) and **Module 4** (Config/Storage) logically follow, adding networking and state. **Module 5** provides a capstone on reliability, aligning with the 'Capable' goal."
}

This is just an ideal example to showcase the level of detail, granularity, cognitive load and ideal progression.
Do not copy exact contents or structure from the example. Draft new ideal output for each unique learning goal and type. 

================================================================================
FINAL BEHAVIOR
================================================================================

- Use internal planning but NEVER reveal it.
- Ensure modules progress logically.
- Ensure no duplication.
- Ensure hands-on is aligned with topics.
- Ensure strict JSON correctness.
- Ensure expert-level pedagogy.
- Use 2025 best practices.

Your #1 priority is:
A clear, progressive, dependency-driven learning path that a real learner can follow."""

        user_prompt = f"""Create a comprehensive learning path for:

Learning Goal: {learning_goal}
Experience Level: {experience_level.value}
Goal Type: {goal_type}

Based on your expert knowledge (2025), design a structured learning path tailored to {experience_level.value} level on the topic.

Generate the learning path as JSON."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm.invoke(messages)
                self._log_token_usage(response, "Learning Path Generation")
                learning_path = self._extract_json(response.content)
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
                        wait_time = (attempt + 1) * 15  # 15, 30, 45 seconds
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
    print("ADAPTIVE LEARNING OS - LEARNING PATH AGENT")
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

    print(f"\nUsing LLM: {LEARNING_PATH_LLM_CONFIG[0]} - {LEARNING_PATH_LLM_CONFIG[1]}")

    try:

        agent = LearningPathAgent()
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
