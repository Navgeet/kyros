import logging
import re
from base64 import b64encode
from PIL import Image
from io import BytesIO
from typing import Dict, List, Optional

logger = logging.getLogger("kyros.agent")


def resize_image(image, w, h):
    """Resize image to specified dimensions."""
    img = Image.open(BytesIO(image))
    img = img.resize((w, h))
    buf = BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()
    return img_bytes


def parse_code_from_string(input_string):
    """Parse code blocks from LLM response."""
    if input_string.strip() in ["WAIT", "DONE", "FAIL"]:
        return [input_string.strip()]

    # Extract code from triple backticks
    pattern = r"```(?:\w+\s+)?(.*?)```"
    matches = re.findall(pattern, input_string, re.DOTALL)

    codes = []

    for match in matches:
        match = match.strip()
        commands = ["WAIT", "DONE", "FAIL"]

        if match in commands:
            codes.append(match.strip())
        elif match.split("\n")[-1] in commands:
            if len(match.split("\n")) > 1:
                codes.append("\n".join(match.split("\n")[:-1]))
            codes.append(match.split("\n")[-1])
        else:
            codes.append(match)

    return codes


class KyrosAgent:
    """Standalone AutoGLM agent for desktop automation."""

    def __init__(
        self,
        action_space="autoglm_computer_use",
        observation_type="a11y_tree",
        max_trajectory_length=3,
        a11y_tree_max_items=300,
        with_image: bool = True,
        screen_size=(1920, 1080),
        image_size=(1920, 1080),
        with_atree: bool = False,
        glm41v_format: bool = True,
        relative_coordinate: bool = True,
        client_password="password",
        gen_func=None,
        tool_in_sys_msg: bool = True,
    ):
        self.action_space = action_space
        self.observation_type = observation_type
        assert action_space in ["autoglm_computer_use"], "Invalid action space"
        assert observation_type in ["a11y_tree"], "Invalid observation type"
        self.max_trajectory_length = max_trajectory_length
        self.a11y_tree_max_items = a11y_tree_max_items
        self.with_image = with_image
        self.screen_size = screen_size
        self.image_size = image_size
        self.with_atree = with_atree
        self.glm41v_format = glm41v_format
        self.relative_coordinate = relative_coordinate
        self.client_password = client_password
        self.gen_func = gen_func
        self.tool_in_sys_msg = tool_in_sys_msg

        self.tool_list = {
            "libreoffice_calc": "CalcTools",
            "libreoffice_impress": "ImpressTools",
            "libreoffice_writer": "WriterTools",
            "code": "CodeTools",
            "vlc": "VLCTools",
            "google_chrome": "BrowserTools",
        }

        # Import grounding agent and set coordinate mode
        from .prompt.grounding_agent import GroundingAgent
        GroundingAgent.relative_coordinate = relative_coordinate
        self.Agent = GroundingAgent

        self.contents = []

    @property
    def turn_number(self):
        return len(self.contents)

    def prepare(self, instruction: str, obs: Dict, history: List, last_result: str = "") -> List:
        """Prepare messages for the LLM based on current observation."""
        from .prompt.procedural_memory import Prompt
        from .prompt.accessibility_tree_handle import linearize_accessibility_tree, trim_accessibility_tree

        if "exe_result" in obs and not last_result:
            last_result = obs["exe_result"]
            if self.contents:
                self.contents[-1]["exe_result"] = last_result

        cur_app = obs.get("cur_app", "")
        logger.info(f"current app is {cur_app}")

        if cur_app:
            tool_name = cur_app.strip().lower().replace("-", "_")
            tool_name = tool_name if tool_name in self.tool_list.keys() else None
        else:
            tool_name = None

        setup_prompt, func_def_prompt, note_prompt = Prompt.construct_procedural_memory(
            self.Agent,
            app_name=tool_name,
            client_password=self.client_password,
            with_image=self.with_image,
            with_atree=self.with_atree,
            relative_coordinate=self.relative_coordinate,
            glm41v_format=self.glm41v_format
        )

        if self.tool_in_sys_msg:
            system_message = setup_prompt + "\n\n" + func_def_prompt + "\n\n" + note_prompt
        else:
            system_message = setup_prompt + "\n\n" + note_prompt
        system_message += "\n\n**IMPORTANT** You are asked to complete the following task: {}".format(instruction)

        messages = [
            {
                "role": "system",
                "content": system_message,
            }
        ]
        messages.extend(history)

        if obs.get("apps"):
            app_str = "Window ID    App Name    Title\n"
            for window_id, app in obs["apps"].items():
                app_str += f"{window_id}    {app['app_name']}    {app['title']}\n"
        else:
            app_str = "None"

        last_result = last_result.strip() if last_result else "None"
        last_result = last_result[:2000] + "..." if len(last_result) > 2000 else last_result

        tree = ""
        if obs.get("accessibility_tree"):
            tree = linearize_accessibility_tree(
                obs["accessibility_tree"],
                "Ubuntu",
                use_relative_coordinates=self.relative_coordinate,
                screen_size=self.screen_size
            )
            tree = trim_accessibility_tree(tree, 300)

        app_info = obs.get("app_info", "").strip() if obs.get("app_info") else "None"
        app_info = app_info[:5000] + "..." if len(app_info) > 5000 else app_info

        prompt = "* Apps: {}\n\n* Current App: {}{}\n\n* App Info: {}\n\n* Previous Action Result: {}".format(
            app_str.strip(),
            obs.get("cur_window_id", "").strip() if obs.get("cur_window_id") in app_str else "None",
            '\n\n* A11y Tree: {}'.format(tree.strip()) if self.with_atree else "",
            app_info,
            last_result if last_result else "None",
        ) + (
            "\n\n" + func_def_prompt if not self.tool_in_sys_msg else ""
        )

        content = [{"type": "text", "text": prompt}]
        if self.with_image and obs.get('screenshot'):
            screenshot = resize_image(obs['screenshot'], self.image_size[0], self.image_size[1])
            images = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64encode(screenshot).decode('utf-8')}",
                        "detail": "high",
                    },
                }
            ]

            # Add previous screenshot if available for comparison
            if obs.get('previous_screenshot'):
                prev_screenshot = resize_image(obs['previous_screenshot'], self.image_size[0], self.image_size[1])
                images.insert(0, {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64encode(prev_screenshot).decode('utf-8')}",
                        "detail": "high",
                    },
                })

            content = images + content

        messages.append({"role": "user", "content": content})

        return messages

    def execute(self, response, obs):
        """Parse and execute actions from LLM response."""
        try:
            actions = parse_code_from_string(response)
            action = actions[0]
            # logger.info(f"The parsed action is {action}")

            if "Agent." in action:
                # Replace Agent. with self.Agent. and evaluate in proper context
                exec_globals = {"Agent": self.Agent}
                actions = [
                    eval(action, exec_globals),
                ]
            elif "BrowserTools." in action:
                actions = [
                    eval(action),
                ]
            else:
                cur_app = obs.get("cur_app", "").strip().replace("-", "_").lower()
                actions = self.Agent.tool_commands(action, cur_app)
                logger.info(f"The grounded action is {actions[0]}")
        except Exception as e:
            print("Failed to parse action from response", e)
            actions = []

        return actions

    def format_history(self, max_turns=30):
        """Format conversation history for context."""
        history = []
        for ix in range(self.turn_number):
            if ix == 0:
                env_input = "**Environment State (Omitted)**"
            else:
                env_input = (
                    f"**Environment State (Omitted)**\nPrevious Action Result: {self.contents[ix - 1]['exe_result']}"
                )

            env_input = env_input[:2000] + "..." if len(env_input) > 2000 else env_input
            response = (
                self.contents[ix]["response"][:1500] + "..."
                if len(self.contents[ix]["response"]) > 1500
                else self.contents[ix]["response"]
            )
            history.append({"role": "user", "content": [{"type": "text", "text": env_input}]})
            history.append({"role": "assistant", "content": [{"type": "text", "text": response}]})

        return history[-max_turns * 2:]

    def predict(self, instruction: str, obs: Dict) -> tuple:
        """Generate next action based on instruction and observation."""
        history = self.format_history()
        messages = self.prepare(instruction, obs, history)

        assert self.gen_func is not None, "gen_func is not set"
        try:
            response = self.gen_func(messages)
        except Exception as e:
            logger.error("Failed to call gen_func, Error: " + str(e))
            response = ""

        logger.info("RESPONSE: %s", response)

        actions = self.execute(response, obs)

        # Update the contents
        self.contents.append(
            {
                "instruction": instruction,
                "index": len(self.contents),
                "response": response,
                "action": "Parse error" if not actions else actions[0],
                "exe_result": "Invalid action" if not actions else "",
                **obs,
            }
        )
        return response, actions

    def reset(self, _logger=None):
        """Reset agent state."""
        global logger
        logger = _logger if _logger is not None else logging.getLogger("kyros.agent")
        self.contents = []