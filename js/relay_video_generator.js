import { app } from "../../scripts/app.js";

const VEO_ONLY_WIDGETS = ["enhance_prompt", "enable_HD"];

const GROK_RATIOS = ["auto", "16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"];
const VEO_RATIOS = ["16:9", "9:16"];

const GROK_SIZES = ["720P", "1080P"];
const VEO_SIZES = ["720P", "1080P"];

const GROK_DURATIONS = ["6", "10", "15", "30"];
const VEO_DURATIONS = ["4", "6", "8"];
const DEFAULT_DURATION_BY_PLATFORM = {
    Grok: "10",
    Veo: "8",
};

const GROK_MAX_IMAGES = 7;
const VEO_MAX_IMAGES = 3;

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

function showWidget(widget) {
    if (!widget || !isWidgetHidden(widget)) return;
    widget.hidden = false;
    widget.type = widget._origType || "combo";
    if (widget._origComputeSize) {
        widget.computeSize = widget._origComputeSize;
    } else {
        delete widget.computeSize;
    }
    if (widget.inputEl) {
        widget.inputEl.style.display = "";
        widget.inputEl.style.visibility = "";
        widget.inputEl.style.pointerEvents = "";
        widget.inputEl.tabIndex = 0;
    }
}

function needsPlatformApply(node, platform) {
    const plat = (platform || "Grok").trim();
    for (const w of node.widgets || []) {
        if (!VEO_ONLY_WIDGETS.includes(w.name)) continue;
        const shouldHide = plat !== "Veo";
        if (shouldHide !== isWidgetHidden(w)) return true;
    }
    return false;
}

function applyPlatform(node, platform, preferredSize) {
    const plat = (platform || "Grok").trim();
    let changed = false;
    const maxImg = plat === "Veo" ? VEO_MAX_IMAGES : GROK_MAX_IMAGES;

    for (const w of node.widgets || []) {
        if (VEO_ONLY_WIDGETS.includes(w.name)) {
            const shouldHide = plat !== "Veo";
            if (shouldHide && !isWidgetHidden(w)) { hideWidget(w); changed = true; }
            if (!shouldHide && isWidgetHidden(w)) { showWidget(w); changed = true; }
        }

        if (w.name === "ratio") {
            const newValues = plat === "Veo" ? VEO_RATIOS : GROK_RATIOS;
            if (JSON.stringify(w.options.values) !== JSON.stringify(newValues)) {
                w.options.values = newValues;
                if (!newValues.includes(w.value)) w.value = newValues[0];
                changed = true;
            }
        }

        if (w.name === "size") {
            const newValues = plat === "Veo" ? VEO_SIZES : GROK_SIZES;
            if (JSON.stringify(w.options.values) !== JSON.stringify(newValues)) {
                w.options.values = newValues;
                if (!newValues.includes(w.value)) w.value = newValues[0];
                changed = true;
            }
        }

        if (w.name === "duration") {
            const newValues = plat === "Veo" ? VEO_DURATIONS : GROK_DURATIONS;
            if (JSON.stringify(w.options.values) !== JSON.stringify(newValues)) {
                w.options.values = newValues;
                if (!newValues.includes(w.value)) {
                    w.value = DEFAULT_DURATION_BY_PLATFORM[plat] || newValues[0];
                }
                changed = true;
            }
        }
    }

    for (const input of node.inputs || []) {
        const m = input.name.match(/^image(\d+)$/);
        if (!m) continue;
        const idx = parseInt(m[1], 10);
        const shouldHide = idx > maxImg;

        if (shouldHide && !input._hidden) {
            if (input.link) {
                const linkInfo = app.graph.links[input.link];
                if (linkInfo) {
                    const srcNode = app.graph.getNodeById(linkInfo.origin_id);
                    if (srcNode) srcNode.disconnectOutput(linkInfo.origin_slot);
                }
            }
            input._hidden = true;
            input._origType = input.type;
            input.type = -1;
            changed = true;
        }
        if (!shouldHide && input._hidden) {
            input._hidden = false;
            input.type = input._origType || "IMAGE";
            changed = true;
        }
    }

    if (changed) {
        preserveNodeSize(node, preferredSize);
        app.graph.setDirtyCanvas(true);
    }
}

function getPlatformFromSource(node) {
    if (node.comfyClass === "RelayGrokVideo") return "Grok";

    const infoSlot = node.inputs?.find(i => i.name === "info");
    if (!infoSlot || !infoSlot.link) return "Grok";

    const link = app.graph.links[infoSlot.link];
    if (!link) return "Grok";

    const srcNode = app.graph.getNodeById(link.origin_id);
    if (!srcNode) return "Grok";

    const pw = srcNode.widgets?.find(w => w.name === "platform");
    return pw ? pw.value : "Grok";
}

function hasImageConnected(node) {
    for (const input of node.inputs || []) {
        if (/^image\d+$/.test(input.name) && input.link) return true;
    }
    return false;
}

