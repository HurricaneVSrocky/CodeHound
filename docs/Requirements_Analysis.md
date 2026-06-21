# C++ 代码图谱与 AI 辅助定位系统 - 需求分析文档
[toc]
**文档版本**: v1.0 (MVP)v
**更新日期**: 202X-XX-XX
**项目状态**: 需求已锁定，准备进入开发阶段

## 1. 项目概述 (Project Overview)

### 1.1 项目背景
在大型 C++ 项目中，代码结构极其复杂（涉及深层继承、海量调用栈）。当出现缺陷 (Bug) 时，单纯依赖大语言模型 (LLM) 直接阅读散落的代码文件，往往因上下文窗口限制而产生“幻觉”，或无法精确定位。
本项目旨在通过静态解析 C++ 编译过程件，提取代码实体与关系，构建基于内存的高性能**代码图谱 (Code Property Graph)**。该图谱将作为核心基础设施，一侧为开发者提供前端可视化代码追踪，另一侧作为 RAG（检索增强生成）的结构化数据源，为 AI Agent 提供精准的“代码拓扑上下文”。

### 1.2 核心业务价值
*   **研发提效**：提供毫秒级响应的全局代码关系检索，替代传统的 `grep` 或 IDE 缓慢的 "Find Usages"。
*   **AI 赋能**：将大模型从“文本阅读者”升级为“图谱漫游者”，实现具备强逻辑支撑的 C++ 缺陷定位。

### 1.3 MVP 阶段边界说明
为保证项目快速落地（MVP），第一期系统聚焦于**函数级/轻量级粗粒度图谱**（暂不包含函数体内部的控制流/数据流）。图谱重点解决“谁调用了谁”、“谁继承了谁”、“谁修改了哪个全局变量”的问题。

---

## 2. 系统架构 (System Architecture)

系统采用**高度解耦**的架构设计，分为四大独立运行的子系统：
1.  **离线解析器 (C++ CLI)**：负责纯粹的 AST 提取。
2.  **核心图检索引擎 (C++ Library + Pybind11)**：负责内存驻留与极速图遍历。
3.  **API/BFF 后端 (Python FastAPI)**：负责调度流转与接口暴露。
4.  **客户端 (前端 Web UI & AI Agent)**：作为两个独立的消费者调用后端 API。

```mermaid
graph TD
    subgraph 子系统1: 离线解析器 (C++ CLI)
        A[C++ 源码 + compile_commands.json] -->|libclang 解析| B(解析器核心)
        B -->|序列化| C[(graph_data.bin / FlatBuffers)]
        B -->|局部更新| C2[(delta_a.bin)]
    end

    subgraph 子系统2: 内存检索引擎 (C++ & Pybind11)
        C -.->|冷/热启动加载| D[C++ 内存图谱引擎 GraphEngine]
        C2 -.->|增量合并| D
        D <-->|Pybind11 零拷贝| E[检索引擎接口]
    end

    subgraph 子系统3: 业务后端 (Python FastAPI)
        E --> F[FastAPI Web 服务]
        G[Watchdog 文件监控] -->|触发更新| F
        F -->|调用CLI工具| B
    end

    subgraph 子系统4: 消费者侧 (解耦)
        F <-->|REST API / WS| H[前端可视化 UI]
        F <-->|Tools / Function Calling| I[AI Agent 服务]
    end
```

---

## 3. 功能需求详细说明 (Functional Requirements)

### 3.1 子系统1：离线解析器模块 (C++ CLI)
本模块是一个独立的命令行工具（如 `codegraph-parser`）。
*   **F-1.1 基于编译数据库解析**：必须读取 `compile_commands.json` 获取精确的 include 路径和宏定义，确保 C++ 解析不产生大量错误。
*   **F-1.2 实体提取 (Nodes)**：基于 Clang AST，提取以下级别的节点：文件 (File)、类/结构体 (Class/Struct)、函数/方法 (Function/Method)、成员/全局变量 (Variable)。
*   **F-1.3 关系提取 (Edges)**：提取实体间的边关系：包含 (`Includes`)、继承 (`Inherits`)、调用 (`Calls`)、读取 (`Reads`)、写入 (`Writes`)。
*   **F-1.4 序列化输出**：解析完成后，将内存数据严格按照 FlatBuffers 契约，输出为二进制文件 (`.bin`)。
*   **F-1.5 增量解析模式**：支持通过参数传递单个修改过的文件（如 `codegraph-parser --update a.cpp --out delta.bin`），仅输出该文件的节点变化数据。

