# RAG Testing Usage Examples

## Basic Usage

Test RAG with a plan file:
```bash
python test_rag.py sample_plan.txt
```

## With User Request Context

Provide original user request for better context:
```bash
python test_rag.py sample_plan.txt --user-request "Calculate 5+3 using the calculator app"
```

## Verbose Output

Enable detailed logging:
```bash
python test_rag.py sample_plan.txt --verbose
```

## What the Script Does

1. **Reads Plan File**: Loads your plan from a text file
2. **Generates Embedding**: Creates vector embedding using dengcao/Qwen3-Embedding-8B:Q4_K_M
3. **Searches Learning Objects**: Queries Couchbase for relevant past experiences
4. **Shows Results**: Displays found learning objects with similarity scores
5. **Refines Plan**: Uses InternLM to improve the plan based on learned knowledge
6. **Compares Output**: Shows before/after comparison and impact analysis

## Environment Variables

Make sure these are set:
```bash
export COUCHBASE_USERNAME='admin'
export COUCHBASE_PASSWORD='admin123'
export COUCHBASE_CONNECTION='couchbase://192.168.0.213'
export COUCHBASE_BUCKET='foo'
export COUCHBASE_SCOPE='bar'
export COUCHBASE_COLLECTION='learnings'
export COUCHBASE_SEARCH_INDEX='learnings'
```

## Sample Plan Format

Create a text file with your plan steps:
```
1. Focus on the calculator application window
2. Click on the number "5" button
3. Click on the "+" operator button
4. Click on the number "3" button
5. Click on the "=" button to calculate the result
6. Verify the result shows "8" in the display
7. Take a screenshot to confirm the calculation was successful
```

## Expected Output

The script will show:
- Original plan content
- Generated embedding dimensions
- Found learning objects with scores
- Refined plan incorporating learned knowledge
- Impact analysis (length changes, learning objects used, etc.)