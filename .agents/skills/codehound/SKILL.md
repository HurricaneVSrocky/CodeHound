---
name: codehound
description: C++ Memory Graph Database tool for AI Agents to traverse call-graphs, trace pointer crashes, and analyze codebase relations without reading raw text files.
---
# codehound

CodeHound allows AI Agents to autonomously query an in-memory graph database generated from a C++ AST compilation dump. Instead of searching raw files or loading thousands of lines of source code into the context window, you should use CodeHound to pinpoint variable references, track inheritance chains, trace function calls, and locate segmentation fault reasons.

---

## 🛠 Available Tools

The following tools are available as Python functions in `backend/agent_tools.py` for direct Function Calling, or via CLI script `scripts/query_graph.py`.

### 1. `find_node_by_name`
- **Purpose**: Search the in-memory code graph database for a node spelling/name (e.g. function declarations, global variables, class definitions).
- **Arguments**:
  - `name`: String. The exact or fuzzy name of the class, struct, function, method, or variable.
- **Example Usage (Function Calling)**:
  `find_node_by_name("main")`
- **Example Usage (CLI)**:
  `python .agents/skills/codehound/scripts/query_graph.py search "main"`

### 2. `get_node_relations`
- **Purpose**: Retrieve neighbor nodes and dependency edges for a specific node ID. Useful for finding what a function calls, what variables it reads/writes, or who calls it.
- **Arguments**:
  - `node_id`: Integer. The node ID found using `find_node_by_name`.
  - `depth`: Integer (optional, default: `1`). Travel distance depth. Keep it small (`1` or `2`) to prevent response truncation.
  - `direction`: Integer (optional, default: `0`).
    - `0`: Both directions (incoming + outgoing relations).
    - `1`: Outgoing relations (targets this node calls, reads, or inherits from).
    - `2`: Incoming relations (sources calling this node or reading/writing to it).
- **Example Usage (Function Calling)**:
  `get_node_relations(13353, depth=1, direction=1)`
- **Example Usage (CLI)**:
  `python .agents/skills/codehound/scripts/query_graph.py relations 13353 --depth 1 --direction 1`

---

## 🧠 Recommended Workflow for AI Agents

When analyzing bug descriptions, segmentation faults, or tracing code logic:

### Step 1: Locate Target Nodes
Start by finding the global Node IDs of functions or variables mentioned in the user bug description or stack trace.
*Example: Search for the main function or suspected classes.*
```bash
python .agents/skills/codehound/scripts/query_graph.py search "main"
```

### Step 2: Traverse Dependencies
Use the returned Node ID to inspect what functions it calls or what variables it accesses.
*Example: If Node ID 13353 is `main`, inspect outgoing calls (`direction=1`).*
```bash
python .agents/skills/codehound/scripts/query_graph.py relations 13353 --direction 1
```

### Step 3: Deep Dive suspect Nodes
Iterate by looking up related nodes, tracing calls down or finding variable reads/writes.
*Example: If main calls `dangerousAction` (Node ID 11207), check its outgoing dependencies.*
```bash
python .agents/skills/codehound/scripts/query_graph.py relations 11207 --direction 1
```

### Step 4: Formulate Conclusion
Analyze the dependency flow (e.g. `dangerousAction` --[Reads]--> `DangerPointer`). If `DangerPointer` is an uninitialized global pointer, you can immediately identify the root cause without parsing raw files.

---

## ⚠️ Common Node/Edge Types Reference

### Node Types
- `File` (1): Compilation translation unit.
- `Class` (2) / `Struct` (3): Class and Structure declarations.
- `Function` (4) / `Method` (5): Free functions and Class member methods.
- `Variable` (6): Global/local variable and field declarations.

### Edge Types
- `Includes` (1): Header file import.
- `Inherits` (2): Class base specifier inheritance.
- `Calls` (3): Function call expression.
- `Reads` (4): Read access of a variable.
- `Writes` (5): Write access or assignment of a variable.
