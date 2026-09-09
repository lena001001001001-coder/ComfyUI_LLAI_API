import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Direct LLAI nodes use the same API contract on these two relay sites.
// Keep the Volcengine/Ark node untouched: it has its own endpoint and key format.
const LLAI_BASE_OPTIONS = [
    "https://api.llaiapi.host",
    "https://cn.llai.xin",
];

const EXCLUDED_CLASSES = new Set([
    "LLVolcengineSeedream",
]);

app.registerExtension({
    name: "LLAI.ApiBaseSelector",

    async nodeCreated(node) {
        if (EXCLUDED_CLASSES.has(node.comfyClass)) return;

        const apiBaseWidget = node.widgets?.find(widget => widget.name === "api_base");
        if (!apiBaseWidget || apiBaseWidget.hidden || apiBaseWidget.type === "hidden") return;

        await new Promise(resolve => setTimeout(resolve, 100));

        let values = [...LLAI_BASE_OPTIONS];
        try {
            const response = await api.fetchApi("/relayapi/api_bases");
            if (response.ok) {
                const bases = await response.json();
                if (Array.isArray(bases)) {
                    values = bases.filter(base => typeof base === "string" && base.trim());
                }
            }
        } catch (error) {
            console.warn("[LLAI] API 地址列表加载失败，使用默认地址列表", error);
        }

        for (const base of LLAI_BASE_OPTIONS) {
            if (!values.includes(base)) values.unshift(base);
        }

        const currentValue = String(apiBaseWidget.value || "").replace(/\/+$/, "");
        apiBaseWidget.type = "combo";
        apiBaseWidget.options = apiBaseWidget.options || {};
        apiBaseWidget.options.values = values;
        apiBaseWidget.value = values.includes(currentValue) ? currentValue : values[0];
        app.graph.setDirtyCanvas(true);
    },
});
