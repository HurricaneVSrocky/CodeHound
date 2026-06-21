import { Graph } from '@antv/g6';

const API_BASE = 'http://localhost:8000/api';

// Vibrant Tech Colors for Dark Mode
const nodeTypeColors: Record<number, string> = {
  1: '#8B5CF6', // File (Violet)
  2: '#F59E0B', // Class (Amber)
  3: '#EC4899', // Struct (Pink)
  4: '#3B82F6', // Function (Blue)
  5: '#06B6D4', // Method (Cyan)
  6: '#10B981'  // Variable (Emerald)
};

const nodeTypeLabels: Record<number, string> = {
  1: 'File',
  2: 'Class',
  3: 'Struct',
  4: 'Function',
  5: 'Method',
  6: 'Variable'
};

const edgeTypeLabels: Record<number, string> = {
  1: 'Includes',
  2: 'Inherits',
  3: 'Calls',
  4: 'Reads',
  5: 'Writes'
};

let graph: any = null;

async function initGraph() {
  const container = document.getElementById('mountNode');
  if (!container) return;

  const width = container.scrollWidth || window.innerWidth;
  const height = container.scrollHeight || window.innerHeight;

  graph = new Graph({
    container: 'mountNode',
    width,
    height,
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    layout: {
      type: 'force',
      linkDistance: 250,
      nodeStrength: 2000,
      edgeStrength: 0.2,
      preventOverlap: true,
      nodeSize: 60,
      collideStrength: 0.8
    }
  });

  graph.on('node:click', (e: any) => {
    const nodeId = e.target.id;
    const nodeData = graph.getNodeData(nodeId);
    updatePropertiesPanel(nodeId, nodeData);
  });

  graph.on('node:dblclick', async (e: any) => {
    const nodeId = e.target.id;
    await fetchAndExpandNode(parseInt(nodeId));
  });
}

function updatePropertiesPanel(id: string, nodeData: any) {
  const panelWrapper = document.getElementById('propertiesPanel');
  const panelContent = document.getElementById('nodeInfo');
  
  if (!panelWrapper || !panelContent) return;
  
  // Show the panel
  panelWrapper.classList.remove('hidden');

  const n = nodeData.data || {};
  const color = nodeTypeColors[n.type] || '#1890FF';
  
  panelContent.innerHTML = `
    <div class="prop-item">
      <span class="prop-label">Type</span>
      <span class="type-badge" style="background-color: ${color}; color: #000;">
        ${nodeTypeLabels[n.type] || n.type}
      </span>
    </div>
    <div class="prop-item">
      <span class="prop-label">Name</span>
      <div class="prop-value code-font">${nodeData.style?.labelText || ''}</div>
    </div>
    <div class="prop-item">
      <span class="prop-label">File Path</span>
      <div class="prop-value code-font">${n.file_path || 'N/A'}</div>
    </div>
    <div class="prop-item">
      <span class="prop-label">Line Number</span>
      <div class="prop-value">${n.start_line || 'N/A'}</div>
    </div>
    <div class="prop-item">
      <span class="prop-label">Node ID</span>
      <div class="prop-value">${id}</div>
    </div>
  `;
}

async function fetchAndExpandNode(nodeId: number) {
  try {
    const res = await fetch(`${API_BASE}/graph/relations?node_id=${nodeId}&depth=1&direction=0`);
    const data = await res.json();
    await mergeDataToGraph(data.nodes, data.edges);
  } catch (err) {
    console.error('Failed to fetch relations:', err);
  }
}

async function searchAndRender() {
  const input = document.getElementById('searchInput') as HTMLInputElement;
  const keyword = input.value.trim();
  
  // Hide panel on new search
  const panelWrapper = document.getElementById('propertiesPanel');
  if (panelWrapper) panelWrapper.classList.add('hidden');

  try {
    const res = await fetch(`${API_BASE}/search?keyword=${encodeURIComponent(keyword)}&limit=10`);
    const data = await res.json();
    
    if (data && data.length > 0) {
      const targetNode = data.find((n: any) => n.name === keyword) || data[0];
      await fetchAndExpandNode(targetNode.id);
    } else {
      // In a real app we'd use a nice toast, but alert for MVP
      alert('Node not found!');
    }
  } catch (err) {
    console.error('Search failed:', err);
  }
}

