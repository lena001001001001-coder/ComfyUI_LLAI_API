import { app } from "../../scripts/app.js";

const BATCH_TEXT_PLATFORMS = {
    GeminiText: {
        apiFormat: "v1beta/models",
        models: ["gemini-3-flash-preview", "gemini-3.5-flash", "gemini-3.6-flash"],
        supportsImages: true,
        supportsVideo: true,
        supportsAudio: true,
    },
    xAI: {
        apiFormat: "v1/chat/completions",
        models: ["grok-4.5", "grok-4-1-fast-reasoning"],
        imageModels: ["grok-4.5"],
        supportsVideo: false,
        supportsAudio: false,
    },
    OpenAI: {
        apiFormat: "v1/chat/completions",
        models: ["gpt-5.6-sol", "gpt-5-pro", "gpt-4o-mini"],
        supportsImages: true,
        supportsVideo: false,
        supportsAudio: false,
    },
    Anthropic: {
        apiFormat: "v1/chat/completions",
        models: ["claude-fable-5", "claude-opus-4-8", "claude-opus-4-1-20250805"],
        supportsImages: true,
        supportsVideo: false,
        supportsAudio: false,
    },
    "智谱": {
        apiFormat: "v1/chat/completions",
        models: ["glm-5", "glm-4-flash"],
        supportsImages: false,
        supportsVideo: false,
        supportsAudio: false,
    },
    "通义千问": {
        apiFormat: "v1/chat/completions",
        models: ["qwen3.7-max", "qwen3.5-flash", "qwen3-vl-8b-instruct"],
        imageModels: ["qwen3.5-flash", "qwen3-vl-8b-instruct"],
        videoModels: ["qwen3.5-flash", "qwen3-vl-8b-instruct"],
        supportsAudio: false,
    },
    DeepSeek: {
        apiFormat: "v1/chat/completions",
        models: ["deepseek-v4-flash", "deepseek-v3"],
        supportsImages: false,
        supportsVideo: false,
        supportsAudio: false,
    },
    "豆包": {
        apiFormat: "v1/chat/completions",
        models: [
            "doubao-seed-2-1-pro-260628",
            "doubao-seed-2-0-lite-260428",
            "doubao-seed-1-8-251228",
            "doubao-seed-1-6-vision-250815",
        ],
        hiddenModels: ["doubao-seed-2-1-pro-260628"],
        supportsImages: true,
        videoModels: ["doubao-seed-2-0-lite-260428"],
        audioModels: ["doubao-seed-2-0-lite-260428"],
    },
};

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
        if (node.comfyClass === "RelayLLMTextBatch") {
            await new Promise(r => setTimeout(r, 200));

            const platformW = node.widgets?.find(w => w.name === "platform");
            const apiFormatW = node.widgets?.find(w => w.name === "api_format");
            const modelW = node.widgets?.find(w => w.name === "model");
            const apiBaseW = node.widgets?.find(w => w.name === "api_base");

            // Keep these compatibility inputs in the workflow payload while hiding
            // implementation details that are fixed/derived for the batch node.
            if (apiFormatW) hideWidget(apiFormatW);
            if (apiBaseW) hideWidget(apiBaseW);
            const imageInputNames = new Set(Array.from({ length: 8 }, (_, index) => `image${index + 1}`));
            const videoInputNames = new Set(["video"]);
            const audioInputNames = new Set(["audio"]);

            const setInputsEnabled = (inputNames, enabled) => {
                node.inputs?.forEach((input, index) => {
                    if (!inputNames.has(input.name)) return;

                    if (input._llaiOriginalType === undefined) input._llaiOriginalType = input.type;
                    input._llaiDisabled = !enabled;

                    if (enabled) {
                        input.type = input._llaiOriginalType;
                        if (input._llaiOriginalColorOn === undefined) delete input.color_on;
                        else input.color_on = input._llaiOriginalColorOn;
                        if (input._llaiOriginalColorOff === undefined) delete input.color_off;
                        else input.color_off = input._llaiOriginalColorOff;
                    } else {
                        if (input._llaiOriginalColorOn === undefined) input._llaiOriginalColorOn = input.color_on;
                        if (input._llaiOriginalColorOff === undefined) input._llaiOriginalColorOff = input.color_off;
                        if (input.link != null || input._floatingLinks?.size) node.disconnectInput(index);
                        input.type = "LLAI_DISABLED";
                        input.color_on = "#555555";
                        input.color_off = "#555555";
                    }
                });
            };

            const applyInputCapabilities = (config, model) => {
                const supportsImages = config.imageModels
                    ? config.imageModels.includes(model)
                    : config.supportsImages;
                const supportsVideo = config.videoModels
                    ? config.videoModels.includes(model)
                    : config.supportsVideo;
                const supportsAudio = config.audioModels
                    ? config.audioModels.includes(model)
                    : config.supportsAudio;
                setInputsEnabled(imageInputNames, Boolean(supportsImages));
                setInputsEnabled(videoInputNames, Boolean(supportsVideo));
                setInputsEnabled(audioInputNames, Boolean(supportsAudio));
            };

            const originalOnConnectInput = node.onConnectInput;
            node.onConnectInput = function(inputIndex) {
                if (this.inputs?.[inputIndex]?._llaiDisabled) return false;
                return originalOnConnectInput?.apply(this, arguments) ?? true;
            };

            const applyBatchPlatform = (platform) => {
                const selectedPlatform = BATCH_TEXT_PLATFORMS[platform] ? platform : "GeminiText";
                const config = BATCH_TEXT_PLATFORMS[selectedPlatform];
                const visibleModels = config.models.filter(
                    model => !config.hiddenModels?.includes(model)
                );

                if (platformW) platformW.value = selectedPlatform;
                if (apiFormatW) {
                    apiFormatW.options.values = [config.apiFormat];
                    apiFormatW.value = config.apiFormat;
                }
                if (modelW) {
                    modelW.options.values = visibleModels;
                    if (!visibleModels.includes(modelW.value)) modelW.value = visibleModels[0];
                }
                applyInputCapabilities(config, modelW?.value || visibleModels[0]);
                app.graph.setDirtyCanvas(true);
            };

            if (platformW) {
                platformW.options.values = Object.keys(BATCH_TEXT_PLATFORMS);
                const originalPlatformCallback = platformW.callback;
                platformW.callback = function(value) {
                    if (originalPlatformCallback) originalPlatformCallback.call(this, value);
                    applyBatchPlatform(value);
                };
                applyBatchPlatform(platformW.value);
            }

            if (modelW) {
                const originalModelCallback = modelW.callback;
                modelW.callback = function(value) {
                    if (originalModelCallback) originalModelCallback.call(this, value);
                    const config = BATCH_TEXT_PLATFORMS[platformW?.value || "GeminiText"];
                    if (config) applyInputCapabilities(config, value);
                    app.graph.setDirtyCanvas(true);
                };
            }

            if (apiBaseW) {
                apiBaseW.value = "https://api.llaiapi.host";
            }

            const templateW = node.widgets?.find(w => w.name === "prompt_template");
            if (templateW && (!templateW.value || templateW.value === "prompt_template")) {
                templateW.value = "";
                if (templateW.inputEl) templateW.inputEl.placeholder = "You are a assistant...";
            }
            return;
        }

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
