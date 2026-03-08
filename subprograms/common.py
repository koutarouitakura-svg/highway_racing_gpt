import pyxel
import math
import random
import json
import os
import sys
import base64
import threading
import queue

# ── Thrustmaster T-300 RS / 汎用ジョイスティック対応 ──
# pygameのjoystick APIを使用。インストール: pip install pygame
try:
    import pygame as _pg
    _pg.init()
    _pg.joystick.init()
    _JOY = _pg.joystick.Joystick(0) if _pg.joystick.get_count() > 0 else None
    if _JOY:
        _JOY.init()
        print(f"[Joystick] {_JOY.get_name()} ({_JOY.get_numaxes()} axes, {_JOY.get_numbuttons()} buttons)")
    _HAS_JOY = _JOY is not None
except Exception as _joy_err:
    _HAS_JOY = False
    _JOY     = None

def _joy_axis(idx, deadzone=0.04):
    """軸の値を取得。デッドゾーン処理済み (-1.0〜1.0)。"""
    if not _HAS_JOY: return 0.0
    try:
        _pg.event.pump()   # イベントキューを更新
        v = _JOY.get_axis(idx)
        return v if abs(v) > deadzone else 0.0
    except Exception: return 0.0

def _joy_btn(idx):
    """ボタンの押下状態を取得。"""
    if not _HAS_JOY: return False
    try:
        _pg.event.pump()
        return bool(_JOY.get_button(idx))
    except Exception: return False

def _joy_hat(hat_idx=0):
    """十字キー(Hat)の状態を取得。(x, y) タプル。x: -1=左/+1=右, y: -1=下/+1=上"""
    if not _HAS_JOY: return (0, 0)
    try:
        _pg.event.pump()
        return _JOY.get_hat(hat_idx)
    except Exception: return (0, 0)

# T-300 RS ボタン番号マッピング（PC接続モード）
# Btn 4  = 左パドル  → シフトダウン
# Btn 5  = 右パドル  → シフトアップ
# Btn 7  = R2ボタン  → ニトロ（ブースト）
# Btn 9  = OPTIONSボタン → ESC（ポーズ）
# Hat 0  = 十字キー  → WASD相当（メニュー操作）

# ──────────────────────────────────────────────────────────────────────────────
# Supabase Realtime Broadcast を使ったP2P中継クライアント
#
# 【セットアップ手順】
# 1. https://supabase.com で無料アカウント作成（クレカ不要）
# 2. 新規プロジェクト作成 → Settings > API で以下2つをコピー
#      SUPABASE_URL  = "https://xxxx.supabase.co"
#      SUPABASE_ANON_KEY = "eyJ..."
# 3. 下の2変数を書き換えるだけで動作（サーバー不要・常時起動・無料）
#
# 【Renderとの違い】
#   旧: Render中継サーバー → 15分スリープ→コールドスタートラグ、帯域制限
#   新: Supabase Realtime  → 常時起動、直接broadcast、ラグ30-80ms
# ──────────────────────────────────────────────────────────────────────────────
SUPABASE_URL      = "https://mreguvyqoehrnpdcebix.supabase.co"   # ← 自分のURLに変更
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1yZWd1dnlxb2Vocm5wZGNlYml4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4Njk4MzUsImV4cCI6MjA4ODQ0NTgzNX0.PiEvIFxYNySItxRd2hVlGyVoXpyMo6mgfJORyYUjK-0"                 # ← 自分のキーに変更

try:
    import websockets as _ws
    import asyncio as _asyncio
    _HAS_WS = True
except ImportError:
    _HAS_WS = False

import time as _time

try:
    import js # type: ignore
    IS_WEB = True
except ImportError:
    IS_WEB = False

# ファイルダイアログ (tkinter) - なくてもゲームは動く
try:
    import tkinter as _tk
    from tkinter import filedialog as _fd
    _HAS_TK = True
except Exception:
    _HAS_TK = False

def _ask_open(title, ftypes):
    if not _HAS_TK: return None
    try:
        r = _tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
        p = _fd.askopenfilename(title=title, filetypes=ftypes)
        r.destroy(); return p or None
    except Exception: return None

def _ask_save(title, default, ftypes):
    if not _HAS_TK: return None
    try:
        r = _tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
        p = _fd.asksaveasfilename(title=title, initialfile=default,
                                  defaultextension=".json", filetypes=ftypes)
        r.destroy(); return p or None
    except Exception: return None
