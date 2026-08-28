# CapCut draft_content.json 整合失敗根因分析

> **專案**: AI 製片工廠 — CapCut 自動化時間軸組裝
> **日期**: 2026-08-20
> **解決耗時**: 約 5 輪迭代失敗後才找到真正根因

---

## 🔴 最終根因 (Root Cause)

**CapCut 的 `draft_content.json` 有一套極嚴格且未公開的 Schema 驗證機制。**

我們從零生成的精簡 JSON（僅包含 `canvas_config`, `materials`, `tracks`, `fps`, `id`, `version` 共 6 個頂層 key）完全無法通過 CapCut 的內部驗證。CapCut 載入專案時，一旦偵測到 Schema 不合格，會**靜默地將整個 `draft_content.json` 覆寫回預設空白骨架**（固定 4,197 bytes），且不會顯示任何錯誤訊息。

### 真實專案的 draft_content.json 需要的頂層 Key（至少 35 個）：

```
canvas_config, color_space, config, cover, create_time, draft_type, duration,
extra_info, fps, free_render_index_mode_on, function_assistant_info,
group_container, id, is_drop_frame_timecode, keyframe_graph_list, keyframes,
last_modified_platform, lyrics_effects, materials, mutable_config,
new_version, platform, relationships, render_index, retouch_cover,
smart_subtitle_info, source_generator, static_cover_image_path, tracks,
update_time, version, ...（以及更多隱藏欄位）
```

### 我們錯誤生成的精簡版只有 6 個 Key：
```
canvas_config, color_space, fps, id, materials, tracks, version
```

---

## 🟡 過程中的錯誤假設（走過的彎路）

### 假設 1：「ID 不對」 ❌
- **症狀**: 寫入後 CapCut 重設為空白
- **誤判**: 以為是 `draft_content.json` 的 `"id"` 欄位與 `draft_meta_info.json` 的 `"draft_id"` 不匹配
- **修復嘗試**: 改為從 `draft_content.json` 讀取現有 ID 並繼承
- **結果**: 仍然被重設 → 因為 ID 只是問題之一，不是根因

## 🎨 分鏡表與視覺資產呈現最佳實踐：HTML 互動式儀表板 (2026-08-21)

* **情境**：純 Markdown 表格或純文字分鏡在面對大量鏡頭（15~30+ Shots）、提示詞過長、音訊時間碼與資產對位時，閱讀與操作體驗極為繁瑣。
* **解法**：全面升級為 **Dark-Mode 互動式 HTML 儀表板 (`storyboard_dashboard.html` / `index.html`)**。
* **必備標準**：
  1. 內建 Master Audio / Stems 邊聽邊看播放器。
  2. 鏡頭焦段（35mm / 85mm）與 3D 運鏡標籤。
  3. 一鍵複製 Prompt 與 Toast 提示。
  4. 即時關鍵字搜尋與運鏡模式篩選。
  5. 主角三視圖（Turnaround Sheet）與分段環境 Keyframe 視覺卡片。
* **管線整合**：由 `scripts/generate_html_dashboard.py` 驅動，並在 `02_concept_and_prompt_engine.py` 完成時自動觸發生成。

### 假設 2：「素材檔案損壞」 ❌
- **症狀**: 依然空白
- **誤判**: 以為是 Mock MP4 檔案（35 bytes 純文字）無法被 CapCut 解析
- **修復嘗試**: 用 FFmpeg 生成真實的空白 MP4 影片覆蓋所有 mock 檔案
- **結果**: 仍然被重設 → 素材格式不是重設的觸發條件

### 假設 3：「Material ID 不匹配」 ❌
- **症狀**: 依然空白
- **誤判**: 以為是 `materials.videos[].id` 與 `tracks[].segments[].material_id` 之間的 UUID 不一致
- **修復嘗試**: 確保兩邊使用相同的 UUID
- **結果**: 仍然被重設 → ID 匹配是必要條件但不是充分條件

---

## 🟢 正確解法 (Final Fix)

### Schema-Clone 策略

**不要從零組裝 JSON，而是複製一個真實可運作的 CapCut 專案的 `draft_content.json` 作為模板（Donor Schema），然後只替換 `materials` 和 `tracks` 兩個區段。**

```python
# 1. 讀取真實專案的 draft_content.json 作為模板
draft = load_json("老陸 - 逆風的火/draft_content.json")  # 501KB, 35+ keys

# 2. 保留目標專案的內部 ID
draft["id"] = existing_project_id

# 3. 只替換素材和軌道
draft["materials"]["audios"] = [our_audio]
draft["materials"]["videos"] = [our_videos]
draft["tracks"] = [our_video_track, our_audio_track]

# 4. 保留所有其他欄位不動（config, keyframes, last_modified_platform, 等）
save_json(target_path, draft)
```

### 關鍵差異

| 項目 | 失敗版 (v1) | 成功版 (v2) |
|------|------------|------------|
| 頂層 Key 數 | 6 個 | 35+ 個 |
| 檔案大小 | 24 KB | 575 KB |
| materials 子陣列 | 只有 `audios` + `videos` | 包含 47 個子類別（含空陣列） |
| Segment 欄位 | 只有 `id`, `material_id`, `target_timerange` | 包含 `clip`, `source_timerange`, `hdr_settings`, `responsive_layout` 等 30+ 欄位 |
| Track 欄位 | 只有 `id`, `type`, `segments` | 包含 `attribute`, `flag`, `is_default_name`, `name` |
| CapCut 驗證 | ❌ 直接重設為空白 | ✅ 成功載入時間軸 |

---

## 📋 給未來開發的 Checklist

1. **永遠不要從零組裝 CapCut 的 draft_content.json** — 必須以真實專案為模板
2. **materials 區段必須包含所有 47 個子類別**（即使是空陣列也必須存在）
3. **每個 Segment 必須包含完整欄位結構**（`clip`, `source_timerange`, `target_timerange`, `hdr_settings`, `responsive_layout`, `uniform_scale` 等）
4. **`last_modified_platform` 欄位必須存在**且包含 `app_id`, `app_source`, `app_version`, `device_id`, `os` 等
5. **先保留目標專案的 `"id"` 欄位**再覆寫（從現有 `draft_content.json` 讀取）
6. **CapCut 的錯誤處理是靜默覆寫**，不會報錯，只會悄悄把檔案重設為空白骨架（4,197 bytes）

---

## 🔧 最終工作腳本

`scripts/06_capcut_assembler_v2.py`

```bash
python scripts/06_capcut_assembler_v2.py \
  --template-dir "<真實CapCut專案資料夾>" \
 ### 2026-08-21: Pro Tools on Windows High DPI (2K/4K 200% Scaling) Rendering Fix
- **Problem**: Pro Tools on Windows 2K/4K high DPI displays can suffer from tiny UI text or black-bordered viewports on the startup Dashboard window when maximized.
- **Root Cause**: `System (Enhanced)` causes Qt/DirectX sub-window coordinate calculation mismatch in the Dashboard modal.
- **Solution**: In `ProTools.exe` Properties -> Compatibility -> "Change high DPI settings", select **`System` (系統)** (not Enhanced). This perfectly scales both the main Mixer/Edit windows and the startup Dashboard without black borders.
  --beats zijin_night/beats_manifest.json \
  --shots zijin_night/shots_manifest.json \
  --renders-dir temp/renders \
  --audio-dir assets/audio \
  --output-dir "<目標CapCut專案資料夾>"
```
