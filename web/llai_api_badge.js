import { app } from "../../scripts/app.js";

const OLD_BADGE_TEXT = "KuAi_Power";
const NEW_BADGE_TEXT = "LLAI_API";

function replaceBadgeText(value) {
  if (typeof value !== "string") {
    return value;
  }

  return value
    .replaceAll("ComfyUI_LLAI_API-main", NEW_BADGE_TEXT)
    .replaceAll("ComfyUI_LLAI_API", NEW_BADGE_TEXT)
    .replaceAll(OLD_BADGE_TEXT, NEW_BADGE_TEXT);
}

function patchCanvasText() {
  if (CanvasRenderingContext2D.prototype.__llaiApiBadgePatched) {
    return;
  }

  const originalFillText = CanvasRenderingContext2D.prototype.fillText;
  const originalStrokeText = CanvasRenderingContext2D.prototype.strokeText;
  const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;

  CanvasRenderingContext2D.prototype.fillText = function (text, ...args) {
    return originalFillText.call(this, replaceBadgeText(text), ...args);
  };

  CanvasRenderingContext2D.prototype.strokeText = function (text, ...args) {
    return originalStrokeText.call(this, replaceBadgeText(text), ...args);
  };

  CanvasRenderingContext2D.prototype.measureText = function (text) {
    return originalMeasureText.call(this, replaceBadgeText(text));
  };

  CanvasRenderingContext2D.prototype.__llaiApiBadgePatched = true;
}

app.registerExtension({
  name: "LLAI_API.Badge",

  async setup() {
    patchCanvasText();
  },

  async beforeRegisterNodeDef(_nodeType, nodeData) {
    if (!nodeData) {
      return;
    }

    nodeData.python_module = replaceBadgeText(nodeData.python_module);
    nodeData.pythonModule = replaceBadgeText(nodeData.pythonModule);
    nodeData.category = replaceBadgeText(nodeData.category);
  },
});
