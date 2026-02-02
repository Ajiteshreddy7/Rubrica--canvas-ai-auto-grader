# Copilot SDK Integration Guide

Deep dive into how this grading agent uses the GitHub Copilot SDK.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Grading Agent (Python)                   │
│                                                             │
│  ┌──────────────┐                                           │
│  │   daemon.py  │ ──┐                                       │
│  └──────────────┘   │                                       │
│                     │                                       │
│  ┌──────────────┐   │    ┌──────────────────────────┐      │
│  │   grader.py  │ ◄─┴────│  Copilot SDK (Python)    │      │
│  │              │        │                          │      │
│  │ ┌──────────┐ │        │  • CopilotClient         │      │
│  │ │Mock Mode │ │        │  • define_tool           │      │
│  │ └──────────┘ │        │  • Session Management    │      │
│  │ ┌──────────┐ │        └────────┬─────────────────┘      │
│  │ │Copilot   │ │                 │                        │
│  │ │SDK Mode  │ │                 │ JSON-RPC               │
│  │ └──────────┘ │                 ▼                        │
│  └──────────────┘        ┌──────────────────────┐          │
│                          │  Copilot CLI         │          │
│                          │  (@github/copilot)   │          │
│  ┌──────────────┐        │                      │          │
│  │  prompts/*.md│────────│  • OAuth Auth        │          │
│  └──────────────┘        │  • Model Access      │          │
└─────────────────────────▼┴──────────────────────┴──────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │  GitHub Copilot API  │
                │  (gpt-4.1, etc.)     │
                └──────────────────────┘
```

## SDK Components

### 1. CopilotClient

The main SDK entry point that manages the CLI lifecycle.

```python
from copilot import CopilotClient

# Create client with OAuth authentication
client = CopilotClient({
    "log_level": "error",      # Reduce noise
    "auto_start": True,        # Auto-start CLI server
    "use_stdio": True,         # Use stdio transport (default)
})

# Start the client (spawns CLI subprocess)
await client.start()

# Check authentication
auth = await client.get_auth_status()
assert auth.is_authenticated

# Use the client...

# Clean up
await client.stop()
```

**Key Options:**
- `cli_path`: Path to Copilot CLI (default: "copilot" from PATH)
- `auto_start`: Auto-start CLI server (default: True)
- `use_stdio`: Use stdin/stdout instead of TCP (default: True)
- `log_level`: "error", "warning", "info", "debug" (default: "info")
- `github_token`: Optional token auth (OAuth is preferred)

### 2. CopilotSession

Created from the client, manages a conversation context.

```python
session = await client.create_session({
    "model": "gpt-4.1",           # Model to use
    "tools": [save_grading],      # Custom tools
    "system_message": {           # System prompt
        "content": prompt,
        "mode": "replace"          # Replace default system message
    },
    "streaming": False            # Disable streaming for grading
})

# Send message
await session.send({"prompt": "Grade this submission..."})

# Wait for completion
done = asyncio.Event()
session.on(lambda e: done.set() if e.type == "session.idle" else None)
await done.wait()

# Clean up
await session.destroy()
```

**Key Options:**
- `model`: "gpt-4.1", "gpt-5", "claude-sonnet-4.5", etc.
- `tools`: List of custom tool functions
- `system_message`: System prompt configuration
- `streaming`: Enable/disable streaming responses

### 3. Custom Tools

Tools allow Copilot to call Python functions.

```python
from copilot.tools import define_tool
from pydantic import BaseModel, Field

# Define parameter schema with Pydantic
class SaveGradingParams(BaseModel):
    score: float = Field(description="Score between 0 and max_points")
    feedback_md: str = Field(description="Markdown feedback")

# Define the tool
@define_tool(
    description="Save grading results for the current submission"
)
async def save_grading(params: SaveGradingParams) -> str:
    # Tool implementation
    save_to_file(params.score, params.feedback_md)
    return f"Grading saved. Score: {params.score}"

# Use in session
session = await client.create_session({
    "tools": [save_grading]
})
```

**How Tools Work:**
1. SDK registers tool with Copilot
2. Copilot decides when to call the tool
3. SDK validates parameters via Pydantic
4. Python function executes
5. Result returned to Copilot
6. Copilot continues conversation

## OAuth Authentication

### How It Works

The SDK uses OAuth authentication by default (no API keys needed):

```
1. User runs: copilot auth login
2. Browser opens → GitHub login
3. User grants Copilot permissions
4. CLI stores OAuth tokens
5. SDK automatically uses stored tokens
```

### Checking Auth Status

```python
auth = await client.get_auth_status()

if auth.is_authenticated:
    print(f"Logged in as: {auth.login}")
    print(f"Auth type: {auth.authType}")
else:
    print("Not authenticated")
    print("Run: copilot auth login")
```

### Alternative: Token Authentication

```python
# Use GitHub token instead of OAuth
client = CopilotClient({
    "github_token": os.environ["GITHUB_TOKEN"],
    "use_logged_in_user": False
})
```

## Event-Driven Architecture

Sessions emit events during processing:

```python
def on_event(event):
    event_type = event.type.value  # or str(event.type)
    
    if event_type == "user.message":
        print("User sent:", event.data.content)
    
    elif event_type == "assistant.message":
        print("Assistant:", event.data.content)
    
    elif event_type == "tool.execution_start":
        print(f"Calling tool: {event.data.toolName}")
    
    elif event_type == "tool.execution_complete":
        print(f"Tool result: {event.data.result}")
    
    elif event_type == "session.idle":
        print("Session finished")
    
    elif event_type == "error":
        print("Error:", event.data.message)

session.on(on_event)
```

**Key Events:**
- `user.message` - User sent a message
- `assistant.message` - Assistant response
- `assistant.message_delta` - Streaming chunk
- `tool.execution_start` - Tool called
- `tool.execution_complete` - Tool finished
- `session.idle` - Session finished processing
- `error` - Error occurred

## Grading Implementation

### Full Grading Flow

```python
async def grade_submission_copilot(submission: Dict) -> Dict:
    # 1. Define grading tool with Pydantic validation
    class SaveGradingParams(BaseModel):
        score: float = Field(ge=0, le=max_points)
        feedback_md: str
    
    grading_result = {"success": False}
    
    @define_tool(description="Save grading results")
    async def save_grading(params: SaveGradingParams) -> str:
        # Save to file
        grading_file = save_grading_file(
            submission["student"],
            params.score,
            params.feedback_md,
            submission
        )
        grading_result["success"] = True
        grading_result["score"] = params.score
        grading_result["grading_file"] = grading_file
        return f"Saved: {grading_file}"
    
    # 2. Build system prompt from templates
    system_prompt = build_grading_prompt(submission)
    
    # 3. Create Copilot client
    client = CopilotClient({"log_level": "error", "auto_start": True})
    
    try:
        # 4. Start and authenticate
        await client.start()
        auth = await client.get_auth_status()
        if not auth.is_authenticated:
            raise RuntimeError("Not authenticated")
        
        # 5. Create session with grading tool
        session = await client.create_session({
            "model": "gpt-4.1",
            "tools": [save_grading],
            "system_message": {
                "content": system_prompt,
                "mode": "replace"
            },
            "streaming": False
        })
        
        # 6. Set up event handler
        done = asyncio.Event()
        error_message = None
        
        def on_event(event):
            nonlocal error_message
            event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
            
            if event_type == "session.idle":
                done.set()
            elif event_type == "error":
                error_message = getattr(event.data, 'message', str(event.data))
                done.set()
        
        session.on(on_event)
        
        # 7. Send grading request
        await session.send({
            "prompt": (
                "Please grade this submission according to the rubric. "
                "Call the save_grading tool with the score and detailed feedback."
            )
        })
        
        # 8. Wait for completion (with timeout)
        await asyncio.wait_for(done.wait(), timeout=120.0)
        
        if error_message:
            raise RuntimeError(f"Copilot error: {error_message}")
        
        # 9. Clean up
        await session.destroy()
        
    finally:
        await client.stop()
    
    if not grading_result["success"]:
        raise RuntimeError("Grading incomplete")
    
    return grading_result
```

### Prompt Construction

```python
def build_grading_prompt(submission: Dict) -> str:
    # Load templates
    system_md = load_prompt("system")        # AI persona
    grading_md = load_prompt("grading")      # Workflow
    feedback_md = load_prompt("feedback")    # Tone guide
    rubric = load_rubric()                   # Grading criteria
    
    # Get submission content
    content = get_submission_content(submission)
    
    # Replace template variables
    status = load_status()
    grading_md = grading_md.replace("{rubric}", rubric)
    grading_md = grading_md.replace("{submission_type}", submission["type"])
    grading_md = grading_md.replace("{student_id}", submission["student"])
    grading_md = grading_md.replace("{submission_content}", content)
    grading_md = grading_md.replace("{assignment_name}", status["assignmentName"])
    grading_md = grading_md.replace("{max_points}", str(status["maxPoints"]))
    
    # Combine all prompts
    full_prompt = f"{system_md}\n\n{grading_md}\n\n{feedback_md}"
    
    return full_prompt
```

## CLI Binary Details

### What is the Copilot CLI?

The `@github/copilot` npm package contains:
- `index.js` - Node.js entry point
- Copilot CLI server implementation
- Model access and routing logic
- OAuth token management

### How the SDK Uses It

```python
# SDK spawns CLI as subprocess
# Equivalent to:
node /path/to/@github/copilot/index.js --server --log-level error --stdio

# SDK communicates via:
# - stdin: Send JSON-RPC requests
# - stdout: Receive JSON-RPC responses
# - stderr: Logs and errors
```

### CLI Installation Locations

**Global npm install:**
```
Windows: %APPDATA%\npm\node_modules\@github\copilot\index.js
Mac/Linux: /usr/local/lib/node_modules/@github/copilot/index.js
```

**Environment variable:**
```bash
export COPILOT_CLI_PATH="/custom/path/to/copilot-cli"
```

### Manual CLI Testing

```bash
# Start CLI server manually
copilot --server --stdio

# Or with node
node /path/to/@github/copilot/index.js --server --stdio

# Check auth
copilot auth status

# Check version
copilot --version
```

## Error Handling

### Common Errors and Solutions

#### 1. "Client not connected"

```python
# Problem: Forgot to call start()
client = CopilotClient()
session = await client.create_session()  # Error!

# Solution: Always start first
await client.start()
session = await client.create_session()  # Works
```

#### 2. "Not authenticated"

```python
# Check auth before use
auth = await client.get_auth_status()
if not auth.is_authenticated:
    raise RuntimeError(
        "Not authenticated. Run: copilot auth login"
    )
```

#### 3. "Timeout waiting for session.idle"

```python
# Increase timeout
await asyncio.wait_for(done.wait(), timeout=300.0)  # 5 minutes

# Or use send_and_wait with timeout
response = await session.send_and_wait(
    {"prompt": "..."},
    timeout=300.0
)
```

#### 4. "Tool not called"

```python
# Make tool description clear
@define_tool(
    description="IMPORTANT: Call this tool to save grading results. Required."
)
async def save_grading(params): ...

# Be explicit in prompt
await session.send({
    "prompt": "Grade and CALL save_grading tool with results"
})
```

## Best Practices

### 1. Always Clean Up

```python
try:
    await client.start()
    # ... use client ...
finally:
    await client.stop()  # Always stop
```

### 2. Validate Tool Parameters

```python
# Use Pydantic for validation
class Params(BaseModel):
    score: float = Field(ge=0, le=100)  # Constrained
    feedback: str = Field(min_length=50)  # Minimum length

@define_tool(...)
async def tool(params: Params): ...
```

### 3. Handle Timeouts

```python
try:
    await asyncio.wait_for(done.wait(), timeout=120.0)
except asyncio.TimeoutError:
    await session.abort()  # Cancel long-running request
    raise RuntimeError("Grading timed out")
```

### 4. Log Events

```python
def on_event(event):
    # Log for debugging
    logger.debug(f"Event: {event.type} - {event.data}")
    
    # Handle specific events
    if event.type == "tool.execution_start":
        logger.info(f"Calling {event.data.toolName}")
```

### 5. Use Appropriate Models

```python
# For grading: Use capable models
session = await client.create_session({
    "model": "gpt-4.1"  # Good for analysis
})

# For simple tasks: Use faster models
session = await client.create_session({
    "model": "gpt-3.5-turbo"  # Faster, cheaper
})
```

## Performance Considerations

### SDK Startup Time

- **First start**: 2-5 seconds (spawns CLI, authenticates)
- **Subsequent requests**: Instant (reuses connection)
- **Recommendation**: Keep client alive for multiple requests

### Grading Time

- **Simple submission**: 5-15 seconds
- **Complex submission**: 30-60 seconds
- **With tools**: +2-5 seconds (tool execution overhead)

### Resource Usage

- **Memory**: ~100MB (CLI process)
- **CPU**: Low (mostly waiting for API)
- **Network**: Depends on model and submission size

## Advanced Features

### Custom Models

```python
# Use custom OpenAI-compatible API
session = await client.create_session({
    "model": "custom-model-name",
    "provider": {
        "type": "openai",
        "base_url": "https://api.example.com/v1",
        "api_key": os.environ["API_KEY"]
    }
})
```

### Streaming Responses

```python
# Enable streaming for long responses
session = await client.create_session({
    "streaming": True
})

def on_event(event):
    if event.type == "assistant.message_delta":
        print(event.data.deltaContent, end="", flush=True)

session.on(on_event)
```

### Multiple Tools

```python
@define_tool(description="Save grading")
async def save_grading(params): ...

@define_tool(description="Request clarification")
async def ask_ta(params): ...

session = await client.create_session({
    "tools": [save_grading, ask_ta]
})
```

## Debugging

### Enable Debug Logging

```python
client = CopilotClient({"log_level": "debug"})
```

### Check CLI Output

```bash
# Run CLI manually to see logs
copilot --server --stdio --log-level debug
```

### Verify SDK Version

```python
import copilot
print(copilot.__version__)  # Should be >= 0.1.0
```

### Test Connection

```python
await client.start()
ping = await client.ping("test")
print(f"Ping: {ping.message}")
```

## References

- **SDK Repository**: https://github.com/github/copilot-sdk
- **Python SDK Docs**: https://github.com/github/copilot-sdk/tree/main/python
- **CLI Installation**: `npm install -g @github/copilot`
- **Authentication**: `copilot auth login`

---

This grading agent is a reference implementation showing how to build production-ready applications with the Copilot SDK.
