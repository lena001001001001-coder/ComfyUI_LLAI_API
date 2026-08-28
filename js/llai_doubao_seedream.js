import { app } from "../../scripts/app.js";


const RATIOS_2K = [
    "2048x2048（1:1 方图）",
    "2560x1440（16:9 横图）",
    "1440x2560（9:16 竖图）",
    "2304x1728（4:3 横图）",
    "1728x2304（3:4 竖图）",
    "2496x1664（3:2 横图）",
    "1664x2496（2:3 竖图）",
    "2560x1600（16:10 横图）",
    "1600x2560（10:16 竖图）",
];
const RATIOS_4K = [
    "3840x2160（4K 16:9 横图）",
    "2160x3840（4K 9:16 竖图）",
    "3072x2304（4K 4:3 横图）",
    "2304x3072（4K 3:4 竖图）",
    "3072x3072（4K 1:1 方图）",
    "4096x4096（最大方图）",
];
const RATIOS_40_1K = [
    "1024x1024（1:1 方图）", "1152x864（4:3 横图）", "864x1152（3:4 竖图）",
    "1280x720（16:9 横图）", "720x1280（9:16 竖图）",
    "1248x832（3:2 横图）", "832x1248（2:3 竖图）", "1512x648（21:9 超宽图）",
];
const RATIOS_40_2K = [
    "2048x2048（1:1 方图）", "2304x1728（4:3 横图）", "1728x2304（3:4 竖图）",
    "2848x1600（16:9 横图）", "1600x2848（9:16 竖图）",
    "2496x1664（3:2 横图）", "1664x2496（2:3 竖图）", "3136x1344（21:9 超宽图）",
];
const RATIOS_40_4K = [
    "4096x4096（1:1 方图）", "4704x3520（4:3 横图）", "3520x4704（3:4 竖图）",
    "5504x3040（16:9 横图）", "3040x5504（9:16 竖图）",
    "4992x3328（3:2 横图）", "3328x4992（2:3 竖图）", "6240x2656（21:9 超宽图）",
];
const RATIOS_50_PRO_1K = [
    "1024x1024（1:1 方图）", "1152x864（4:3 横图）", "864x1152（3:4 竖图）",
    "1424x800（16:9 横图）", "800x1424（9:16 竖图）", "1248x832（3:2 横图）",
    "832x1248（2:3 竖图）", "1568x672（21:9 超宽图）",
];
const RATIOS_50_PRO_15K = [
    "1536x1536（1:1 方图）", "1792x1344（4:3 横图）", "1344x1792（3:4 竖图）",
    "2048x1152（16:9 横图）", "1152x2048（9:16 竖图）", "1872x1248（3:2 横图）",
    "1248x1872（2:3 竖图）", "2352x1008（21:9 超宽图）",
];
const RATIOS_50_PRO_2K = [
    "2048x2048（1:1 方图）", "2368x1776（4:3 横图）", "1776x2368（3:4 竖图）",
    "2816x1584（16:9 横图）", "1584x2816（9:16 竖图）", "2496x1664（3:2 横图）",
    "1664x2496（2:3 竖图）", "3136x1344（21:9 超宽图）",
];
const RATIOS_50_LITE_2K = [
    "2048x2048（1:1 方图）", "2304x1728（4:3 横图）", "1728x2304（3:4 竖图）",
    "2848x1600（16:9 横图）", "1600x2848（9:16 竖图）", "2496x1664（3:2 横图）",
    "1664x2496（2:3 竖图）", "3136x1344（21:9 超宽图）",
];
const RATIOS_50_LITE_3K = [
    "3072x3072（1:1 方图）", "3456x2592（4:3 横图）", "2592x3456（3:4 竖图）",
    "4096x2304（16:9 横图）", "2304x4096（9:16 竖图）", "3744x2496（3:2 横图）",
    "2496x3744（2:3 竖图）", "4704x2016（21:9 超宽图）",
];
const LEGACY_RATIOS_40 = new Map([
    ["1536x1024（3:2 横图）", "1248x832（3:2 横图）"],
    ["1024x1536（2:3 竖图）", "832x1248（2:3 竖图）"],
    ["2560x1440（16:9 横图）", "2848x1600（16:9 横图）"],
    ["1440x2560（9:16 竖图）", "1600x2848（9:16 竖图）"],
    ["3840x2160（16:9 横图）", "5504x3040（16:9 横图）"],
    ["2160x3840（9:16 竖图）", "3040x5504（9:16 竖图）"],
    ["3072x2304（4:3 横图）", "4704x3520（4:3 横图）"],
    ["2304x3072（3:4 竖图）", "3520x4704（3:4 竖图）"],
]);


function hideWidget(widget) {
    if (!widget || widget.hidden || widget.type === "hidden") return;

    widget.hidden = true;
    widget._llaiOriginalType = widget.type;
    widget._llaiOriginalComputeSize = widget.computeSize;
    widget.type = "hidden";
    widget.computeSize = () => [0, 0];

    if (widget.inputEl) {
        widget.inputEl.style.display = "none";
        widget.inputEl.style.visibility = "hidden";
        widget.inputEl.style.pointerEvents = "none";
        widget.inputEl.tabIndex = -1;
    }
}


