<template>
  <div class="topo-container">
    <div class="controls">
      <el-button-group>
        <el-button @click="fitView" size="small">自适应</el-button>
        <el-button @click="refreshTopo" :loading="refreshing" type="primary" size="small">刷新拓扑</el-button>
      </el-button-group>
      <div class="legend">
        <div class="legend-item"><span class="dot cpu"></span>CPU/Switch</div>
        <div class="legend-item"><span class="dot gpu"></span>GPU/NPU</div>
        <div class="legend-item"><span class="dot net"></span>Network</div>
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
    
    elements.push({
      group: 'nodes',
      data: { 
        id: n.id, 
        label: n.label.replace(/\\n/g, '\n'), 
        parent: group ? group.id : null,
        // Move style data to data field
        bgColor: n.style?.fillcolor || '#fff',
        shape: shapeMap[n.style?.shape] || 'round-rectangle',
        borderWidth: n.style?.penwidth || 1
      },
      classes: 'node'
    });
  });

  // Edges
  (graphData.links || []).forEach(l => {
    elements.push({
      group: 'edges',
      data: { 
        id: `${l.source}-${l.target}`, 
        source: l.source, 
        target: l.target,
        label: l.label ? l.label.replace(/\\n/g, '\n') : '',
        // Move style data to data field
        lineColor: l.style?.color || '#999',
        width: l.style?.penwidth || 1,
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
          'font-size': '12px',
          'text-wrap': 'wrap',
          // Auto-size based on label
          'width': 'label',
          'height': 'label',
          'padding': '12px',
          // Ensure label is visible on top of node
          'color': '#333',
          'text-max-width': '200px'
        }
      },
      {
        selector: 'node.group',
        style: {
          'label': 'data(label)',
          'text-valign': 'top',
          'text-halign': 'center',
          'background-opacity': 0.05,
          'border-width': 1,
          'border-style': 'dashed',
          'border-color': '#ccc',
          'background-color': 'data(bgColor)',
          // Group nodes also need to size to content but usually layout handles this
          'text-margin-y': -10,
          'font-weight': 'bold',
          'color': '#666'
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
          'line-style': 'data(lineStyle)',
          'curve-style': 'bezier',
          'font-size': '10px',
          // Horizontal label without background
          'text-rotation': 'none',
          'color': '#555',
          'text-margin-y': -5,
          // Enable text wrapping for multiline labels
          'text-wrap': 'wrap',
          // Add white outline (halo) to make text readable over lines/nodes
          'text-outline-color': '#fff',
          'text-outline-width': 2,
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
};

const fetchTopo = async () => {
  loading.value = true;
  error.value = null;
  isEmpty.value = false;
  try {
    const res = await axios.get(`/machines/${props.machineId}/topo`);
    if (res.data.error) {
      error.value = res.data.error;
    } else {
      initCytoscape(res.data);
    }
  } catch (err) {
    error.value = "无法加载拓扑数据: " + (err.response?.data?.detail || err.message);
  } finally {
    loading.value = false;
  }
};

const refreshTopo = async () => {
  refreshing.value = true;
  try {
    await axios.post(`/machines/${props.machineId}/topo/refresh`);
    ElMessage.success("刷新请求已发送，请稍后刷新页面查看");
    // Start polling or just wait
    setTimeout(fetchTopo, 5000); 
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
});

watch(() => props.machineId, () => {
  fetchTopo();
});

onUnmounted(() => {
  if (cy) cy.destroy();
});
</script>

<style scoped>
.topo-container {
  width: 100%;
  height: 600px;
  position: relative;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: #f8f9fa;
  overflow: hidden;
}

#cy {
  width: 100%;
  height: 100%;
}

.controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.legend {
  background: rgba(255, 255, 255, 0.9);
  padding: 8px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  font-size: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  margin: 4px 0;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  margin-right: 6px;
}

.dot.cpu { background: #FFD700; }
.dot.gpu { background: #98FB98; }
.dot.net { background: #ADD8E6; }

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