### 3.2 子系统2：内存图谱引擎 (C++ 图引擎)
本模块作为核心动态库，由 Python 进程加载运行。
*   **F-2.1 高速加载**：支持从 FlatBuffers 二进制文件中瞬间反序列化（或 mmap 映射）恢复图谱，构建基于数组的高效邻接表结构。
*   **F-2.2 高性能检索**：
    *   **节点检索**：基于节点名称（如函数名）进行精确/模糊匹配，返回全局唯一 Node ID。
    *   **邻居遍历 (Get Relations)**：输入中心 Node ID、深度 (Depth) 和方向 (In/Out)，毫秒级返回调用链路（子图）。
*   **F-2.3 动态更新 (Apply Delta)**：接收离线解析器生成的 `delta.bin`，在内存中采用“软删除 (Tombstone)”机制安全替换旧节点，保证图谱 ID 体系不崩溃。
*   **F-2.4 并发安全**：通过 `std::shared_mutex` 保障一写（增量更新）多读（并发查询）的线程安全。

### 3.3 子系统3：业务后端 (Python FastAPI)
*   **F-3.1 API 服务层**：封装 C++ 引擎暴露的 Pybind11 接口，提供标准的 RESTful API 供前端和 AI 调用。
    *   `GET /api/search?keyword=xxx`
    *   `GET /api/graph/relations?node_id=xxx&depth=2&direction=both`
*   **F-3.2 源码变更监听**：集成 `watchdog` 监听目标源码目录，当文件被保存时：
    1. 触发 CLI 解析器生成 `delta.bin`。
    2. 调用 C++ 引擎 `apply_delta()`。
    3. 通过 WebSocket 广播 `GraphUpdated` 事件。

### 3.4 子系统4A：前端可视化 (Web UI)
*   **F-4.1 大图局部渲染**：基于 G6 等高性能图库。避免一次性渲染全图。采用懒加载机制：默认展示搜索命中的核心节点，用户双击节点自动请求 `/api/graph/relations` 展开相邻节点。
*   **F-4.2 检索交互**：顶部提供全局搜索框，支持自动补全，选中后主画布居中对焦到该节点。
*   **F-4.3 属性面板**：点击节点或边，侧边栏展示该实体的详细属性（文件路径、代码行号）。

### 3.5 子系统4B：AI Agent 接口
AI 工具链与前端无 UI 耦合，通过纯 API 交互。
*   **F-5.1 工具注册 (Tools)**：为 LangChain/LlamaIndex 提供标准化 Tool 声明：
    *   `find_functions_by_name(name)`
    *   `get_call_chain(func_name, depth)`
    *   `get_variables_modified_by(func_name)`
*   **F-5.2 增强上下文组装**：后台拦截 AI 的图谱请求，将图结构转化为格式化的文本（如 Markdown 列表或 JSON 树），注入 AI 的 Prompt Context 中。

---

## 4. 非功能需求 (Non-Functional Requirements)

*   **性能要求**：
    *   **冷启动**：对于 10 万行级别的 C++ 项目，全量解析构建图谱耗时应 < 3 分钟。
    *   **热启动**：从 `.bin` 文件加载 100 万规模的节点/边进入内存，耗时 < 1 秒。
    *   **查询延迟**：深度为 3 的图谱遍历 API 响应时间 < 20 毫秒。
*   **内存约束**：C++ 图引擎处理 100 万个节点和边，进程常驻内存 (RSS) 需控制在 500MB 以内。
*   **平台支持**：解析器与图引擎必须能基于 CMake 在 Linux 和 macOS 环境下编译运行。

---

## 5. 数据模型与契约 (Data Schema)

前后端、解析器与引擎之间的唯一数据契约采用 **FlatBuffers** 定义。

