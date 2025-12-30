<template>
  <el-container class="main-container">
    <el-header class="header">
      <div class="logo-title">
        <el-icon :size="24" color="#409EFF"><Monitor /></el-icon>
        <span>AI服务器监控系统</span>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openSettings" :icon="Setting"
          >设置</el-button
        >
        <el-button type="success" @click="dialogVisible = true" :icon="Plus"
          >新增机器</el-button
        >
      </div>
    </el-header>

    <el-main>
      <el-card shadow="hover" class="table-card">
        <template #header>
          <div class="card-header">
            <div class="title-group">
              <span class="title">机器列表</span>
              <el-tag type="info" size="small" effect="plain"
                >共 {{ total }} 台</el-tag
              >
            </div>
            <div class="header-right">
              <el-select
                v-model="filterArch"
                placeholder="架构"
                clearable
                class="filter-select"
                @change="handleSearch"
              >
                <el-option label="x86_64" value="x86_64" />
                <el-option label="aarch64" value="aarch64" />
              </el-select>
              <el-select
                v-model="filterStatus"
                placeholder="状态"
                clearable
                class="filter-select"
                @change="handleSearch"
              >
                <el-option label="在线" value="Online" />
                <el-option label="离线" value="Offline" />
                <el-option label="错误" value="Error" />
              </el-select>
              <el-select
                v-model="filterAcc"
                placeholder="卡状态"
                clearable
                class="filter-select"
                @change="handleSearch"
              >
                <el-option label="有加速卡" value="HasAcc" />
                <el-option label="无加速卡" value="NoAcc" />
                <el-option label="有闲置卡" value="Idle" />
                <el-option label="有忙碌卡" value="Busy" />
                <el-option label="有异常卡" value="Warning" />
              </el-select>
              <el-input
                v-model="searchQuery"
                placeholder="搜索 IP/用户/卡型号"
                class="search-input"
                clearable
                @clear="handleSearch"
                @keyup.enter="handleSearch"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-button
                :icon="Refresh"
                circle
                @click="refreshAllMachines"
                :loading="loading"
              ></el-button>

              <!-- 新增 导入/导出 按钮 -->
              <el-button type="primary" plain @click="exportMachines">导出</el-button>
              <el-button type="info" plain @click="importMachines">导入</el-button>
              <el-button type="warning" plain @click="downloadTemplate">下载模板</el-button>
              <input type="file" ref="fileInput" accept=".csv,text/csv" style="display:none" @change="handleFileChange" />
            </div>
          </div>
        </template>

        <el-table
          :data="machines"
          style="width: 100%"
          v-loading="loading"
          border
          stripe
          class="custom-table"
        >
          <el-table-column
            prop="ip"
            label="IP 地址"
            width="140"
            fixed
          ></el-table-column>
          <el-table-column
            prop="username"
            label="用户名"
            width="100"
          ></el-table-column>
          <el-table-column label="密码" width="150">
            <template #default="{ row }">
              <div class="password-cell">
                <span v-if="row.showPassword">{{ row.password }}</span>
                <span v-else>******</span>
                <el-button
                  link
                  :icon="row.showPassword ? View : Hide"
                  @click="row.showPassword = !row.showPassword"
                ></el-button>
                <el-button
                  link
                  :icon="CopyDocument"
                  @click="copyToClipboard(row.password)"
                ></el-button>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="加速卡" min-width="120">
            <template #default="{ row }">
              <el-tag
                v-if="row.accelerator_type && row.accelerator_type !== 'None'"
                size="small"
                effect="dark"
                >{{ row.accelerator_type }}</el-tag
              >
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column label="加速卡详情" min-width="180">
            <template #default="{ row }">
              <div
                v-if="row.accelerator_type && row.accelerator_type !== 'None'"
              >
                <span class="acc-count">总数: {{ row.accelerator_count }}</span>
                <span
                  style="display: inline-block; margin-left: 4px"
                  v-if="row.accelerator_status"
                  @click="showDetails(row)"
                >
                  <el-tooltip placement="top" effect="light">
                    <template #content>
                      <div style="max-width: 300px; line-height: 1.5">
                        <div style="font-weight: bold; margin-bottom: 4px">
                          {{ row.accelerator_type }} ({{
                            row.accelerator_count
                          }})
                        </div>
                        <div
                          v-for="(item, index) in parseAcceleratorStatus(
                            row.accelerator_status
                          ).slice(0, 8)"
                          :key="index"
                          style="font-size: 12px"
                        >
                          {{ item.name }}: 显存 {{ item.memory_used }}/{{
                            item.memory_total
                          }}
                          | 温度 {{ item.temp }}
                        </div>
                        <div
                          v-if="
                            parseAcceleratorStatus(row.accelerator_status)
                              .length > 8
                          "
                          style="color: #909399; font-size: 12px"
                        >
                          ...点击查看更多
                        </div>
                      </div>
                    </template>
                    <el-icon class="info-icon"><InfoFilled /></el-icon>
                  </el-tooltip>
                </span>
              </div>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column label="卡状态" width="220">
            <template #default="{ row }">
              <div v-if="row.accelerator_count > 0" class="card-status-row">
                <el-badge
                  :value="row.idle_count"
                  type="success"
                  class="custom-badge-inline"
                >
                  <el-tag type="success" size="small" effect="plain"
                    >闲置</el-tag
                  >
                </el-badge>
                <el-badge
                  :value="row.busy_count"
                  type="danger"
                  class="custom-badge-inline"
                >
                  <el-tag type="danger" size="small" effect="plain"
                    >忙碌</el-tag
                  >
                </el-badge>
                <el-badge
                  v-if="row.warning_count > 0"
                  :value="row.warning_count"
                  type="warning"
                  class="custom-badge-inline"
                >
                  <el-tag type="warning" size="small" effect="plain"
                    >异常</el-tag
                  >
                </el-badge>
              </div>
              <span v-else>-</span>
            </template>
          </el-table-column>

          <el-table-column
            prop="os_info"
            label="操作系统"
            min-width="150"
            show-overflow-tooltip
          ></el-table-column>
          <el-table-column
            prop="arch"
            label="架构"
            width="100"
          ></el-table-column>

          <!-- 新增备注列（可编辑） -->
          <el-table-column label="备注" width="200">
            <template #default="{ row }">
              <el-input
                v-model="row.remark"
                placeholder="备注"
                size="small"
                @blur="updateRemark(row)"
              />
            </template>
          </el-table-column>

          <el-table-column prop="last_updated" label="最后更新" width="170">
            <template #default="{ row }">{{
              formatDate(row.last_updated)
            }}</template>
          </el-table-column>

          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <el-button
                size="small"
                type="primary"
                plain
                @click="refreshMachine(row)"
                :loading="row.refreshing"
                >刷新</el-button
              >
              <el-button
                size="small"
                type="warning"
                plain
                @click="openEditDialog(row)"
                >编辑</el-button
              >
              <el-button
                size="small"
                type="danger"
                plain
                @click="deleteMachine(row)"
                >删除</el-button
              >
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[5, 10, 15, 30, 50]"
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </el-card>
    </el-main>

    <!-- 新增机器对话框 -->
    <el-dialog
      v-model="detailsDialogVisible"
      :title="`加速卡详情 - ${currentMachineName}`"
      width="800px"
      top="5vh"
    >
      <el-tabs type="border-card">
        <el-tab-pane label="概览">
          <el-table
            :data="currentDetails"
            stripe
            style="width: 100%"
            height="400"
          >
            <el-table-column prop="name" label="卡号/名称" width="180" />
            <el-table-column prop="memory_used" label="显存已用" width="120" />
            <el-table-column prop="memory_total" label="显存总量" width="120" />
            <el-table-column prop="temp" label="温度" width="100" />
            <el-table-column label="状态" min-width="100">
              <template #default="{ row }">
                <el-tag
                  :type="row.health === 'OK' ? 'success' : 'danger'"
                  size="small"
                  >{{ row.health || "Unknown" }}</el-tag
                >
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="实时终端输出 (Raw)">
          <div v-loading="loadingRaw" style="min-height: 200px">
            <pre
              style="
                background: #1e1e1e;
                color: #d4d4d4;
                padding: 12px;
                border-radius: 4px;
                overflow: auto;
                max-height: 500px;
                font-family: Consolas, monospace;
              "
              >{{ currentRawOutput }}</pre
            >
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailsDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>

    <el-dialog
      v-model="dialogVisible"
      title="添加机器"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-width="80px" label-position="left">
        <el-form-item label="IP 地址">
          <el-input
            v-model="form.ip"
            placeholder="例如: 192.168.1.100"
          ></el-input>
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number
            v-model="form.port"
            :min="1"
            :max="65535"
            style="width: 100%"
          ></el-input-number>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="root"></el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="SSH 密码"
          ></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="addMachine" :loading="adding"
            >确定</el-button
          >
        </span>
      </template>
    </el-dialog>

    <!-- 编辑机器对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑机器" width="400px">
      <el-form :model="editForm" label-width="80px" label-position="left">
        <el-form-item label="IP 地址">
          <el-input v-model="editForm.ip" disabled></el-input>
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" placeholder="root"></el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="editForm.password"
            type="password"
            show-password
            placeholder="SSH 密码"
          ></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEdit" :loading="updating"
            >保存</el-button
          >
        </span>
      </template>
    </el-dialog>

    <!-- 设置对话框 -->
    <el-dialog v-model="settingsVisible" title="系统设置" width="400px">
      <el-form :model="settingsForm" label-width="120px" label-position="left">
        <el-form-item label="检测间隔 (秒)">
          <el-input-number
            v-model="settingsForm.interval_seconds"
            :min="10"
            style="width: 100%"
          ></el-input-number>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="settingsVisible = false">取消</el-button>
          <el-button type="primary" @click="saveSettings">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import axios from "axios";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Refresh,
  InfoFilled,
  Monitor,
  Setting,
  Plus,
  View,
  Hide,
  CopyDocument,
  Search,
} from "@element-plus/icons-vue";

