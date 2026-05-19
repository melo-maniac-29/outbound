"""
Run: python scripts/gen_diagram.py
Generates docs/pipeline.excalidraw.json — open at excalidraw.com
"""
import json, random, os

def uid():
    return f"el-{random.randint(100000, 999999)}"

def rect(x, y, w, h, label, bg, stroke, font=13):
    rid, tid = uid(), uid()
    shape = {
        "id": rid, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": bg, "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": {"type": 3},
        "seed": random.randint(1, 9999), "version": 1, "versionNonce": 1, "isDeleted": False,
        "boundElements": [{"type": "text", "id": tid}], "updated": 1, "link": None, "locked": False
    }
    text = {
        "id": tid, "type": "text", "x": x + 6, "y": y + 4, "width": w - 12, "height": h - 8,
        "angle": 0, "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid", "roughness": 0,
        "opacity": 100, "groupIds": [], "frameId": None, "roundness": None,
        "seed": random.randint(1, 9999), "version": 1, "versionNonce": 1, "isDeleted": False,
        "text": label, "fontSize": font, "fontFamily": 1, "textAlign": "center",
        "verticalAlign": "middle", "containerId": rid, "originalText": label,
        "lineHeight": 1.3, "boundElements": [], "updated": 1, "link": None, "locked": False
    }
    return [shape, text], rid

def diamond(x, y, w, h, label):
    rid, tid = uid(), uid()
    shape = {
        "id": rid, "type": "diamond", "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": "#b45309", "backgroundColor": "#fef9c3", "fillStyle": "solid",
        "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": {"type": 3},
        "seed": random.randint(1, 9999), "version": 1, "versionNonce": 1, "isDeleted": False,
        "boundElements": [{"type": "text", "id": tid}], "updated": 1, "link": None, "locked": False
    }
    text = {
        "id": tid, "type": "text", "x": x + 10, "y": y + 8, "width": w - 20, "height": h - 16,
        "angle": 0, "strokeColor": "#78350f", "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid", "roughness": 0,
        "opacity": 100, "groupIds": [], "frameId": None, "roundness": None,
        "seed": random.randint(1, 9999), "version": 1, "versionNonce": 1, "isDeleted": False,
        "text": label, "fontSize": 12, "fontFamily": 1, "textAlign": "center",
        "verticalAlign": "middle", "containerId": rid, "originalText": label,
        "lineHeight": 1.3, "boundElements": [], "updated": 1, "link": None, "locked": False
    }
    return [shape, text], rid

def arrow(x1, y1, x2, y2, label="", color="#6b7280"):
    aid = uid()
    dx, dy = x2 - x1, y2 - y1
    el = {
        "id": aid, "type": "arrow", "x": x1, "y": y1,
        "width": abs(dx), "height": abs(dy), "angle": 0,
        "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": {"type": 2}, "seed": random.randint(1, 9999),
        "version": 1, "versionNonce": 1, "isDeleted": False,
        "points": [[0, 0], [dx, dy]], "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": "arrow",
        "boundElements": [], "updated": 1, "link": None, "locked": False
    }
    items = [el]
    if label:
        tid = uid()
        items.append({
            "id": tid, "type": "text",
            "x": x1 + dx // 2 - 30, "y": y1 + dy // 2 - 10,
            "width": 60, "height": 20, "angle": 0,
            "strokeColor": "#374151", "backgroundColor": "#f3f4f6",
            "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
            "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
            "roundness": None, "seed": random.randint(1, 9999),
            "version": 1, "versionNonce": 1, "isDeleted": False,
            "text": label, "fontSize": 11, "fontFamily": 1,
            "textAlign": "center", "verticalAlign": "middle",
            "containerId": None, "originalText": label,
            "lineHeight": 1.25, "boundElements": [], "updated": 1,
            "link": None, "locked": False
        })
    return items

def lbl(x, y, w, text, color="#374151", size=12):
    return {
        "id": uid(), "type": "text", "x": x, "y": y, "width": w, "height": 22,
        "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 0, "opacity": 100, "groupIds": [], "frameId": None,
        "roundness": None, "seed": random.randint(1, 9999),
        "version": 1, "versionNonce": 1, "isDeleted": False,
        "text": text, "fontSize": size, "fontFamily": 1,
        "textAlign": "center", "verticalAlign": "middle",
        "containerId": None, "originalText": text,
        "lineHeight": 1.25, "boundElements": [], "updated": 1,
        "link": None, "locked": False
    }

# ── Color palette (light pastels, dark strokes) ────────────────────────────────
BLU_BG = "#dbeafe"; BLU_S = "#1d4ed8"   # crawl
PUR_BG = "#ede9fe"; PUR_S = "#6d28d9"   # LLM / GPT
GRN_BG = "#dcfce7"; GRN_S = "#15803d"   # lookup / terminal OK
TEA_BG = "#ccfbf1"; TEA_S = "#0f766e"   # enrich / personalize
SLA_BG = "#f1f5f9"; SLA_S = "#475569"   # merge / validate / pattern
RED_BG = "#fee2e2"; RED_S = "#b91c1c"   # dead
STA_BG = "#f0fdf4"; STA_S = "#166534"   # READY

elements = []
E = elements.extend

CX = 600; NW = 290; NL = CX - NW // 2
RCX = 1070; RNW = 330; RNL = RCX - RNW // 2

# Title
elements.append(lbl(450, -40, 500, "OUTBOUND NEXUS — LangGraph Pipeline", "#111827", 18))

# START
els, _ = rect(CX - 55, 0, 110, 36, "▶  START", "#f9fafb", "#374151", 13)
E(els)
E(arrow(CX, 36, CX, 74))

