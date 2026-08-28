import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_NAME = "LL-Read-Excel";
const EXTENSIONS = [".xlsx", ".xls"];

function isExcelFile(file) {
    const name = String(file?.name || "").toLowerCase();
    return EXTENSIONS.some((extension) => name.endsWith(extension));
}

function setExcelWidget(node, value) {
    const widget = (node.widgets || []).find((item) => item.name === "excel_file");
    if (!widget) return;
    widget.value = value;
    widget.callback?.(value);
    node.graph?.setDirtyCanvas(true, true);
    app.graph?.setDirtyCanvas(true, true);
}

function promptWidgets(node) {
    return (node?.widgets || [])
        .filter((widget) => /^prompt_\d+$/.test(widget.name))
        .sort((a, b) => Number(a.name.slice(7)) - Number(b.name.slice(7)));
}

function updateConnectedPromptList(node, prompts) {
    const values = Array.isArray(prompts) ? prompts : [];
    const links = node?.outputs?.[0]?.links || [];
    for (const linkId of links) {
        const link = app.graph?.links?.[linkId];
        const target = link ? app.graph.getNodeById(link.target_id) : null;
        const widgets = promptWidgets(target);
        if (!widgets.length) continue;
        widgets.forEach((widget, index) => {
            widget.value = values[index] || "";
            widget.callback?.(widget.value);
        });
        target.setDirtyCanvas?.(true, true);
    }
    app.graph?.setDirtyCanvas(true, true);
}

function extractPromptList(message) {
    const candidates = [
        message?.llai_prompt_list,
        message?.output?.llai_prompt_list,
        message?.ui?.llai_prompt_list,
        message?.output?.ui?.llai_prompt_list,
        message?.result,
        message?.output?.result,
    ];
    for (const candidate of candidates) {
        if (Array.isArray(candidate) && candidate.length && typeof candidate[0] === "string") {
            return candidate.map((item) => String(item));
        }
        const value = Array.isArray(candidate) && Array.isArray(candidate[0]) ? candidate[0] : candidate;
        if (Array.isArray(value)) return value.map((item) => String(item));
    }
    return [];
}

async function uploadExcel(node, file) {
    if (!isExcelFile(file)) {
        throw new Error("只支持 .xlsx 或 .xls 文件");
    }

    const body = new FormData();
    body.append("image", file, file.name);
    body.append("type", "input");

    const response = await api.fetchApi("/upload/image", {
        method: "POST",
        body,
    });
    if (!response.ok) {
        throw new Error(`上传失败（HTTP ${response.status}）`);
    }

    const result = await response.json();
    const name = result.subfolder ? `${result.subfolder}/${result.name}` : result.name;
    if (!name) throw new Error("上传响应缺少文件名");
    setExcelWidget(node, name);
}

app.registerExtension({
    name: "LLAI.ReadExcelUpload",
    nodeCreated(node) {
        if (node?.comfyClass !== NODE_NAME) return;
        const originalExecuted = node.onExecuted;
        node.onExecuted = function (message) {
            originalExecuted?.apply(this, arguments);
            updateConnectedPromptList(this, extractPromptList(message));
        };
        node.onDropFile = async (file) => {
            try {
                await uploadExcel(node, file);
            } catch (error) {
                console.error("[LLAI] Excel 上传失败:", error);
                window.alert(`Excel 上传失败：${error.message || error}`);
            }
            return true;
        };
    },
});

// Some ComfyUI versions dispatch execution results through the API event bus
// instead of calling the node's onExecuted hook directly.
api.addEventListener("executed", (event) => {
    const detail = event?.detail || {};
    const nodeId = detail.node ?? detail.node_id ?? detail.nodeId;
    const node = nodeId != null ? app.graph?.getNodeById(Number(nodeId)) : null;
    if (node?.comfyClass !== NODE_NAME) return;
    updateConnectedPromptList(node, extractPromptList(detail.output || detail));
});

function getNodeAtDropPosition(event) {
    const canvas = app.canvas;
    if (!canvas?.canvas || !app.graph) return null;
    const rect = canvas.canvas.getBoundingClientRect();
    const scale = canvas.ds?.scale || 1;
    const offset = canvas.ds?.offset || [0, 0];
    const graphPosition = [
        (event.clientX - rect.left) / scale - offset[0],
        (event.clientY - rect.top) / scale - offset[1],
    ];
    return app.graph.getNodeOnPos?.(graphPosition[0], graphPosition[1]) || null;
}

function isExcelDrop(event) {
    return Array.from(event.dataTransfer?.files || []).some(isExcelFile);
}

document.addEventListener("dragover", (event) => {
    if (!isExcelDrop(event)) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
}, true);

document.addEventListener("drop", async (event) => {
    if (!isExcelDrop(event)) return;
    event.preventDefault();
    event.stopPropagation();

    const node = getNodeAtDropPosition(event);
    if (node?.comfyClass !== NODE_NAME) return;
    const file = Array.from(event.dataTransfer.files).find(isExcelFile);
    if (file) await node.onDropFile(file);
}, true);
