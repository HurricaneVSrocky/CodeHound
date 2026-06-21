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
  (window as any).graph = graph;

  graph.on('node:click', (e: any) => {
    const nodeId = e.target.id;
    const nodeData = graph.getNodeData(nodeId);
    updatePropertiesPanel(nodeId, nodeData);
  });

  graph.on('node:dblclick', async (e: any) => {
    const nodeId = e.target.id || (e.item && e.item.getModel().id);
    let x = 400, y = 300;
    if (e.item) {
      const model = e.item.getModel();
      if (model.x !== undefined) x = model.x;
      if (model.y !== undefined) y = model.y;
    }
    await fetchAndExpandNode(parseInt(nodeId), x, y);
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
    
    <div class="relations-header">
      <span class="prop-label" style="margin-bottom: 0;">Context & Relations</span>
      <span class="relations-loading" id="relationsLoading">Loading...</span>
    </div>
    <div id="relationsList" class="relations-list"></div>
  `;

  // Fetch relations context for the panel
  fetch(`${API_BASE}/graph/relations?node_id=${id}&depth=1&direction=0`)
    .then(res => res.json())
    .then(data => {
      const loadingEl = document.getElementById('relationsLoading');
      if (loadingEl) loadingEl.style.display = 'none';
      
      const listEl = document.getElementById('relationsList');
      if (!listEl) return;
      
      if (!data.edges || data.edges.length === 0) {
        listEl.innerHTML = '<div class="empty-state" style="margin-top: 10px;">No contextual relations found.</div>';
        return;
      }
      
      let html = '';
      data.edges.forEach((edge: any) => {
        const isIncoming = edge.target_id === parseInt(id);
        const relatedNodeId = isIncoming ? edge.source_id : edge.target_id;
        const relatedNode = data.nodes.find((n: any) => n.id === relatedNodeId);
        if (!relatedNode) return;
        
        const tColor = nodeTypeColors[relatedNode.type] || '#3B82F6';
        const edgeLabel = edgeTypeLabels[edge.type] || 'Unknown';
        
        // Quick navigation to related node
        const onClickHandler = `document.getElementById('searchInput').value='${relatedNode.name}'; document.getElementById('searchBtn').click();`;
        
        html += `
          <div class="relation-item" onclick="${onClickHandler}">
            <div class="relation-meta">
              <span class="relation-edge-badge">${edgeLabel}</span>
              <span class="relation-dir">${isIncoming ? '← from' : '→ to'}</span>
              <span class="relation-type-badge" style="background-color: ${tColor};">${nodeTypeLabels[relatedNode.type] || relatedNode.type}</span>
            </div>
            <div class="relation-name" title="${relatedNode.name}">
              ${relatedNode.name}
            </div>
          </div>
        `;
      });
      listEl.innerHTML = html;
    })
    .catch(err => {
      const loadingEl = document.getElementById('relationsLoading');
      if (loadingEl) loadingEl.innerText = 'Failed to load context';
      console.error('Failed to fetch relations context:', err);
    });
}

async function fetchAndExpandNode(nodeId: number, sourceX: number = 400, sourceY: number = 300) {
  try {
    const res = await fetch(`${API_BASE}/graph/relations?node_id=${nodeId}&depth=1&direction=0`);
    const data = await res.json();
    await mergeDataToGraph(data.nodes, data.edges, sourceX, sourceY);
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
    const res = await fetch(`${API_BASE}/search?keyword=${encodeURIComponent(keyword)}&limit=100`);
    const data = await res.json();
    
    if (data && data.length > 0) {
      const targetNode = data.find((n: any) => n.name === keyword) || data[0];
      await fetchAndExpandNode(targetNode.id);
      
      setTimeout(() => {
        if (graph) {
          graph.focusItem(String(targetNode.id), true, {
            easing: 'easeCubic',
            duration: 500,
          });
          graph.setItemState(String(targetNode.id), 'selected', true);
        }
      }, 800);
    } else {
      // In a real app we'd use a nice toast, but alert for MVP
      alert('Node not found!');
    }
  } catch (err) {
    console.error('Search failed:', err);
  }
}

async function fetchTopLevelNodes() {
  try {
    const res = await fetch(`${API_BASE}/graph/top_level`);
    const nodes = await res.json();
    if (nodes && nodes.length > 0) {
      const w = window.innerWidth || 800;
      const h = window.innerHeight || 600;
      await mergeDataToGraph(nodes, [], w / 2, h / 2);
    }
  } catch (err) {
    console.error('Failed to fetch top level nodes:', err);
  }
}

async function fetchAllNodesAndRelations() {
  try {
    const res = await fetch(`${API_BASE}/graph/all`);
    const data = await res.json();
    if (data && data.nodes && data.nodes.length > 0) {
      const w = window.innerWidth || 800;
      const h = window.innerHeight || 600;
      await mergeDataToGraph(data.nodes, data.edges || [], w / 2, h / 2);
    }
  } catch (err) {
    console.error('Failed to fetch all nodes and relations:', err);
  }
}

async function mergeDataToGraph(nodes: any[], edges: any[], sourceX: number = 400, sourceY: number = 300) {
  if (!graph) return;

  const currentData = graph.getData();
  const existingNodeIds = new Set((currentData.nodes || []).map((n: any) => n.id));
  const existingEdgeIds = new Set((currentData.edges || []).map((e: any) => `${e.source}-${e.target}-${e.style?.labelText}`));

  const childNodeIds = new Set(
    edges.map((e: any) => String(e.target_id))
  );

  const newNodesToRender = nodes.filter(n => !existingNodeIds.has(String(n.id)));
  const newNodes = newNodesToRender.map((n, i) => {
    const angle = (i / newNodesToRender.length) * 2 * Math.PI;
    const radius = 250 + Math.random() * 50;
    const color = nodeTypeColors[n.type] || '#3B82F6';
    const isRoot = !childNodeIds.has(String(n.id));
    
    return {
      id: String(n.id),
      type: 'circle',
      x: sourceX + radius * Math.cos(angle),
      y: sourceY + radius * Math.sin(angle),
      style: {
        r: isRoot ? 32 : 25,
        labelText: n.name,
        fill: color,
        stroke: '#F8FAFC',
        lineWidth: isRoot ? 4 : 2,
        size: isRoot ? 64 : 50,
        // High contrast glowing shadows for dark mode
        shadowColor: color,
        shadowBlur: isRoot ? 30 : 15,
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
    searchInput.value = ''; // Clear default search
  }
  
  // Load all nodes and relations by default
  await fetchAllNodesAndRelations();
}

bootstrap();
