import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const TASK_PLATFORMS = {
    image: ["banana-pro", "banana-2", "gpt-image2"],
    video: ["Grok", "Veo"],
    sound: ["Suno"],
    text: ["GeminiText", "OpenaiText"],
};

const TASK_API_FORMATS = {
    image: ["runninghub-/openapi/v2", "v1beta/models", "v1/images", "v1/chat/completions"],
    video: ["runninghub-/openapi/v2", "v1/video", "v1/videos", "v2/videos"],
    sound: ["runninghub-/openapi/v2", "suno/submit"],
    text: ["runninghub-/v1", "v1beta/models", "v1/chat/completions"],
};

const PLATFORM_API_FORMATS = {
    "gpt-image2": ["runninghub-/openapi/v2", "v1/images"],
    "banana-2": ["runninghub-/openapi/v2", "v1beta/models", "v1/chat/completions"],
    "Veo": ["runninghub-/openapi/v2", "v1/video", "v1/videos", "v2/videos"],
    "OpenaiText": ["runninghub-/v1", "v1/chat/completions"],
};

app.registerExtension({
    name: "RelayAPI.Settings",

    async nodeCreated(node) {
        if (node.comfyClass !== "RelayAPISettings") return;

        await new Promise(r => setTimeout(r, 100));

        const w = {};
        for (const widget of node.widgets) {
            w[widget.name] = widget;
        }

        const { task_type, platform, api_format, api_base, model, custom_api_base, custom_model, apikey } = w;
        if (!task_type || !platform || !api_base || !model) return;

        if (apikey && apikey.inputEl) {
            apikey.inputEl.type = "text";
            apikey.inputEl.autocomplete = "off";
            apikey.inputEl.spellcheck = false;
        }

        for (const widget of [api_base, custom_api_base, custom_model]) {
            if (!widget) continue;
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

        // api_format uses endpoint path names. The task/platform decides which endpoints are selectable.
        function applyApiFormats(tt, plat) {
            const formats = PLATFORM_API_FORMATS[plat] || TASK_API_FORMATS[tt] || [];

            if (api_format && formats.length > 0) {
                api_format.options.values = formats;
                if (!formats.includes(api_format.value)) api_format.value = formats[0];
            }
        }

        function applyTaskType(tt) {
            const platforms = TASK_PLATFORMS[tt] || [];

            if (platform && platforms.length > 0) {
                platform.options.values = platforms;
                if (!platforms.includes(platform.value)) platform.value = platforms[0];
            }

            const plat = platform.value || platforms[0] || "Grok";
            applyApiFormats(tt, plat);
            refreshModels(plat, api_format ? api_format.value : "");
            app.graph.setDirtyCanvas(true);
        }

        // api_base 动态管理
        async function refreshBases() {
            try {
                const resp = await api.fetchApi("/relayapi/api_bases");
                if (!resp.ok) return;
                const list = await resp.json();
                if (Array.isArray(list) && list.length > 0) {
                    api_base.options.values = list;
                    if (!list.includes(api_base.value)) api_base.value = list[0];
                    refreshModels(platform.value || "Grok", api_format ? api_format.value : "");
                    app.graph.setDirtyCanvas(true);
                }
            } catch (e) { console.warn("[RelayAPI]", e); }
        }

        async function handleBaseInput(raw) {
            raw = (raw || "").trim();
            if (!raw) return;
            const del = "delete:";
            if (raw.toLowerCase().startsWith(del)) {
                const target = raw.substring(del.length).trim().replace(/\/+$/, "");
                if (!target) return;
                try {
                    const resp = await api.fetchApi("/relayapi/api_bases/remove", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ url: target }),
                    });
                    if (!resp.ok) return;
                    const r = await resp.json();
                    if (r.success && Array.isArray(r.list)) {
                        api_base.options.values = r.list;
                        if (!r.list.includes(api_base.value)) api_base.value = r.list[0];
                        if (custom_api_base) custom_api_base.value = "";
                        refreshModels(platform.value || "Grok", api_format ? api_format.value : "");
                        app.graph.setDirtyCanvas(true);
                    }
                } catch (e) { console.warn("[RelayAPI]", e); }
                return;
            }
            const url = raw.replace(/\/+$/, "");
            try {
                const resp = await api.fetchApi("/relayapi/api_bases/add", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url }),
                });
                if (!resp.ok) return;
                const r = await resp.json();
                if (r.success && Array.isArray(r.list)) {
                    api_base.options.values = r.list;
                    api_base.value = url;
                    if (custom_api_base) custom_api_base.value = "";
                    refreshModels(platform.value || "Grok", api_format ? api_format.value : "");
                    app.graph.setDirtyCanvas(true);
                }
            } catch (e) { console.warn("[RelayAPI]", e); }
        }

        // model 动态管理
        async function refreshModels(plat, fmt) {
            const f = fmt || (api_format ? api_format.value : "");
            try {
                let url = `/relayapi/models?platform=${encodeURIComponent(plat)}`;
                if (f) url += `&api_format=${encodeURIComponent(f)}`;
                const resp = await api.fetchApi(url);
                if (!resp.ok) return;
                const list = await resp.json();
                if (Array.isArray(list) && list.length > 0) {
                    model.options.values = list;
                    if (!list.includes(model.value)) model.value = list[0];
                    app.graph.setDirtyCanvas(true);
                }
            } catch (e) { console.warn("[RelayAPI]", e); }
        }

        async function handleModelInput(raw) {
            raw = (raw || "").trim();
            if (!raw) return;
            const plat = platform.value || "Grok";
            const del = "delete:";
            if (raw.toLowerCase().startsWith(del)) {
                const target = raw.substring(del.length).trim();
                if (!target) return;
                try {
                    const resp = await api.fetchApi("/relayapi/models/remove", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ platform: plat, model: target }),
                    });
                    if (!resp.ok) return;
                    const r = await resp.json();
                    if (r.success && Array.isArray(r.list)) {
                        model.options.values = r.list;
                        if (!r.list.includes(model.value)) model.value = r.list[0];
                        if (custom_model) custom_model.value = "";
                        app.graph.setDirtyCanvas(true);
                    }
                } catch (e) { console.warn("[RelayAPI]", e); }
                return;
            }
            try {
                const resp = await api.fetchApi("/relayapi/models/add", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ platform: plat, model: raw }),
                });
                if (!resp.ok) return;
                const r = await resp.json();
                if (r.success && Array.isArray(r.list)) {
                    model.options.values = r.list;
                    model.value = raw;
                    if (custom_model) custom_model.value = "";
                    app.graph.setDirtyCanvas(true);
                }
            } catch (e) { console.warn("[RelayAPI]", e); }
        }

        // 初始化
        await refreshBases();
        applyTaskType(task_type.value || "video");

        const origTaskTypeCb = task_type.callback;
        task_type.callback = function (value) {
            if (origTaskTypeCb) origTaskTypeCb.call(this, value);
            applyTaskType(value);
        };

        const origPlatformCb = platform.callback;
        platform.callback = function (value) {
            if (origPlatformCb) origPlatformCb.call(this, value);
            applyApiFormats(task_type.value || "video", value);
            refreshModels(value, api_format ? api_format.value : "");
        };

        const origApiBaseCb = api_base.callback;
        api_base.callback = function (value) {
            if (origApiBaseCb) origApiBaseCb.call(this, value);
            refreshModels(platform.value || "Grok", api_format ? api_format.value : "");
        };

        const RH_TEXT_BASE = "https://llm.runninghub.ai";
        const RH_MEDIA_BASE = "https://www.runninghub.cn";

        function autoSwitchBaseForFormat(fmt) {
            if (!api_base) return;
            const bases = api_base.options.values || [];
            if (fmt === "runninghub-/v1") {
                if (bases.includes(RH_TEXT_BASE)) {
                    api_base.value = RH_TEXT_BASE;
                }
            } else if (fmt === "runninghub-/openapi/v2") {
                if (bases.includes(RH_MEDIA_BASE)) {
                    api_base.value = RH_MEDIA_BASE;
                }
            }
        }

        if (api_format) {
            const origFormatCb = api_format.callback;
            api_format.callback = function (value) {
                if (origFormatCb) origFormatCb.call(this, value);
                autoSwitchBaseForFormat(value);
                refreshModels(platform.value, value);
            };
        }

        if (custom_api_base) {
            const origCb = custom_api_base.callback;
            custom_api_base.callback = function (value) {
                if (origCb) origCb.call(this, value);
                handleBaseInput(value);
            };
            const el = custom_api_base.inputEl;
            if (el) {
                el.addEventListener("change", () => handleBaseInput(el.value));
                el.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") { e.preventDefault(); handleBaseInput(el.value); }
                });
            }
        }

        if (custom_model) {
            const origCb = custom_model.callback;
            custom_model.callback = function (value) {
                if (origCb) origCb.call(this, value);
                handleModelInput(value);
            };
            const el = custom_model.inputEl;
            if (el) {
                el.addEventListener("change", () => handleModelInput(el.value));
                el.addEventListener("keydown", (e) => {
                    if (e.key === "Enter") { e.preventDefault(); handleModelInput(el.value); }
                });
            }
        }
    },
});
