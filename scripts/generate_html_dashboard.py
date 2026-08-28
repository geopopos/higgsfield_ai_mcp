#!/usr/bin/env python3
"""
generate_html_dashboard.py
Generates a stunning, interactive Dark-Mode Cyberpunk / Drill HTML dashboard
for AI Video Production: Storyboard, Visual Assets, Audio Stems & Lyrics.
"""

import json
import os
from pathlib import Path

def generate_dashboard(project_dir_str: str):
    project_dir = Path(project_dir_str)
    shots_file = project_dir / "shots_manifest.json"
    assets_file = project_dir / "assets_manifest.json"
    beats_file = project_dir / "beats_manifest.json"
    lyrics_file = project_dir / "01_script" / "lyrics.txt"
    style_file = project_dir / "01_script" / "style_prompt.txt"

    shots_data = {}
    if shots_file.exists():
        with open(shots_file, "r", encoding="utf-8") as f:
            shots_data = json.load(f)

    assets_data = {}
    if assets_file.exists():
        with open(assets_file, "r", encoding="utf-8") as f:
            assets_data = json.load(f)

    beats_data = {}
    if beats_file.exists():
        with open(beats_file, "r", encoding="utf-8") as f:
            beats_data = json.load(f)

    lyrics_text = ""
    if lyrics_file.exists():
        with open(lyrics_file, "r", encoding="utf-8") as f:
            lyrics_text = f.read()

    style_text = ""
    if style_file.exists():
        with open(style_file, "r", encoding="utf-8") as f:
            style_text = f.read()

    # Stem files list
    stems_dir = project_dir / "02_audio" / "stems"
    stems_list = []
    if stems_dir.exists():
        for s in sorted(stems_dir.glob("*.mp3")):
            size_mb = f"{s.stat().st_size / 1024 / 1024:.2f} MB"
            stems_list.append({"name": s.name, "size": size_mb, "path": f"02_audio/stems/{s.name}"})

    # Curate Shot Data with rich human lyrics mapping and visual themes
    shots = shots_data.get("shots", [])
    
    # Precise scene thematic mappings for Midnight Glitch
    scene_descriptions = [
        {"sec": 1, "name": "Intro: Seoul-Taipei Smoke", "theme": "深夜都市高空俯瞰，霧氣瀰漫的台北與首爾交錯霓虹街景，低沉暗黑氛圍"},
        {"sec": 2, "name": "Verse 1: Dark Trap Flow", "theme": "地下街頭雨夜，主角身穿暗黑龐克風衣手持麥克風，808 重低音踩踏地面震動"},
        {"sec": 3, "name": "Pre-Chorus: Rising Tension", "theme": "緊張感上升，急速加速的軍鼓，警示紅光閃爍，主角面部特寫與眼神殺氣"},
        {"sec": 4, "name": "Chorus 1: Heavy Trap Drop", "theme": "王座降臨！巨大能量爆發，火焰與金色碎屑飛濺，身後重機與群體氣勢震撼"},
        {"sec": 5, "name": "Break: UK Drill Switch", "theme": "磁帶急停靜音！警笛呼嘯，槍機上膛音效，畫面瞬間切換至 140 BPM 黑白高對比抽格"},
        {"sec": 6, "name": "Verse 2: Drill Velocity", "theme": "極速雙倍押 Drill 刀光流！滑音 808 狂飆，手勢快切與金屬反光撕裂夜空"},
        {"sec": 7, "name": "Bridge & Climax Outro", "theme": "火海中破曉重生，極致廣角升降鏡頭，宣告掌控全城，冷峻定格 Game Over"}
    ]

    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MIDNIGHT GLITCH - AI 製片分鏡與視覺資產總覽</title>
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Inter:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@latest"></script>
  <style>
    :root {{
      --bg-primary: #07090e;
      --bg-secondary: #0d1117;
      --bg-card: rgba(18, 24, 38, 0.75);
      --bg-card-hover: rgba(28, 36, 56, 0.85);
      --border-color: rgba(255, 255, 255, 0.08);
      --border-accent: rgba(255, 59, 105, 0.35);
      
      --accent-pink: #ff2a6d;
      --accent-cyan: #05d9e8;
      --accent-purple: #9d4edd;
      --accent-gold: #ffbe0b;
      --accent-green: #00f5d4;

      --text-main: #f0f4f8;
      --text-muted: #8b9bb4;
      --text-dim: #50607a;

      --font-display: 'Cinzel', serif;
      --font-body: 'Inter', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg-primary);
      color: var(--text-main);
      font-family: var(--font-body);
      min-height: 100vh;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(255, 42, 109, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(5, 217, 232, 0.07) 0%, transparent 40%),
        linear-gradient(to bottom, #07090e, #0a0d14);
      background-attachment: fixed;
    }}

    /* Container */
    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 32px 24px 80px 24px;
    }}

    /* Header */
    .header {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--border-color);
      margin-bottom: 32px;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 18px;
    }}

    .badge-mv {{
      background: linear-gradient(135deg, var(--accent-pink), var(--accent-purple));
      color: #fff;
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      letter-spacing: 1.5px;
      text-transform: uppercase;
    }}

    .project-title {{
      font-family: var(--font-display);
      font-size: 32px;
      font-weight: 900;
      letter-spacing: 2px;
      background: linear-gradient(90deg, #fff, #ff2a6d 50%, #05d9e8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      text-shadow: 0 0 25px rgba(255, 42, 109, 0.3);
    }}

    .project-subtitle {{
      color: var(--text-muted);
      font-size: 13px;
      margin-top: 4px;
      letter-spacing: 0.5px;
    }}

    /* Audio Pill / Player Bar */
    .audio-player-pill {{
      display: flex;
      align-items: center;
      gap: 14px;
      background: var(--bg-card);
      border: 1px solid var(--border-accent);
      padding: 10px 18px;
      border-radius: 40px;
      backdrop-filter: blur(16px);
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }}

    .play-btn {{
      background: linear-gradient(135deg, var(--accent-pink), #ff0055);
      border: none;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: white;
      transition: all 0.2s ease;
      box-shadow: 0 0 15px rgba(255, 42, 109, 0.5);
    }}

    .play-btn:hover {{
      transform: scale(1.08);
      box-shadow: 0 0 25px rgba(255, 42, 109, 0.8);
    }}

    .audio-meta {{
      display: flex;
      flex-direction: column;
    }}

    .audio-title {{
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
    }}

    .audio-sub {{
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--accent-cyan);
    }}

    /* Stats Grid */
    .stats-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }}

    .stat-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      padding: 18px 20px;
      border-radius: 14px;
      backdrop-filter: blur(12px);
      position: relative;
      overflow: hidden;
      transition: transform 0.2s, border-color 0.2s;
    }}

    .stat-card:hover {{
      transform: translateY(-2px);
      border-color: var(--border-accent);
    }}

    .stat-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 3px;
      height: 100%;
      background: var(--accent-cyan);
    }}

    .stat-card:nth-child(2)::before {{ background: var(--accent-pink); }}
    .stat-card:nth-child(3)::before {{ background: var(--accent-purple); }}
    .stat-card:nth-child(4)::before {{ background: var(--accent-gold); }}
    .stat-card:nth-child(5)::before {{ background: var(--accent-green); }}

    .stat-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-dim);
      font-weight: 600;
      margin-bottom: 6px;
    }}

    .stat-value {{
      font-size: 22px;
      font-weight: 800;
      font-family: var(--font-mono);
      color: var(--text-main);
    }}

    .stat-desc {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
    }}

    /* Navigation Tabs */
    .tabs-nav {{
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 12px;
      overflow-x: auto;
    }}

    .tab-btn {{
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      padding: 10px 20px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
      white-space: nowrap;
    }}

    .tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.04);
    }}

    .tab-btn.active {{
      background: linear-gradient(135deg, rgba(255, 42, 109, 0.15), rgba(5, 217, 232, 0.15));
      border: 1px solid var(--border-accent);
      color: #fff;
      box-shadow: 0 4px 15px rgba(255, 42, 109, 0.2);
    }}

    /* Content Panes */
    .tab-pane {{
      display: none;
    }}

    .tab-pane.active {{
      display: block;
      animation: fadeIn 0.3s ease;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Controls / Filters */
    .table-controls {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
      background: var(--bg-card);
      padding: 14px 20px;
      border-radius: 12px;
      border: 1px solid var(--border-color);
    }}

    .filter-group {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .filter-label {{
      font-size: 12px;
      color: var(--text-dim);
      font-weight: 600;
      text-transform: uppercase;
    }}

    .filter-select, .search-input {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
    }}

    .filter-select:focus, .search-input:focus {{
      border-color: var(--accent-cyan);
    }}

    .btn-action {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }}

    .btn-action:hover {{
      background: rgba(255, 42, 109, 0.2);
      border-color: var(--accent-pink);
      color: #fff;
    }}

    /* Shot Cards & Grid */
    .shots-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }}

    .shot-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 20px;
      backdrop-filter: blur(12px);
      transition: all 0.2s ease;
      display: grid;
      grid-template-columns: 140px 160px 1fr 340px;
      gap: 20px;
      align-items: start;
    }}

    @media (max-width: 1100px) {{
      .shot-card {{
        grid-template-columns: 1fr;
        gap: 14px;
      }}
    }}

    .shot-card:hover {{
      border-color: var(--border-accent);
      background: var(--bg-card-hover);
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
    }}

    /* Shot ID & Time */
    .shot-id-box {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    .shot-id-badge {{
      font-family: var(--font-mono);
      font-size: 15px;
      font-weight: 700;
      color: var(--accent-cyan);
      background: rgba(5, 217, 232, 0.1);
      border: 1px solid rgba(5, 217, 232, 0.3);
      padding: 6px 10px;
      border-radius: 8px;
      text-align: center;
    }}

    .shot-time-info {{
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-muted);
      text-align: center;
      line-height: 1.4;
    }}

    .shot-duration-tag {{
      display: inline-block;
      background: rgba(255, 255, 255, 0.06);
      padding: 2px 6px;
      border-radius: 4px;
      color: var(--accent-gold);
      font-weight: 600;
    }}

    /* Camera Info */
    .shot-camera-box {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .tag-lens {{
      font-size: 12px;
      font-weight: 600;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .tag-motion {{
      font-family: var(--font-mono);
      font-size: 11px;
      padding: 4px 8px;
      border-radius: 6px;
      background: rgba(157, 78, 221, 0.15);
      border: 1px solid rgba(157, 78, 221, 0.4);
      color: #d8b4fe;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}

    /* Lyric & Emotion Box */
    .shot-lyric-box {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}

    .lyric-title {{
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      line-height: 1.4;
    }}

    .lyric-title span {{
      color: var(--accent-pink);
    }}

    .scene-mood-desc {{
      font-size: 12px;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    /* Prompt Box */
    .shot-prompt-box {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: rgba(0, 0, 0, 0.35);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px;
      position: relative;
    }}

    .prompt-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .prompt-tag {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-dim);
    }}

    .btn-copy {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-muted);
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 11px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s ease;
    }}

    .btn-copy:hover {{
      background: var(--accent-pink);
      color: #fff;
      border-color: var(--accent-pink);
    }}

    .prompt-text {{
      font-size: 12px;
      color: #c9d1d9;
      line-height: 1.45;
      font-family: var(--font-mono);
      max-height: 75px;
      overflow-y: auto;
      word-break: break-word;
    }}

    /* Asset Grid (Tab 2) */
    .assets-container {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 24px;
    }}

    .asset-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 24px;
      backdrop-filter: blur(12px);
      transition: all 0.2s ease;
    }}

    .asset-card:hover {{
      border-color: var(--border-accent);
      transform: translateY(-3px);
    }}

    .asset-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }}

    .asset-type-badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 4px 8px;
      border-radius: 6px;
      text-transform: uppercase;
      font-family: var(--font-mono);
    }}

    .type-char {{
      background: rgba(255, 42, 109, 0.15);
      color: var(--accent-pink);
      border: 1px solid rgba(255, 42, 109, 0.4);
    }}

    .type-loc {{
      background: rgba(5, 217, 232, 0.15);
      color: var(--accent-cyan);
      border: 1px solid rgba(5, 217, 232, 0.4);
    }}

    .asset-name {{
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }}

    .asset-file {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--accent-gold);
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}

    .asset-prompt-box {{
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 14px;
      margin-top: 12px;
    }}

    /* Stems & Audio (Tab 3) */
    .stems-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }}

    .stem-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      transition: all 0.2s;
    }}

    .stem-card:hover {{
      border-color: var(--accent-cyan);
    }}

    .stem-info {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .stem-name {{
      font-weight: 700;
      font-size: 14px;
      color: #fff;
    }}

    .stem-size {{
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-dim);
    }}

    /* Lyrics Display */
    .lyrics-container {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 28px;
      font-family: var(--font-mono);
      line-height: 1.7;
      white-space: pre-wrap;
      color: #d1d5db;
      font-size: 13px;
      max-height: 500px;
      overflow-y: auto;
    }}

    /* Toast Notification */
    #toast {{
      position: fixed;
      bottom: 30px;
      right: 30px;
      background: #111827;
      color: #fff;
      border: 1px solid var(--accent-pink);
      padding: 12px 20px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 10px 30px rgba(0,0,0,0.6);
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
      z-index: 9999;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    #toast.show {{
      transform: translateY(0);
      opacity: 1;
    }}
  </style>