文件: `graph.fbs`
```flatbuffers
namespace CodeGraph;

// 1. 实体类型定义
enum NodeType : byte {
    Unknown = 0,
    File = 1,
    Class = 2,
    Struct = 3,
    Function = 4,
    Method = 5,
    Variable = 6
}

// 2. 关系类型定义
enum EdgeType : byte {
    Unknown = 0,
    Includes = 1,
    Inherits = 2,
    Calls = 3,
    Reads = 4,
    Writes = 5
}

// 3. 节点表 (动态长度，适合存储字符串)
table Node {
    id: int32;              // 全局唯一ID
    type: NodeType;         // 实体类型
    name: string;           // 节点名称/签名
    file_path: string;      // 归属文件相对路径
    start_line: int32;      // 源码起始行号
}

// 4. 边结构体 (固定长度内存布局，极致优化存储)
struct Edge {
    source_id: int32;       // 发起方 Node ID
    target_id: int32;       // 接收方 Node ID
    type: EdgeType;         // 边类型
}

// 5. 传输载荷根结构
table GraphPayload {
    version: int32;         // 数据版本号，用于升级兼容
    nodes: [Node];          // 节点数组
    edges: [Edge];          // 关系数组
}

root_type GraphPayload;
```

---

## 6. 开发阶段规划 (Milestones)

### Phase 1: MVP 最小可行性产品 (当前规划)
*   **目标**：跑通端到端的数据流转，验证架构可行性。
*   **范围**：
    1. 编写 FlatBuffers schema 并生成对应语言代码。
    2. 编写 C++ `GraphEngine`，实现基于文件的热启动加载、内存邻接表构建、单节点上下游深度优先检索。完成 Pybind11 绑定。
    3. 编写 FastAPI 简单服务，包装查询 API。
    4. 编写轻量前端页面，利用 G6 实现节点搜索与点击展开。
    5. *(Mock)* 第一版暂不写真实 Clang 解析器，使用 Python 脚本生成假数据 (Dummy FlatBuffers) 进行全链路测试。

### Phase 2: 真实代码解析与动态更新
*   **目标**：接入真实 C++ 业务项目。
*   **范围**：
    1. 编写 `codegraph-parser` (C++ CLI)，基于 `libclang` 读取 `compile_commands.json`，遍历 AST 产出真实的 FlatBuffers 文件。
    2. 实现增量解析机制与 `apply_delta` 内存软删除更新。
    3. 集成 `watchdog` 实现保存文件即刷新图谱。

### Phase 3: AI 定位实战接入
*   **目标**：验证 AI 借助图谱解决实际 Bug 的能力。
*   **范围**：
    1. 将 FastAPI 提供的查询接口封装为 LangChain Tools。
    2. 设计 AI Prompt 策略，测试 "Crash in module X" 类的缺陷排查能力。
    3. 根据 AI 实战反馈，反向优化图谱的节点提取逻辑（如增加关键常量的解析等）。
为保证项目快速落地（MVP），第一期系统聚焦于**函数级/轻量级粗粒度图谱**（暂不包含函数体内部的控制流/数据流）。图谱重点解决“谁调用了谁”、“谁继承了谁”、“谁修改了哪个全局变量”的问题。

---

## 2. 系统架构 (System Architecture)

系统采用**高度解耦**的架构设计，分为四大独立运行的子系统：
1.  **离线解析器 (C++ CLI)**：负责纯粹的 AST 提取。
2.  **核心图检索引擎 (C++ Library + Pybind11)**：负责内存驻留与极速图遍历。
3.  **API/BFF 后端 (Python FastAPI)**：负责调度流转与接口暴露。
4.  **客户端 (前端 Web UI & AI Agent)**：作为两个独立的消费者调用后端 API。

```mermaid
graph TD
    subgraph 子系统1: 离线解析器 (C++ CLI)
        A[C++ 源码 + compile_commands.json] -->|libclang 解析| B(解析器核心)
        B -->|序列化| C[(graph_data.bin / FlatBuffers)]
        B -->|局部更新| C2[(delta_a.bin)]
    end

    subgraph 子系统2: 内存检索引擎 (C++ & Pybind11)
        C -.->|冷/热启动加载| D[C++ 内存图谱引擎 GraphEngine]
        C2 -.->|增量合并| D
        D <-->|Pybind11 零拷贝| E[检索引擎接口]
    end

    subgraph 子系统3: 业务后端 (Python FastAPI)
        E --> F[FastAPI Web 服务]
        G[Watchdog 文件监控] -->|触发更新| F
        F -->|调用CLI工具| B
    end

    subgraph 子系统4: 消费者侧 (解耦)
        F <-->|REST API / WS| H[前端可视化 UI]
        F <-->|Tools / Function Calling| I[AI Agent 服务]
    end
```