function updateRatioOptions(sizeWidget, ratioWidget, is40, migrateLegacyValue = false) {
    if (!sizeWidget || !ratioWidget) return;

    const oldSize = sizeWidget.value;
    const ratios1K = is40 ? RATIOS_40_1K : RATIOS_2K;
    const ratios2K = is40 ? RATIOS_40_2K : RATIOS_2K;
    const ratios4K = is40 ? RATIOS_40_4K : RATIOS_4K;
    if (migrateLegacyValue && is40 && RATIOS_40_1K.includes(oldSize)) {
        sizeWidget.value = "1K";
        ratioWidget.value = oldSize;
    } else if (migrateLegacyValue && is40 && RATIOS_40_2K.includes(oldSize)) {
        sizeWidget.value = "2K";
        ratioWidget.value = oldSize;
    } else if (migrateLegacyValue && RATIOS_2K.includes(oldSize)) {
        sizeWidget.value = "2K";
        ratioWidget.value = oldSize;
    } else if (migrateLegacyValue && RATIOS_4K.includes(oldSize)) {
        sizeWidget.value = "4K";
        ratioWidget.value = oldSize;
    } else if (migrateLegacyValue && String(oldSize).startsWith("2K")) {
        sizeWidget.value = "2K";
    } else if (migrateLegacyValue && String(oldSize).startsWith("4K")) {
        sizeWidget.value = "4K";
    }

    const values = sizeWidget.value === "4K" ? ratios4K : (sizeWidget.value === "1K" ? ratios1K : ratios2K);
    sizeWidget.value = is40 ? (values === ratios4K ? "4K" : values === ratios1K ? "1K" : "2K") : (sizeWidget.value === "4K" ? "4K" : "2K");
    ratioWidget.options.values = values;
    if (is40 && LEGACY_RATIOS_40.has(ratioWidget.value)) {
        ratioWidget.value = LEGACY_RATIOS_40.get(ratioWidget.value);
    }
    if (!values.includes(ratioWidget.value)) {
        ratioWidget.value = values[0];
    }
    ratioWidget.callback?.(ratioWidget.value);
}


function moveWidgetBefore(node, widget, target) {
    if (!widget || !target || widget === target) return;
    const oldIndex = node.widgets.indexOf(widget);
    if (oldIndex < 0) return;
    node.widgets.splice(oldIndex, 1);
    const targetIndex = node.widgets.indexOf(target);
    node.widgets.splice(targetIndex, 0, widget);
}


app.registerExtension({
    name: "LLAI.DoubaoSeedream",

    async nodeCreated(node) {
        if (!["LLDoubaoSeedream40TextToImage", "LLDoubaoSeedream40", "LLDoubaoSeedream45", "LLDoubaoSeedream50Pro", "LLDoubaoSeedream50Lite"].includes(node.comfyClass)) return;

        await new Promise(resolve => setTimeout(resolve, 100));

        // Preserve the backend widget order when saving old and new workflows.
        const serializationWidgets = [...(node.widgets || [])];
        const originalSerialize = node.serialize;
        node.serialize = function (...args) {
            const data = originalSerialize.apply(this, args);
            data.widgets_values = serializationWidgets.map(widget => widget.value);
            return data;
        };

        for (const name of ["watermark", "response_format"]) {
            hideWidget(node.widgets?.find(widget => widget.name === name));
        }

        const sizeWidget = node.widgets?.find(widget => widget.name === "size");
        const ratioWidget = node.widgets?.find(widget => widget.name === "ratio");
        const is40 = ["LLDoubaoSeedream40TextToImage", "LLDoubaoSeedream40"].includes(node.comfyClass);
        const is50Pro = ["LLDoubaoSeedream50Pro"].includes(node.comfyClass);
        const is50Lite = node.comfyClass === "LLDoubaoSeedream50Lite";
        if (is50Lite) {
            const updateLite = () => {
                const values = sizeWidget.value === "3K" ? RATIOS_50_LITE_3K : RATIOS_50_LITE_2K;
                ratioWidget.options.values = values;
                if (!values.includes(ratioWidget.value)) ratioWidget.value = values[0];
                ratioWidget.callback?.(ratioWidget.value);
            };
            updateLite();
            if (sizeWidget) {
                const originalLiteCallback = sizeWidget.callback;
                sizeWidget.callback = function (value) {
                    sizeWidget.value = value;
                    originalLiteCallback?.call(this, value);
                    updateLite();
                    app.graph.setDirtyCanvas(true);
                };
            }
        } else if (is50Pro) {
            const proSizeWidget = sizeWidget;
            const proRatioWidget = ratioWidget;
            const updatePro = () => {
                const values = proSizeWidget.value === "1K" ? RATIOS_50_PRO_1K : (proSizeWidget.value === "1.5K" ? RATIOS_50_PRO_15K : RATIOS_50_PRO_2K);
                proRatioWidget.options.values = values;
                if (!values.includes(proRatioWidget.value)) proRatioWidget.value = values[0];
                proRatioWidget.callback?.(proRatioWidget.value);
            };
            updatePro();
            if (proSizeWidget) {
                const originalProCallback = proSizeWidget.callback;
                proSizeWidget.callback = function (value) {
                    proSizeWidget.value = value;
                    originalProCallback?.call(this, value);
                    updatePro();
                    app.graph.setDirtyCanvas(true);
                };
            }
        } else {
            updateRatioOptions(sizeWidget, ratioWidget, is40, true);
            if (sizeWidget) {
                const originalSizeCallback = sizeWidget.callback;
                sizeWidget.callback = function (value) {
                    sizeWidget.value = value;
                    if (originalSizeCallback) originalSizeCallback.call(this, value);
                    updateRatioOptions(sizeWidget, ratioWidget, is40);
                    app.graph.setDirtyCanvas(true);
                };
            }
        }
        moveWidgetBefore(node, ratioWidget, sizeWidget);

        const computed = node.computeSize();
        node.setSize([Math.max(node.size?.[0] || 0, computed[0]), computed[1]]);
        app.graph.setDirtyCanvas(true);
    },
});
