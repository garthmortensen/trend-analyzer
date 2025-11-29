# Agent-driven analysis overview

This documentation is built from openai docs, sometimes customized for this project.

An "agent" just adds a controlled loop around the prompt model so it can:
- ask for data via tools
- look at the results
- decide next steps
- stop when it’s done

Everyone has used prompts in browser. [Here's a code approach](https://platform.openai.com/docs/guides/text?lang=python):

```python
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5-nano",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)
```

The reponse:

```json
[
    {
        "id": "msg_67b73f697ba4819183a15cc17d011509",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "output_text",
                "text": "Under the soft glow of the moon, Luna the unicorn danced through fields of twinkling stardust, leaving trails of dreams for every child asleep.",
                "annotations": []
            }
        ]
    }
]
```

---
## 1. Core Idea
Each cycle you send the model: 
1. conversation history
1. list of tools it can call
1. optional - a JSON output shape you want.

The model answers with text AND zero/one/many tool calls. 

You run those tools, append their results to the history, and call the model again.

Repeat until it stops (no new tool calls / final JSON / step limit).

LLM plans; executes my code; then LLM sees results; 
   plans again; executes my code; then LLM sees results; 
      plans again; executes my code; then LLM sees results...

That’s the agent loop.

---
## 2. Roles

Instructions with higher authority override those with lower authority. This chain of command is designed to maximize steerability and control for users and developers, enabling them to adjust the model's behavior to their needs while staying within clear boundaries.

1. Platform: Rules that cannot be overridden by developers or users. Avoid behaviors that could contribute to catastrophic risks, cause direct physical harm to people, violate laws.

2. Developer: Instructions given by developers using our API.

3. User: Instructions from end users. Honor user requests unless they conflict with developer- or platform-level instructions.

4. Guideline: Instructions that can be implicitly overridden. To maximally empower end users and avoid being paternalistic, we prefer to place as many instructions as possible at this level. For example, if a user asks the model to speak like a realistic pirate, this implicitly overrides the guideline to avoid swearing.

```python
from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5",
    reasoning={"effort": "low"},
    input=[
        {
            "role": "developer",
            "content": "Talk like a pirate."
        },
        {
            "role": "user",
            "content": "Are semicolons optional in JavaScript?"
        }
    ]
)

print(response.output_text)
```

---
## 3. [Tools (Function calling)](https://platform.openai.com/docs/guides/function-calling)

***TODO: Have i created json schema for args?***
You declare capabilities as structured functions (name + JSON schema for arguments). In this repo typical tools would be:
- list_dimensions
- get_trend_data
- get_dimension_values
***

The model can ask for several in one turn (batch). The dispatcher runs them and returns results as tool messages.

Why tools? They give the model “eyes and hands” (data retrieval) without giving it free-form execution power.

A function or tool refers in the abstract to a piece of functionality that we tell the model it has access to. As a model generates a response to a prompt, it may decide that it needs data or functionality provided by a tool to follow the prompt's instructions.

You could give the model access to tools that:

    Get today's weather for a location
    Access account details for a given user ID
    Issue refunds for a lost order

Or anything else you'd like the model to be able to know or do as it responds to a prompt.

When we make an API request to the model with a prompt, we can include a list of tools the model could consider using. For example, if we wanted the model to be able to answer questions about the current weather somewhere in the world, we might give it access to a get_weather tool that takes location as an argument.

### Tool call

If the model receives a prompt like "what is the weather in Paris?" in an API request, it could respond to that prompt with a tool call for the get_weather tool, with Paris as the location argument.

### Tool call output

A function call output or tool call output refers to the response a tool generates using the input from a model's tool call. The tool call output can either be structured JSON or plain text, and it should contain a reference to a specific model tool call (referenced by call_id in the examples to come)

    - The model has access to a `get_weather` tool that takes location as an argument.
    - In response to a prompt like "what's the weather in Paris?" the model returns a tool call that contains a location argument with a value of Paris
    - The tool call output might return a JSON object (e.g., `{"temperature": "25", "unit": "C"}`, indicating a current temperature of 25 degrees), Image contents, or File contents.

We then send all of the tool definition, the original prompt, the model's tool call, and the tool call output back to the model to finally receive a text response like:

`The weather in Paris today is 25C.`

```python
from openai import OpenAI
import json

client = OpenAI()

# 1. Define a list of callable tools for the model
tools = [
    {
        "type": "function",
        "name": "get_horoscope",
        "description": "Get today's horoscope for an astrological sign.",
        "parameters": {
            "type": "object",
            "properties": {
                "sign": {
                    "type": "string",
                    "description": "An astrological sign like Taurus or Aquarius",
                },
            },
            "required": ["sign"],
        },
    },
]

def get_horoscope(sign):
    return f"{sign}: Next Tuesday you will befriend a baby otter."

# Create a running input list we will add to over time
input_list = [
    {"role": "user", "content": "What is my horoscope? I am an Aquarius."}
]

# 2. Prompt the model with tools defined
response = client.responses.create(
    model="gpt-5",
    tools=tools,
    input=input_list,
)

# Save function call outputs for subsequent requests
input_list += response.output

for item in response.output:
    if item.type == "function_call":
        if item.name == "get_horoscope":
            # 3. Execute the function logic for get_horoscope
            horoscope = get_horoscope(json.loads(item.arguments))
            
            # 4. Provide function call results to the model
            input_list.append({
                "type": "function_call_output",
                "call_id": item.call_id, #ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
                "output": json.dumps({
                  "horoscope": horoscope
                })
            })

print("Final input:")
print(input_list)

response = client.responses.create(
    model="gpt-5",
    instructions="Respond only with a horoscope generated by a tool.",
    tools=tools,
    input=input_list,
)

# 5. The model should be able to give a response!
print("Final output:")
print(response.model_dump_json(indent=2))
print("\n" + response.output_text)
```

### Example

```python
 @function_tool: Decorator from OpenAI Agents SDK that converts a Python function into a tool
# the AI agent can call. It generates JSON schema for function parameters and handles serialization.
#
# async def: Required by OpenAI Agents SDK - all function_tool decorated functions must be async
# even if they don't perform I/O operations. The SDK's Runner uses asyncio for event streaming.
@function_tool
async def get_trend_data_tool(
    group_by_dimensions: str = "",
    filters: str = "",
    top_n: int = 999
) -> str:
```

---
## 4. Structured JSON Output
Structured Outputs ensures model responses adhere to your supplied JSON Schema, so you don't need to worry about the model omitting a required key, or hallucinating an invalid enum value. That makes downstream reporting deterministic. 

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class ResearchPaperExtraction(BaseModel):
    title: str
    authors: list[str]
    abstract: str
    keywords: list[str]

response = client.responses.parse(
    model="gpt-4o-2024-08-06",
    input=[
        {
            "role": "system",
            "content": "You are an expert at structured data extraction. You will be given unstructured text from a research paper and should convert it into the given structure.",
        },
        {"role": "user", "content": "..."},
    ],
    text_format=ResearchPaperExtraction,
)

research_paper = response.output_parsed
```

The response:

```json
{
  "title": "Application of Quantum Algorithms in Interstellar Navigation: A New Frontier",
  "authors": [
    "Dr. Stella Voyager",
    "Dr. Nova Star",
    "Dr. Lyra Hunter"
  ],
  "abstract": "This paper investigates the utilization of quantum algorithms to improve interstellar navigation systems. By leveraging quantum superposition and entanglement, our proposed navigation system can calculate optimal travel paths through space-time anomalies more efficiently than classical methods. Experimental simulations suggest a significant reduction in travel time and fuel consumption for interstellar missions.",
  "keywords": [
    "Quantum algorithms",
    "interstellar navigation",
    "space-time anomalies",
    "quantum superposition",
    "quantum entanglement",
    "space travel"
  ]
}
```

---
## 5. Loop Skeleton (Plain English)
1. Start messages with system + user.
2. Call model with tools + maybe desired JSON schema.
3. If response has tool calls:
   - For each call: parse arguments, run local Python function, append result.
   - Go back to step 2.
4. Else if response has final structured JSON → done.
5. Else (no tools, no JSON) → treat its text as final and stop.

Add a step counter (e.g., max 8) to avoid infinite loops.