async function mergeDataToGraph(nodes: any[], edges: any[]) {
  if (!graph) return;

  const currentData = graph.getData();
  const existingNodeIds = new Set((currentData.nodes || []).map((n: any) => n.id));
  const existingEdgeIds = new Set((currentData.edges || []).map((e: any) => `${e.source}-${e.target}-${e.style?.labelText}`));

  const newNodesToRender = nodes.filter(n => !existingNodeIds.has(String(n.id)));
  const newNodes = newNodesToRender.map((n, i) => {
    const angle = (i / newNodesToRender.length) * 2 * Math.PI;
    const radius = 250 + Math.random() * 50;
    const color = nodeTypeColors[n.type] || '#3B82F6';
    
    return {
      id: String(n.id),
      x: 400 + radius * Math.cos(angle),
      y: 300 + radius * Math.sin(angle),
      style: {
        labelText: n.name,
        fill: color,
        stroke: '#F8FAFC',
        lineWidth: 2,
        size: 50,
        // High contrast glowing shadows for dark mode
        shadowColor: color,
        shadowBlur: 15,
        shadowOffsetY: 0,
        // Label styling for dark mode
        labelFill: '#F8FAFC',
        labelFontSize: 12,
        labelFontFamily: "'JetBrains Mono', monospace",
        labelFontWeight: '600',
        labelBackgroundFill: 'rgba(15, 23, 42, 0.7)',
        labelBackgroundRadius: 4,
        labelBackgroundPadding: [4, 8, 4, 8],
        labelBackgroundBorder: `1px solid ${color}`
      },
      data: n
    };
  });

  const newEdges = edges
    .map(e => ({
      source: String(e.source_id),
      target: String(e.target_id),
      style: {
        labelText: edgeTypeLabels[e.type] || 'Unknown',
        labelFontSize: 10,
        labelFontFamily: "'JetBrains Mono', monospace",
        labelFill: '#F8FAFC',
        labelBackgroundFill: 'rgba(15, 23, 42, 0.8)',
        labelBackgroundRadius: 4,
        labelBackgroundPadding: [2, 6, 2, 6],
        endArrow: true,
        // Sci-fi tech line color
        stroke: 'rgba(148, 163, 184, 0.3)',
        lineWidth: 2,
        lineAppendWidth: 6
      }
    }))
    .filter(e => !existingEdgeIds.has(`${e.source}-${e.target}-${e.style.labelText}`));

  if (newNodes.length > 0 || newEdges.length > 0) {
    if (currentData.nodes && currentData.nodes.length > 0) {
      graph.addData({ nodes: newNodes, edges: newEdges });
    } else {
      graph.setData({ nodes: newNodes, edges: newEdges });
    }
    await graph.render();
  }
}

function setupWebSocket() {
  const ws = new WebSocket('ws://localhost:8000/api/ws');
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event === 'GraphUpdated') {
        console.log('Graph data updated in backend. Refreshing view...');
        if (graph) {
          graph.clear();
          searchAndRender();
        }
      }
    } catch (e) {
      console.error('WebSocket message parsing failed:', e);
    }
  };
  ws.onclose = () => {
    console.log('WebSocket disconnected, retrying in 5s...');
    setTimeout(setupWebSocket, 5000);
  };
}

async function bootstrap() {
  await initGraph();
  setupWebSocket();

  document.getElementById('searchBtn')?.addEventListener('click', searchAndRender);
  document.getElementById('searchInput')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      searchAndRender();
    }
  });

  const searchInput = document.getElementById('searchInput') as HTMLInputElement;
  if (searchInput) {
    searchInput.value = 'main';
    await searchAndRender();
  }
}

bootstrap();
