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
  - `node_id`: Integer. The node ID found using `find_node_by_name` or `find_node_by_location`.
  - `depth`: Integer (optional, default: `1`). Travel distance depth. Keep it small (`1` or `2`) to prevent response truncation.
  - `direction`: Integer (optional, default: `0`).
    - `0`: Both directions (incoming + outgoing relations).
    - `1`: Outgoing relations (targets this node calls, reads, or inherits from).
    - `2`: Incoming relations (sources calling this node or reading/writing to it).
- **Example Usage (Function Calling)**:
  `get_node_relations(13353, depth=1, direction=1)`
- **Example Usage (CLI)**:
  `python .agents/skills/codehound/scripts/query_graph.py relations 13353 --depth 1 --direction 1`

### 3. `find_node_by_location`
- **Purpose**: Locate AST nodes (e.g. functions, variables, classes) that correspond to or contain a specific line number within a file. Best for tracing crash stack traces or compiler warnings where only `file:line` is known.
- **Arguments**:
  - `file_path`: String. The file path or a substring (e.g. `main.cpp`).
  - `line_number`: Integer. The line number from the log or compiler output.
- **Example Usage (Function Calling)**:
  `find_node_by_location("main.cpp", 52)`
- **Example Usage (CLI)**:
  `python .agents/skills/codehound/scripts/query_graph.py locate "main.cpp" 52`

---

## 🧠 Recommended Workflow for AI Agents

When analyzing bug descriptions, segmentation faults, or tracing code logic:

### Step 1: Locate Target Nodes
Start by finding the global Node IDs.
- If you have function/variable names from the bug report, use `find_node_by_name` (or CLI `search`):
  ```bash
  python .agents/skills/codehound/scripts/query_graph.py search "main"
  ```
- If you only have filename and line numbers from compiler warnings or crash logs, use `find_node_by_location` (or CLI `locate`):
  ```bash
  python .agents/skills/codehound/scripts/query_graph.py locate "main.cpp" 52
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

---

## 🛠️ Case Study: Debugging crash trace with file & line

Suppose you are given a stack trace showing a crash in `Dog.cpp` at line 16.

### Step 1: Locate the node for Dog.cpp:16
Run `locate` to find the exact C++ symbol:
```bash
python .agents/skills/codehound/scripts/query_graph.py locate "Dog.cpp" 16
```
Output:
```text
Found 1 nodes matching location 'Dog.cpp:16':
  - Node ID: 11205 | Type: Method | Name: Zoo::Dog::dangerousAction | Location: tests/dummy_project/Dog.cpp:14
```
*Note: Even though the crash happened at line 16, CodeHound correctly resolved it to `Zoo::Dog::dangerousAction` which starts at line 14.*

### Step 2: Fetch outgoing relations of Node 11205
Check what this method calls or reads at Node ID 11205:
```bash
python .agents/skills/codehound/scripts/query_graph.py relations 11205 --direction 1
```
Output:
```text
Dependency relations for Node ID 11205 (Depth 1, Direction 1):
  - Zoo::Dog::dangerousAction --[Reads]--> Zoo::GlobalAnimalCount
  - Zoo::Dog::dangerousAction --[Reads]--> Zoo::Dog::uninitializedPtr
```
*Analysis: The function reads `Zoo::Dog::uninitializedPtr`. If a method reads a member pointer right before crashing, `uninitializedPtr` is a high suspect for null-pointer dereferencing.*

### Step 3: Trace writes to `uninitializedPtr`
Find who writes to `uninitializedPtr` to see if it was ever initialized. First locate `uninitializedPtr` Node ID:
```bash
python .agents/skills/codehound/scripts/query_graph.py search "uninitializedPtr"
```
Output:
```text
Found 1 nodes matching 'uninitializedPtr':
  - Node ID: 11206 | Type: Variable | Name: Zoo::Dog::uninitializedPtr | Location: tests/dummy_project/Dog.h:20
```
Query incoming relations (who writes to it, `direction=2`):
```bash
python .agents/skills/codehound/scripts/query_graph.py relations 11206 --direction 2
```
Output:
```text
Dependency relations for Node ID 11206 (Depth 1, Direction 2):
  - Zoo::Dog::dangerousAction --[Reads]--> Zoo::Dog::uninitializedPtr
```
*Conclusion: There are NO `[Writes]` relations pointing to `uninitializedPtr`! The pointer is never initialized, leading directly to a segmentation fault when dereferenced in `Zoo::Dog::dangerousAction`.*