---

## 3. 功能需求详细说明 (Functional Requirements)

### 3.1 子系统1：离线解析器模块 (C++ CLI)
本模块是一个独立的命令行工具（如 `codegraph-parser`）。
*   **F-1.1 基于编译数据库解析**：必须读取 `compile_commands.json` 获取精确的 include 路径和宏定义，确保 C++ 解析不产生大量错误。
*   **F-1.2 实体提取 (Nodes)**：基于 Clang AST，提取以下级别的节点：文件 (File)、类/结构体 (Class/Struct)、函数/方法 (Function/Method)、成员/全局变量 (Variable)。
*   **F-1.3 关系提取 (Edges)**：提取实体间的边关系：包含 (`Includes`)、继承 (`Inherits`)、调用 (`Calls`)、读取 (`Reads`)、写入 (`Writes`)。
*   **F-1.4 序列化输出**：解析完成后，将内存数据严格按照 FlatBuffers 契约，输出为二进制文件 (`.bin`)。
*   **F-1.5 增量解析模式**：支持通过参数传递单个修改过的文件（如 `codegraph-parser --update a.cpp --out delta.bin`），仅输出该文件的节点变化数据。

### 3.2 子系统2：内存图谱引擎 (C++ 图引擎)
本模块作为核心动态库，由 Python 进程加载运行。
*   **F-2.1 高速加载**：支持从 FlatBuffers 二进制文件中瞬间反序列化（或 mmap 映射）恢复图谱，构建基于数组的高效邻接表结构。
*   **F-2.2 高性能检索**：
    *   **节点检索**：基于节点名称（如函数名）进行精确/模糊匹配，返回全局唯一 Node ID。
    *   **邻居遍历 (Get Relations)**：输入中心 Node ID、深度 (Depth) 和方向 (In/Out)，毫秒级返回调用链路（子图）。
*   **F-2.3 动态更新 (Apply Delta)**：接收离线解析器生成的 `delta.bin`，在内存中采用“软删除 (Tombstone)”机制安全替换旧节点，保证图谱 ID 体系不崩溃。
*   **F-2.4 并发安全**：通过 `std::shared_mutex` 保障一写（增量更新）多读（并发查询）的线程安全。

### 3.3 子系统3：业务后端 (Python FastAPI)
*   **F-3.1 API 服务层**：封装 C++ 引擎暴露的 Pybind11 接口，提供标准的 RESTful API 供前端和 AI 调用。
    *   `GET /api/search?keyword=xxx`
    *   `GET /api/graph/relations?node_id=xxx&depth=2&direction=both`
*   **F-3.2 源码变更监听**：集成 `watchdog` 监听目标源码目录，当文件被保存时：
    1. 触发 CLI 解析器生成 `delta.bin`。
    2. 调用 C++ 引擎 `apply_delta()`。
    3. 通过 WebSocket 广播 `GraphUpdated` 事件。

### 3.4 子系统4A：前端可视化 (Web UI)
*   **F-4.1 大图局部渲染**：基于 G6 等高性能图库。避免一次性渲染全图。采用懒加载机制：默认展示搜索命中的核心节点，用户双击节点自动请求 `/api/graph/relations` 展开相邻节点。
*   **F-4.2 检索交互**：顶部提供全局搜索框，支持自动补全，选中后主画布居中对焦到该节点。
*   **F-4.3 属性面板**：点击节点或边，侧边栏展示该实体的详细属性（文件路径、代码行号）。

### 3.5 子系统4B：AI Agent 接口
AI 工具链与前端无 UI 耦合，通过纯 API 交互。
*   **F-5.1 工具注册 (Tools)**：为 LangChain/LlamaIndex 提供标准化 Tool 声明：
    *   `find_functions_by_name(name)`
    *   `get_call_chain(func_name, depth)`
    *   `get_variables_modified_by(func_name)`
