#!/usr/bin/env python3
"""
generate_mixing_html.py
Generates the definitive dark-mode studio mixing console HTML dashboard
tailored 100% to the user's Pro Tools AAX plugins and the two-phase AI stem restoration & mastering pipeline.
"""

import json
import os
from pathlib import Path

def generate_mixing_html(stem_dir_str: str, song_title: str = "MIDNIGHT GLITCH"):
    stem_dir = Path(stem_dir_str)
    analysis_file = stem_dir / "stem_analysis.json"

    if not analysis_file.exists():
        print(f"❌ Analysis file not found: {analysis_file}")
        return None

    with open(analysis_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Color tokens for frequency bands
    band_colors = {
        "Sub (20-60Hz)": "#ff2a6d",
        "Low (60-250Hz)": "#ff9e00",
        "Low-Mid (250-500Hz)": "#ffd166",
        "Mid (500-2000Hz)": "#05d9e8",
        "Presence (2000-6000Hz)": "#9d4edd",
        "Air (6000-20000Hz)": "#00f5d4"
    }

    # Fader recommendations based on stem analysis & user plugin arsenal
    fader_presets = {
        "0 Lead Vocals": {"fader": "0.0 dB", "pan": "Center", "role": "主唱核心", "chain": "Ozone 11 EQ ➔ MC77 (1176) ➔ BF-2A (LA-2A)"},
        "1 Backing Vocals": {"fader": "-6.0 dB", "pan": "45L / 45R", "role": "和聲包覆", "chain": "EQ3 7-Band ➔ BF-76 ➔ ValhallaVintageVerb"},
        "2 Drums": {"fader": "-2.5 dB", "pan": "Center", "role": "節奏骨架", "chain": "Ozone 11 EQ ➔ Pultec EQP-1A (60Hz 雙推)"},
        "3 Bass": {"fader": "-3.0 dB", "pan": "Center", "role": "808 地鳴", "chain": "Ozone 11 EQ (70Hz 挖槽) ➔ Ozone 11 Vintage Tape (保全尾巴)"},
        "4 Keyboard": {"fader": "-12.0 dB", "pan": "30L / 30R", "role": "環境氛圍", "chain": "EQ3 7-Band ➔ AIR StereoWidth ➔ Valhalla"},
        "5 Percussion": {"fader": "-7.5 dB", "pan": "Center", "role": "Drill Hi-Hats", "chain": "Ozone 11 Vintage Tape ➔ Spectral Shaper"},
        "6 Synth": {"fader": "-6.5 dB", "pan": "25L / 25R", "role": "旋律 Hook", "chain": "Ozone 11 EQ ➔ Ozone Exciter ➔ ModDelay_III"},
        "7 Other": {"fader": "-10.0 dB", "pan": "Center", "role": "FX / Risers", "chain": "EQ3 7-Band (HPF 120Hz 釋放低頻) ➔ DVerb"},
        "8 Brass": {"fader": "MUTE", "pan": "MUTE", "role": "靜音空軌", "chain": "Direct Mute (底噪封印)"}
    }

    # Build Stem cards
    stem_cards_html = ""
    for stem_name, info in data.items():
        peak = info.get("peak_dbfs", 0.0)
        rms = info.get("rms_dbfs", 0.0)
        crest = info.get("crest_factor_db", 0.0)
        freqs = info.get("freq_distribution_percentage", {})
        corr = info.get("stereo_correlation", 1.0)

        is_silent = rms < -60.0 or peak < -45.0
        key_stem = stem_name.replace(".mp3", "").replace(".wav", "")
        fader_info = fader_presets.get(key_stem, {"fader": "-6.0 dB", "pan": "Center", "role": "音軌", "chain": "Ozone 11 EQ"})

        if is_silent:
            crest_badge = '<span class="badge" style="background:rgba(255,255,255,0.06); color:var(--text-dim); border:1px solid var(--border-line);">🔇 靜音軌 (建議 Mute)</span>'
            freq_section_html = """
            <div class="freq-section" style="background:rgba(0,0,0,0.4); text-align:center; padding:16px 12px;">
              <div style="color:var(--text-dim); font-size:12px; font-weight:700; margin-bottom:3px;">🔇 無實質訊號 (RMS < -60 dBFS)</div>
              <div style="color:var(--text-muted); font-size:11px; line-height:1.4;">
                此軌為 AI 拆軌底噪，在 Pro Tools 中<strong>直接點 M 靜音或刪除</strong>，避免底噪污染並節省系統資源。
              </div>
            </div>
            """
            meter_fader_val = '<span class="meter-val" style="color:var(--text-dim);">MUTE</span>'
        else:
            crest_badge = f'<span class="badge badge-good">動態適中 {crest}dB</span>'
            if crest > 32:
                crest_badge = f'<span class="badge badge-danger">⚠️ 尖銳突波 {crest}dB (Tape 柔化中)</span>'
            elif crest < 12:
                crest_badge = f'<span class="badge badge-warn">過度壓縮 {crest}dB</span>'

            freq_bars = ""
            for b_name, b_pct in freqs.items():
                color = band_colors.get(b_name, "#05d9e8")
                freq_bars += f"""
                <div class="freq-row">
                  <div class="freq-label">
                    <span style="color:{color}; font-weight:700;">●</span> {b_name}
                    <span class="freq-pct">{b_pct}%</span>
                  </div>
                  <div class="freq-track">
                    <div class="freq-fill" style="width: {min(b_pct * 1.5, 100)}%; background: {color};"></div>
                  </div>
                </div>
                """

            freq_section_html = f"""
            <div class="freq-section">
              <div class="freq-header">頻譜能量分佈 (FFT Spectrum Distribution)</div>
              {freq_bars}
            </div>
            """
            meter_fader_val = f'<span class="meter-val val-cyan">{fader_info["fader"]}</span>'

        stem_cards_html += f"""
        <div class="stem-card" style="{'opacity:0.6;' if is_silent else ''}">
          <div class="stem-header">
            <div class="stem-title-wrap">
              <span class="role-tag" style="{'color:var(--text-dim); background:rgba(255,255,255,0.05);' if is_silent else ''}">{fader_info['role']}</span>
              <h3 class="stem-title">{stem_name}</h3>
            </div>
            {crest_badge}
          </div>

          <!-- Plugin Chain Pill -->
          <div style="background:rgba(255,42,109,0.08); border:1px solid rgba(255,42,109,0.25); border-radius:8px; padding:6px 10px; margin-bottom:12px; font-size:11px; font-family:var(--font-mono); color:#f3f6fa;">
            ⚡ <strong>專屬插件鏈：</strong><span style="color:var(--neon-cyan);">{fader_info['chain']}</span>
          </div>

          <!-- Meters Grid -->
          <div class="meters-grid">
            <div class="meter-box">
              <span class="meter-lbl">Peak 峰值</span>
              <span class="meter-val {'val-danger' if peak > -1.0 else ('val-good' if not is_silent else '')}">{peak} dBFS</span>
            </div>
            <div class="meter-box">
              <span class="meter-lbl">RMS 能量</span>
              <span class="meter-val">{rms} dBFS</span>
            </div>
            <div class="meter-box">
              <span class="meter-lbl">推薦 Fader</span>
              {meter_fader_val}
            </div>
            <div class="meter-box">
              <span class="meter-lbl">相位 Pan</span>
              <span class="meter-val">{fader_info['pan']}</span>
            </div>
          </div>

          <!-- Frequency Breakdown -->
          {freq_section_html}
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{song_title} - 頂級實戰混音與母帶指南 (Pro Tools Custom Pipeline)</title>
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@latest"></script>
  <style>
    :root {{
      --bg-dark: #07090e;
      --bg-card: rgba(16, 22, 34, 0.88);
      --bg-card-hover: rgba(24, 32, 50, 0.95);
      --border-line: rgba(255, 255, 255, 0.08);
      --border-glow: rgba(255, 42, 109, 0.35);

      --neon-pink: #ff2a6d;
      --neon-cyan: #05d9e8;
      --neon-purple: #9d4edd;
      --neon-gold: #ffbe0b;
      --neon-green: #00f5d4;

      --text-main: #f3f6fa;
      --text-muted: #8b9bb4;
      --text-dim: #50607a;

      --font-ui: 'Outfit', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-ui);
      min-height: 100vh;
      background-image: 
        radial-gradient(circle at 10% 15%, rgba(255, 42, 109, 0.1) 0%, transparent 40%),
        radial-gradient(circle at 90% 85%, rgba(5, 217, 232, 0.09) 0%, transparent 40%),
        linear-gradient(to bottom, #07090e, #0a0e17);
      background-attachment: fixed;
      padding: 36px 20px 80px 20px;
    }}

    .container {{ max-width: 1440px; margin: 0 auto; }}

    /* Header */
    .header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 20px;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--border-line);
      margin-bottom: 32px;
    }}

    .studio-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, var(--neon-pink), var(--neon-purple));
      color: #fff;
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}

    .title {{
      font-size: 34px;
      font-weight: 900;
      letter-spacing: 1px;
      background: linear-gradient(90deg, #fff, #ff2a6d 45%, #05d9e8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}

    .subtitle {{
      color: var(--text-muted);
      font-size: 14px;
      margin-top: 4px;
    }}

    /* Arsenal Banner */
    .arsenal-banner {{
      background: linear-gradient(135deg, rgba(5, 217, 232, 0.1), rgba(157, 78, 221, 0.15));
      border: 1px solid rgba(5, 217, 232, 0.3);
      border-radius: 14px;
      padding: 16px 22px;
      margin-bottom: 32px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }}

    .arsenal-title {{
      font-size: 14px;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .arsenal-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .arsenal-tag {{
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--neon-cyan);
    }}

    /* Section Title */
    .section-title {{
      font-size: 22px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    /* Step Cards */
    .steps-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 22px;
      margin-bottom: 44px;
    }}

    .step-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-line);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(14px);
      position: relative;
      transition: all 0.2s ease;
    }}

    .step-card:hover {{
      border-color: var(--border-glow);
      transform: translateY(-2px);
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5);
    }}

    .step-badge-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}

    .step-number {{
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 800;
      color: var(--neon-pink);
      background: rgba(255, 42, 109, 0.12);
      border: 1px solid rgba(255, 42, 109, 0.35);
      padding: 3px 8px;
      border-radius: 6px;
    }}

    .step-target {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-dim);
    }}

    .step-title {{
      font-size: 17px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 14px;
    }}

    .plugin-action-box {{
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--border-line);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 12px;
    }}

    .plugin-name {{
      font-size: 13px;
      font-weight: 700;
      color: var(--neon-cyan);
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 6px;
    }}

    .plugin-knobs {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: #d1d5db;
      line-height: 1.6;
    }}

    .plugin-knobs strong {{
      color: var(--neon-gold);
    }}

    /* Stems Grid */
    .stems-container {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
      gap: 20px;
    }}

    .stem-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-line);
      border-radius: 16px;
      padding: 22px;
      backdrop-filter: blur(14px);
      transition: all 0.2s ease;
    }}

    .stem-card:hover {{
      border-color: rgba(5, 217, 232, 0.4);
      background: var(--bg-card-hover);
    }}

    .stem-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }}

    .role-tag {{
      display: inline-block;
      font-size: 10px;
      font-family: var(--font-mono);
      text-transform: uppercase;
      font-weight: 700;
      color: var(--neon-cyan);
      background: rgba(5, 217, 232, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 4px;
    }}

    .stem-title {{
      font-size: 16px;
      font-weight: 800;
      color: #fff;
    }}

    .badge {{
      font-size: 11px;
      font-family: var(--font-mono);
      font-weight: 700;
      padding: 4px 8px;
      border-radius: 6px;
      white-space: nowrap;
    }}

    .badge-good {{ background: rgba(0, 245, 212, 0.15); color: var(--neon-green); border: 1px solid rgba(0, 245, 212, 0.3); }}
    .badge-danger {{ background: rgba(255, 42, 109, 0.15); color: var(--neon-pink); border: 1px solid rgba(255, 42, 109, 0.4); }}
    .badge-warn {{ background: rgba(255, 190, 11, 0.15); color: var(--neon-gold); border: 1px solid rgba(255, 190, 11, 0.4); }}

    /* Meters Grid */
    .meters-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--border-line);
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 16px;
    }}

    .meter-box {{ display: flex; flex-direction: column; gap: 2px; }}
    .meter-lbl {{ font-size: 10px; text-transform: uppercase; font-family: var(--font-mono); color: var(--text-dim); font-weight: 600; }}
    .meter-val {{ font-size: 13px; font-family: var(--font-mono); font-weight: 700; color: #fff; }}
    .val-good {{ color: var(--neon-green); }}
    .val-danger {{ color: var(--neon-pink); }}
    .val-cyan {{ color: var(--neon-cyan); }}

    /* Frequency rows */
    .freq-section {{
      background: rgba(0, 0, 0, 0.25);
      border-radius: 10px;
      padding: 12px 14px;
      border: 1px solid var(--border-line);
    }}

    .freq-header {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-bottom: 10px;
    }}

    .freq-row {{ margin-bottom: 7px; }}
    .freq-row:last-child {{ margin-bottom: 0; }}
    .freq-label {{ display: flex; justify-content: space-between; font-size: 11px; font-family: var(--font-mono); color: #c9d1d9; margin-bottom: 2px; }}
    .freq-pct {{ font-weight: 700; color: #fff; }}
    .freq-track {{ width: 100%; height: 5px; background: rgba(255, 255, 255, 0.06); border-radius: 10px; overflow: hidden; }}
    .freq-fill {{ height: 100%; border-radius: 10px; transition: width 0.3s ease; }}
  </style>
</head>
<body>

  <div class="container">
    <!-- Header -->
    <header class="header">
      <div>
        <div class="studio-badge">
          <i data-lucide="sliders" style="width:12px; height:12px;"></i>
          Pro Tools Custom Mixing Suite
        </div>
        <h1 class="title">{song_title}</h1>
        <p class="subtitle">Custom-Tailored for Pro Tools AAX: Ozone 11 Suite, Pultec EQP-1A, MC77, BF-2A & Valhalla</p>
      </div>

      <button onclick="window.print()" style="background:var(--bg-card); border:1px solid var(--border-line); color:#fff; padding:10px 18px; border-radius:10px; font-weight:700; cursor:pointer; display:flex; align-items:center; gap:8px;">
        <i data-lucide="printer" style="width:14px; height:14px;"></i> 列印 / 導出 PDF
      </button>
    </header>

    <!-- Pro Tools Session Layout Banner -->
    <div style="background:rgba(16, 22, 34, 0.95); border:1px solid rgba(5, 217, 232, 0.3); border-radius:14px; padding:18px 22px; margin-bottom:32px; box-shadow:0 8px 25px rgba(0,0,0,0.4);">
      <div style="font-size:15px; font-weight:800; color:#fff; display:flex; align-items:center; gap:8px; margin-bottom:12px;">
        <i data-lucide="layout-grid" style="color:var(--neon-cyan);"></i>
        創作者專屬 Pro Tools 工程架構 (Session Template Architecture)
      </div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:14px; font-family:var(--font-mono); font-size:12px;">
        <div style="background:rgba(0,0,0,0.5); padding:12px; border-radius:8px; border-left:3px solid var(--neon-pink);">
          <strong style="color:var(--neon-pink);">📁 VOCAL 組 (vocal)</strong><br>
          • 0LedVcls.1 ➔ Ozone 11 EQ + MC77 + BF-2A<br>
          • Send ➔ VOCAL KEY (側鏈 0dB)<br>
          • Send ➔ VOCAL_WID (-18.5dB 加寬)<br>
          • Send ➔ VOCAL_VE (-16.5dB 閃避殘響)<br>
          • Send ➔ vc satur (-20.6dB Lo-Fi 染色)<br>
          • 1BckngVc1 ➔ Pan 45L/45R + Send to Verb
        </div>
        <div style="background:rgba(0,0,0,0.5); padding:12px; border-radius:8px; border-left:3px solid var(--neon-cyan);">
          <strong style="color:var(--neon-cyan);">📁 GROOVE 組 (groove)</strong><br>
          • 2 Drums.1 ➔ Ozone 11 EQ + Pultec 60Hz 雙推<br>
          • Send ➔ DRUM_CR (-16dB MC77 極限紐約壓縮)<br>
          • 3 Bass.1 ➔ 70Hz 挖槽 + Vintage Tape 15ips<br>
          • sc bass ➔ Sidechain 專用軌
        </div>
        <div style="background:rgba(0,0,0,0.5); padding:12px; border-radius:8px; border-left:3px solid var(--neon-gold);">
          <strong style="color:var(--neon-gold);">📁 MELODY 組 (melody)</strong><br>
          • 4Keybrd.1 ➔ Pan 30L/30R<br>
          • 5Percusn.1 ➔ Tape + Spectral Shaper (8k-20k)<br>
          • 6 Synth ➔ Pan 25L/25R<br>
          • 7 Other ➔ HPF 120Hz | 8 Brass ➔ MUTE
        </div>
      </div>
    </div>

    <!-- Phase 1: Stem Surgery -->
    <h2 class="section-title">
      <i data-lucide="scissors" style="color:var(--neon-cyan);"></i>
      第一階段：分軌手術工序 (Stem Surgery & Track Balancing)
    </h2>

    <div class="steps-grid">

      <!-- Step 00 -->
      <div class="step-card" style="border-color:rgba(5, 217, 232, 0.4); background:rgba(16, 22, 34, 0.95);">
        <div class="step-badge-row">
          <span class="step-number" style="background:rgba(5, 217, 232, 0.15); color:var(--neon-cyan); border-color:var(--neon-cyan);">STAGE 00</span>
          <span class="step-target" style="color:var(--neon-cyan); font-weight:800;">📍 導入音軌後之標準初始化 3 部曲</span>
        </div>
        <h3 class="step-title">0. 專案工程整理與 Aux 建立 (Post-Import Setup)</h3>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="list-ordered"></i> ① 原始音軌 1~9 順序整理</div>
          <div class="plugin-knobs" style="font-size:11px; line-height:1.6;">
            剛拖入 Stems 時先排好 9 條原軌：<strong>0 Lead Vocals</strong> ➔ <strong>1 Backing Vocals</strong> ➔ <strong>2 Drums</strong> ➔ <strong>3 Bass</strong> ➔ <strong>4 Keyboard</strong> ➔ <strong>5 Percussion</strong> ➔ <strong>6 Synth</strong> ➔ <strong>7 Other</strong> ➔ <strong>8 Brass (點 Mute)</strong>
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="plus-circle"></i> ② 新建 Aux 軌道與 VCA (<kbd>Ctrl+Shift+N</kbd>)</div>
          <div class="plugin-knobs" style="font-size:11px; line-height:1.6;">
            • <strong>人聲區</strong>：新建 4 條 Stereo Aux (<code>VOCAL KEY</code>, <code>VOCAL_WID</code>, <code>VOCAL_VE</code>, <code>vc satur</code>) + 1 條 VCA (<code>vocal</code>)<br>
            • <strong>節奏區</strong>：新建 2 條 Stereo Aux (<code>DRUM_CR</code>, <code>sc bass</code>) + 1 條 VCA (<code>groove</code>)<br>
            • <strong>旋律區</strong>：新建 1 條 VCA (<code>melody</code>)
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="layout-grid"></i> ③ 拖曳歸位成 1~18 軌全功能戰鬥陣列</div>
          <div class="plugin-knobs" style="font-size:11px; line-height:1.6;">
            將 Aux 與 VCA 拖至對應音軌旁，形成 <code>vocal</code> ➔ <code>0LedVcls.1</code> ➔ 4條人聲Aux ➔ <code>1BckngVc1</code> ➔ <code>groove</code> ➔ <code>2 Drums.1</code> ➔ <code>DRUM_CR</code> ➔ <code>3 Bass.1</code> ➔ <code>sc bass</code> ➔ <code>melody</code> ➔ 旋律各軌。
          </div>
        </div>
      </div>

      <!-- Step 1 -->
      <div class="step-card">
        <div class="step-badge-row">
          <span class="step-number">STAGE 01</span>
          <span class="step-target" style="color:var(--neon-pink); font-weight:800;">📍 音軌：8 Brass & 4 Keyboard / 6 Synth</span>
        </div>
        <h3 class="step-title">1. 底噪封印與聲相拓寬 (Cleanup & Panning)</h3>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="volume-x"></i> 【音軌：8 Brass】 靜音處理</div>
          <div class="plugin-knobs">
            • 混音台把 <strong><code>8 Brass</code></strong> 直接點 <strong>M (Mute)</strong> 靜音（RMS -89dB 為純底噪，直接封印省 CPU）
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="move-horizontal"></i> 【音軌：4 Keyboard & 6 Synth】 聲相拓寬</div>
          <div class="plugin-knobs">
            • <strong><code>4 Keyboard</code></strong> 音軌：Pan 轉到 <strong>30L / 30R</strong><br>
            • <strong><code>6 Synth</code></strong> 音軌：Pan 轉到 <strong>25L / 25R</strong>（把中間 100% 留給主唱與 808 地鳴！）
          </div>
        </div>
      </div>

      <!-- Step 2 -->
      <div class="step-card">
        <div class="step-badge-row">
          <span class="step-number">STAGE 02</span>
          <span class="step-target" style="color:var(--neon-cyan); font-weight:800;">📍 音軌：2 Drums</span>
        </div>
        <h3 class="step-title">2. 大鼓 Punch 擊胸感雕刻 (Kick Punch)</h3>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="activity"></i> 【音軌：2 Drums】 插槽 A ➔ Ozone 11 Equalizer</div>
          <div class="plugin-knobs">
            • <strong>30Hz</strong>：High-Pass Filter (切除超低泥濘)<br>
            • <strong>70Hz</strong>：Proportional Q 提升 <strong>+2.5 dB</strong> (Q=3.5，鎖定擊胸點)<br>
            • <strong>350Hz</strong>：Bell 挖掉 <strong>-2.5 dB</strong> (Q=2.0，切除紙箱箱音)
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="zap"></i> 【音軌：2 Drums】 插槽 B ➔ Pultec EQP-1A（傳奇低頻雙推）</div>
          <div class="plugin-knobs">
            • <strong>CPS (頻率)</strong>：選 <strong>60 Hz</strong><br>
            • <strong>BOOST</strong>：轉到 <strong>3.0</strong> | <strong>ATTEN</strong>：轉到 <strong>2.5</strong>（同時推+拉，低頻緊實收束！）
          </div>
        </div>
      </div>

      <!-- Step 3 -->
      <div class="step-card">
        <div class="step-badge-row">
          <span class="step-number">STAGE 03</span>
          <span class="step-target" style="color:var(--neon-gold); font-weight:800;">📍 音軌：3 Bass</span>
        </div>
        <h3 class="step-title">3. 808 挖槽讓位與磁帶保全尾巴 (808 Sustain)</h3>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="radio"></i> 【音軌：3 Bass】 插槽 A ➔ Ozone 11 Equalizer (70Hz 挖槽)</div>
          <div class="plugin-knobs">
            • <strong>70Hz</strong>：Bell 挖凹槽 <strong>-3.0 dB</strong> (Q=3.5，鏡像對應大鼓)<br>
            • <em>大鼓踩下時 70Hz 完美避讓；808 的 35~55Hz 超低頻地鳴 100% 毫髮無傷保留！</em>
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="disc"></i> 【音軌：3 Bass】 插槽 B ➔ Ozone 11 Vintage Tape (保全尾巴 🔥)</div>
          <div class="plugin-knobs">
            • <strong>Speed 轉盤</strong>：點選 <strong>15 ips</strong> (低頻 Head Bump 共振，低音更厚更深)<br>
            • <strong>Input Drive</strong>：推至 <strong>+2.5 dB</strong> (軟磁飽和天然拉長 808 尾巴)<br>
            • <strong>Harmonics</strong>：推至 <strong>3.0</strong> (泛音增強，手機外放超清晰且絕不吃尾巴！)<br>
            • <strong>Low / High Emphasis</strong>: Low <strong>2.0</strong> | High <strong>1.0</strong>
          </div>
        </div>
      </div>

      <!-- Step 4 -->
      <div class="step-card">
        <div class="step-badge-row">
          <span class="step-number">STAGE 04</span>
          <span class="step-target" style="color:var(--neon-pink); font-weight:800;">📍 音軌：0 Lead Vocals</span>
        </div>
        <h3 class="step-title">4. 饒舌主唱快嘴咬字穿透力鏈條 (Lead Vocal Chain)</h3>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="activity"></i> 【音軌：0 Lead Vocals】 插槽 A ➔ Ozone 11 Equalizer</div>
          <div class="plugin-knobs">
            • <strong>90Hz HPF</strong>：切除噴麥與舞台低頻泥濘<br>
            • <strong>300Hz</strong>：Bell 挖掉 <strong>-2.0 dB</strong> (Q=2.0，清空胸腔濁音)<br>
            • <strong>3.5kHz</strong>：Bell 提升 <strong>+2.5 dB</strong> (Q=2.5，🔥 兇悍咬字與穿透力！)<br>
            • <strong>12kHz</strong>：High-Shelf 提升 <strong>+2.0 dB</strong> (現代空氣感)
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="gauge"></i> 【音軌：0 Lead Vocals】 插槽 B & C ➔ MC77 + BF-2A</div>
          <div class="plugin-knobs">
            • <strong>插槽 B [Purple Audio MC77 (1176)]</strong>: Ratio 4:1 | Attack 3 | Release 7 | 轉 Input 讓快嘴重音瞬態壓 <strong>3~4 dB</strong><br>
            • <strong>插槽 C [BF-2A (LA-2A)]</strong>: 接在 MC77 後方，Peak Reduction 轉到指針微動 <strong>1~2 dB</strong>，平滑推厚人聲！
          </div>
        </div>
      </div>

      <!-- Step 5 -->
      <div class="step-card">
        <div class="step-badge-row">
          <span class="step-number">STAGE 05</span>
          <span class="step-target" style="color:var(--neon-green); font-weight:800;">📍 音軌：5 Percussion</span>
        </div>
        <h3 class="step-title">5. Drill 滾奏 Hi-Hat 瞬態柔化 (Hi-Hat Taming)</h3>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="disc"></i> 【音軌：5 Percussion】 插槽 A ➔ Ozone 11 Vintage Tape</div>
          <div class="plugin-knobs">
            • <strong>Speed</strong>: 15 ips (削去頂端 39dB 刺耳瞬態，轉化為溫暖膠感)<br>
            • <strong>Input Drive</strong>: +1.5 dB | <strong>Bias</strong>: 0.0
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="sparkles"></i> 【音軌：5 Percussion】 插槽 B ➔ Ozone 11 Spectral Shaper</div>
          <div class="plugin-knobs">
            • 頻段選 <strong>High (8kHz - 20kHz)</strong><br>
            • <strong>Amount</strong>: 3.0 | <strong>Tone</strong>: Smooth (壓制 Hi-Hat 連發刺耳共振)
          </div>
        </div>
      </div>

      <!-- Step 6 -->
      <div class="step-card">
        <div class="step-badge-row">
          <span class="step-number">STAGE 06</span>
          <span class="step-target" style="color:#d1d5db; font-weight:800;">📍 音軌：7 Other & Vocal Aux</span>
        </div>
        <h3 class="step-title">6. 釋放低頻空間與空間景深 (Space & Aux)</h3>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="filter"></i> 【音軌：7 Other】 低頻切除</div>
          <div class="plugin-knobs">
            • 插槽 A 掛 <strong><code>EQ3 7-Band</code></strong> 或 <strong><code>Ozone EQ</code></strong>，設 High-Pass Filter 砍到 <strong>120 Hz</strong> 以下（釋放總線 Headroom）
          </div>
        </div>
        <div class="plugin-action-box">
          <div class="plugin-name"><i data-lucide="waves"></i> 【音軌：Vocal Reverb Aux】 D-Verb (立體聲)</div>
          <div class="plugin-knobs">
            • <strong>Type</strong>: Plate (金屬板，饒舌最貼耳) | <strong>Size</strong>: Medium | <strong>Decay</strong>: 1.6s<br>
            • <strong>Pre-Delay</strong>: 30ms (咬字先出，25ms 後出空間) | <strong>HF Cut</strong>: 6kHz | <strong>LP Filter</strong>: 200Hz<br>
            • <em>Aux 軌 Mix 設 100% / 若直插主唱軌 Mix 設 12%~15%</em>
          </div>
        </div>
      </div>

    </div>

    <!-- Phase 2: Master Bus AI Restoration & Mastering -->
    <h2 class="section-title">
      <i data-lucide="bot" style="color:var(--neon-pink);"></i>
      第二階段：Master 總線 4 大 AI 聲學解毒與商業母帶（一鍵起飛）
    </h2>

    <div style="background:var(--bg-card); border:1px solid var(--border-glow); border-radius:18px; padding:26px; margin-bottom:44px; backdrop-filter:blur(16px); box-shadow:0 10px 30px rgba(0,0,0,0.5);">
      
      <!-- Key Note: Why Keep Track EQs -->
      <div style="background:rgba(255,42,109,0.1); border:1px solid rgba(255,42,109,0.35); border-radius:12px; padding:16px 20px; margin-bottom:22px; display:flex; align-items:flex-start; gap:14px;">
        <i data-lucide="alert-circle" style="color:var(--neon-pink); width:24px; height:24px; flex-shrink:0; margin-top:2px;"></i>
        <div>
          <h4 style="font-size:15px; font-weight:800; color:#fff; margin-bottom:4px;">🚨 關鍵觀念：分軌上的 Drum / 808 EQ 絕對要保留開著！</h4>
          <p style="font-size:12px; color:#d1d5db; line-height:1.6;">
            <strong>分軌 EQ（微觀手術）</strong>：是在教 Kick 與 808「如何互相讓位」，只有在分軌上才能精準避讓 70Hz。<br>
            <strong>Master 上的 Ozone 11（宏觀解毒與拋光）</strong>：是把已經調好、不打架的聲音「一鍵抹去 AI 塑膠感，推到商業串流音量 (-8.5 LUFS)」。分軌做得越乾淨，Ozone 炸出來的低音就越震撼且完全不破音！
          </p>
        </div>
      </div>

      <!-- 4 Modules in Ozone 11 Master Chain -->
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:18px;">
        
        <!-- Module 1 -->
        <div style="background:rgba(0,0,0,0.4); border:1px solid var(--border-line); border-radius:12px; padding:18px;">
          <div style="font-family:var(--font-mono); font-size:11px; font-weight:700; color:var(--neon-cyan); margin-bottom:6px;">MODULE 01 🛡️</div>
          <h4 style="font-size:15px; font-weight:800; color:#fff; margin-bottom:8px;">Ozone 11 Stabilizer (自適應平衡)</h4>
          <p style="font-size:12px; color:var(--text-muted); line-height:1.5; margin-bottom:8px;">
            專治 AI 突發金屬刺耳頻率與相位空洞。
          </p>
          <div style="font-family:var(--font-mono); font-size:11px; color:#c9d1d9; background:rgba(255,255,255,0.04); padding:8px; border-radius:6px;">
            • <strong>Mode</strong>: Cut 模式<br>
            • <strong>Amount</strong>: 30%<br>
            • <strong>Speed</strong>: Medium
          </div>
        </div>

        <!-- Module 2 -->
        <div style="background:rgba(0,0,0,0.4); border:1px solid var(--border-line); border-radius:12px; padding:18px;">
          <div style="font-family:var(--font-mono); font-size:11px; font-weight:700; color:var(--neon-green); margin-bottom:6px;">MODULE 02 💎</div>
          <h4 style="font-size:15px; font-weight:800; color:#fff; margin-bottom:8px;">Ozone 11 Clarity (心理聲學去濁)</h4>
          <p style="font-size:12px; color:var(--text-muted); line-height:1.5; margin-bottom:8px;">
            一鍵抽乾 AI 特有的「塑膠箱子感」，空氣感爆發！
          </p>
          <div style="font-family:var(--font-mono); font-size:11px; color:#c9d1d9; background:rgba(255,255,255,0.04); padding:8px; border-radius:6px;">
            • <strong>Amount</strong>: 20% (超靈敏，20% 效果極致)<br>
            • <strong>Target</strong>: Mid / High-Mid
          </div>
        </div>

        <!-- Module 3 -->
        <div style="background:rgba(0,0,0,0.4); border:1px solid var(--border-line); border-radius:12px; padding:18px;">
          <div style="font-family:var(--font-mono); font-size:11px; font-weight:700; color:var(--neon-gold); margin-bottom:6px;">MODULE 03 🥊</div>
          <h4 style="font-size:15px; font-weight:800; color:#fff; margin-bottom:8px;">Ozone 11 Low End Focus (低頻對焦)</h4>
          <p style="font-size:12px; color:var(--text-muted); line-height:1.5; margin-bottom:8px;">
            把 AI 鬆散模糊的 808 凝聚成顆粒分明的鐵球！
          </p>
          <div style="font-family:var(--font-mono); font-size:11px; color:#c9d1d9; background:rgba(255,255,255,0.04); padding:8px; border-radius:6px;">
            • <strong>Mode</strong>: Punchy 模式<br>
            • <strong>Range</strong>: 35 Hz ~ 140 Hz<br>
            • <strong>Contrast</strong>: 30%
          </div>
        </div>

        <!-- Module 4 -->
        <div style="background:rgba(0,0,0,0.4); border:1px solid var(--border-line); border-radius:12px; padding:18px;">
          <div style="font-family:var(--font-mono); font-size:11px; font-weight:700; color:var(--neon-pink); margin-bottom:6px;">MODULE 04 🚀</div>
          <h4 style="font-size:15px; font-weight:800; color:#fff; margin-bottom:8px;">Ozone 11 Maximizer (商業串流響度)</h4>
          <p style="font-size:12px; color:var(--text-muted); line-height:1.5; margin-bottom:8px;">
            達到 Spotify / YouTube 頂級商業發行音量標準。
          </p>
          <div style="font-family:var(--font-mono); font-size:11px; color:#c9d1d9; background:rgba(255,255,255,0.04); padding:8px; border-radius:6px;">
            • <strong>IRC Mode</strong>: IRC IV Modern<br>
            • <strong>True Peak</strong>: -1.0 dBTP (防破音)<br>
            • <strong>Target</strong>: -8.5 LUFS (第 57s Drop 總驗收！)
          </div>
        </div>

      </div>

    </div>

    <!-- All Stems Analysis Matrix -->
    <h2 class="section-title">
      <i data-lucide="layers" style="color:var(--neon-cyan);"></i>
      9 軌分軌聲學數據與推桿表 (Stem Diagnostic Matrix)
    </h2>

    <div class="stems-container">
      {stem_cards_html}
    </div>
  </div>

  <script>
    lucide.createIcons();
  </script>
</body>
</html>
"""

    out_file = stem_dir / "mixing_guide.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✨ Custom Plugin Mixing HTML generated: {out_file.resolve()}")
    return out_file

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else r"D:\作品集\KAI ONYX 作品集\MIDNIGHT GLITCH\MIDNIGHT GLITCH - v4 Stems"
    generate_mixing_html(target)
