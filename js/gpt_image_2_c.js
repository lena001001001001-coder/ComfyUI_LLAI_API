// Keep the low-cost GPT image node's resolution and ratio widgets synchronized.
import { app } from "/scripts/app.js";

const NODE_CLASSES = new Set(["GPTImage2CFullSize"]);
const LOW_COST_RATIO_OPTIONS = {
    "1K": ["1024x1024（1:1）", "1536x1024（3:2）", "1024x1536（2:3）"],
    "2K": ["2048x2048（1:1）", "2048x1152（16:9）"],
    "4K": ["3840x2160（16:9）", "2160x3840（9:16）"],
};
const LOW_COST_DEFAULTS = {
    "1K": "1024x1024（1:1）",
    "2K": "2048x2048（1:1）",
    "4K": "3840x2160（16:9）",
};
const FULL_SIZE_RATIO_OPTIONS = ["auto", "1:1", "2:3", "3:2", "4:3", "3:4", "9:16", "16:9", "9:21", "21:9", "1:3", "3:1"];

app.registerExtension({
    name: "ComfyUI_LLAI_API.GPTImage2CResolutionSync",
    nodeCreated(node) {
        if (!NODE_CLASSES.has(node.comfyClass)) return;
        const resolutionWidget = node.widgets?.find((widget) => widget.name === "分辨率");
        const ratioWidget = node.widgets?.find((widget) => widget.name === "图像比例");
        if (!resolutionWidget || !ratioWidget) return;

        const syncRatio = () => {
            const fullSize = node.comfyClass === "GPTImage2CFullSize";
            const values = fullSize ? FULL_SIZE_RATIO_OPTIONS : LOW_COST_RATIO_OPTIONS[resolutionWidget.value];
            if (values && ratioWidget.options) {
                ratioWidget.options.values = values;
            }
            const nextRatio = fullSize ? "1:1" : LOW_COST_DEFAULTS[resolutionWidget.value];
            if (!nextRatio) {
                node.setDirtyCanvas(true, true);
                return;
            }
            ratioWidget.value = nextRatio;
            if (typeof ratioWidget.callback === "function") {
                ratioWidget.callback(ratioWidget.value);
            }
            node.setDirtyCanvas(true, true);
        };

        const originalCallback = resolutionWidget.callback;
        resolutionWidget.callback = function(value) {
            if (typeof originalCallback === "function") originalCallback.call(this, value);
            syncRatio();
        };
        syncRatio();
    },
});