*   **F-5.2 增强上下文组装**：后台拦截 AI 的图谱请求，将图结构转化为格式化的文本（如 Markdown 列表或 JSON 树），注入 AI 的 Prompt Context 中。

---

## 4. 非功能需求 (Non-Functional Requirements)

*   **性能要求**：
    *   **冷启动**：对于 10 万行级别的 C++ 项目，全量解析构建图谱耗时应 < 3 分钟。
    *   **热启动**：从 `.bin` 文件加载 100 万规模的节点/边进入内存，耗时 < 1 秒。
    *   **查询延迟**：深度为 3 的图谱遍历 API 响应时间 < 20 毫秒。
*   **内存约束**：C++ 图引擎处理 100 万个节点和边，进程常驻内存 (RSS) 需控制在 500MB 以内。
*   **平台支持**：解析器与图引擎必须能基于 CMake 在 Linux 和 macOS 环境下编译运行。

---

## 5. 数据模型与契约 (Data Schema)

前后端、解析器与引擎之间的唯一数据契约采用 **FlatBuffers** 定义。

文件: `graph.fbs`
```flatbuffers
namespace CodeGraph;

// 1. 实体类型定义
enum NodeType : byte {
    Unknown = 0,
    File = 1,
    Class = 2,
    Struct = 3,
    Function = 4,
    Method = 5,
    Variable = 6
}

// 2. 关系类型定义
enum EdgeType : byte {
    Unknown = 0,
    Includes = 1,
    Inherits = 2,
    Calls = 3,
    Reads = 4,
    Writes = 5
}

// 3. 节点表 (动态长度，适合存储字符串)
table Node {
    id: int32;              // 全局唯一ID
    type: NodeType;         // 实体类型
    name: string;           // 节点名称/签名
    file_path: string;      // 归属文件相对路径
    start_line: int32;      // 源码起始行号
}

// 4. 边结构体 (固定长度内存布局，极致优化存储)
struct Edge {
    source_id: int32;       // 发起方 Node ID
    target_id: int32;       // 接收方 Node ID
    type: EdgeType;         // 边类型
}

// 5. 传输载荷根结构
table GraphPayload {
    version: int32;         // 数据版本号，用于升级兼容
    nodes: [Node];          // 节点数组
    edges: [Edge];          // 关系数组
}

root_type GraphPayload;
```

---

## 6. 开发阶段规划 (Milestones)

### Phase 1: MVP 最小可行性产品 (当前规划)
*   **目标**：跑通端到端的数据流转，验证架构可行性。
*   **范围**：
    1. 编写 FlatBuffers schema 并生成对应语言代码。
    2. 编写 C++ `GraphEngine`，实现基于文件的热启动加载、内存邻接表构建、单节点上下游深度优先检索。完成 Pybind11 绑定。
    3. 编写 FastAPI 简单服务，包装查询 API。
    4. 编写轻量前端页面，利用 G6 实现节点搜索与点击展开。
    5. *(Mock)* 第一版暂不写真实 Clang 解析器，使用 Python 脚本生成假数据 (Dummy FlatBuffers) 进行全链路测试。

### Phase 2: 真实代码解析与动态更新
*   **目标**：接入真实 C++ 业务项目。
*   **范围**：
    1. 编写 `codegraph-parser` (C++ CLI)，基于 `libclang` 读取 `compile_commands.json`，遍历 AST 产出真实的 FlatBuffers 文件。
    2. 实现增量解析机制与 `apply_delta` 内存软删除更新。
    3. 集成 `watchdog` 实现保存文件即刷新图谱。

### Phase 3: AI 定位实战接入
*   **目标**：验证 AI 借助图谱解决实际 Bug 的能力。
*   **范围**：
    1. 将 FastAPI 提供的查询接口封装为 LangChain Tools。
    2. 设计 AI Prompt 策略，测试 "Crash in module X" 类的缺陷排查能力。
    3. 根据 AI 实战反馈，反向优化图谱的节点提取逻辑（如增加关键常量的解析等）。