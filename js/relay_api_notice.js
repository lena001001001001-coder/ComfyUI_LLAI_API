import { app } from "../../scripts/app.js";

const OUTER_PADDING_X = 24;
const OUTER_PADDING_Y = 8;
const INNER_PADDING_X = 18;
const INNER_PADDING_Y = 14;
const BOX_RADIUS = 12;
const LINE_HEIGHT = 24;
const BOX_TOP_GAP = 8;
const TEXT_FONT = "16px sans-serif";
const LINK_COLOR = "#8ec5ff";
const TEXT_COLOR = "#dddddd";

function wrapText(ctx, text, maxWidth) {
    const chars = Array.from(text || "");
    const lines = [];
    let current = "";

    for (const ch of chars) {
        const next = current + ch;
        if (current && ctx.measureText(next).width > maxWidth) {
            lines.push(current);
            current = ch;
        } else {
            current = next;
        }
    }

    if (current) lines.push(current);
    return lines.length ? lines : [""];
}

function parseNoticeLine(line) {
    const match = String(line || "").match(/^\s*\[([^\]]+)\]\((https?:\/\/[^)]+)\)\s*$/);
    if (match) {
        return {
            text: match[1],
            url: match[2],
        };
    }
    return {
        text: String(line || ""),
        url: "",
    };
}

function getNoticeLines(node) {
    const message = String(node._noticeMessage || "").replace(/\r\n/g, "\n");
    return message ? message.split("\n") : [""];
}

function getWrappedLines(ctx, node, width) {
    const textWidth = Math.max(40, width - OUTER_PADDING_X * 2 - INNER_PADDING_X * 2);
    return getNoticeLines(node).flatMap((line) => {
        const parsed = parseNoticeLine(line);
        return wrapText(ctx, parsed.text, textWidth).map((text) => ({
            text,
            url: parsed.url,
        }));
    });
}

function openNoticeLink(url) {
    if (!url) return;
    window.open(url, "_blank", "noopener,noreferrer");
}

app.registerExtension({
    name: "RelayAPI.Notice",

    async nodeCreated(node) {
        if (node.comfyClass !== "RelayAPINotice") return;

        node.resizable = true;
        if (!Array.isArray(node.size) || node.size.length < 2) {
            node.size = [360, 180];
        }

        const messageWidgetIndex = (node.widgets || []).findIndex((widget) => widget.name === "message");
        if (messageWidgetIndex >= 0) {
            const messageWidget = node.widgets[messageWidgetIndex];
            node._noticeMessage = String(messageWidget.value || "");
            if (messageWidget.inputEl) {
                messageWidget.inputEl.style.display = "none";
                messageWidget.inputEl.style.visibility = "hidden";
                messageWidget.inputEl.style.pointerEvents = "none";
                messageWidget.inputEl.tabIndex = -1;
            }
            node.widgets.splice(messageWidgetIndex, 1);
        }

        node._noticeHitRegions = [];

        const originalOnMouseDown = node.onMouseDown?.bind(node);
        node.onMouseDown = function (event, pos, graphCanvas) {
            const [x, y] = pos || [];
            const hit = (this._noticeHitRegions || []).find((region) => (
                x >= region.x
                && x <= region.x + region.width
                && y >= region.y
                && y <= region.y + region.height
            ));

            if (hit?.url) {
                event?.preventDefault?.();
                event?.stopPropagation?.();
                openNoticeLink(hit.url);
                return true;
            }

            return originalOnMouseDown ? originalOnMouseDown(event, pos, graphCanvas) : false;
        };

        const originalOnMouseMove = node.onMouseMove?.bind(node);
        node.onMouseMove = function (event, pos, graphCanvas) {
            const [x, y] = pos || [];
            const hit = (this._noticeHitRegions || []).some((region) => (
                x >= region.x
                && x <= region.x + region.width
                && y >= region.y
                && y <= region.y + region.height
            ));
            if (graphCanvas?.canvas?.style) {
                graphCanvas.canvas.style.cursor = hit ? "pointer" : "";
            }
            return originalOnMouseMove ? originalOnMouseMove(event, pos, graphCanvas) : false;
        };

        const originalOnResize = node.onResize?.bind(node);
        node.onResize = function (size) {
            if (originalOnResize) originalOnResize(size);
            app.graph.setDirtyCanvas(true);
        };

        const originalDrawForeground = node.onDrawForeground?.bind(node);
        node.onDrawForeground = function (ctx) {
            if (originalDrawForeground) {
                originalDrawForeground(ctx);
            }

            if (this.flags?.collapsed) {
                return;
            }

            const width = this.size?.[0] || 360;
            const height = this.size?.[1] || 180;
            const boxX = OUTER_PADDING_X;
            const boxY = BOX_TOP_GAP;
            const boxWidth = Math.max(120, width - OUTER_PADDING_X * 2);
            const textX = boxX + INNER_PADDING_X;
            const textY = boxY + INNER_PADDING_Y;

            ctx.save();
            ctx.beginPath();
            ctx.rect(0, 0, width, height);
            ctx.clip();

            ctx.font = TEXT_FONT;
            ctx.textAlign = "left";
            ctx.textBaseline = "top";

            const lines = getWrappedLines(ctx, this, width);
            const boxHeight = INNER_PADDING_Y * 2 + lines.length * LINE_HEIGHT + OUTER_PADDING_Y;
            this._noticeHitRegions = [];

            ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
            ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(boxX, boxY, boxWidth, boxHeight, BOX_RADIUS);
            ctx.fill();
            ctx.stroke();

            lines.forEach((line, index) => {
                const y = textY + index * LINE_HEIGHT;
                ctx.fillStyle = line.url ? LINK_COLOR : TEXT_COLOR;
                ctx.fillText(line.text, textX, y);

                if (line.url) {
                    const metrics = ctx.measureText(line.text);
                    const linkWidth = metrics.width;
                    ctx.strokeStyle = LINK_COLOR;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(textX, y + LINE_HEIGHT - 4);
                    ctx.lineTo(textX + linkWidth, y + LINE_HEIGHT - 4);
                    ctx.stroke();
                    this._noticeHitRegions.push({
                        x: textX,
                        y,
                        width: linkWidth,
                        height: LINE_HEIGHT,
                        url: line.url,
                    });
                }
            });

            ctx.restore();
        };

        app.graph.setDirtyCanvas(true);
    },
});
