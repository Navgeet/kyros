import inspect
import json
import os
import textwrap

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_func(json_data):
    """Generate function definitions from JSON API specs."""
    class_funcs = {}
    no_class_funcs = []
    cls_name = ""

    for item in json_data:
        if item["type"] == "function":
            func = item["function"]
            func_parts = func["name"].split(".")

            if len(func_parts) == 2:
                class_name, func_name = func_parts
                if class_name not in class_funcs:
                    class_funcs[class_name] = []
                class_funcs[class_name].append(item)
            else:
                no_class_funcs.append(item)

    code = ""

    # Generate class-based functions
    for class_name, funcs in class_funcs.items():
        code += f"class {class_name}:\n"
        cls_name = class_name
        for item in funcs:
            func = item["function"]
            func_name = func["name"].split(".")[-1]
            description = func["description"]
            params = func["parameters"]["properties"]
            required = func["parameters"].get("required", [])

            # Build parameter list
            param_list = ["cls"]
            # Add required parameters first
            for param_name in required:
                param_list.append(f"{param_name}")
            # Then add optional parameters
            for param_name in params:
                if param_name not in required:
                    param_list.append(f"{param_name}")

            # Build function definition
            func_def = f"    def {func_name}({', '.join(param_list)}):\n"

            # Build docstring
            docstring = f'        """\n        {description}\n\n        Args:\n'
            if len(param_list) == 1:  # Only cls parameter
                docstring += "            None\n"
            else:
                # Document required parameters first
                for param_name in required:
                    param_type = params[param_name]["type"]
                    param_desc = params[param_name].get("description", "")
                    docstring += f"            {param_name} ({param_type}): {param_desc}\n"
                # Then document optional parameters
                for param_name in params:
                    if param_name not in required:
                        param_type = params[param_name]["type"]
                        param_desc = params[param_name].get("description", "")
                        docstring += f"            {param_name} ({param_type}, optional): {param_desc}\n"

            docstring += '        """\n'

            code += func_def + docstring + "\n"

        code += "\n"

    # Generate standalone functions
    for item in no_class_funcs:
        func = item["function"]
        func_name = func["name"]
        description = func["description"]
        params = func["parameters"]["properties"]
        required = func["parameters"].get("required", [])

        # Build parameter list
        param_list = []
        # Add required parameters first
        for param_name in required:
            param_list.append(f"{param_name}")
        # Then add optional parameters
        for param_name in params:
            if param_name not in required:
                param_list.append(f"{param_name}")

        # Build function definition
        func_def = f"def {func_name}({', '.join(param_list)}):\n"

        # Build docstring
        docstring = f'    """\n    {description}\n\n    Args:\n'
        if not param_list:
            docstring += "        None\n"
        else:
            # Document required parameters first
            for param_name in required:
                param_type = params[param_name]["type"]
                param_desc = params[param_name].get("description", "")
                docstring += f"        {param_name} ({param_type}): {param_desc}\n"
            # Document optional parameters
            for param_name in params:
                if param_name not in required:
                    param_type = params[param_name]["type"]
                    param_desc = params[param_name].get("description", "")
                    docstring += f"        {param_name} ({param_type}, optional): {param_desc}\n"

        docstring += '    """\n'

        code += func_def + docstring + "\n"

    return code.strip(), cls_name


setup_prompt = """You are an agent which follow my instruction and perform desktop computer tasks as instructed.
You have good knowledge of computer and good internet connection and assume your code will run on a computer for controlling the mouse and keyboard.
For each step, you will get an observation of the desktop by 1) screenshot; 2) current application name; 3) accessibility tree, which is based on AT-SPI library; 4) application info; 5) last action result.
You should first generate a plan for completing the task, confirm the previous results, reflect on the current status, then generate operations to complete the task in python-style pseudo code using the predefined functions.

Your output should STRICTLY follow the format:
<think>
{**YOUR-PLAN-AND-THINKING**}
</think>
```python
{**ONE-LINE-OF-CODE**}
```"""