app.registerExtension({
    name: "RelayAPI.VideoGenerator",

    async nodeCreated(node) {
        if (!["RelayVideoGenerator", "RelayGrokVideo", "RelayGrokImagineVideo"].includes(node.comfyClass)) return;

        await new Promise(r => setTimeout(r, 200));

        const initialPlatform = getPlatformFromSource(node);
        node._lastPlatform = initialPlatform;
        node._lastHasImage = hasImageConnected(node);
        applyPlatform(node, initialPlatform, Array.isArray(node.size) ? [...node.size] : null);

        if (node.comfyClass === "RelayGrokImagineVideo") {
            const apiKeyW = node.widgets?.find(w => w.name === "api_key");
            const modelW = node.widgets?.find(w => w.name === "model");
            const resolutionW = node.widgets?.find(w => w.name === "resolution");
            const aspectRatioW = node.widgets?.find(w => w.name === "aspect_ratio");
            const durationW = node.widgets?.find(w => w.name === "duration");
            const afterControlW = node.widgets?.find(w => w.name === "after_control");
            const apiBaseW = node.widgets?.find(w => w.name === "api_base");

            if (apiKeyW?.inputEl) {
                apiKeyW.inputEl.type = "text";
                apiKeyW.inputEl.autocomplete = "off";
                apiKeyW.inputEl.spellcheck = false;
            }

            if (apiBaseW) hideWidget(apiBaseW);

            if (apiKeyW && modelW) {
                const current = node.widgets.indexOf(apiKeyW);
                const target = node.widgets.indexOf(modelW) + 1;
                if (current > -1 && current !== target) {
                    node.widgets.splice(current, 1);
                    node.widgets.splice(target > current ? target - 1 : target, 0, apiKeyW);
                }
            }

            for (const w of [resolutionW, aspectRatioW, durationW, afterControlW]) {
                if (w) showWidget(w);
            }

            const imageInputs = (node.inputs || []).filter(i => /^image\d+$/.test(i.name));
            imageInputs.forEach((input, idx) => {
                const shouldHide = idx >= 3;
                if (shouldHide && !input._hidden) {
                    input._hidden = true;
                    input._origType = input.type;
                    input.type = -1;
                } else if (!shouldHide && input._hidden) {
                    input._hidden = false;
                    input.type = input._origType || "IMAGE";
                }
            });

            preserveNodeSize(node, Array.isArray(node.size) ? [...node.size] : null);
        } else if (false && node.comfyClass === "RelayGrokImagineVideo15") {
            const apiKeyW = node.widgets?.find(w => w.name === "api_key");
            const apiBaseW = node.widgets?.find(w => w.name === "api_base");
            const modelW = node.widgets?.find(w => w.name === "model");
            const imageInputs = (node.inputs || []).filter(i => /^image$/.test(i.name));

            if (apiKeyW?.inputEl) {
                apiKeyW.inputEl.type = "text";
                apiKeyW.inputEl.autocomplete = "off";
                apiKeyW.inputEl.spellcheck = false;
            }
            if (apiBaseW) hideWidget(apiBaseW);
            if (imageInputs.length > 1) {
                imageInputs.slice(1).forEach(input => {
                    if (!input._hidden) {
                        input._hidden = true;
                        input._origType = input.type;
                        input.type = -1;
                    }
                });
            }
            if (apiKeyW && modelW) {
                const current = node.widgets.indexOf(apiKeyW);
                const target = node.widgets.indexOf(modelW) + 1;
                if (current > -1 && current !== target) {
                    node.widgets.splice(current, 1);
                    node.widgets.splice(target > current ? target - 1 : target, 0, apiKeyW);
                }
            }
            preserveNodeSize(node, Array.isArray(node.size) ? [...node.size] : null);
        } else if (["RelayVideoGenerator", "RelayGrokVideo"].includes(node.comfyClass)) {
            const apiBaseW = node.widgets?.find(w => w.name === "api_base");
            if (apiBaseW) hideWidget(apiBaseW);
        } else if (["RelayVideoGenerator", "RelayGrokVideo"].includes(node.comfyClass)) {
            const apiBaseW = node.widgets?.find(w => w.name === "api_base");
            if (apiBaseW) hideWidget(apiBaseW);
            const taskTypeW = node.widgets?.find(w => w.name === "task_type");
            if (taskTypeW) {
                taskTypeW.options.values = ["video"];
                taskTypeW.value = "video";
            }
            const platformW = node.widgets?.find(w => w.name === "platform");
            if (platformW) {
                platformW.options.values = ["Grok"];
                platformW.value = "Grok";
            }
            const apiFormatW = node.widgets?.find(w => w.name === "api_format");
            if (apiFormatW) {
                apiFormatW.options.values = ["v1/video"];
                apiFormatW.value = "v1/video";
            }
            const modelW = node.widgets?.find(w => w.name === "model");
            if (modelW && !modelW.value) {
                modelW.value = "grok-video-3-10s";
            }
            const apikeyW = node.widgets?.find(w => w.name === "apikey");
            if (apikeyW?.inputEl) {
                apikeyW.inputEl.type = "text";
                apikeyW.inputEl.autocomplete = "off";
                apikeyW.inputEl.spellcheck = false;
            }
            preserveNodeSize(node, Array.isArray(node.size) ? [...node.size] : null);
        }
        setInterval(() => {
            const preferredSize = Array.isArray(node.size) ? [...node.size] : null;
            const plat = getPlatformFromSource(node);
            if (plat !== node._lastPlatform || needsPlatformApply(node, plat)) {
                node._lastPlatform = plat;
                applyPlatform(node, plat, preferredSize);
            }

            const hasImg = hasImageConnected(node);
            if (hasImg !== node._lastHasImage) {
                node._lastHasImage = hasImg;
                const ratioW = node.widgets?.find(w => w.name === "ratio");
                if (ratioW && plat !== "Veo") {
                    const target = hasImg ? "auto" : "16:9";
                    if (ratioW.options.values.includes(target) && ratioW.value !== target) {
                        ratioW.value = target;
                        preserveNodeSize(node, preferredSize);
                        app.graph.setDirtyCanvas(true);
                    }
                }
            }
        }, 500);
    },
});


