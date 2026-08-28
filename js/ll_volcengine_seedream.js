import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const RESOLUTIONS = {
    "Doubao-Seedream-4.0": ["1K", "2K", "4K"],
    "Doubao-Seedream-4.5": ["2K", "4K"],
    "Doubao-Seedream-5.0-lite": ["2K", "3K", "4K"],
    "Doubao-Seedream-5.0-lite 260128": ["2K", "3K", "4K"],
    "Doubao-Seedream-5.0-pro": ["1K", "1.5K", "2K"],
};
const SIZE_WARNING = "火山限制单图不超过 30MB，请缩放图像比例或尺寸";
const MODEL_IMAGE_LIMITS = {
    "Doubao-Seedream-4.0": 14,
    "Doubao-Seedream-4.5": 14,
    "Doubao-Seedream-5.0-lite": 14,
    "Doubao-Seedream-5.0-lite 260128": 14,
    "Doubao-Seedream-5.0-pro": 10,
};
const DISABLED_IMAGE_TYPE = "LLAI_DISABLED_IMAGE";
const DISABLED_SOCKET_COLOR = "#555555";
const API_KEY_PLACEHOLDER = "ark-...";

function updateResolution(node) {
    const model = node.widgets?.find((widget) => widget.name === "model");
    const resolution = node.widgets?.find((widget) => widget.name === "resolution");
    if (!model || !resolution) return;
    const values = RESOLUTIONS[model.value] || RESOLUTIONS["Doubao-Seedream-4.5"];
    resolution.options.values = values;
    if (!values.includes(resolution.value)) resolution.value = values.includes("2K") ? "2K" : values[0];
}

function updateImageInputs(node) {
    const model = node.widgets?.find((widget) => widget.name === "model");
    const limit = MODEL_IMAGE_LIMITS[model?.value] || 14;
    for (let index = 0; index < (node.inputs || []).length; index++) {
        const input = node.inputs[index];
        if (input.name !== "image" && !/^image_\d+$/.test(input.name)) continue;
        const imageNumber = input.name === "image" ? 1 : Number(input.name.slice(6));
        const enabled = imageNumber <= limit;
        input._llaiOriginalType ??= "IMAGE";
        input.type = enabled ? input._llaiOriginalType : DISABLED_IMAGE_TYPE;
        if (enabled) {
            delete input.color_on;
            delete input.color_off;
        } else {
            input.color_on = DISABLED_SOCKET_COLOR;
            input.color_off = DISABLED_SOCKET_COLOR;
            if (input.link != null) node.disconnectInput(index);
        }
    }
}

app.registerExtension({
    name: "LLAI.VolcengineSeedream",
    async nodeCreated(node) {
        if (node.comfyClass !== "LLVolcengineSeedream") return;
        await new Promise((resolve) => setTimeout(resolve, 100));
        const apiKey = node.widgets?.find((widget) => widget.name === "api_key");
        if (apiKey) {
            apiKey.options = { ...(apiKey.options || {}), placeholder: API_KEY_PLACEHOLDER };
            if (apiKey.inputEl) apiKey.inputEl.placeholder = API_KEY_PLACEHOLDER;
        }
        const model = node.widgets?.find((widget) => widget.name === "model");
        updateResolution(node);
        updateImageInputs(node);
        if (model) {
            const original = model.callback;
            model.callback = function (value) {
                model.value = value;
                original?.call(this, value);
                updateResolution(node);
                updateImageInputs(node);
                app.graph.setDirtyCanvas(true);
            };
        }

        node._volcengineBaseHeight = node.size?.[1] || node.computeSize()[1];
        const originalDraw = node.onDrawForeground?.bind(node);
        node.onDrawForeground = function (ctx) {
            originalDraw?.(ctx);
            if (!this.flags?.collapsed && apiKey && !String(apiKey.value || "").trim() && Number.isFinite(apiKey.last_y)) {
                ctx.save();
                ctx.fillStyle = "rgba(190, 190, 190, 0.58)";
                ctx.font = "14px sans-serif";
                ctx.textAlign = "right";
                ctx.textBaseline = "middle";
                ctx.fillText(API_KEY_PLACEHOLDER, this.size[0] - 18, apiKey.last_y + 10);
                ctx.restore();
            }
            if (!this._volcengineSizeWarning || this.flags?.collapsed) return;
            ctx.save();
            ctx.fillStyle = "#ff5b5b";
            ctx.font = "13px sans-serif";
            ctx.textAlign = "left";
            ctx.textBaseline = "bottom";
            ctx.fillText(SIZE_WARNING, 10, this.size[1] - 7, Math.max(120, this.size[0] - 20));
            ctx.restore();
        };
    },
});

api.addEventListener("execution_start", () => {
    for (const node of app.graph?._nodes || []) {
        if (node.comfyClass !== "LLVolcengineSeedream" || !node._volcengineSizeWarning) continue;
        node._volcengineSizeWarning = false;
        node.setSize([node.size[0], node._volcengineBaseHeight]);
    }
});

api.addEventListener("execution_error", (event) => {
    const detail = event.detail || {};
    const message = String(detail.exception_message || detail.exception_type || detail.message || "");
    if (!message.includes(SIZE_WARNING)) return;
    const node = app.graph?.getNodeById?.(detail.node_id);
    if (!node || node.comfyClass !== "LLVolcengineSeedream") return;
    node._volcengineSizeWarning = true;
    node.setSize([Math.max(node.size[0], 390), Math.max(node.size[1], node._volcengineBaseHeight + 30)]);
    app.graph.setDirtyCanvas(true);
});
