# Action Verification System

This document describes the 2-LLM call action verification system implemented for Kyros.

## Overview

The verification system adds intelligence to the Kyros automation agent by implementing two sequential LLM calls:

1. **Action Verification Call**: Analyzes before/after screenshots to determine if the previous action succeeded
2. **Planning Improvement Call**: Uses verification results to provide strategic guidance for the next steps

## Architecture

```
Action Execution → Screenshot Capture → Verification LLM → Planning LLM → Next Action
                      ↓                      ↓               ↓
                Before/After Images    Success Analysis   Strategic Guidance
```

## Key Components

### ActionVerifier Class (`action_verification.py`)

The main class that handles both LLM calls:

- `verify_action()`: First LLM call for action verification
- `improve_planning()`: Second LLM call for planning improvement
- `_parse_verification_response()`: Parses structured verification output
- `_parse_planning_response()`: Parses structured planning output

### Integration Points

1. **Enhanced Working Example** (`working_example_with_verification.py`)
   - Full integration with the existing Kyros workflow
   - Verification runs after each action execution
   - Planning guidance influences next action generation

2. **Test System** (`test_action_verification.py`)
   - Standalone testing with mock screenshots
   - Validates the verification system independently

## LLM Call Details

### First Call: Action Verification

**Input:**
- Before screenshot (base64 encoded)
- After screenshot (base64 encoded)
- Task context
- Action taken
- Action execution result

**Output Structure:**
```
SUCCESS: [YES/NO/PARTIAL]
CHANGES: [Description of visual changes]
EXPECTED_VS_ACTUAL: [Comparison]
ISSUES: [Any problems found, or "None"]
CONFIDENCE: [HIGH/MEDIUM/LOW]
REASONING: [Detailed explanation]
```

### Second Call: Planning Improvement

**Input:**
- Task context
- Verification results from first call
- Current system state
- Historical verification data

**Output Structure:**
```
STRATEGY: [Overall approach for next steps]
CORRECTIONS: [Specific corrections needed, or "None"]
RISKS: [Potential risks to avoid]
SUCCESS_INDICATORS: [How to measure success]
ALTERNATIVES: [Alternative approaches to consider]
CONFIDENCE: [HIGH/MEDIUM/LOW]
REASONING: [Detailed explanation]
```

## Usage Examples

### Basic Usage

```python
from action_verification import ActionVerifier
from llm_integration import create_internlm_function

# Create LLM function
llm_func = create_internlm_function()

# Create verifier
verifier = ActionVerifier(gen_func=llm_func)

# Verify an action
verification_result = verifier.verify_action(
    task="Click the submit button",
    previous_action="pyautogui.click(400, 300)",
    before_screenshot=before_img_bytes,
    after_screenshot=after_img_bytes,
    action_result="Clicked at (400, 300)"
)

# Improve planning
planning_result = verifier.improve_planning(
    task="Click the submit button",
    verification_result=verification_result,
    current_context=obs
)
```

### Integration with Kyros Agent

```python
# In the main loop after action execution:
if previous_action and previous_screenshot:
    # Verify the previous action
    verification_result = verifier.verify_action(
        task=instruction,
        previous_action=previous_action,
        before_screenshot=previous_screenshot,
        after_screenshot=current_screenshot,
        action_result=executor.get_last_result()
    )

    # Improve planning
    planning_result = verifier.improve_planning(
        task=instruction,
        verification_result=verification_result,
        current_context=obs
    )

    # Add guidance to next action generation
    obs["planning_guidance"] = planning_result
```

## Benefits

1. **Self-Correction**: Agent can detect when actions fail and adjust strategy
2. **Learning**: Historical verification data improves future planning
3. **Reliability**: Higher success rates through feedback loops
4. **Transparency**: Clear understanding of what worked and what didn't
5. **Strategic Planning**: Proactive risk assessment and alternative strategies

## Configuration

### Environment Variables

- `INTERNLM_API_URL`: InternLM API endpoint
- `INTERNLM_API_KEY`: Authentication key for API access

### Parameters

- `image_size`: Resolution for screenshot processing (default: 1920x1080)
- `model`: LLM model to use (default: "internvl3.5-241b-a28b")

## Testing

Run the test suite to validate the verification system:

```bash
# Set required environment variables
export INTERNLM_API_URL="https://chat.intern-ai.org.cn/api"
export INTERNLM_API_KEY="your_api_key_here"

# Run verification system test
python test_action_verification.py

# Run full integration test
python working_example_with_verification.py
```

## Performance Considerations

- Each verification cycle adds 2 additional LLM calls
- Image processing requires sufficient memory for screenshot handling
- API latency affects overall execution speed
- Consider batching multiple actions before verification in time-critical scenarios

## Future Enhancements

1. **Confidence-Based Verification**: Skip verification for high-confidence actions
2. **Verification Caching**: Cache results for identical action patterns
3. **Multi-Modal Analysis**: Include accessibility tree analysis in verification
4. **Learning Algorithms**: Train models on verification history for better predictions
5. **Parallel Processing**: Run verification and planning calls concurrently

## Error Handling

The system includes robust error handling for:
- API failures
- Image processing errors
- Malformed LLM responses
- Network timeouts

Failed verifications default to safe fallback strategies rather than stopping execution.