import re


def parse_line(line):
    """Parse accessibility tree line format."""
    # Parse format like: label   Google Chrome   (191, 13)       (104, 17)
    pattern = r"^(\S+)\s+(.+?)\s+\((\d+), (\d+)\)\s+\((\d+), (\d+)\)"
    m = re.match(pattern, line)
    if not m:
        return None
    node_type, text, cx, cy, w, h = m.groups()
    cx, cy, w, h = map(int, (cx, cy, w, h))
    # bounding box as (x1, y1, x2, y2)
    x1 = cx - w // 2
    y1 = cy - h // 2
    x2 = x1 + w
    y2 = y1 + h
    return {
        "type": node_type,
        "text": text.strip(),
        "bbox": (x1, y1, x2, y2),
        "center": (cx, cy),
        "size": (w, h),
        "raw": line,
    }


def iou(box1, box2):
    """Calculate Intersection over Union of two bounding boxes."""
    # box: (x1, y1, x2, y2)
    xi1 = max(box1[0], box2[0])
    yi1 = max(box1[1], box2[1])
    xi2 = min(box1[2], box2[2])
    yi2 = min(box1[3], box2[3])
    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    inter_area = inter_width * inter_height
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - inter_area
    if union == 0:
        return 0
    return inter_area / union


def norm_text(s):
    """Normalize text: lowercase, remove spaces."""
    return re.sub(r"\s+", "", s.lower())


def text_similarity(a, b):
    """Simple text similarity: 1 if identical, 0 otherwise."""
    na, nb = norm_text(a), norm_text(b)
    if na == nb:
        return 1.0
    else:
        return 0


def filter_similar_nodes(linearized_accessibility_tree):
    """Filter out similar/duplicate nodes from accessibility tree."""
    lines = [ln for ln in linearized_accessibility_tree.split("\n") if ln.strip()]
    # parse all nodes
    nodes = []
    for ln in lines:
        node = parse_line(ln)
        if node:
            nodes.append(node)
        else:
            # Keep unparseable lines
            nodes.append({"raw": ln, "invalid": True})

    filtered = []
    removed = [False] * len(nodes)
    # Thresholds can be adjusted
    IOU_THRESH = 0.2
    TEXT_THRESH = 0.9

    for i, ni in enumerate(nodes):
        if ni.get("invalid"):
            filtered.append(ni["raw"])
            continue
        if removed[i]:
            continue
        for j in range(i + 1, len(nodes)):
            nj = nodes[j]
            if nj.get("invalid"):
                continue
            iou_val = iou(ni["bbox"], nj["bbox"])
            text_sim = text_similarity(ni["text"], nj["text"])
            if iou_val > IOU_THRESH and text_sim > TEXT_THRESH:
                # Remove the latter one if very similar
                removed[j] = True
        # Keep if not marked for removal
        if not removed[i]:
            filtered.append(ni["raw"])

    return "\n".join(filtered)