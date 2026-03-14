from .common import pyxel, math, random, json, os, sys, base64, IS_WEB, _ask_open, _ask_save, _HAS_JOY, _pg, _joy_axis, _joy_btn, _joy_hat, SUPABASE_URL, SUPABASE_ANON_KEY
try:
    import js
except ImportError:
    js = None
class AppMakerMixin:
        def _maker_reset(self):
            """コースメーカー状態を初期化"""
            self.mk_mode      = self._CM_DRAW
            self.mk_road      = 0
            self.mk_cx        = 128.0
            self.mk_cy        = 96.0
            self.mk_spd       = 1.5
            self.mk_pts       = []
            self.mk_cps       = []
            self.mk_goal      = None
            self.mk_dir       = 0.0
            self.mk_smooth    = []
            self.mk_name_mode = False
            self.mk_name      = ""
            self.mk_msg       = ""
            self.mk_msg_timer = 0
            self.mk_del_idx   = -1
            self.mk_del_timer = 0
            self.mk_walls      = []    # 壁リスト: [{"x1","y1","x2","y2"}, ...]
            self.mk_wall_p1    = None  # 壁の始点 (x,y) or None

        def _maker_msg(self, txt, frames=100):
            self.mk_msg       = txt
            self.mk_msg_timer = frames

        def _maker_refresh_smooth(self):
            if len(self.mk_pts) >= 3:
                self.mk_smooth = self._calc_smooth_points(self.mk_pts)
            else:
                self.mk_smooth = []

        def _maker_build_course(self, name):
            """現在のメーカー状態からコース定義 dict を生成"""
            rp = self._ROAD_PRESETS[self.mk_road]
            pts = self.mk_pts
            # ゴール位置 (未設定なら先頭点)
            gx, gy = self.mk_goal if self.mk_goal else pts[0]
            # チェックポイント (未設定なら等間隔4点を自動生成)
            cps = list(self.mk_cps)
            if not cps:
                n = len(pts)
                cps = [pts[n // 4 % n], pts[n // 2 % n], pts[3 * n // 4 % n], (gx, gy)]
            return {
                "name":           name,
                "control_points": [list(p) for p in pts],
                "checkpoints":    [list(p) for p in cps],
                "start_pos":      [float(gx), float(gy)],
                "start_angle":    self.mk_dir,
                "start_line":     [float(gx), float(gy), float(self.mk_dir),
                                   self._ROAD_PRESETS[self.mk_road]["road_outer"]],
                "road_outer":     rp["road_outer"],
                "road_mid":       rp["road_mid"],
                "road_inner":     rp["road_inner"],
                "out_distance":   rp["out_distance"],
                "col_outer":      rp["col_outer"],
                "col_mid":        rp["col_mid"],
                "col_inner":      rp["col_inner"],
                "col_ground":     rp["col_ground"],
                "night_remap":    dict(rp["night_remap"]),
                "walls":          [dict(w) for w in self.mk_walls],
            }

        def _maker_save(self):
            """コースを COURSES に登録してファイル保存"""
            name = self.mk_name.strip().upper()
            if not name:
                self._maker_msg("NAME REQUIRED!")
                return False
            if len(self.mk_pts) < 4:
                self._maker_msg("NEED 4+ POINTS!")
                return False
            cd = self._maker_build_course(name)
            self._normalize_course_definition(cd)
            # 同名コースは上書き
            for i, c in enumerate(self.COURSES):
                if c["name"] == name:
                    self.COURSES[i] = cd
                    sm = self._calc_smooth_points(cd["control_points"])
                    rl = self._calc_racing_line(sm, cd["road_outer"])
                    self.course_data[i] = {"smooth_points": sm, "racing_line": rl}
                    self._save_custom_courses()
                    self._maker_msg("OVERWRITTEN!")
                    return True
            # 新規追加
            self.COURSES.append(cd)
            sm = self._calc_smooth_points(cd["control_points"])
            rl = self._calc_racing_line(sm, cd["road_outer"])
            self.course_data.append({"smooth_points": sm, "racing_line": rl})
            self._save_custom_courses()
            self._maker_msg("SAVED!")
            return True

        def _maker_update(self):
            """コースメーカーの毎フレーム処理"""
            if self.mk_msg_timer > 0:
                self.mk_msg_timer -= 1

            # ── 名前入力モード ───────────────────────────────────────────
            if self.mk_name_mode:
                for key, ch in self._CM_KEYS.items():
                    if pyxel.btnp(key) and len(self.mk_name) < 12:
                        self.mk_name += ch
                        pyxel.play(1, 1)
                if pyxel.btnp(pyxel.KEY_BACKSPACE) and self.mk_name:
                    self.mk_name = self.mk_name[:-1]
                if pyxel.btnp(pyxel.KEY_RETURN):
                    if self._maker_save():
                        # 保存成功→コース選択へ戻り、作ったコースを選択
                        self.mk_name_mode = False
                        self.selected_course = len(self.COURSES) - 1
                        # 同名上書きのときは最後とは限らないので名前で探す
                        nm = self.mk_name.strip().upper()
                        for i, c in enumerate(self.COURSES):
                            if c["name"] == nm:
                                self.selected_course = i
                                break
                        self._build_map(self.selected_course)
                        self.best_lap_time = self.best_times.get(self._course_key(), None)
                        self._start_fade(self.STATE_COURSE_SELECT)
                        pyxel.play(1, 2)
                if (pyxel.btnp(pyxel.KEY_ESCAPE) or self._vjoy_esc):
                    self.mk_name_mode = False
                return

            # ── 削除確認モード ───────────────────────────────────────────
            if self.mk_del_idx >= 0:
                self.mk_del_timer -= 1
                if self.mk_del_timer <= 0:
                    self.mk_del_idx = -1
                if pyxel.btnp(pyxel.KEY_Y):
                    self._delete_custom_course(self.mk_del_idx)
                    self.mk_del_idx = -1
                    self._maker_msg("DELETED!")
                    pyxel.play(1, 1)
                if pyxel.btnp(pyxel.KEY_N) or (pyxel.btnp(pyxel.KEY_ESCAPE) or self._vjoy_esc):
                    self.mk_del_idx = -1
                return

            # ── カーソル移動 (btn で連続移動) ──────────────────────────
            spd = self.mk_spd
            if pyxel.btn(pyxel.KEY_LEFT)  or pyxel.btn(pyxel.KEY_A): self.mk_cx -= spd
            if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D): self.mk_cx += spd
            if pyxel.btn(pyxel.KEY_UP)    or pyxel.btn(pyxel.KEY_W): self.mk_cy -= spd
            if pyxel.btn(pyxel.KEY_DOWN)  or pyxel.btn(pyxel.KEY_S): self.mk_cy += spd
            self.mk_cx = max(4.0, min(251.0, self.mk_cx))
            self.mk_cy = max(4.0, min(251.0, self.mk_cy))

            # カーソル速度 (Q/E キー)
            if pyxel.btnp(pyxel.KEY_Q) or self._vjoy_q and self.mk_spd > 0.5: self.mk_spd = round(self.mk_spd - 0.5, 1)
            if pyxel.btnp(pyxel.KEY_E) or self._vjoy_e and self.mk_spd < 5.0: self.mk_spd = round(self.mk_spd + 0.5, 1)

            cx, cy = int(self.mk_cx), int(self.mk_cy)

            # ── M: 編集モード切り替え ─────────────────────────────────
            if pyxel.btnp(pyxel.KEY_M):
                self.mk_mode = (self.mk_mode + 1) % 4
                labels = ["DRAW MODE", "CHECKPOINT MODE", "GOAL MODE", "WALL MODE"]
                self._maker_msg(labels[self.mk_mode], 80)
                if self.mk_mode != self._CM_WALL:
                    self.mk_wall_p1 = None
                pyxel.play(1, 1)

            # ── R: 進行方向を回転 (GOALが置かれていれば常に有効) ─────────
            if self.mk_goal is not None:
                step = math.pi / 8   # 22.5度ステップ (16方向)
                if pyxel.btnp(pyxel.KEY_R):
                    shift = pyxel.btn(pyxel.KEY_SHIFT)
                    self.mk_dir += -step if shift else step
                    self.mk_dir %= (2 * math.pi)
                    deg = int(round(math.degrees(self.mk_dir))) % 360
                    pyxel.play(1, 1)
                    self._maker_msg(f"DIR: {deg:3d}deg", 60)

            # ── T: 道路タイプ切り替え ───────────────────────────────────
            if pyxel.btnp(pyxel.KEY_T):
                self.mk_road = (self.mk_road + 1) % len(self._ROAD_PRESETS)
                self._maker_msg(f"ROAD: {self._ROAD_PRESETS[self.mk_road]['label']}", 80)
                pyxel.play(1, 1)

            # ── SPACE: 点を置く ─────────────────────────────────────────
            if pyxel.btnp(pyxel.KEY_SPACE) or self._vjoy_space:
                if self.mk_mode == self._CM_DRAW:
                    self.mk_pts.append((cx, cy))
                    self._maker_refresh_smooth()
                    pyxel.play(1, 1)
                elif self.mk_mode == self._CM_CP:
                    self.mk_cps.append((cx, cy))
                    self._maker_msg(f"CP {len(self.mk_cps)} SET", 80)
                    pyxel.play(1, 1)
                elif self.mk_mode == self._CM_GOAL:
                    self.mk_goal = (cx, cy)
                    self._maker_msg("GOAL SET", 80)
                    pyxel.play(1, 1)
                elif self.mk_mode == self._CM_WALL:
                    if self.mk_wall_p1 is None:
                        # 1点目を置く
                        self.mk_wall_p1 = (cx, cy)
                        self._maker_msg("WALL P1 SET - PLACE P2", 120)
                    else:
                        # 2点目で壁確定
                        x1, y1 = self.mk_wall_p1
                        self.mk_walls.append({"x1": x1, "y1": y1, "x2": cx, "y2": cy})
                        self.mk_wall_p1 = None
                        self._maker_msg(f"WALL {len(self.mk_walls)} SET", 80)
                    pyxel.play(1, 1)

            # ── Z: 直前の点を取り消し ───────────────────────────────────
            if pyxel.btnp(pyxel.KEY_Z):
                if self.mk_mode == self._CM_DRAW and self.mk_pts:
                    self.mk_pts.pop()
                    self._maker_refresh_smooth()
                    pyxel.play(1, 1)
                elif self.mk_mode == self._CM_CP and self.mk_cps:
                    self.mk_cps.pop()
                    pyxel.play(1, 1)
                elif self.mk_mode == self._CM_GOAL:
                    self.mk_goal = None
                    pyxel.play(1, 1)
                elif self.mk_mode == self._CM_WALL:
                    if self.mk_wall_p1 is not None:
                        self.mk_wall_p1 = None  # 置き中の始点をキャンセル
                    elif self.mk_walls:
                        self.mk_walls.pop()
                        self._maker_msg(f"WALL REMOVED", 60)
                    pyxel.play(1, 1)

            # ── C: 全点クリア (現在モードのみ) ─────────────────────────
            if pyxel.btnp(pyxel.KEY_C):
                if self.mk_mode == self._CM_DRAW:
                    self.mk_pts.clear(); self.mk_smooth.clear()
                elif self.mk_mode == self._CM_CP:
                    self.mk_cps.clear()
                elif self.mk_mode == self._CM_GOAL:
                    self.mk_goal = None
                elif self.mk_mode == self._CM_WALL:
                    self.mk_walls.clear()
                    self.mk_wall_p1 = None
                self._maker_msg("CLEARED", 60)
                pyxel.play(1, 1)

            # ── ENTER: コース名入力→保存 ────────────────────────────────
            if pyxel.btnp(pyxel.KEY_RETURN):
                if len(self.mk_pts) < 4:
                    self._maker_msg("NEED 4+ POINTS!", 120)
                else:
                    self.mk_name_mode = True
                    self.mk_name = ""
                pyxel.play(1, 1)

            # ── DEL: カスタムコース削除リスト表示 (選択中が4以降) ──────
            if pyxel.btnp(pyxel.KEY_DELETE):
                # コースメーカー内からは現在のカスタムコース一覧を削除できる
                # 削除したいコースを ←→ で選んで Y/N で確認
                # ここでは「コース選択で選ばれているコース」を削除対象とする
                if self.selected_course >= self.DEFAULT_COURSE_COUNT:
                    self.mk_del_idx   = self.selected_course
                    self.mk_del_timer = 200
                    self._maker_msg(f"DELETE '{self.COURSES[self.selected_course]['name']}'? Y/N", 200)
                else:
                    self._maker_msg("BUILT-IN COURSE!", 80)
                pyxel.play(1, 1)

            # ── ESC: コース選択へ戻る ───────────────────────────────────
            if (pyxel.btnp(pyxel.KEY_ESCAPE) or self._vjoy_esc):
                self._start_fade(self.STATE_COURSE_SELECT)
                self._build_map(self.selected_course)
                pyxel.play(1, 1)

        def _mk_wx(self, wx): return self._MK_MAP_X + wx * self._MK_SCALE

        def _mk_wy(self, wy): return self._MK_MAP_Y + wy * self._MK_SCALE

        def _maker_draw(self):
            """コースメーカー画面の描画"""
            MX, MY, MW, MH = self._MK_MAP_X, self._MK_MAP_Y, self._MK_MAP_W, self._MK_MAP_H
            SC = self._MK_SCALE
            rp = self._ROAD_PRESETS[self.mk_road]

            # ── 背景 ──
            pyxel.cls(1)

            # マップ領域背景 (地面色)
            pyxel.rect(MX, MY, MW, MH, rp["col_ground"])
            pyxel.rectb(MX - 1, MY - 1, MW + 2, MH + 2, 13)

            # ── スムーズプレビューライン ──
            if len(self.mk_smooth) >= 2:
                for i in range(len(self.mk_smooth)):
                    p1 = self.mk_smooth[i]
                    p2 = self.mk_smooth[(i + 1) % len(self.mk_smooth)]
                    pyxel.line(self._mk_wx(p1[0]), self._mk_wy(p1[1]),
                               self._mk_wx(p2[0]), self._mk_wy(p2[1]), rp["col_mid"])

            # ── 制御点 ──
            for i, (wx, wy) in enumerate(self.mk_pts):
                sx, sy = self._mk_wx(wx), self._mk_wy(wy)
                col = 9 if i == 0 else 8
                pyxel.pset(sx, sy, col)
                if i == 0:
                    pyxel.rectb(sx - 2, sy - 2, 5, 5, 9)
                if i % 8 == 0 and i > 0:
                    pyxel.text(sx + 1, sy - 4, str(i), 6)

            # ── チェックポイント (黄色 ◆) ──
            for i, (wx, wy) in enumerate(self.mk_cps):
                sx, sy = self._mk_wx(wx), self._mk_wy(wy)
                pyxel.rectb(sx - 2, sy - 2, 5, 5, 10)
                pyxel.pset(sx, sy, 10)

            # ── 壁（灰色の線分） ──
            for w in self.mk_walls:
                sx1 = self._mk_wx(w["x1"]); sy1 = self._mk_wy(w["y1"])
                sx2 = self._mk_wx(w["x2"]); sy2 = self._mk_wy(w["y2"])
                pyxel.line(int(sx1), int(sy1), int(sx2), int(sy2), 13)
                # 端点マーカー
                pyxel.rectb(int(sx1) - 1, int(sy1) - 1, 3, 3, 5)
                pyxel.rectb(int(sx2) - 1, int(sy2) - 1, 3, 3, 13)
            # 壁の置き中プレビュー（始点→カーソル）
            if self.mk_mode == self._CM_WALL and self.mk_wall_p1 is not None:
                sx1 = self._mk_wx(self.mk_wall_p1[0]); sy1 = self._mk_wy(self.mk_wall_p1[1])
                sx2 = self._mk_wx(self.mk_cx);         sy2 = self._mk_wy(self.mk_cy)
                blink_col = 13 if (pyxel.frame_count // 6) % 2 == 0 else 5
                pyxel.line(int(sx1), int(sy1), int(sx2), int(sy2), blink_col)
                pyxel.rectb(int(sx1) - 2, int(sy1) - 2, 5, 5, 13)

            # ── ゴールライン + 進行方向矢印 ──
            if self.mk_goal:
                gsx = self._mk_wx(self.mk_goal[0])
                gsy = self._mk_wy(self.mk_goal[1])

                # --- スタートラインの横棒（進行方向に対して垂直、道幅分） ---
                perp = self.mk_dir + math.pi / 2
                # 道幅に応じた長さ（road_outerをピクセル換算して両側に引く）
                road_half = self._ROAD_PRESETS[self.mk_road]["road_outer"] * 1.0
                # 市松模様のゴールライン（セグメント幅2px）
                seg = 2
                n_segs = max(4, int(road_half * 2 / seg))
                for i in range(-n_segs, n_segs + 1):
                    t = i * seg
                    # 垂直方向
                    bx0 = gsx + math.cos(perp) * t
                    by0 = gsy + math.sin(perp) * t
                    col_ = 7 if i % 2 == 0 else 0
                    # 進行方向に2px幅
                    for d in range(3):
                        px_ = bx0 + math.cos(self.mk_dir) * (d - 1)
                        py_ = by0 + math.sin(self.mk_dir) * (d - 1)
                        pyxel.pset(int(px_), int(py_), col_)

                # --- 進行方向矢印 ---
                adx = math.cos(self.mk_dir)
                ady = math.sin(self.mk_dir)
                tip_x = gsx + adx * 12
                tip_y = gsy + ady * 12
                pyxel.line(int(gsx), int(gsy), int(tip_x), int(tip_y), 10)
                head_len = 5; head_wide = 3
                hbx = tip_x - adx * head_len
                hby = tip_y - ady * head_len
                pdx = -ady * head_wide
                pdy =  adx * head_wide
                pyxel.line(int(tip_x), int(tip_y), int(hbx + pdx), int(hby + pdy), 10)
                pyxel.line(int(tip_x), int(tip_y), int(hbx - pdx), int(hby - pdy), 10)

                # --- ゴール中心マーカー ---
                pyxel.rectb(int(gsx) - 2, int(gsy) - 2, 5, 5, 10)

                # --- 方向テキスト ---
                deg = int(round(math.degrees(self.mk_dir))) % 360
                dir_names = {0:"N", 23:"NNE", 45:"NE", 68:"ENE",
                             90:"E", 113:"ESE", 135:"SE", 158:"SSE",
                             180:"S", 203:"SSW", 225:"SW", 248:"WSW",
                             270:"W", 293:"WNW", 315:"NW", 338:"NNW"}
                closest = min(dir_names, key=lambda d: abs((deg - d + 180) % 360 - 180))
                label = dir_names[closest]
                pyxel.text(int(gsx) + 5, int(gsy) - 10, f"{deg}°{label}", 10)

            # ── カーソル (点滅十字) ──
            sx, sy = self._mk_wx(self.mk_cx), self._mk_wy(self.mk_cy)
            cur_cols = [9, 10, 7, 13]   # DRAW=橙, CP=緑, GOAL=白, WALL=灰
            cc = cur_cols[self.mk_mode]
            if (pyxel.frame_count // 8) % 2 == 0:
                pyxel.line(sx - 5, sy, sx + 5, sy, cc)
                pyxel.line(sx, sy - 5, sx, sy + 5, cc)
            else:
                pyxel.pset(sx, sy, cc)

            # ── 右パネル ──
            PX = MX + MW + 6
            PY = MY

            # 編集モード（ハイライト付き）
            mode_labels = ["DRAW ", "CHKPT", "GOAL ", "WALL "]
            mode_cols   = [9, 10, 7, 13]
            for i, (ml, mc) in enumerate(zip(mode_labels, mode_cols)):
                iy = PY + i * 8
                if self.mk_mode == i:
                    pyxel.rect(PX - 1, iy - 1, 44, 8, 1)
                    pyxel.rectb(PX - 1, iy - 1, 44, 8, mc)
                    pyxel.text(PX + 1, iy, f">{ml}", mc)
                else:
                    pyxel.text(PX + 1, iy, f" {ml}", 5)

            # 道路タイプ
            rt_cols = [7, 9, 4]
            y = PY + 28
            pyxel.text(PX, y+3,     "ROAD:", 6)
            pyxel.text(PX, y + 11, self._ROAD_PRESETS[self.mk_road]["label"],
                       rt_cols[self.mk_road])

            # 状態表示
            y += 20
            pyxel.text(PX, y,      f"PTS:{len(self.mk_pts):3d}", 7)
            pyxel.text(PX, y + 8,  f"CP :{len(self.mk_cps):3d}", 10)
            goal_str = "SET" if self.mk_goal else "---"
            pyxel.text(PX, y + 16, f"GL :{goal_str}", 7 if self.mk_goal else 5)
            import math as _m
            deg = int(round(_m.degrees(self.mk_dir))) % 360
            pyxel.text(PX, y + 24, f"DIR:{deg:3d}", 10 if self.mk_goal else 5)
            if self.mk_goal:
                pyxel.text(PX, y + 32, "[R]:DIR", 6)
            pyxel.text(PX, y + 40, f"WL :{len(self.mk_walls):3d}", 13)
            pyxel.text(PX, y + 48, f"SPD:{self.mk_spd:.1f}", 6)

            # 操作ヒント
            y += 62
            hints = [
                ("ARROWS", "MOVE"),
                ("SPACE",  "SET PT"),
                ("Z",      "UNDO"),
                ("C",      "CLEAR"),
                ("M",      "MODE"),
                ("T",      "ROAD"),
                ("R",      "DIR+"),
                ("ENTER",  "SAVE"),
                ("DEL",    "DELETE"),
                ("ESC",    "BACK"),
            ]
            for i, (k, v) in enumerate(hints):
                pyxel.text(PX,      y + i * 7, k, 6)
                pyxel.text(PX + 28, y + i * 7, v, 5)

            # ── 削除確認ダイアログ ─────────────────────────────────────
            if self.mk_del_idx >= 0 and self.mk_del_idx < len(self.COURSES):
                cn = self.COURSES[self.mk_del_idx]["name"]
                ddw, ddh = 180, 52
                ddx = (pyxel.width - ddw) // 2
                ddy = (pyxel.height - ddh) // 2
                pyxel.rect(ddx, ddy, ddw, ddh, 0)
                pyxel.rectb(ddx, ddy, ddw, ddh, 8)
                msg = f"DELETE '{cn}'?"
                pyxel.text(ddx + (ddw - len(msg)*4) // 2, ddy + 8, msg, 8)
                pyxel.text(ddx + (ddw - 84)//2, ddy + 20, "This cannot be undone!", 5)
                blink = (pyxel.frame_count // 12) % 2 == 0
                pyxel.text(ddx + 20, ddy + 34, "Y : DELETE", 8 if blink else 7)
                pyxel.text(ddx + 96, ddy + 34, "N / ESC : KEEP", 6)

            # ── 名前入力ダイアログ ──────────────────────────────────────
            if self.mk_name_mode:
                dx, dy, dw, dh = 20, 72, 168, 50
                pyxel.rect(dx, dy, dw, dh, 0)
                pyxel.rectb(dx, dy, dw, dh, 14)
                pyxel.text(dx + 4, dy + 4, "ENTER COURSE NAME:", 14)
                # 入力ボックス
                pyxel.rect(dx + 4, dy + 16, dw - 8, 10, 1)
                pyxel.rectb(dx + 4, dy + 16, dw - 8, 10, 7)
                blink = (pyxel.frame_count // 15) % 2 == 0
                disp = self.mk_name + ("|" if blink else " ")
                pyxel.text(dx + 6, dy + 18, disp, 10)
                pyxel.text(dx + 4, dy + 30, "ENTER:SAVE  ESC:CANCEL", 6)
                # 同名上書き警告
                nm = self.mk_name.strip().upper()
                exists = any(c["name"] == nm for c in self.COURSES)
                if exists and nm:
                    pyxel.text(dx + 4, dy + 40, "!OVERWRITE EXISTING!", 8)

            # ── ステータスメッセージ ────────────────────────────────────
            if self.mk_msg_timer > 0:
                mc = 10 if self.mk_msg_timer > 40 else 6
                mw = len(self.mk_msg) * 4
                pyxel.text(MX + (MW - mw) // 2, MY + MH - 10, self.mk_msg, mc)
