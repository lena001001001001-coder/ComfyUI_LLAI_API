import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "KuAi.Panel",
  async setup() {
    // 鍒嗙被涓枃鏄犲皠
    const categoryNameMap = {
      "ScriptGenerator": "馃摑 鑴氭湰鐢熸垚",
      "Sora2": "馃幀 Sora2 瑙嗛鐢熸垚",
      "Veo3": "馃殌 Veo3.1 瑙嗛鐢熸垚",
      "Grok": "馃崜 Grok 瑙嗛鐢熸垚",
      "Kling": "馃帪锔?鍙伒瑙嗛鐢熸垚",
      "WAN": "馃拵 WAN 瑙嗛鐢熸垚",
      "Gemini": "馃攳 Gemini 鐞嗚В",
      "NanoBanana": "馃崒 Nano Banana 鍥惧儚鐢熸垚",
      "GPTImage": "馃崘 GPT 鍥惧儚鐢熸垚",
      "GrokImage": "馃崘 Grok Image 鍥惧儚鐢熸垚",
      "Utils": "馃洜锔?宸ュ叿鑺傜偣",
      "Product": "馃摑 浜у搧绠＄悊",
      "閰嶅鑳藉姏": "馃洜锔?閰嶅鑳藉姏",
    };

    // 鑷姩鍙戠幇鑺傜偣
    const discoverNodes = () => {
      const categories = {};

      for (const [nodeType, nodeClass] of Object.entries(LiteGraph.registered_node_types)) {
        const category = nodeClass.category;
        if (category && (category.startsWith("馃崘LLAI/") || category.toLowerCase().startsWith("llai/") || category.toLowerCase().startsWith("kuaipower/"))) {
          const categoryName = category.split("/")[1];
          const displayCategory = categoryNameMap[categoryName] || categoryName;

          if (!categories[displayCategory]) {
            categories[displayCategory] = [];
          }

          const displayName = nodeClass.display_name || nodeClass.title || nodeType;

          categories[displayCategory].push({
            name: nodeType,
            display: displayName
          });
        }
      }

      return categories;
    };

    // 闃叉姈鍑芥暟
    const debounce = (func, wait) => {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    };

    // 娉ㄥ唽宸︿晶渚ц竟鏍忔寜閽?    app.extensionManager.registerSidebarTab({
      id: "kuaipower-panel",
      icon: "pi pi-cog",
      title: "LLAI_API 鑺傜偣",
      tooltip: "蹇嵎閿細Ctrl + Shift + K",
      type: "custom",
      render: (el) => {
        // 瀹瑰櫒鏍峰紡
        el.style.cssText = `
          padding: 12px;
          background: linear-gradient(135deg, #1e1e1e 0%, #252525 100%);
          color: #e0e0e0;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
          height: 100%;
          overflow-y: auto;
          box-sizing: border-box;
        `;

        // 鏍囬鏍?        const header = document.createElement("div");
        header.style.cssText = `
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 2px solid #4a9eff;
        `;
        header.innerHTML = `
          <span style="font-size:16px;font-weight:600;color:#fff;text-shadow:0 1px 2px rgba(0,0,0,0.3);">馃敡 LLAI_API</span>
          <button id="kuai-close" style="background:none;border:none;color:#888;cursor:pointer;font-size:20px;transition:color 0.2s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#888'">脳</button>
        `;
        el.appendChild(header);

        // 鎼滅储妗?        const searchContainer = document.createElement("div");
        searchContainer.style.cssText = "margin-bottom:12px;position:relative;";
        searchContainer.innerHTML = `
          <input 
            id="kuai-search" 
            type="text" 
            placeholder="馃攳 鎼滅储鑺傜偣..." 
            style="
              width:100%;
              padding:8px 32px 8px 10px;
              background:#2a2a2a;
              border:1px solid #3e3e3e;
              border-radius:6px;
              color:#e0e0e0;
              font-size:13px;
              box-sizing:border-box;
              transition:border-color 0.2s;
            "
            onfocus="this.style.borderColor='#4a9eff'"
            onblur="this.style.borderColor='#3e3e3e'"
          />
          <span id="kuai-clear" style="
            position:absolute;
            right:8px;
            top:50%;
            transform:translateY(-50%);
            color:#666;
            cursor:pointer;
            font-size:16px;
            display:none;
            transition:color 0.2s;
          " onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#666'">脳</span>
        `;
        el.appendChild(searchContainer);

        const searchInput = searchContainer.querySelector("#kuai-search");
        const clearBtn = searchContainer.querySelector("#kuai-clear");

        // 蹇嵎閿彁绀?        const shortcutNote = document.createElement("div");
        shortcutNote.textContent = "蹇嵎閿細Ctrl + Shift + K";
        shortcutNote.style.cssText = "color:#666;font-size:11px;margin-bottom:10px;text-align:center;";
        el.appendChild(shortcutNote);

        // 鑺傜偣瀹瑰櫒
        const nodesContainer = document.createElement("div");
        nodesContainer.id = "kuai-nodes-container";
        el.appendChild(nodesContainer);

        // 鑷姩鍙戠幇鑺傜偣
        const allNodes = discoverNodes();
        let currentFilter = "";

        // 娓叉煋鑺傜偣鍒楄〃
        const renderNodes = (filter = "") => {
          nodesContainer.innerHTML = "";
          let hasResults = false;

          Object.entries(allNodes).forEach(([category, items]) => {
            const filteredItems = filter
              ? items.filter(item =>
                item.display.toLowerCase().includes(filter.toLowerCase()) ||
                item.name.toLowerCase().includes(filter.toLowerCase())
              )
              : items;

            if (filteredItems.length === 0) return;
            hasResults = true;

            const categoryDiv = document.createElement("div");
            categoryDiv.style.marginBottom = "8px";

            const title = document.createElement("div");
            title.textContent = `${filter ? '鈻? : '鈻?} ${category} (${filteredItems.length})`;
            title.style.cssText = `
              color: #4a9eff;
              font-size: 13px;
              font-weight: 600;
              padding: 8px 10px;
              background: linear-gradient(135deg, #2a2a2a 0%, #323232 100%);
              border-radius: 6px;
              cursor: pointer;
              user-select: none;
              transition: all 0.2s;
              box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            `;
            title.addEventListener("mouseenter", () => {
              title.style.background = "linear-gradient(135deg, #323232 0%, #3a3a3a 100%)";
              title.style.transform = "translateX(2px)";
            });
            title.addEventListener("mouseleave", () => {
              title.style.background = "linear-gradient(135deg, #2a2a2a 0%, #323232 100%)";
              title.style.transform = "translateX(0)";
            });

            const container = document.createElement("div");
            container.className = "items-container";
            container.style.cssText = `
              display: ${filter ? 'block' : 'none'};
              margin-top: 6px;
              padding-left: 4px;
            `;

            filteredItems.forEach(({ name, display }) => {
              const btn = document.createElement("div");
              btn.textContent = display;
              btn.style.cssText = `
                background: linear-gradient(135deg, #252525 0%, #2d2d2d 100%);
                border-left: 3px solid #4a9eff;
                padding: 8px 12px;
                margin-bottom: 4px;
                cursor: pointer;
                color: #e0e0e0;
                font-size: 12px;
                border-radius: 4px;
                transition: all 0.2s;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
              `;
              btn.addEventListener("mouseenter", () => {
                btn.style.background = "linear-gradient(135deg, #2d2d2d 0%, #353535 100%)";
                btn.style.transform = "translateX(4px)";
                btn.style.borderLeftColor = "#5ab0ff";
              });
              btn.addEventListener("mouseleave", () => {
                btn.style.background = "linear-gradient(135deg, #252525 0%, #2d2d2d 100%)";
                btn.style.transform = "translateX(0)";
                btn.style.borderLeftColor = "#4a9eff";
              });
              btn.addEventListener("click", () => {
                const node = LiteGraph.createNode(name);
                if (node) {
                  node.pos = [app.canvas.graph_mouse[0], app.canvas.graph_mouse[1]];
                  app.graph.add(node);
                  app.canvas.selectNode(node);
                  app.graph.setDirtyCanvas(true, true);

                  // 瑙嗚鍙嶉
                  btn.style.background = "#4a9eff";
                  setTimeout(() => {
                    btn.style.background = "linear-gradient(135deg, #252525 0%, #2d2d2d 100%)";
                  }, 200);
                }
              });
              container.appendChild(btn);
            });

            title.addEventListener("click", () => {
              if (!filter) {
                // 鍏抽棴鎵€鏈夊悓绾?                nodesContainer.querySelectorAll(".items-container").forEach(c => {
                  if (c !== container) {
                    c.style.display = "none";
                    const t = c.previousSibling;
                    // 浣跨敤鏇撮€氱敤鐨勬鍒欙紝鍖归厤浠讳綍 emoji 寮€澶寸殑鍒嗙被鍚?                    const catName = t.textContent.match(/^[鈻垛柤]\s*(.+?)\s*\(/)[1].trim();
                    t.textContent = `鈻?${catName} ${t.textContent.match(/\(\d+\)/)[0]}`;
                  }
                });
                // 鍒囨崲褰撳墠
                const isOpen = container.style.display === "block";
                container.style.display = isOpen ? "none" : "block";
                // 浣跨敤鏇撮€氱敤鐨勬鍒欙紝鍖归厤浠讳綍 emoji 寮€澶寸殑鍒嗙被鍚?                const catName = title.textContent.match(/^[鈻垛柤]\s*(.+?)\s*\(/)[1].trim();
                title.textContent = isOpen
                  ? `鈻?${catName} ${title.textContent.match(/\(\d+\)/)[0]}`
                  : `鈻?${catName} ${title.textContent.match(/\(\d+\)/)[0]}`;
              }
            });

            categoryDiv.append(title, container);
            nodesContainer.appendChild(categoryDiv);
          });

          // 鏃犵粨鏋滄彁绀?          if (!hasResults) {
            nodesContainer.innerHTML = `
              <div style="
                text-align:center;
                padding:20px;
                color:#666;
                font-size:13px;
              ">
                馃槙 鏈壘鍒板尮閰嶇殑鑺傜偣
              </div>
            `;
          }
        };

        // 鍒濆娓叉煋
        renderNodes();

        // 鎼滅储鍔熻兘锛堥槻鎶栵級
        const handleSearch = debounce((value) => {
          currentFilter = value;
          clearBtn.style.display = value ? "block" : "none";
          renderNodes(value);
        }, 300);

        searchInput.addEventListener("input", (e) => handleSearch(e.target.value));

        clearBtn.addEventListener("click", () => {
          searchInput.value = "";
          clearBtn.style.display = "none";
          renderNodes("");
        });

        // 鍏抽棴鎸夐挳
        document.getElementById("kuai-close").addEventListener("click", () => {
          const sidebarButton = document.querySelector('[data-id="kuaipower-panel"]');
          if (sidebarButton) {
            sidebarButton.click();
          }
        });
      }
    });

    // 蹇嵎閿垏鎹晶杈规爮 (Ctrl+Shift+K)
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        e.stopPropagation();

        const sidebarButton = document.querySelector('[data-id="kuaipower-panel"]');
        if (sidebarButton) {
          sidebarButton.click();
        }
      }
    });

    console.log("[LLAI_API] 闈㈡澘鎵╁睍宸插姞杞斤紙澧炲己鐗堬級");
  }
});

