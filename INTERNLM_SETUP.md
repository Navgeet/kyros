# InternLM Setup for Click Coordinate Detection

## Configuration Required

To use the `tools.get_click_coordinates()` function, you need to configure the InternLM API endpoint in `query_image.py`.

### Steps:

1. **Update API endpoint** in `query_image.py` line 42:
   ```python
   api_url = "YOUR_INTERNLM_API_ENDPOINT_HERE"
   ```

2. **Add authentication** if required (line 46-48):
   ```python
   headers = {
       "Content-Type": "application/json",
       "Authorization": "Bearer YOUR_API_KEY_HERE"  # If needed
   }
   ```

### Model Requirements

- Model: `internvl3.5-241b-a28b`
- API format: OpenAI-compatible
- Required capabilities: Vision (image + text input)

### Usage

Once configured, Claude Code will automatically use this for precise clicking:

```python
# Instead of guessing coordinates:
tools.click(0.5, 0.3)

# Claude Code will now use:
coords = tools.get_click_coordinates("submit button")
tools.click(coords[0], coords[1])
```

This should dramatically improve clicking accuracy by using AI vision to locate UI elements precisely.