# crawl
els, _ = rect(NL, 74, NW, 78, "crawl_node\nPlaywright → fetches ≤8 pages → markdown\nstatus: CRAWLED", BLU_BG, BLU_S)
E(els); E(arrow(CX, 152, CX, 192))

# extract_all (wider)
els, _ = rect(CX - 220, 192, 440, 90, "extract_all_node  ← asyncio.gather (parallel)\nFounder extraction  |  Services extraction  |  Signals extraction\n3 simultaneous GPT calls      status: EXTRACTED", PUR_BG, PUR_S)
E(els); E(arrow(CX, 282, CX, 332))

# merge
els, _ = rect(NL, 332, NW, 62, "merge_extractions\nWrites founder · services · signals → LeadState", SLA_BG, SLA_S)
E(els); E(arrow(CX, 394, CX, 440))

# founder gate
els, _ = diamond(NL, 440, NW, 78, "founder_confidence\n≥ 0.75 ?")
E(els)

# dead left
elements.append(lbl(175, 462, 160, "◀  NO  (DEAD)", RED_S, 10))
E(arrow(NL, 479, 310, 530, "NO"))
els, _ = rect(100, 530, 210, 58, "dead_lead_node\nstatus = DEAD_LEAD", RED_BG, RED_S, 12)
E(els); E(arrow(205, 588, 205, 626))
els, _ = rect(130, 626, 150, 36, "⬛  END", "#f9fafb", "#374151", 12)
E(els)

# live right
elements.append(lbl(RCX, 432, 240, "YES  ▶", GRN_S, 10))
E(arrow(NL + NW, 479, RNL, 505, "YES"))

els, _ = rect(RNL, 505, RNW, 72, "linkedin_lookup_node\nTavily searches for founder LinkedIn /in/ URL", GRN_BG, GRN_S)
E(els); E(arrow(RCX, 577, RCX, 619))

els, _ = rect(RNL, 619, RNW, 72, "enrich_node\nHunter.io email lookup\n(skipped if site email confidence ≥ 0.80)", TEA_BG, TEA_S)
E(els); E(arrow(RCX, 691, RCX, 733))

els, _ = rect(RNL, 733, RNW, 90, "build_profile_node\nGPT → summary · positioning · audience\noutreach_angle (the specific hook)    GPT call", PUR_BG, PUR_S)
E(els); E(arrow(RCX, 823, RCX, 873))

# email gate
els, _ = diamond(RNL, 873, RNW, 78, "email_confidence\n≥ 0.70 ?")
E(els)

# pattern guess (left of right column)
elements.append(lbl(790, 870, 120, "◀  NO", "#b45309", 10))
E(arrow(RNL, 912, 940, 955, "NO"))
els, _ = rect(700, 955, 240, 62, "pattern_guess_node\nGuesses first.last@domain.com\nconf = 0.72", SLA_BG, SLA_S, 12)
E(els)
E(arrow(820, 1017, 820, 1053))  # pattern → validate

# validate
elements.append(lbl(RCX + 80, 870, 80, "YES  ▶", GRN_S, 10))
E(arrow(RCX, 951, RCX, 1053, "YES"))
els, _ = rect(RNL, 1053, RNW, 68, "validate_node\nFinal gate: founder ≥ 0.75 AND email ≥ 0.70", SLA_BG, SLA_S)
E(els); E(arrow(RCX, 1121, RCX, 1171))

# validation gate
els, _ = diamond(RNL, 1171, RNW, 78, "status ==\nVALIDATED ?")
E(els)

# dead-2
elements.append(lbl(RNL - 30, 1197, 80, "◀  NO", RED_S, 10))
E(arrow(RNL, 1210, RNL - 100, 1210))
els, _ = rect(RNL - 270, 1192, 170, 36, "⬛  END (dead)", "#f9fafb", "#374151", 12)
E(els)

# personalize
elements.append(lbl(RCX + 80, 1168, 80, "YES  ▶", GRN_S, 10))
E(arrow(RCX, 1249, RCX, 1299, "YES"))
els, _ = rect(RNL, 1299, RNW, 68, "personalize_node\nPicks best signal as outreach hook\nFilters generic strings", TEA_BG, TEA_S)
E(els); E(arrow(RCX, 1367, RCX, 1417))

els, _ = rect(RNL, 1417, RNW, 90, "draft_node\nGPT writes 3-email sequence\nEmail 1 (Day 0) · Email 2 (Day 3) · Email 3 (Day 10)\nmax_tokens=1200", PUR_BG, PUR_S)
E(els); E(arrow(RCX, 1507, RCX, 1557))

els, _ = rect(RNL, 1557, RNW, 68, "outreach_node\nstatus = READY_TO_SEND  — human reviews first\nNothing is sent automatically", GRN_BG, GRN_S)
E(els); E(arrow(RCX, 1625, RCX, 1665))

els, _ = rect(RCX - 90, 1665, 180, 38, "✅  READY_TO_SEND", STA_BG, STA_S, 13)
E(els)

# Legend
E(arrow(260, 760, 380, 760))
elements.append(lbl(260, 740, 260, "MAIN COLUMN  →  entry/merge/decision", "#374151", 10))
elements.append(lbl(RCX, 470, 260, "RIGHT COLUMN  →  live processing branch", GRN_S, 10))

# ── Write output ───────────────────────────────────────────────────────────────
out_path = os.path.join(os.path.dirname(__file__), "..", "docs", "pipeline.excalidraw.json")
diagram = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
    "files": {}
}
with open(out_path, "w") as f:
    json.dump(diagram, f, indent=2)
print(f"Written {os.path.abspath(out_path)} — {len(elements)} elements")