const machines = ref([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editDialogVisible = ref(false);
const detailsDialogVisible = ref(false);
const currentDetails = ref([]);
const currentRawOutput = ref("");
const loadingRaw = ref(false);
const currentMachineName = ref("");
const settingsVisible = ref(false);
const adding = ref(false);
const updating = ref(false);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const searchQuery = ref("");
const filterArch = ref("");
const filterStatus = ref("");
const filterAcc = ref("");
// 导入导出相关
const fileInput = ref(null);
const importing = ref(false);

const form = reactive({ ip: "", port: 22, username: "root", password: "" });
const editForm = reactive({ id: null, ip: "", username: "", password: "" });
const settingsForm = reactive({ interval_seconds: 60 });

const fetchMachines = async () => {
  loading.value = true;
  try {
    const res = await axios.get("/machines", {
      params: {
        page: currentPage.value,
        size: pageSize.value,
        search: searchQuery.value,
        arch: filterArch.value,
        status: filterStatus.value,
        acc_type: filterAcc.value,
      },
    });
    machines.value = res.data.items.map((m) => ({
      ...m,
      refreshing: false,
      showPassword: false,
      remark: m.remark || "",
    }));
    total.value = res.data.total;
  } catch (e) {
    ElMessage.error("获取机器列表失败");
  } finally {
    loading.value = false;
  }
};

// 导出当前机器为 JSON
const exportMachines = () => {
  // 生成 CSV，包含表头并对 " 进行转义
  const headers = [
    "id",
    "ip",
    "port",
    "username",
    "password",
    "os_info",
    "arch",
    "accelerator_type",
    "accelerator_count",
    "accelerator_status",
    "remark",
  ];
  const rows = machines.value.map((m) => {
    return headers
      .map((h) => {
        const v = m[h] === undefined || m[h] === null ? "" : m[h];
        const s = String(v).replace(/"/g, '""');
        return `"${s}"`;
      })
      .join(",");
  });
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "machines.csv";
  a.click();
  URL.revokeObjectURL(url);
};

// 下载导入模板
const downloadTemplate = () => {
  // 生成模板 CSV，只包含必要的字段
  const headers = [
    "ip",
    "port",
    "username",
    "password",
    "remark"
  ];
  
  // 添加示例数据
  const sampleData = [
    "192.168.1.100,22,root,password123,示例服务器1",
    "192.168.1.101,22,admin,password456,示例服务器2"
  ];
  
  const csv = [headers.join(","), ...sampleData].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "machines_template.csv";
  a.click();
  URL.revokeObjectURL(url);
};

// 触发文件选择
const importMachines = () => {
  fileInput.value && fileInput.value.click();
};

// 处理文件并逐台导入（会调用后端添加接口）
const handleFileChange = async (e) => {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  try {
    importing.value = true;
    const text = await file.text();

    // 简单 CSV 解析，支持带双引号和双引号转义的字段
    const parseLine = (line) => {
      const res = [];
      let cur = "";
      let inQuotes = false;
      for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (inQuotes) {
          if (ch === '"') {
            if (line[i + 1] === '"') {
              cur += '"';
              i++;
            } else {
              inQuotes = false;
            }
          } else {
            cur += ch;
          }
        } else {
          if (ch === '"') {
            inQuotes = true;
          } else if (ch === ',') {
            res.push(cur);
            cur = "";
          } else {
            cur += ch;
          }
        }
      }
      res.push(cur);
      return res;
    };

    const lines = text.split(/\r\n|\n/).filter((l) => l.trim() !== "");
    if (lines.length < 1) throw new Error("CSV 文件为空");
    const headers = parseLine(lines[0]).map((h) => h.trim());
    const data = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = parseLine(lines[i]);
      const obj = {};
      for (let j = 0; j < headers.length; j++) {
        obj[headers[j]] = cols[j] !== undefined ? cols[j] : "";
      }
      data.push(obj);
    }

    // data 为对象数组，逐条发送到后端
    for (const item of data) {
      // 根据后端实际字段调整类型或字段名（如 port, accelerator_count 等）
      await axios.post("/machines", item).catch((err) => {
        console.error("导入失败：", item, err?.response?.data || err.message);
      });
    }
    ElMessage.success("导入完成（若有失败请查看控制台）");
    fetchMachines();
  } catch (err) {
    ElMessage.error("导入失败: " + (err.message || err));
  } finally {
    importing.value = false;
    if (fileInput.value) fileInput.value.value = null;
  }
};

// 更新备注字段
const updateRemark = async (row) => {
  try {
    await axios.put(`/machines/${row.id}`, { remark: row.remark });
    ElMessage.success("备注已保存");
  } catch (e) {
    ElMessage.error("保存备注失败");
  }
};

const refreshAllMachines = async () => {
  loading.value = true;
  try {
    await axios.post("/machines/refresh_all");
    await fetchMachines();
    ElMessage.success("刷新完成");
  } catch (e) {
    ElMessage.error("刷新失败");
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  currentPage.value = 1;
  fetchMachines();
};

const handleSizeChange = (val) => {
  pageSize.value = val;
  fetchMachines();
};

const handleCurrentChange = (val) => {
  currentPage.value = val;
  fetchMachines();
};

const addMachine = async () => {
  if (!form.ip || !form.username || !form.password) {
    ElMessage.warning("请填写完整信息");
    return;
  }
  adding.value = true;
  try {
    await axios.post("/machines", form);
    ElMessage.success("机器添加成功");
    dialogVisible.value = false;
    fetchMachines();
    form.ip = "";
    form.password = "";
  } catch (e) {
    const msg = e.response?.data?.detail || "添加失败";
    ElMessage.error(msg);
  } finally {
    adding.value = false;
  }
};

const openEditDialog = (row) => {
  editForm.id = row.id;
  editForm.ip = row.ip;
  editForm.username = row.username;
  editForm.password = row.password;
  editDialogVisible.value = true;
};

const submitEdit = async () => {
  if (!editForm.username || !editForm.password) {
    ElMessage.warning("请填写完整信息");
    return;
  }
  updating.value = true;
  try {
    await axios.put(`/machines/${editForm.id}`, editForm);
    ElMessage.success("修改成功");
    editDialogVisible.value = false;
    fetchMachines();
  } catch (e) {
    ElMessage.error("修改失败");
  } finally {
    updating.value = false;
  }
};

const deleteMachine = (row) => {
  ElMessageBox.confirm("确定要删除该机器吗？", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(async () => {
    try {
      await axios.delete(`/machines/${row.id}`);
      ElMessage.success("已删除");
      fetchMachines();
    } catch (e) {
      ElMessage.error("删除失败");
    }
  });
};

const refreshMachine = async (row) => {
  row.refreshing = true;
  try {
    await axios.post(`/machines/${row.id}/refresh`);
    ElMessage.success("刷新成功");
    fetchMachines();
  } catch (e) {
    ElMessage.error("刷新失败");
  } finally {
    row.refreshing = false;
  }
};

const openSettings = async () => {
  try {
    const res = await axios.get("/settings");
    if (res.data) settingsForm.interval_seconds = res.data.interval_seconds;
    settingsVisible.value = true;
  } catch (e) {
    ElMessage.error("加载设置失败");
  }
};

const saveSettings = async () => {
  try {
    await axios.post("/settings", settingsForm);
    ElMessage.success("设置已保存");
    settingsVisible.value = false;
  } catch (e) {
    ElMessage.error("保存设置失败");
  }
};

const getStatusTagType = (status) => {
  if (status === "Online") return "success";
  if (status === "Error") return "danger";
  return "info";
};

const getStatusText = (status) => {
  if (status === "Online") return "在线";
  if (status === "Offline") return "离线";
  if (status === "Error") return "错误";
  return "未知";
};

const formatDate = (dateStr) =>
  dateStr ? new Date(dateStr).toLocaleString() : "-";

const formatAcceleratorStatus = (jsonStr) => {
  try {
    if (typeof jsonStr !== "string") return JSON.stringify(jsonStr, null, 2);
    const data = JSON.parse(jsonStr);
    if (Array.isArray(data)) {
      return data
        .map(
          (d) =>
            `${d.name}: 显存 ${d.memory_used}/${d.memory_total}, 温度 ${d.temp}`
        )
        .join("\n");
    }
    return jsonStr;
  } catch (e) {
    return jsonStr;
  }
};

const parseAcceleratorStatus = (jsonStr) => {
  try {
    if (typeof jsonStr !== "string") return [];
    console.log("jsonStr:", jsonStr);
    const data = JSON.parse(jsonStr);
    return Array.isArray(data) ? data : [];
  } catch (e) {
    return [];
  }
};

const showDetails = async (row) => {
  currentMachineName.value = row.ip;
  currentDetails.value = parseAcceleratorStatus(row.accelerator_status);
  detailsDialogVisible.value = true;

  // Fetch raw output
  loadingRaw.value = true;
  currentRawOutput.value = "正在获取实时监控数据...";
  try {
    const res = await axios.get(`/machines/${row.id}/raw_monitor`);
    currentRawOutput.value = res.data.output;
  } catch (e) {
    currentRawOutput.value =
      "获取失败: " + (e.response?.data?.detail || e.message);
  } finally {
    loadingRaw.value = false;
  }
};

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制到剪贴板");
  } catch {
    ElMessage.error("复制失败");
  }
};

onMounted(() => {
  fetchMachines();
  setInterval(fetchMachines, 10000);
});
</script>

<style>
body {
  margin: 0;
  background-color: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial;
}
.main-container {
  min-height: 100vh;
}
.header {
  background-color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 10;
}
.logo-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.table-card {
  margin-bottom: 24px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.search-input {
  width: 200px;
}
.filter-select {
  width: 120px;
}
.title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}
.title {
  font-size: 16px;
  font-weight: 600;
}
.password-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}
.acc-count {
  margin-left: 8px;
  font-size: 13px;
  color: #606266;
}
.info-icon {
  margin-left: 4px;
  cursor: pointer;
  color: #909399;
}
.info-icon:hover {
  color: #409eff;
}
.card-status-row {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 4px 0;
}
.custom-badge-inline :deep(.el-badge__content) {
  top: 0;
  right: -10px;
  transform: scale(0.8);
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.popover-content {
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
  background: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
}
pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
