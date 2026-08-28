import { app } from "../../scripts/app.js";

const PROMPT_RE = /^prompt_(\d+)$/;
const PROMPT_HEIGHT = 76;

function promptWidgets(node) {
    return (node.widgets || [])
        .filter((widget) => PROMPT_RE.test(widget.name))
        .sort((a, b) => Number(a.name.match(PROMPT_RE)[1]) - Number(b.name.match(PROMPT_RE)[1]));
}

function setWidgetVisibility(node) {
    for (const widget of promptWidgets(node)) {
        widget.hidden = false;
        widget.options ??= {};
        widget.options.hidden = false;
        widget.options.multiline = true;
        widget.computeSize = () => [0, PROMPT_HEIGHT];
    }
    node.setDirtyCanvas(true, true);
    app.graph?.setDirtyCanvas(true, true);
}

function applyPromptList(node) {
    if (!node || node._llaiPromptListEnhanced) return;
    if (!promptWidgets(node).length) {
        setTimeout(() => applyPromptList(node), 100);
        return;
    }
    node._llaiPromptListEnhanced = true;
    setWidgetVisibility(node);

    const clearButton = node.addWidget("button", "一键清空", null, () => {
        for (const widget of promptWidgets(node)) {
            widget.value = "";
            widget.callback?.(widget.value);
        }
        node.setDirtyCanvas(true, true);
        app.graph?.setDirtyCanvas(true, true);
    });
    clearButton.serialize = false;
    setTimeout(() => {
        setWidgetVisibility(node);
    }, 0);
}

app.registerExtension({
    name: "LLAI.PromptList",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LLAIPromptList" && nodeData.name !== "LL-提示词列表") return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            originalCreated?.apply(this, arguments);
            applyPromptList(this);
        };
        const originalConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            originalConfigure?.apply(this, arguments);
            setTimeout(() => applyPromptList(this), 0);
        };
    },
    nodeCreated(node) {
        const comfyClass = node?.constructor?.comfyClass || node?.comfyClass || node?.type;
        if (comfyClass === "LLAIPromptList" || comfyClass === "LL-提示词列表") applyPromptList(node);
    },
});