</head>
<body>

  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="header-left">
        <div>
          <span class="badge-mv">AI Film Studio Pro</span>
          <h1 class="project-title">MIDNIGHT GLITCH</h1>
          <p class="project-subtitle">Korean Dark Trap ➔ Aggressive UK Drill Beat Switch (KAI ONYX)</p>
        </div>
      </div>

      <!-- Master Audio Preview -->
      <div class="audio-player-pill">
        <audio id="audioMaster" src="02_audio/master_track.wav" preload="metadata"></audio>
        <button class="play-btn" id="playBtn" onclick="togglePlay()">
          <i data-lucide="play" id="playIcon"></i>
        </button>
        <div class="audio-meta">
          <span class="audio-title">Master Audio Track</span>
          <span class="audio-sub" id="timeDisplay">0:00 / {int(float(beats_data.get('duration_sec', 126.68)) // 60)}:{int(float(beats_data.get('duration_sec', 126.68)) % 60):02d} • {float(beats_data.get('bpm', 143.55))} BPM</span>
        </div>
      </div>
    </header>

    <!-- Top Key Metrics -->
    <div class="stats-bar">
      <div class="stat-card">
        <div class="stat-label">Tempo / BPM</div>
        <div class="stat-value">{float(beats_data.get('bpm', 143.55))}</div>
        <div class="stat-desc">Drill / Trap Double Time</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Duration</div>
        <div class="stat-value">{float(beats_data.get('duration_sec', 126.68)):.2f}s</div>
        <div class="stat-desc">{int(round(float(beats_data.get('duration_sec', 126.68)) * 24)):,} Frames @ 24fps</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Storyboard Shots</div>
        <div class="stat-value">{len(shots)} 鏡頭</div>
        <div class="stat-desc">35mm & 85mm 運鏡矩陣</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Beat Switch</div>
        <div class="stat-value">@ 57.0s</div>
        <div class="stat-desc">UK Drill 140BPM Drop</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Audio Stems</div>
        <div class="stat-value">{len(stems_list)} Tracks</div>
        <div class="stat-desc">Vocals, Drums, 808 Bass</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="switchTab('shots')">
        <i data-lucide="clapperboard"></i> 🎬 鏡頭分鏡明細 (Storyboard Matrix)
      </button>
      <button class="tab-btn" onclick="switchTab('bible')">
        <i data-lucide="book-open"></i> 📖 導演企劃與運鏡白皮書 (Director's Master Plan)
      </button>
      <button class="tab-btn" onclick="switchTab('assets')">
        <i data-lucide="palette"></i> 🎨 視覺資產需求庫 (Asset Bible)
      </button>
      <button class="tab-btn" onclick="switchTab('audio')">
        <i data-lucide="music"></i> 🎧 分軌與母帶 (Audio Stems)
      </button>
      <button class="tab-btn" onclick="switchTab('lyrics')">
        <i data-lucide="file-text"></i> 📜 完整歌詞與劇本 (Lyrics & Script)
      </button>
    </div>

    <!-- Tab 1: Shots Storyboard -->
    <div id="pane-shots" class="tab-pane active">
      <div class="table-controls">
        <div class="filter-group">
          <span class="filter-label">運鏡篩選:</span>
          <select id="cameraFilter" class="filter-select" onchange="filterShots()">
            <option value="all">全部鏡頭 (All Shots)</option>
            <option value="slow_push_in">Slow Push In (沉浸推進)</option>
            <option value="orbit_3d">Orbit 3D (環繞運鏡)</option>
            <option value="fast_zoom_drop">Fast Zoom Drop (卡點急推)</option>
          </select>
        </div>

        <div class="filter-group">
          <input type="text" id="searchInput" class="search-input" placeholder="搜尋歌詞或關鍵字..." onkeyup="searchShots()">
          <button class="btn-action" onclick="copyAllPrompts()">
            <i data-lucide="copy"></i> 一鍵複製全部 Prompt
          </button>
        </div>
      </div>

      <div class="shots-grid" id="shotsGrid">
"""

    # Generate each shot card
    for idx, s in enumerate(shots):
        shot_id = s.get("shot_id", f"shot_{idx+1:03d}")
        start_t = s.get("start_time", 0.0)
        end_t = s.get("end_time", 0.0)
        start_f = s.get("start_frame", 0)
        end_f = s.get("end_frame", 0)
        dur = s.get("duration_sec", 0.0)
        cam = s.get("camera", {})
        lens = cam.get("lens", "cinematic_35mm")
        movement = cam.get("movement", "slow_push_in")
        prompt = s.get("prompt", "")

        # Extract lyric
        lyric_theme = ""
        if "Lyric theme:" in prompt:
            parts = prompt.split("Lyric theme:")
            clean_prompt = parts[0].strip()
            lyric_theme = parts[1].strip().strip("'\"")
        else:
            clean_prompt = prompt

        # Determine section theme description
        sec_num = s.get("section", 1)
        theme_desc = "暗黑街頭冷冽光影，808 重低音脈動視覺化"
        for sd in scene_descriptions:
            if sd["sec"] == sec_num:
                theme_desc = sd["theme"]
                break

        # Camera icon
        cam_icon = "camera"
        if "orbit" in movement:
            cam_icon = "rotate-3d"
        elif "push" in movement:
            cam_icon = "move-up-right"

        html_content += f"""
        <div class="shot-card" data-movement="{movement}" data-text="{lyric_theme} {clean_prompt}">
          <!-- Shot ID & Time -->
          <div class="shot-id-box">
            <div class="shot-id-badge">{shot_id}</div>
            <div class="shot-time-info">
              {start_t}s ➔ {end_t}s<br>
              <span class="shot-duration-tag">{dur} 秒</span><br>
              <span style="font-size:10px; color:var(--text-dim);">Frame {start_f}-{end_f}</span>
            </div>
          </div>

          <!-- Camera Settings -->
          <div class="shot-camera-box">
            <div class="tag-lens">
              <i data-lucide="aperture" style="width:14px; height:14px; color:var(--accent-cyan);"></i>
              {lens.replace('_', ' ').upper()}
            </div>
            <div class="tag-motion">
              <i data-lucide="{cam_icon}" style="width:12px; height:12px;"></i>
              {movement.replace('_', ' ').title()}
            </div>
            <div style="font-size:11px; color:var(--text-dim); margin-top:4px;">
              Section #{sec_num}
            </div>
          </div>

          <!-- Lyric Theme & Narrative -->
          <div class="shot-lyric-box">
            <div class="lyric-title">
              <span>🎤</span> {lyric_theme if lyric_theme else "(純音樂節奏過渡 / 氛圍空鏡)"}
            </div>
            <div class="scene-mood-desc">
              💡 <strong>場景意境：</strong>{theme_desc}
            </div>
          </div>

          <!-- Generation Prompt -->
          <div class="shot-prompt-box">
            <div class="prompt-header">
              <span class="prompt-tag">Flux / Higgsfield Prompt</span>
              <button class="btn-copy" onclick="copyText(`{clean_prompt}`)">
                <i data-lucide="copy" style="width:11px; height:11px;"></i> 複製
              </button>
            </div>
            <div class="prompt-text">{clean_prompt}</div>
          </div>
        </div>
"""

    html_content += f"""
      </div>
    </div>

    <!-- Tab: Director's Master Plan & Bible -->
    <div id="pane-bible" class="tab-pane">
      <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:16px; padding:32px; margin-bottom:28px;">
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
          <span style="background:rgba(255,42,133,0.2); color:var(--accent-pink); border:1px solid var(--accent-pink); padding:4px 10px; border-radius:6px; font-size:11px; font-weight:800; text-transform:uppercase;">Director's Vision</span>
          <h2 style="font-size:24px; font-weight:900; color:#fff; font-family:var(--font-display);">《MIDNIGHT GLITCH》導演企劃與運鏡白皮書</h2>
        </div>
        <p style="font-size:14px; color:var(--text-muted); line-height:1.7; margin-bottom:24px;">
          本 MV 不是隨機拼湊畫面的視覺 Demo，而是嚴格按照<strong>「音樂能量曲線（Energy Curve）」</strong>、<strong>「短影音黃金秒數傳播心理學」</strong>與<strong>「好萊塢/K-Pop 頂級工業視覺管線」</strong>深度對位的旗艦級影音 IP。
        </p>

        <!-- Core Pillars Grid -->
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:20px; margin-bottom:32px;">
          <div style="background:rgba(0,0,0,0.4); border:1px solid rgba(5,217,232,0.2); border-radius:12px; padding:20px;">
            <div style="font-size:16px; font-weight:700; color:var(--accent-cyan); margin-bottom:8px; display:flex; align-items:center; gap:8px;">
              <i data-lucide="user-check" style="width:18px; height:18px;"></i> 核心角色與世界觀
            </div>
            <p style="font-size:13px; color:#d1d5db; line-height:1.6;">
              主角 <strong>KAI ONYX</strong> 是首爾/台北暗黑街頭的頂級說唱王者，同時也是掌控深夜數位雜訊的賽博叛客。敘事空間由「地上雨夜街頭（潛行）」➔「地下鐵道（掌控）」➔「機房紅光（蓄力）」➔「火焰王座（爆發）」➔「@57s UK Drill 刀光（突變）」➔「天台天際線（登頂）」，層層遞進！
            </p>
          </div>

          <div style="background:rgba(0,0,0,0.4); border:1px solid rgba(255,42,133,0.2); border-radius:12px; padding:20px;">
            <div style="font-size:16px; font-weight:700; color:var(--accent-pink); margin-bottom:8px; display:flex; align-items:center; gap:8px;">
              <i data-lucide="aperture" style="width:18px; height:18px;"></i> 焦段嚴格分離原則
            </div>
            <p style="font-size:13px; color:#d1d5db; line-height:1.6;">
              <strong>85mm 淺景深長焦</strong>：只在主歌說唱時使用，極致虛化背景，精準鎖定 KAI ONYX 的五官顏值與眼神殺氣。<br>
              <strong>18mm/24mm 變形超廣角</strong>：只在轉場（FPV 階梯急墜）與副歌大爆發時使用，拉滿首爾雨巷、地底鐵道與天際線的空間壓迫感！
            </p>
          </div>

          <div style="background:rgba(0,0,0,0.4); border:1px solid rgba(255,183,3,0.2); border-radius:12px; padding:20px;">
            <div style="font-size:16px; font-weight:700; color:var(--accent-gold); margin-bottom:8px; display:flex; align-items:center; gap:8px;">
              <i data-lucide="zap" style="width:18px; height:18px;"></i> 57s Beat Switch 病毒爆點
            </div>
            <p style="font-size:13px; color:#d1d5db; line-height:1.6;">
              在 57.0 秒處，伴隨<strong>「磁帶急停（Tape Stop）+ 槍機上膛音效（Gun Click）」</strong>，畫面瞬間由彩色切換為<strong>高對比黑白金屬抽格</strong>，曲風由暗黑 Trap 瞬間突變為 140 BPM UK Drill 刀光流，製造短影音傳播的現象級高光時刻！
            </p>
          </div>
        </div>

        <!-- Section by Section Table -->
        <h3 style="font-size:18px; font-weight:800; color:#fff; margin-bottom:16px; display:flex; align-items:center; gap:8px;">
          <i data-lucide="layers" style="width:18px; height:18px; color:var(--accent-cyan);"></i> 8 大分段鉅細靡遺運鏡與音樂卡點解析
        </h3>

        <div style="display:flex; flex-direction:column; gap:14px;">
          
          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:var(--accent-cyan);">📍 Section 1: Intro 孤絕醞釀 (0.0s - 15.0s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">4 鏡頭 | 85mm & 24mm</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>首爾弘大/江南雨夜巷弄（노래방、편의점 24시、포장마차 霓虹燈箱），凌晨三點地面雨水倒影與人孔蓋蒸氣。<br>
              <strong>運鏡哲學：</strong>前 12 秒採用 85mm 慢速 Orbit 3D 沉浸推進，第 12~15 秒（shot_004）化為 <strong>FPV 24mm 廣角階梯急速俯衝（Speed Ramp Dive）</strong>，以三倍速旋風墜入地鐵通道，為 15.0 秒的 808 Drop 蓄積最強下墜力！
            </p>
          </div>

          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:var(--accent-pink);">🚇 Section 2: Verse 1 Dark Trap 降臨 (15.0s - 30.0s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">4 鏡頭 | 808 Bass Shake</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>衝出階梯，首爾地鐵 2 號線地下軌道與維修月台（鋼管、高壓電纜、冷色長條螢光燈）。<br>
              <strong>運鏡哲學：</strong>低角度仰拍 (Low-Angle Hero Shot) 結合 808 踩點震動 (Punch Shake)。KAI ONYX 正對鏡頭開唱 <code>새벽 세 시, 어둠 속에 번지는 smoke</code>，每當 808 重低音落下畫面產生微震反饋，展現地下統治力！
            </p>
          </div>

          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:var(--accent-gold);">🚨 Section 3: Pre-Chorus 緊張感攀升 (30.0s - 45.0s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">4 鏡頭 | Snare Rolls Accelerating</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>地下伺服器機房，警示紅光開始旋轉狂閃，數據流超載。<br>
              <strong>運鏡哲學：</strong>快速橫移 (Whip Pan) + 面部極限特寫急推 (Crash Zoom)。剪輯頻率隨軍鼓加速滾奏縮短，在 <code>倒數三秒, 撕開黑夜的鎖</code> 將即將爆炸的窒息壓迫感拉到最頂點！
            </p>
          </div>

          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:#ff5e7e;">👑 Section 4: Chorus 1 王座大爆發 (45.0s - 60.0s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">4 鏡頭 | 18mm 廣角升降搖臂</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>廢棄工業巨型穹頂，身後數台重機頭燈直射，金色火花與火焰在兩側狂飆。<br>
              <strong>運鏡哲學：</strong>超廣角 (18mm) 升降搖臂 (Crane Jib Up) + 能量環繞 (Dynamic Orbit)。鏡頭從低處急速升起俯瞰全場，配合 <code>We run this city! We run this throne!</code> 展現君臨天下的磅礴氣勢！
            </p>
          </div>

          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:#00f5d4;">🗡️ Section 5: Break & UK Drill 刀光切換 (60.0s - 75.0s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">4 鏡頭 | @57s Beat Switch 抽格快切</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>57.0 秒處磁帶急停！槍機上膛音效，畫面瞬間由彩色切換為 <strong>高對比黑白金屬抽格</strong>！<br>
              <strong>運鏡哲學：</strong>45° 荷蘭角傾斜 (Dutch Angle) + 0.5 秒卡點快切。配合歌詞 <code>내 혓바닥은 칼날 / 誰敢擋在前面, 刀光劃破夜空</code>，手部手勢、刀光金屬反光與槍機音效毫秒級對位，速度感炸裂！
            </p>
          </div>

          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:#b5179e;">⚡ Section 6: Verse 2 Drill Velocity 極速推進 (75.0s - 90.0s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">4 鏡頭 | Sliding 808 FPV</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>首爾高架橋下穿梭，黑白工業廢墟與數位雜訊流動。<br>
              <strong>運鏡哲學：</strong>FPV 穿梭運鏡 (FPV Drone Rush) + 光影左右拉扯 (Glitch Whip)。鏡頭隨著 808 的滑音起伏進行波浪式平滑滑移，將聽覺滑音完美轉化為視覺動態！
            </p>
          </div>

          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:#f72585;">🔥 Section 7: Chorus 2 UK Drill 終極高潮 (90.0s - 105.0s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">5 鏡頭 | 全城天際線俯瞰</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>首爾摩天大樓頂層天台，背後是全城雨夜天際線，腳下踩著巨大發光數位 LOGO。<br>
              <strong>運鏡哲學：</strong>卡點急推急煞 (Fast Zoom Drop) + 360度極致升降。每一句 <code>Hey!</code> 伴隨全城霓虹過載爆閃，全方位展現掌控全城的制霸感！
            </p>
          </div>

          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:10px; padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span style="font-size:14px; font-weight:700; color:#7209b7;">⬛ Section 8 & 9: Outro 冷峻定格與信號終結 (105.0s - 126.68s)</span>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--text-dim);">6 鏡頭 | CCTV Glitch ➔ Hard Cut to Black</span>
            </div>
            <p style="font-size:12px; color:#9ca3af; line-height:1.5;">
              <strong>畫面意境：</strong>天台高空背影，轉為閉路電視 (CCTV) 綠色雜訊抽格。<br>
              <strong>運鏡哲學：</strong>慢速後拉遠景 (Slow Pull Back) ➔ 數位訊號故障 (Signal Glitch)。在 124 秒最後一句 <code>game over</code> 說完的瞬間畫面被擊碎，信號瞬間切黑 (Cold Stop)，留下回味無窮的冷峻餘韻！
            </p>
          </div>

        </div>
      </div>
    </div>

    <!-- Tab 2: Visual Assets Bible -->
    <div id="pane-assets" class="tab-pane">
      <h2 style="font-size:20px; font-weight:800; margin-bottom:16px; color:#fff;">👤 主角設計設定 (Character Turnaround Sheet)</h2>
      <div class="assets-container" style="margin-bottom:36px;">
"""

    # Characters
    for char in assets_data.get("characters", []):
        fn = char.get('output_filename', 'character.png')
        img_tag = ""
        img_path = project_dir / "03_storyboard" / fn
        if img_path.exists():
            img_tag = f'<div style="margin:12px 0;"><a href="03_storyboard/{fn}" target="_blank"><img src="03_storyboard/{fn}" style="width:100%; max-height:420px; object-fit:cover; border-radius:10px; border:1px solid rgba(5,217,232,0.3); box-shadow:0 8px 24px rgba(0,0,0,0.6);" alt="{fn}"></a></div>'

        html_content += f"""
        <div class="asset-card">
          <div class="asset-header">
            <span class="asset-name">{char.get('name', '主角')}</span>
            <span class="asset-type-badge type-char">Character Sheet</span>
          </div>
          <div class="asset-file">
            <i data-lucide="image" style="width:14px; height:14px;"></i> {fn}
          </div>
          {img_tag}
          <p style="font-size:12px; color:var(--text-muted); line-height:1.5; margin-bottom:10px;">
            設定要求：4視角三視圖（正、側、3/4、背面）、暗黑龐克街頭服飾、高細節臉部一致性錨定。
          </p>
          <div class="asset-prompt-box">
            <div class="prompt-header">
              <span class="prompt-tag">生圖提示詞 (Generation Prompt)</span>
              <button class="btn-copy" onclick="copyText(`{char.get('prompt', '')}`)">
                <i data-lucide="copy" style="width:11px; height:11px;"></i> 複製
              </button>
            </div>
            <div class="prompt-text" style="max-height:100px;">{char.get('prompt', '')}</div>
          </div>
        </div>
"""

    html_content += f"""
      </div>

      <h2 style="font-size:20px; font-weight:800; margin-bottom:16px; color:#fff;">📍 分段環境場景 Keyframe (Locations)</h2>
      <div class="assets-container">
"""

    # Locations
    for loc in assets_data.get("locations", []):
        fn = loc.get('output_filename', 'location.png')
        img_tag = ""
        img_path = project_dir / "03_storyboard" / fn
        if img_path.exists():
            img_tag = f'<div style="margin:12px 0;"><a href="03_storyboard/{fn}" target="_blank"><img src="03_storyboard/{fn}" style="width:100%; max-height:280px; object-fit:cover; border-radius:10px; border:1px solid rgba(255,42,133,0.3); box-shadow:0 8px 24px rgba(0,0,0,0.6);" alt="{fn}"></a></div>'

        html_content += f"""
        <div class="asset-card">
          <div class="asset-header">
            <span class="asset-name">{loc.get('name', '場景')}</span>
            <span class="asset-type-badge type-loc">Environment</span>
          </div>
          <div class="asset-file">
            <i data-lucide="map-pin" style="width:14px; height:14px;"></i> {fn}
          </div>
          {img_tag}
          <div class="asset-prompt-box">
            <div class="prompt-header">
              <span class="prompt-tag">場景提示詞 (Location Prompt)</span>
              <button class="btn-copy" onclick="copyText(`{loc.get('prompt', '')}`)">
                <i data-lucide="copy" style="width:11px; height:11px;"></i> 複製
              </button>
            </div>
            <div class="prompt-text">{loc.get('prompt', '')}</div>
          </div>
        </div>
"""

    html_content += f"""
      </div>
    </div>

    <!-- Tab 3: Stems & Audio Studio -->
    <div id="pane-audio" class="tab-pane">
      <h2 style="font-size:20px; font-weight:800; margin-bottom:16px; color:#fff;">🎧 9 軌無損分軌庫 (Audio Stems Breakdown)</h2>
      <div class="stems-grid">
"""

    for st in stems_list:
        html_content += f"""
        <div class="stem-card">
          <div class="stem-info">
            <span class="stem-name">{st['name']}</span>
            <span class="stem-size">{st['size']} • 44.1kHz WAV/MP3</span>
          </div>
          <button class="btn-copy" onclick="playStem('{st['path']}')">
            <i data-lucide="volume-2" style="width:12px; height:12px;"></i> 試聽
          </button>
        </div>
"""

    html_content += f"""
      </div>
    </div>

    <!-- Tab 4: Lyrics & Screenplay -->
    <div id="pane-lyrics" class="tab-pane">
      <h2 style="font-size:20px; font-weight:800; margin-bottom:16px; color:#fff;">📜 歌詞與段落結構 (Full Lyrics & Beat Structure)</h2>
      <div class="lyrics-container">{lyrics_text}</div>
    </div>

  </div>

  <!-- Toast -->
  <div id="toast">
    <i data-lucide="check-circle" style="color:var(--accent-green);"></i>
    <span id="toastMsg">已複製到剪貼簿！</span>
  </div>

  <script>
    lucide.createIcons();

    // Tab Switching
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
      
      const targetBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (targetBtn) targetBtn.classList.add('active');

      const targetPane = document.getElementById('pane-' + tabId);
    <!-- Floating Back to Top Button -->
    <button id="btnBackToTop" onclick="scrollToTop()" style="position:fixed; bottom:30px; left:30px; background:rgba(13,17,26,0.9); border:1px solid var(--accent-cyan); color:var(--accent-cyan); width:45px; height:45px; border-radius:50%; display:flex; align-items:center; justify-content:center; cursor:pointer; box-shadow:0 0 15px rgba(5,217,232,0.3); transition:all 0.3s; z-index:9999;" title="回到頂部">
      <i data-lucide="arrow-up" style="width:20px; height:20px;"></i>
    </button>

  </div>

  <!-- Toast -->
  <div id="toast">
    <i data-lucide="check-circle" style="color:var(--accent-green);"></i>
    <span id="toastMsg">已複製到剪貼簿！</span>
  </div>

  <script>
    lucide.createIcons();

    // Auto Scroll to Top on Load
    window.onload = () => {{
      window.scrollTo(0, 0);
    }};

    function scrollToTop() {{
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    // Tab Switching with Auto Scroll to Top
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
      
      const targetBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
      if (targetBtn) targetBtn.classList.add('active');

      const targetPane = document.getElementById('pane-' + tabId);
      if (targetPane) targetPane.classList.add('active');

      // Auto scroll to top on tab change
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    // Filter Shots by Movement
    function filterShots() {{
      const val = document.getElementById('cameraFilter').value;
      document.querySelectorAll('.shot-card').forEach(card => {{
        if (val === 'all' || card.getAttribute('data-movement') === val) {{
          card.style.display = 'grid';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}

    // Search Shots
    function searchShots() {{
      const query = document.getElementById('searchInput').value.toLowerCase();
      document.querySelectorAll('.shot-card').forEach(card => {{
        const text = (card.getAttribute('data-text') || '').toLowerCase();
        if (text.includes(query)) {{
          card.style.display = 'grid';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}

    // Copy to Clipboard
    function copyText(text) {{
      navigator.clipboard.writeText(text).then(() => {{
        showToast('已成功複製 Prompt 到剪貼簿！');
      }});
    }}

    function copyAllPrompts() {{
      const prompts = Array.from(document.querySelectorAll('.prompt-text')).map(p => p.innerText).join('\\n\\n');
      copyText(prompts);
      showToast('已一鍵複製全部 ' + document.querySelectorAll('.prompt-text').length + ' 個鏡頭 Prompt！');
    }}

    function showToast(msg) {{
      const toast = document.getElementById('toast');
      document.getElementById('toastMsg').innerText = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('