<template>
  <div class="topo-container">
    <div class="controls">
      <el-button-group>
        <el-button @click="fitView" size="small">自适应</el-button>
        <el-button @click="refreshTopo" :loading="refreshing" type="primary" size="small">刷新拓扑</el-button>
      </el-button-group>
      <div class="legend">
        <div class="legend-item" :class="{ disabled: !visibleTypes.cpu }" @click="toggleType('cpu')"><span class="dot cpu"></span>CPU/Switch</div>
        <div class="legend-item" :class="{ disabled: !visibleTypes.gpu }" @click="toggleType('gpu')"><span class="dot gpu"></span>GPU/NPU</div>
        <div class="legend-item" :class="{ disabled: !visibleTypes.net }" @click="toggleType('net')"><span class="dot net"></span>Network</div>
        <div class="legend-item" :class="{ disabled: !visibleTypes.storage }" @click="toggleType('storage')"><span class="dot storage"></span>Storage</div>
      </div>
    </div>
    <div ref="cyContainer" id="cy" v-show="!isEmpty"></div>
    <div v-if="isEmpty && !loading && !error" class="empty-state">
      <el-empty description="暂无 PCIe 拓扑数据" />
    </div>
    <div v-if="loading" class="loading-overlay">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
    <div v-if="error" class="error-overlay">
      <el-alert :title="error" type="error" :closable="false" show-icon />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import axios from 'axios';
import { ElMessage } from 'element-plus';

const props = defineProps({
  machineId: {
    type: Number,
    required: true
  }
});

const cyContainer = ref(null);
const loading = ref(false);
const refreshing = ref(false);
const error = ref(null);
const isEmpty = ref(false);
let cy = null;
let currentTopoJsonStr = "";
let pollingTimer = null;

const visibleTypes = ref({
  cpu: true,
  gpu: true,
  net: true,
  storage: true
});

const toggleType = (type) => {
  visibleTypes.value[type] = !visibleTypes.value[type];
  if (!cy) return;
  
  cy.batch(() => {
    cy.nodes().forEach(node => {
      if (node.data('nodeType') === type) {
        if (visibleTypes.value[type]) {
          node.style('display', 'element');
        } else {
          node.style('display', 'none');
        }
      }
    });
  });
};

if (!cytoscape.prototype.dagre) {
  cytoscape.use(dagre);
}

const initCytoscape = async (graphData) => {
  if (!cyContainer.value) return;

  if (!graphData.nodes || graphData.nodes.length === 0) {
    isEmpty.value = true;
    if (cy) {
      cy.destroy();
      cy = null;
    }
    return;
  }
  isEmpty.value = false;
  await nextTick(); // Wait for v-show to take effect so container has dimensions

  const elements = [];

  // Groups
  (graphData.groups || []).forEach(g => {
    elements.push({
      group: 'nodes',
      data: { 
        id: g.id, 
        label: g.label,
        // Move style data to data field to be used by mapper
        bgColor: g.style?.fillcolor || '#f0f0f0'
      },
      classes: 'group'
    });
  });

  // Nodes
  (graphData.nodes || []).forEach(n => {
    const group = (graphData.groups || []).find(g => g.nodes && g.nodes.includes(n.id));
    const shapeMap = { 'hexagon': 'hexagon', 'diamond': 'diamond', 'component': 'barrel', 'point': 'ellipse' };
    
    const bgColor = n.style?.fillcolor || '#fff';
    let nodeType = 'other';
    const colorUpper = bgColor.toUpperCase();
    if (colorUpper === '#FFD700') nodeType = 'cpu';
    else if (colorUpper === '#98FB98') nodeType = 'gpu';
    else if (colorUpper === '#ADD8E6') nodeType = 'net';
    else if (colorUpper === '#FFA07A') nodeType = 'storage';
    
    elements.push({
      group: 'nodes',
      data: { 
        id: n.id, 
        label: n.label.replace(/\\n/g, '\n'), 
        parent: group ? group.id : null,
        // Move style data to data field
        bgColor: bgColor,
        shape: shapeMap[n.style?.shape] || 'round-rectangle',
        borderWidth: n.style?.penwidth || 1,
        nodeType: nodeType
      },
      classes: 'node'
    });
  });

  // Edges
  const edgeIdCounter = {};
  (graphData.links || []).forEach(l => {
    // 过滤HCCS连接线（黄色的线），保持和TOPO模块默认渲染特性相同
    if (l.type === 'hccs') return;

    // Ensure unique edge IDs when multiple edges connect same source-target
    const baseId = `${l.source}-${l.target}`;
    edgeIdCounter[baseId] = (edgeIdCounter[baseId] || 0) + 1;
    const edgeId = edgeIdCounter[baseId] > 1 ? `${baseId}_${edgeIdCounter[baseId]}` : baseId;
    elements.push({
      group: 'edges',
      data: { 
        id: edgeId, 
        source: l.source, 
        target: l.target,
        label: l.label ? l.label.replace(/\\n/g, '\n') : '',
        // Move style data to data field
        lineColor: l.style?.color || '#999',
        width: (l.style?.penwidth || 1) * 3, // Triple the width for better visibility
        lineStyle: l.style?.style === 'dashed' ? 'dashed' : 'solid',
        targetArrowShape: ['pcie', 'cpu_link'].includes(l.type) ? 'triangle' : 'none',
        targetArrowColor: l.style?.color || '#999'
      }
    });
  });

  if (cy) {
    cy.destroy();
  }

  // Assign to outer variable
  cy = cytoscape({
    container: cyContainer.value,
    elements: elements,
    wheelSensitivity: 0.5, // Increase scroll zoom sensitivity (default is usually low)
    pixelRatio: window.devicePixelRatio ? Math.max(window.devicePixelRatio, 2) : 2, // 强制高DPI渲染，解决模糊问题
    style: [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'text-valign': 'center',
          'text-halign': 'center',
          'background-color': 'data(bgColor)',
          // Remove default border
          'border-width': 0,
          'shape': 'data(shape)',
          'font-size': '16px', // Increased font size for clarity
          'font-weight': 'bold',
          'text-wrap': 'wrap',
          // Auto-size based on label
          'width': 'label',
          'height': 'label',
          'padding': '20px', // Increased padding
          // Ensure label is visible on top of node
          'color': '#222', // Darker text for better contrast
          'text-max-width': '280px'
        }
      },
      {
        selector: 'node.group',
        style: {
          'label': 'data(label)',
          'text-valign': 'top',
          'text-halign': 'center',
          'background-opacity': 0.05,
          'border-width': 2, // Thicker border
          'border-style': 'dashed',
          'border-color': '#ccc',
          'background-color': 'data(bgColor)',
          // Group nodes also need to size to content but usually layout handles this
          'text-margin-y': -10,
          'font-weight': 'bold',
          'color': '#eee', // Lighter text for dark background
          'font-size': '18px'
        }
      },
      {
        selector: 'edge',
        style: {
          'label': 'data(label)',
          'width': 'data(width)',
          'line-color': 'data(lineColor)',
          'target-arrow-color': 'data(targetArrowColor)',
          'target-arrow-shape': 'data(targetArrowShape)',
          'arrow-scale': 1.5, // 放大箭头
          'line-style': 'data(lineStyle)',
          'curve-style': 'bezier',
          'font-size': '14px', // Larger edge labels
          'font-weight': 'bold',
          // Horizontal label without background
          'text-rotation': 'none',
          'color': '#fff', // Light text for dark background
          'text-margin-y': -10,
          // Enable text wrapping for multiline labels
          'text-wrap': 'wrap',
          // Add dark outline (halo) to make text readable over lines/nodes in dark mode
          'text-outline-color': '#222', // Deeper outline
          'text-outline-width': 4, // Thicker outline
          'text-outline-opacity': 1
        }
      }
    ],
    layout: {
      name: 'dagre',
      nodeSep: 50,
      rankSep: 120,
      rankDir: 'TB'
    }
  });

  // Apply initial visibility
  cy.batch(() => {
    cy.nodes().forEach(node => {
      const type = node.data('nodeType');
      if (type && type !== 'other' && !visibleTypes.value[type]) {
        node.style('display', 'none');
      }
    });
  });
};

