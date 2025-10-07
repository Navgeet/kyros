#!/usr/bin/env python3
"""
Action verification system for Kyros.
Implements a 2-LLM call system:
1. First LLM call: Verifies if the action worked as expected using before/after screenshots
2. Second LLM call: Uses verification results to improve planning
"""

import logging
from base64 import b64encode
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image
from io import BytesIO

logger = logging.getLogger("kyros.verification")


def resize_image(image_bytes, w, h):
    """Resize image bytes to specified dimensions."""
    img = Image.open(BytesIO(image_bytes))
    img = img.resize((w, h))
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class ActionVerifier:
    """Handles action verification using dual LLM calls."""

    def __init__(self, gen_func, image_size=(1920, 1080)):
        """
        Initialize the action verifier.

        Args:
            gen_func: LLM generation function
            image_size: Size to resize images to
        """
        self.gen_func = gen_func
        self.image_size = image_size
        self.verification_history = []

    def verify_action(
        self,
        task: str,
        previous_action: str,
        before_screenshot: bytes,
        after_screenshot: bytes,
        action_result: str
    ) -> Dict[str, Any]:
        """
        First LLM call: Verify if the action worked as expected.

        Args:
            task: The overall task being performed
            previous_action: The action that was taken
            before_screenshot: Screenshot before the action
            after_screenshot: Screenshot after the action
            action_result: Result message from action execution

        Returns:
            Dict containing verification results
        """
        logger.info("🔍 Starting action verification...")

        # Resize images for consistency
        before_img = resize_image(before_screenshot, self.image_size[0], self.image_size[1])
        after_img = resize_image(after_screenshot, self.image_size[0], self.image_size[1])

        # Construct verification prompt
        verification_prompt = f"""You are analyzing whether a desktop automation action worked as expected.

**Task Context:** {task}

**Action Taken:** {previous_action}

**Action Result:** {action_result}

Please analyze the before and after screenshots to determine:

1. **Success Status**: Did the action achieve its intended effect? (YES/NO/PARTIAL)
2. **Visual Changes**: What specific visual changes occurred between the screenshots?
3. **Expected vs Actual**: How do the actual results compare to what was expected?
4. **Issues Found**: Any problems, errors, or unexpected behaviors?
5. **Confidence**: How confident are you in this assessment? (HIGH/MEDIUM/LOW)

Provide your analysis in this format:
SUCCESS: [YES/NO/PARTIAL]
CHANGES: [Description of visual changes]
EXPECTED_VS_ACTUAL: [Comparison]
ISSUES: [Any problems found, or "None"]
CONFIDENCE: [HIGH/MEDIUM/LOW]
REASONING: [Detailed explanation of your assessment]"""

        # Prepare messages with both images
        messages = [
            {
                "role": "system",
                "content": "You are an expert at analyzing desktop automation results by comparing before and after screenshots."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64encode(before_img).decode('utf-8')}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64encode(after_img).decode('utf-8')}",
                            "detail": "high"
                        }
                    },
                    {
                        "type": "text",
                        "text": verification_prompt
                    }
                ]
            }
        ]

        try:
            # Make the first LLM call
            verification_response = self.gen_func(messages)
            logger.info(f"📊 Verification response: {verification_response[:200]}...")

            # Parse the verification response
            verification_result = self._parse_verification_response(verification_response)
            verification_result.update({
                "task": task,
                "action": previous_action,
                "action_result": action_result,
                "raw_response": verification_response
            })

            # Store in history
            self.verification_history.append(verification_result)

            return verification_result

        except Exception as e:
            logger.error(f"❌ Error in action verification: {e}")
            return {
                "success": "UNKNOWN",
                "changes": "Error during verification",
                "expected_vs_actual": "Could not analyze",
                "issues": f"Verification error: {e}",
                "confidence": "LOW",
                "reasoning": f"Technical error prevented verification: {e}",
                "task": task,
                "action": previous_action,
                "action_result": action_result,
                "raw_response": ""
            }

    def improve_planning(
        self,
        task: str,
        verification_result: Dict[str, Any],
        current_context: Dict[str, Any],
        agent_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Second LLM call: Use verification results to improve planning.

        Args:
            task: The overall task being performed
            verification_result: Results from the verification step
            current_context: Current state and context information
            agent_history: Previous agent interactions

        Returns:
            Dict containing planning improvements
        """
        logger.info("🧠 Starting planning improvement...")

        # Prepare context about verification results
        verification_summary = f"""
Action Verification Results:
- Success: {verification_result.get('success', 'UNKNOWN')}
- Changes Observed: {verification_result.get('changes', 'None')}
- Issues Found: {verification_result.get('issues', 'None')}
- Confidence: {verification_result.get('confidence', 'UNKNOWN')}
- Reasoning: {verification_result.get('reasoning', 'No reasoning provided')}
"""

        # Include recent verification history for context
        history_context = ""
        if len(self.verification_history) > 1:
            recent_verifications = self.verification_history[-3:]  # Last 3 verifications
            history_context = "\n\nRecent Verification History:\n"
            for i, v in enumerate(recent_verifications[:-1], 1):  # Exclude current one
                history_context += f"{i}. Action: {v.get('action', 'Unknown')[:50]}... -> Success: {v.get('success', 'Unknown')}\n"

        # Construct planning improvement prompt
        planning_prompt = f"""You are helping improve the planning for a desktop automation agent.

**Overall Task:** {task}

**Current Situation:**
{verification_summary}

**Previous Action:** {verification_result.get('action', 'Unknown')}
**Action Result:** {verification_result.get('action_result', 'Unknown')}

{history_context}

Based on the verification results, provide strategic guidance for the next steps:

1. **Next Action Strategy**: What approach should be taken next?
2. **Corrective Actions**: If the previous action failed, what corrections are needed?
3. **Risk Assessment**: What potential issues should be avoided?
4. **Success Indicators**: How will we know if the next action succeeds?
5. **Alternative Approaches**: What other strategies could be considered?

Provide your analysis in this format:
STRATEGY: [Overall approach for next steps]
CORRECTIONS: [Specific corrections needed, or "None"]
RISKS: [Potential risks to avoid]
SUCCESS_INDICATORS: [How to measure success]
ALTERNATIVES: [Alternative approaches to consider]
CONFIDENCE: [HIGH/MEDIUM/LOW]
REASONING: [Detailed explanation of recommendations]"""

        messages = [
            {
                "role": "system",
                "content": "You are an expert at strategic planning for desktop automation, helping agents learn from action verification results."
            },
            {
                "role": "user",
                "content": planning_prompt
            }
        ]

        try:
            # Make the second LLM call
            planning_response = self.gen_func(messages)
            logger.info(f"📋 Planning response: {planning_response[:200]}...")

            # Parse the planning response
            planning_result = self._parse_planning_response(planning_response)
            planning_result.update({
                "task": task,
                "verification_input": verification_result,
                "raw_response": planning_response
            })

            return planning_result

        except Exception as e:
            logger.error(f"❌ Error in planning improvement: {e}")
            return {
                "strategy": "Continue with basic approach",
                "corrections": f"Planning error: {e}",
                "risks": "High risk due to planning failure",
                "success_indicators": "Unknown",
                "alternatives": "Retry or manual intervention",
                "confidence": "LOW",
                "reasoning": f"Technical error prevented planning: {e}",
                "task": task,
                "verification_input": verification_result,
                "raw_response": ""
            }

    def _parse_verification_response(self, response: str) -> Dict[str, str]:
        """Parse the structured verification response."""
        result = {
            "success": "UNKNOWN",
            "changes": "Unknown",
            "expected_vs_actual": "Unknown",
            "issues": "Unknown",
            "confidence": "UNKNOWN",
            "reasoning": "No reasoning provided"
        }

        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SUCCESS:'):
                result["success"] = line.replace('SUCCESS:', '').strip()
            elif line.startswith('CHANGES:'):
                result["changes"] = line.replace('CHANGES:', '').strip()
            elif line.startswith('EXPECTED_VS_ACTUAL:'):
                result["expected_vs_actual"] = line.replace('EXPECTED_VS_ACTUAL:', '').strip()
            elif line.startswith('ISSUES:'):
                result["issues"] = line.replace('ISSUES:', '').strip()
            elif line.startswith('CONFIDENCE:'):
                result["confidence"] = line.replace('CONFIDENCE:', '').strip()
            elif line.startswith('REASONING:'):
                result["reasoning"] = line.replace('REASONING:', '').strip()

        return result

    def _parse_planning_response(self, response: str) -> Dict[str, str]:
        """Parse the structured planning response."""
        result = {
            "strategy": "Continue with basic approach",
            "corrections": "Unknown",
            "risks": "Unknown",
            "success_indicators": "Unknown",
            "alternatives": "Unknown",
            "confidence": "UNKNOWN",
            "reasoning": "No reasoning provided"
        }

        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('STRATEGY:'):
                result["strategy"] = line.replace('STRATEGY:', '').strip()
            elif line.startswith('CORRECTIONS:'):
                result["corrections"] = line.replace('CORRECTIONS:', '').strip()
            elif line.startswith('RISKS:'):
                result["risks"] = line.replace('RISKS:', '').strip()
            elif line.startswith('SUCCESS_INDICATORS:'):
                result["success_indicators"] = line.replace('SUCCESS_INDICATORS:', '').strip()
            elif line.startswith('ALTERNATIVES:'):
                result["alternatives"] = line.replace('ALTERNATIVES:', '').strip()
            elif line.startswith('CONFIDENCE:'):
                result["confidence"] = line.replace('CONFIDENCE:', '').strip()
            elif line.startswith('REASONING:'):
                result["reasoning"] = line.replace('REASONING:', '').strip()

        return result

    def get_verification_history(self) -> List[Dict[str, Any]]:
        """Get the verification history."""
        return self.verification_history.copy()

    def clear_history(self):
        """Clear the verification history."""
        self.verification_history.clear()
        logger.info("🗑️ Verification history cleared")