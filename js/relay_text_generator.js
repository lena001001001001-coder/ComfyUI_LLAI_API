import { app } from "../../scripts/app.js";

function isWidgetHidden(widget) {
    return widget?.hidden || widget?.type === "hidden";
}

function hideWidget(widget) {
    if (!widget || isWidgetHidden(widget)) return;
    widget._origType = widget.type;
    widget._origComputeSize = widget.computeSize;
    widget.hidden = true;
    widget.type = "hidden";
    widget.computeSize = () => [0, 0];
    if (widget.inputEl) {
        widget.inputEl.style.display = "none";
        widget.inputEl.style.visibility = "hidden";
        widget.inputEl.style.pointerEvents = "none";
        widget.inputEl.tabIndex = -1;
    }
}

function applyMinSize(node, preferred) {
    if (!node || typeof node.computeSize !== "function") return;
    const computed = node.computeSize();
    const current = Array.isArray(preferred) ? preferred : (Array.isArray(node.size) ? node.size : computed);
    node.setSize([
        Math.max(current[0] || 0, computed[0] || 0),
        Math.max(current[1] || 0, computed[1] || 0),
    ]);
}

function preserveNodeSize(node, preferred) {
    if (!Array.isArray(preferred)) return;
    applyMinSize(node, preferred);
    setTimeout(() => applyMinSize(node, preferred), 0);
    requestAnimationFrame(() => applyMinSize(node, preferred));
}

app.registerExtension({
    name: "RelayAPI.TextGenerator",

    async nodeCreated(node) {
        if (node.comfyClass !== "RelayLLMText") return;

        await new Promise(r => setTimeout(r, 200));

        const preferredSize = Array.isArray(node.size) ? [...node.size] : null;
        const apiBaseW = node.widgets?.find(w => w.name === "api_base");
        if (apiBaseW) hideWidget(apiBaseW);

        const apiFormatW = node.widgets?.find(w => w.name === "api_format");
        if (apiFormatW) {
            apiFormatW.options.values = ["v1beta/models"];
            apiFormatW.value = "v1beta/models";
        }

        const templateW = node.widgets?.find(w => w.name === "prompt_template");
        if (templateW?.value === "prompt_template") {
            templateW.value = "";
        }

        const apikeyW = node.widgets?.find(w => w.name === "apikey");
        if (apikeyW?.inputEl) {
            apikeyW.inputEl.type = "text";
            apikeyW.inputEl.autocomplete = "off";
            apikeyW.inputEl.spellcheck = false;
        }

        preserveNodeSize(node, preferredSize);
        app.graph.setDirtyCanvas(true);
    },
});
