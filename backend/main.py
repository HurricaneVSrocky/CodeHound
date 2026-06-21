import sys
import os
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio

# 尝试导入 C++ 引擎扩展 (构建系统通常会在根目录 build 文件夹下生成 codegraph_engine.pyd)
sys.path.append(os.path.join(os.path.dirname(__file__), '../build'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../build/Release'))

try:
    import codegraph_engine
    engine_available = True
    print("Successfully imported C++ GraphEngine.")
except ImportError:
    engine_available = False
    print("Warning: C++ GraphEngine (codegraph_engine) not found. APIs will return dummy data.")

app = FastAPI(title="CodeHound Graph API")

# 配置跨域，供前端本地调试使用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化引擎
engine = None
if engine_available:
    engine = codegraph_engine.GraphEngine()
    dummy_data_path = os.path.join(os.path.dirname(__file__), '../graph_data.bin')
    if os.path.exists(dummy_data_path):
        success = engine.load_from_file(dummy_data_path)
        if not success:
            print(f"Failed to load graph data from {dummy_data_path}")
    else:
        print(f"Graph data not found at {dummy_data_path}. Please run codegraph-parser first.")

    # 启动 Watchdog 监听 Dummy 项目
    import watcher
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/dummy_project'))
    parser_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../parser/codegraph_parser.py'))
    
    out_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), '../delta.bin'))
    
    async def notify_frontend():
        await broadcast_update()
        
    print(f"Starting watcher on {project_dir}")
    observer = watcher.start_watcher(engine, project_dir, parser_path, out_bin, notify_frontend)

# --- WebSocket Management ---
active_connections: List[WebSocket] = []

async def broadcast_update():
    for connection in active_connections:
        try:
            await connection.send_json({"event": "GraphUpdated"})
        except Exception as e:
            print(f"Failed to send WS message: {e}")

# --- API Models ---

class NodeModel(BaseModel):
    id: int
    type: int
    name: str
    file_path: str
    start_line: int

class EdgeModel(BaseModel):
    source_id: int
    target_id: int
    type: int

class GraphRelationsResponse(BaseModel):
    nodes: List[NodeModel]
    edges: List[EdgeModel]

# --- API Endpoints ---

@app.get("/api/search", response_model=List[NodeModel])
def search_nodes(keyword: str = Query("", description="Keyword to search for node names"), limit: int = 50):
    """
    基于关键字检索图谱节点。
    """
    if not engine_available or engine is None:
        # Fallback dummy data for API testing if C++ engine failed to load
        return [
            NodeModel(id=3, type=4, name="main (mock)", file_path="src/main.cpp", start_line=50)
        ]
    
    results = engine.search_nodes(keyword, limit)
    return [
        NodeModel(id=n.id, type=n.type, name=n.name, file_path=n.file_path, start_line=n.start_line)
        for n in results
    ]

@app.get("/api/graph/relations", response_model=GraphRelationsResponse)
def get_graph_relations(node_id: int, depth: int = 1, direction: int = 0):
    """
    获取指定节点的邻居子图。
    direction: 0=Both, 1=Out(下级), 2=In(上级)
    """
    if not engine_available or engine is None:
        # Fallback dummy data
        return GraphRelationsResponse(
            nodes=[
                NodeModel(id=3, type=4, name="main", file_path="src/main.cpp", start_line=50),
                NodeModel(id=4, type=5, name="App::init", file_path="src/main.cpp", start_line=12)
            ],
            edges=[
                EdgeModel(source_id=3, target_id=4, type=3)
            ]
        )
    
    nodes, edges = engine.get_relations(node_id, depth, direction)
    return GraphRelationsResponse(
        nodes=[NodeModel(id=n.id, type=n.type, name=n.name, file_path=n.file_path, start_line=n.start_line) for n in nodes],
        edges=[EdgeModel(source_id=e.source_id, target_id=e.target_id, type=e.type) for e in edges]
    )

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