func_def_tool_template = """You will be provided access to the following methods to interact with the UI:
    1. class Agent, a grounding agent which provides basic action space to interact with desktop.
    2. class {tool_class_name}, which provides tools to interact with the current application {app_name}.

Here are the defination of the classes:
```python
{class_content}
```"""

func_def_template = """You will be provided access to the following methods to interact with the UI:

```python
{class_content}
```"""

def get_note_prompt(client_password="password", relative_coordinate=True):
    """Get note prompt with coordinate system information."""
    coordinate_info = ""
    if relative_coordinate:
        coordinate_info = """- **COORDINATE SYSTEM**: Use relative coordinates (0.0 to 1.0) for all position-based actions
  - [0.0, 0.0] = top-left corner of screen
  - [1.0, 1.0] = bottom-right corner of screen
  - [0.5, 0.5] = center of screen
  - Example: Agent.click([0.5, 0.3]) clicks at horizontal center, 30% down from top
  - Accessibility tree coordinates are also in relative format"""
    else:
        coordinate_info = """- **COORDINATE SYSTEM**: Use absolute pixel coordinates for all position-based actions
  - Coordinates are in pixels relative to top-left corner [0, 0]
  - Example: Agent.click([960, 540]) clicks at pixel position (960, 540)"""

    return f"""* Note:
- Your code should be wrapped in ```python```, and your plan and thinking should be wrapped in <think></think>.
- Only **ONE-LINE-OF-CODE** at a time.
- Each code block is context independent, and variables from the previous round cannot be used in the next round.
- Do not put anything other than python code in ```python```.
- You **can only use the above methods to interact with the UI**, do not invent new methods.
- Return with `Agent.exit(success=True)` or `Agent.exit(success=True, message="description")` immediately after the task is completed.
- If you think cannot complete the task, **DO NOT keep repeating actions, just return with `Agent.exit(success=False)` or `Agent.exit(success=False, message="reason")`.**
- The computer's environment is Linux, e.g., Desktop path is '/home/user/Desktop'
- My computer's password is '{client_password}', feel free to use it when you need sudo rights
{coordinate_info}"""

# Keep the old note_prompt for backward compatibility
note_prompt = """* Note:
- Your code should be wrapped in ```python```, and your plan and thinking should be wrapped in <think></think>.
- Only **ONE-LINE-OF-CODE** at a time.
- Each code block is context independent, and variables from the previous round cannot be used in the next round.
- Do not put anything other than python code in ```python```.
- You **can only use the above methods to interact with the UI**, do not invent new methods.
- Return with `Agent.exit(success=True)` or `Agent.exit(success=True, message="description")` immediately after the task is completed.
- If you think cannot complete the task, **DO NOT keep repeating actions, just return with `Agent.exit(success=False)` or `Agent.exit(success=False, message="reason")`.**
- The computer's environment is Linux, e.g., Desktop path is '/home/user/Desktop'
- My computer's password is '{client_password}', feel free to use it when you need sudo rights"""


class Prompt:
    @staticmethod
    def construct_procedural_memory(
        agent_class,
        app_name=None,
        client_password="password",
        with_image=True,
        with_atree=False,
        relative_coordinate=True,
        glm41v_format=True
    ):
        """Construct prompts for the agent."""
        agent_class_content = "Class Agent:"
        for attr_name in dir(agent_class):
            attr = getattr(agent_class, attr_name)
            if callable(attr) and hasattr(attr, "is_agent_action"):
                # Use inspect to get the full function signature
                signature = inspect.signature(attr)
                agent_class_content += f"""
    def {attr_name}{signature}:
        '''{attr.__doc__}'''
    """

        # For standalone version, we'll skip tool loading since we don't have the tool JSON files
        # This could be extended to include tool definitions if needed

        func_def_prompt = func_def_template.format(class_content=agent_class_content.strip())
        note_prompt_formatted = get_note_prompt(client_password=client_password, relative_coordinate=relative_coordinate)

        return setup_prompt, func_def_prompt, note_prompt_formatted


if __name__ == "__main__":
    from grounding_agent import GroundingAgent

    print(Prompt.construct_procedural_memory(GroundingAgent))