const fetchTopo = async (isBackground = false) => {
  if (!isBackground) {
    loading.value = true;
    error.value = null;
  }
  try {
    const res = await axios.get(`/machines/${props.machineId}/topo`);
    if (res.data.error) {
      if (!isBackground) error.value = res.data.error;
    } else {
      const newJsonStr = JSON.stringify(res.data);
      if (newJsonStr !== currentTopoJsonStr) {
        currentTopoJsonStr = newJsonStr;
        isEmpty.value = false;
        initCytoscape(res.data);
      }
    }
  } catch (err) {
    if (!isBackground) error.value = "无法加载拓扑数据: " + (err.response?.data?.detail || err.message);
  } finally {
    if (!isBackground) loading.value = false;
  }
};

const startPolling = () => {
  if (pollingTimer) clearInterval(pollingTimer);
  pollingTimer = setInterval(() => {
    fetchTopo(true);
  }, 5000); // 5 seconds interval
};

const refreshTopo = async () => {
  refreshing.value = true;
  try {
    await axios.post(`/machines/${props.machineId}/topo/refresh`);
    ElMessage.success("刷新请求已发送，拓扑图将在数据准备好后自动更新");
    // Start polling or just wait (polling is already running)
    setTimeout(() => fetchTopo(true), 2000); 
  } catch (err) {
    ElMessage.error("刷新失败: " + (err.response?.data?.detail || err.message));
  } finally {
    refreshing.value = false;
  }
};

const fitView = () => {
  if (cy) cy.fit(null, 50);
};

onMounted(() => {
  fetchTopo();
  startPolling();
});

watch(() => props.machineId, () => {
  currentTopoJsonStr = ""; // reset for new machine
  fetchTopo();
  startPolling();
});

onUnmounted(() => {
  if (pollingTimer) clearInterval(pollingTimer);
  if (cy) cy.destroy();
});
</script>

<style scoped>
.topo-container {
  width: 100%;
  height: 100%;
  min-height: 600px;
  position: relative;
  /* Border removed for cleaner UI */
  background: transparent;
  overflow: hidden;
}

#cy {
  width: 100%;
  height: 100%;
}

.controls {
  position: absolute;
  top: 24px;
  left: 24px;
  right: auto;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
  pointer-events: none; /* Let clicks pass through empty areas */
}

.controls > * {
  pointer-events: auto; /* Re-enable clicks for children */
}

.legend {
  background: rgba(30, 30, 30, 0.85);
  backdrop-filter: blur(12px);
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  font-size: 13px;
  color: #e0e0e0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  min-width: 140px;
}

.legend-item {
  display: flex;
  align-items: center;
  margin: 6px 0;
  font-weight: 500;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.2s;
}

.legend-item:hover {
  transform: translateX(2px);
}

.legend-item.disabled {
  opacity: 0.4;
  text-decoration: line-through;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 10px;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
}

.dot.cpu { background: #FFD700; }
.dot.gpu { background: #98FB98; }
.dot.net { background: #ADD8E6; }
.dot.storage { background: #FFA07A; }

.loading-overlay, .error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  z-index: 20;
}

.error-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
  width: 80%;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 5;
}
</style>
