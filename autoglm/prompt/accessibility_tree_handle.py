import io
import re
import xml.etree.ElementTree as ET
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

from .deduplicate_node import filter_similar_nodes

attributes_ns_ubuntu = "https://accessibility.windows.example.org/ns/attributes"
attributes_ns_windows = "https://accessibility.windows.example.org/ns/attributes"
state_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/state"
state_ns_windows = "https://accessibility.windows.example.org/ns/state"
component_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/component"
component_ns_windows = "https://accessibility.windows.example.org/ns/component"
value_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/value"
value_ns_windows = "https://accessibility.windows.example.org/ns/value"
class_ns_windows = "https://accessibility.windows.example.org/ns/class"


def find_leaf_nodes(xlm_file_str):
    """Find all leaf nodes in the XML tree."""
    if not xlm_file_str:
        return []

    root = ET.fromstring(xlm_file_str)

    def collect_leaf_nodes(node, leaf_nodes):
        if not list(node):
            leaf_nodes.append(node)
        for child in node:
            collect_leaf_nodes(child, leaf_nodes)

    leaf_nodes = []
    collect_leaf_nodes(root, leaf_nodes)
    return leaf_nodes


def judge_node(node: ET, platform="Ubuntu", check_image=False) -> bool:
    """Judge whether a node should be kept based on platform-specific criteria."""
    if platform == "Ubuntu":
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
    elif platform == "Windows":
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'Ubuntu' or 'Windows'")

    keeps: bool = (
        node.tag.startswith("document")
        or node.tag.endswith("item")
        or node.tag.endswith("button")
        or node.tag.endswith("heading")
        or node.tag.endswith("label")
        or node.tag.endswith("scrollbar")
        or node.tag.endswith("searchbox")
        or node.tag.endswith("textbox")
        or node.tag.endswith("link")
        or node.tag.endswith("tabelement")
        or node.tag.endswith("textfield")
        or node.tag.endswith("textarea")
        or node.tag.endswith("menu")
        or node.tag
        in {
            "alert",
            "canvas",
            "check-box",
            "combo-box",
            "entry",
            "icon",
            "image",
            "paragraph",
            "scroll-bar",
            "section",
            "slider",
            "static",
            "table-cell",
            "terminal",
            "text",
            "netuiribbontab",
            "start",
            "trayclockwclass",
            "traydummysearchcontrol",
            "uiimage",
            "uiproperty",
            "uiribboncommandbar",
        }
    )
    keeps = (
        keeps
        and (
            platform == "Ubuntu"
            and node.get("{{{:}}}showing".format(_state_ns), "false") == "true"
            and node.get("{{{:}}}visible".format(_state_ns), "false") == "true"
            or platform == "Windows"
            and node.get("{{{:}}}visible".format(_state_ns), "false") == "true"
        )
        and (
            node.get("name", "") != ""
            or node.text is not None
            and len(node.text) > 0
            or check_image
            and node.get("image", "false") == "true"
        )
    )

    coordinates: Tuple[int, int] = eval(node.get("{{{:}}}screencoord".format(_component_ns), "(-1, -1)"))
    sizes: Tuple[int, int] = eval(node.get("{{{:}}}size".format(_component_ns), "(-1, -1)"))
    keeps = keeps and coordinates[0] >= 0 and coordinates[1] >= 0 and sizes[0] > 0 and sizes[1] > 0
    return keeps


def filter_nodes(root: ET, platform="Ubuntu", check_image=False):
    """Filter nodes based on platform-specific criteria."""
    filtered_nodes = []

    for node in root.iter():
        if judge_node(node, platform, check_image):
            filtered_nodes.append(node)

    return filtered_nodes


def find_active_applications(tree, state_ns):
    """Find applications that are currently active."""
    apps_with_active_tag = []
    for application in list(tree.getroot()):
        app_name = application.attrib.get("name")
        for frame in application:
            is_active = frame.attrib.get("{{{:}}}active".format(state_ns), "false")
            if is_active == "true":
                apps_with_active_tag.append(app_name)
    if apps_with_active_tag:
        to_keep = apps_with_active_tag + ["gnome-shell"]
    else:
        to_keep = ["gjs", "gnome-shell"]
    return to_keep


def linearize_accessibility_tree(accessibility_tree, platform="Ubuntu", use_relative_coordinates=True, screen_size=(1920, 1080)):
    """Convert accessibility tree XML to linearized format."""
    if platform == "Ubuntu":
        _attributes_ns = attributes_ns_ubuntu
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
        _value_ns = value_ns_ubuntu
    elif platform == "Windows":
        _attributes_ns = attributes_ns_windows
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
        _value_ns = value_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'Ubuntu' or 'Windows'")

    try:
        tree = ET.ElementTree(ET.fromstring(accessibility_tree))
        keep_apps = find_active_applications(tree, _state_ns)

        # Remove inactive applications
        for application in list(tree.getroot()):
            if application.get("name") not in keep_apps:
                tree.getroot().remove(application)

        filtered_nodes = filter_nodes(tree.getroot(), platform, check_image=True)
        linearized_accessibility_tree = ["tag\ttext\tposition (center x & y)\tsize (w & h)"]

        # Linearize the accessibility tree nodes into a table format
        for node in filtered_nodes:
            try:
                text = node.text if node.text is not None else ""
                text = text.strip()
                name = node.get("name", "").strip()
                if text == "":
                    text = name
                elif name != "" and text != name:
                    text = f"{name} ({text})"

                text = text.replace("\n", "\\n")
                pos = node.get("{{{:}}}screencoord".format(_component_ns), "")
                size = node.get("{{{:}}}size".format(_component_ns), "")

                x, y = re.match(r"\((\d+), (\d+)\)", pos).groups()
                w, h = re.match(r"\((\d+), (\d+)\)", size).groups()
                x_mid, y_mid = int(x) + int(w) // 2, int(y) + int(h) // 2

                if use_relative_coordinates:
                    # Convert to relative coordinates (0-1)
                    screen_width, screen_height = screen_size
                    rel_x = round(x_mid / screen_width, 3)
                    rel_y = round(y_mid / screen_height, 3)
                    rel_w = round(int(w) / screen_width, 3)
                    rel_h = round(int(h) / screen_height, 3)
                    coords_str = f"({rel_x}, {rel_y})"
                    size_str = f"({rel_w}, {rel_h})"
                else:
                    coords_str = f"({x_mid}, {y_mid})"
                    size_str = size

                linearized_accessibility_tree.append(
                    "{:}\t{:}\t{:}\t{:}".format(node.tag, text, coords_str, size_str)
                )
            except Exception as e:
                continue

        # Filter out similar nodes
        linearized_accessibility_tree = filter_similar_nodes("\n".join(linearized_accessibility_tree))
    except Exception as e:
        print(f"Error in linearize_accessibility_tree: {e}")
        linearized_accessibility_tree = ""

    return linearized_accessibility_tree


def trim_accessibility_tree(linearized_accessibility_tree, max_items):
    """Trim accessibility tree to max number of items."""
    lines = linearized_accessibility_tree.strip().split("\n")
    if len(lines) > max_items:
        lines = lines[:max_items]
        linearized_accessibility_tree = "\n".join(lines)
        linearized_accessibility_tree += "\n..."
    return linearized_accessibility_tree