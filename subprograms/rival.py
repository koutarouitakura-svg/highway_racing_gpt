from .common import pyxel, math, random

class RivalCar:
    def __init__(self, color, start_pos, start_angle):
        self.x = start_pos[0]
        self.y = start_pos[1]
        self.angle = start_angle
        self.velocity = 0.0
        self.vx = 0.0               # 慣性速度ベクトルX
        self.vy = 0.0               # 慣性速度ベクトルY
        self.slip_angle = 0.0       # スリップ角
        self.gear = 0
        self.rpm = 0
        self.color = color
        self.u = 49
        self.w = 0
        self.boost_timer = 0
        self.lap = 0
        self.prev_idx = 0
        self.progress = 0
        self.is_stopping = False
        self.rubber_speed    = 1.0
        self.rubber_handling = 1.0
        self.perf_scale      = 1.0    # 個別性能スケール（0.7〜1.0）
        self.rocket_timer    = 0      # ロケットスタート残フレーム
        self.is_rocket_start = False  # ロケットスタート中フラグ
        self.prev_can_move   = False  # 前フレームのcan_move（スタート瞬間検出用）
        self.smoke_particles = []     # ロケットスタート煙パーティクル

    def update(self, course_points, gear_settings, is_offroad, can_move, player_progress=0,
               racing_line=None, player_speed_scale=1.0,
               map_image=None, ground_col=11, other_rivals=None):
        # カウントダウン中
        if not can_move:
            self.u, self.w = 49, 0
            self.prev_can_move = False
            return

        # スタート瞬間：80%の確率でロケットスタート
        if not self.prev_can_move and can_move:
            if random.random() < 0.80:
                self.is_rocket_start = True
                self.rocket_timer = 80
                # 初速を付与
                self.vx = math.cos(self.angle) * 0.30
                self.vy = math.sin(self.angle) * 0.30
        self.prev_can_move = True

        # ロケットスタートタイマー管理（60km/h≈0.15で終了）
        if self.rocket_timer > 0:
            self.rocket_timer -= 1
            spd_now = (self.vx**2 + self.vy**2) ** 0.5
            if spd_now > 0.15 or self.rocket_timer == 0:
                self.rocket_timer = 0
                self.is_rocket_start = False

        # ゴール後はゆっくり減速
        if self.is_stopping:
            self.vx *= 0.982
            self.vy *= 0.982
            self.velocity = (self.vx**2 + self.vy**2) ** 0.5
            self.x += self.vx
            self.y += self.vy
            self.u, self.w = 49, 0
            return

        n = len(course_points)

        # ── 最近傍インデックス探索（局所サーチでO(n)→O(k)に高速化）──
        # 前回インデックスの前後 SEARCH_RADIUS 点だけ調べる
        SEARCH_RADIUS = 20
        best_dist = float('inf')
        closest_idx = self.prev_idx
        for offset in range(-SEARCH_RADIUS, SEARCH_RADIUS + 1):
            i = (self.prev_idx + offset) % n
            px, py = course_points[i]
            d = (px - self.x) ** 2 + (py - self.y) ** 2
            if d < best_dist:
                best_dist = d
                closest_idx = i

        if self.prev_idx > n * 0.8 and closest_idx < n * 0.2:
            self.lap += 1
        elif self.prev_idx < n * 0.2 and closest_idx > n * 0.8:
            self.lap -= 1
        self.prev_idx = closest_idx
        self.progress = self.lap * n + closest_idx

        # ── ラバーバンドAI ──
        raw_diff = self.progress - player_progress
        if raw_diff >  n * 0.5: raw_diff -= n
        elif raw_diff < -n * 0.5: raw_diff += n
        progress_diff = raw_diff
        threshold = n * 0.03

        if progress_diff > threshold:
            excess = min((progress_diff - threshold) / (n * 0.25), 1.0)
            target_speed    = 1.0 - excess * 0.15
            target_handling = 1.0 - excess * 0.10
        elif progress_diff < -threshold:
            shortage = min((-progress_diff - threshold) / (n * 0.20), 1.0)
            target_speed    = 1.0 + shortage * 0.65
            target_handling = 1.0 + shortage * 0.40
        else:
            target_speed    = 1.0
            target_handling = 1.0

        lerp_rate = 0.06 if progress_diff < -threshold else 0.03
        self.rubber_speed    += (target_speed    - self.rubber_speed)    * lerp_rate
        self.rubber_handling += (target_handling - self.rubber_handling) * lerp_rate
        if abs(progress_diff) < threshold * 0.5:
            self.rubber_speed    += (1.0 - self.rubber_speed)    * 0.08
            self.rubber_handling += (1.0 - self.rubber_handling) * 0.08

        # ── ダート（コース外）判定 ──
        cx_i = int(self.x)
        cy_i = int(self.y)
        on_dirt = False
        if map_image is not None and 0 <= cx_i < 256 and 0 <= cy_i < 256:
            pix = map_image.pget(cx_i, cy_i)
            on_dirt = (pix == ground_col)

        # ダート走行時の速度ペナルティ（プレイヤーと同等の減速）
        dirt_speed_mult = 1.0
        if on_dirt:
            dirt_speed_mult = 0.72  # コース外では大きく減速

        # ── コース逸脱防止：前方ピクセルチェック & 境界修正 ──
        # コースライン上の最近傍点をターゲットとして「強制帰還」方向を計算する
        boundary_steer_bias = 0.0   # 正=右旋回追加, 負=左旋回追加
        if map_image is not None:
            # 現在地から前方 PROBE_DIST 分を複数点サンプリングして境界を予測
            PROBE_DIST = max(3.0, (self.vx**2 + self.vy**2)**0.5 * 20)
            fwd_x_probe = math.cos(self.angle)
            fwd_y_probe = math.sin(self.angle)
            side_x_probe = -math.sin(self.angle)
            side_y_probe =  math.cos(self.angle)

            # 前方3点 × 左右3本のレーンをサンプリング
            probe_hits_left  = 0
            probe_hits_right = 0
            for dist_frac in (0.4, 0.7, 1.0):
                dist = PROBE_DIST * dist_frac
                for lane_off, is_left_probe in ((-2.5, True), (0.0, False), (2.5, False)):
                    px_p = self.x + fwd_x_probe * dist + side_x_probe * lane_off
                    py_p = self.y + fwd_y_probe * dist + side_y_probe * lane_off
                    pi_p, pj_p = int(px_p), int(py_p)
                    if 0 <= pi_p < 256 and 0 <= pj_p < 256:
                        if map_image.pget(pi_p, pj_p) == ground_col:
                            if lane_off < 0:
                                probe_hits_left += 1
                            else:
                                probe_hits_right += 1

            # ヒット数に応じてステアリングバイアスを加算（反対側に曲げる）
            # 左側がダート → 右に曲げる（正バイアス）
            # 右側がダート → 左に曲げる（負バイアス）
            if probe_hits_left > 0 or probe_hits_right > 0:
                total_hits = probe_hits_left + probe_hits_right
                # 左側のヒット割合が高いほど右へ補正
                bias_strength = min(total_hits / 6.0, 1.0) * 0.08
                boundary_steer_bias = (probe_hits_left - probe_hits_right) / max(total_hits, 1) * bias_strength
            
            # 既にダートに入っていれば強制的にコース中心へ向かわせる
            if on_dirt:
                cp_x, cp_y = course_points[closest_idx]
                center_angle = math.atan2(cp_y - self.y, cp_x - self.x)
                center_diff  = (center_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
                boundary_steer_bias += center_diff * 0.25

        # ── 追い越し：前方ライバルを検知してラインをずらす ──
        overtake_offset = 0.0   # 横オフセット（正=右, 負=左）
        if other_rivals is not None:
            for other in other_rivals:
                if other is self:
                    continue
                dx_ov = other.x - self.x
                dy_ov = other.y - self.y
                dist_ov = math.hypot(dx_ov, dy_ov)
                if dist_ov < 6.0:
                    # 自分の前方にいる相手のみ対象
                    fwd_x_ov = math.cos(self.angle)
                    fwd_y_ov = math.sin(self.angle)
                    fwd_dot = dx_ov * fwd_x_ov + dy_ov * fwd_y_ov
                    if fwd_dot > 0.5:  # 前方にいる
                        # 相手が自分の左右どちらにいるか
                        side_x_ov = -math.sin(self.angle)
                        side_y_ov =  math.cos(self.angle)
                        lateral_pos = dx_ov * side_x_ov + dy_ov * side_y_ov
                        # 相手が右にいれば左へ、左にいれば右へ回避
                        avoid_dir = -1.0 if lateral_pos > 0 else 1.0
                        # 近いほど強く回避（最大±4.0の横オフセット）
                        strength = (1.0 - dist_ov / 6.0) * 4.0
                        overtake_offset += avoid_dir * strength

        # ── ステアリング・先読みにレーシングラインを使用 ──
        line = racing_line if racing_line is not None else course_points
        steer_look = max(6, int(8 + self.velocity * 15))

        # 追い越しオフセットをターゲット点に反映
        base_tx, base_ty = line[(closest_idx + steer_look) % n]
        if abs(overtake_offset) > 0.01:
            # ターゲット点に対して垂直方向へオフセットを加える
            next_pt = line[(closest_idx + steer_look + 4) % n]
            seg_dx  = next_pt[0] - base_tx
            seg_dy  = next_pt[1] - base_ty
            seg_len = math.hypot(seg_dx, seg_dy) or 1.0
            # 垂直方向（コース横断方向）
            perp_x = -seg_dy / seg_len
            perp_y =  seg_dx / seg_len
            # クランプ（大きすぎるオフセットはコース外に出る危険）
            ov_clamped = max(-3.5, min(overtake_offset, 3.5))
            tx = base_tx + perp_x * ov_clamped
            ty = base_ty + perp_y * ov_clamped
        else:
            tx, ty = base_tx, base_ty

        target_angle = math.atan2(ty - self.y, tx - self.x)
        angle_diff = (target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi

        spd = (self.vx**2 + self.vy**2) ** 0.5
        # 先読み距離：低速でも十分な先を見る（最低30点）
        brake_look = max(30, int(spd * 120))
        future_angles = []
        # サンプリング間隔を細かくして誤検知を防ぐ
        step = max(2, brake_look // 10)
        for fi in range(4, brake_look, step):
            fax, fay = line[(closest_idx + fi) % n]
            fbx, fby = line[(closest_idx + fi + 4) % n]
            fa = math.atan2(fby - fay, fbx - fax)
            future_angles.append(fa)
        max_corner = 0.0
        for i in range(1, len(future_angles)):
            da = abs((future_angles[i] - future_angles[i-1] + math.pi) % (2*math.pi) - math.pi)
            max_corner = max(max_corner, da)

        # ── ブースト ──
        if max_corner < 0.08 and spd > 0.25 and self.boost_timer <= 0:
            if random.random() < 0.008:
                self.boost_timer = 90
        boost_mult = 1.0
        if self.boost_timer > 0:
            self.boost_timer -= 1
            boost_mult = 1.4

        # ── グリップ係数 ──
        if is_offroad:
            grip_base      = 0.60
            traction_limit = 0.50
        else:
            grip_base      = 0.80
            traction_limit = 0.78
        grip_base *= self.rubber_handling

        # ── ステアリング（車体向きを回す）──
        if spd > 0.01:
            steer_max    = 0.055 if not is_offroad else 0.042
            speed_factor = (spd / 0.7) ** 1.2
            steer_rate   = steer_max / (1.0 + speed_factor * 1.3)
            steer_rate   = max(steer_rate, 0.007) * self.rubber_handling
        else:
            steer_rate = 0.0

        # 境界修正バイアスを angle_diff に加算してからステアリング判定
        effective_angle_diff = angle_diff + boundary_steer_bias
        if effective_angle_diff < -0.08:
            self.angle -= steer_rate
            self.u, self.w = -50, 26
        elif effective_angle_diff > 0.08:
            self.angle += steer_rate
            self.u, self.w = 50, 26
        else:
            self.u, self.w = 49, 0

        # ── 速度コントロール（先読みコーナーに基づく）──
        fwd_x = math.cos(self.angle)
        fwd_y = math.sin(self.angle)
        speed_along_fwd = self.vx * fwd_x + self.vy * fwd_y

        corner_severity = min(max_corner / 0.8, 1.0)
        straight_bonus = 1.0 + (1.0 - corner_severity) * 0.20
        if is_offroad:
            target_spd = 0.55 - corner_severity * 0.18
        else:
            target_spd = 0.70 - corner_severity * 0.20
        target_spd *= self.rubber_speed * boost_mult * player_speed_scale * straight_bonus
        # ダート走行ペナルティを速度目標に適用
        target_spd *= dirt_speed_mult

        need_brake = spd > target_spd + 0.02

        if need_brake:
            brake_force = min((spd - target_spd) * 0.15, 0.012)
            if spd > 0.001:
                self.vx -= (self.vx / spd) * brake_force
                self.vy -= (self.vy / spd) * brake_force
        else:
            gear_set   = gear_settings[self.gear]
            max_vel    = gear_set["max_vel"] * boost_mult * self.rubber_speed * player_speed_scale
            accel_rate = 0.002 * gear_set["accel"] * boost_mult * self.rubber_speed * player_speed_scale * 0.9
            # ロケットスタート追加加速
            if self.rocket_timer > 0:
                accel_rate += 0.006 * (self.rocket_timer / 80.0)

            # ギアシフト
            spd_rpm = spd / max_vel if max_vel > 0 else 0
            self.rpm += (min(spd_rpm, 1.0) - self.rpm) * 0.2
            if self.rpm > 0.85 and self.gear < 4:
                self.gear += 1
            elif self.rpm < 0.4 and self.gear > 0:
                self.gear -= 1

            # エンジンブレーキ（ギア上限超え）
            raw_rpm = spd / max_vel if max_vel > 0 else 0
            if raw_rpm > 1.0:
                eb = 1.0 - 0.008 * (raw_rpm - 1.0)
                self.vx *= max(eb, 0.94)
                self.vy *= max(eb, 0.94)

            self.vx += fwd_x * accel_rate
            self.vy += fwd_y * accel_rate

        # ── グリップ補正（横速度を車体向きに引き戻す）──
        if spd > 0.001:
            vel_angle = math.atan2(self.vy, self.vx)
            self.slip_angle = (vel_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
            slip_abs = abs(self.slip_angle)

            grip_peak = 0.38
            if slip_abs < grip_peak:
                grip_factor = grip_base * (slip_abs / grip_peak)
            else:
                over = min((slip_abs - grip_peak) / 0.5, 1.0)
                grip_factor = grip_base * (1.0 - over * 0.55)

            side_x = math.cos(self.angle + math.pi/2)
            side_y = math.sin(self.angle + math.pi/2)
            lateral_vel = self.vx * side_x + self.vy * side_y
            correction  = lateral_vel * grip_factor
            self.vx -= side_x * correction
            self.vy -= side_y * correction
        else:
            self.slip_angle = 0.0

        # 空気抵抗
        spd2 = (self.vx**2 + self.vy**2) ** 0.5
        drag = 1.0 - spd2 * 0.00086
        self.vx *= max(drag, 0.9986)
        self.vy *= max(drag, 0.9986)

        # 惰性減衰（アクセル放し）
        if not (abs(angle_diff) <= 0.35):
            pass  # ブレーキ処理済み
        else:
            self.vx *= 0.9992
            self.vy *= 0.9992

        self.velocity = (self.vx**2 + self.vy**2) ** 0.5
        self.x += self.vx
        self.y += self.vy

        # ロケットスタート中の煙パーティクル生成（ワールド座標）
        if self.is_rocket_start and self.rocket_timer > 0:
            burst = max(1, self.rocket_timer // 16)
            for _ in range(burst):
                # 車体後方方向に煙を出す
                back_x = self.x - math.cos(self.angle) * 0.3
                back_y = self.y - math.sin(self.angle) * 0.3
                self.smoke_particles.append({
                    "wx": back_x + random.uniform(-0.15, 0.15),
                    "wy": back_y + random.uniform(-0.15, 0.15),
                    "life": random.randint(10, 20),
                    "max_life": 20,
                    "size": random.uniform(1.5, 3.5),
                })
        # パーティクル更新（リスト内包表記でO(n)除去）
        for p in self.smoke_particles:
            p["life"] -= 1
            p["size"] += 0.2
        self.smoke_particles = [p for p in self.smoke_particles if p["life"] > 0]

    def draw_3d(self, cam_x, cam_y, cam_angle):
        # 道路描画と完全に一致する投影計算式
        horizon = 80
        cam_z = 40.0
        fov = 1.3
        scale_factor = 0.02

        dx = self.x - cam_x
        dy = self.y - cam_y

        sn = math.sin(cam_angle)
        cs = math.cos(cam_angle)

        # カメラ空間のローカル座標に変換
        local_z = dx * cs + dy * sn
        local_x = -dx * sn + dy * cs

        # ロケット煙のスクリーン投影描画
        for p in self.smoke_particles:
            pdx = p["wx"] - cam_x
            pdy = p["wy"] - cam_y
            plz =  pdx * cs + pdy * sn
            plx = -pdx * sn + pdy * cs
            if plz > 0.1:
                pdy_s = (cam_z * 100.0 * scale_factor) / plz
                psx   = pyxel.width / 2 + (plx * 100.0) / (fov * plz)
                psy   = horizon + pdy_s
                alpha = p["life"] / p["max_life"]
                col   = 7 if alpha > 0.6 else (13 if alpha > 0.3 else 5)
                r = max(1, int(p["size"] * (pdy_s / 62.0)))
                pyxel.circ(psx, psy, r, col)

        # カメラ空間のローカル座標に変換
        local_z = dx * cs + dy * sn
        local_x = -dx * sn + dy * cs

        # カメラの前方にある場合のみ描画
        if local_z > 0.1:
            # 道路式からの逆算でスクリーンY座標を計算
            dy_screen = (cam_z * 100.0 * scale_factor) / local_z
            screen_y = horizon + dy_screen
            
            # スクリーンX座標の計算
            px = (local_x * 100.0) / (fov * local_z)
            screen_x = (pyxel.width / 2) + px
            
            # 描画スケール（自車の描画位置 dy_screen=62 を基準(1.0)とする）
            # BASE = 80 / (CAR_HL*2) = 80/1.04 ≈ 76.92
            # → 衝突距離(local_z=1.04)のとき scale=1.0 = 自車と同じ大きさ
            scale = dy_screen / 76.92
            
            if 0.1 < scale < 5.0:
                # 接地感を出すための影（中心を screen_x, screen_y に配置）
                shadow_w = 40 * scale
                shadow_h = 10 * scale
                pyxel.elli(screen_x - shadow_w/2, screen_y - shadow_h/2, shadow_w, shadow_h, 0)
                
                # 車体の描画
                pyxel.pal(195, self.color)
                
                # ====================================================
                # 【ズレ修正】Pyxelのスケール仕様に合わせた正確な座標計算
                # 画像の高さ(24)の下端を、影の中心(screen_y)にピッタリ合わせる式
                base_y = screen_y - 12 - (12 * scale)
                
                # 画像の幅(self.u)の中心を、影の中心(screen_x)にピッタリ合わせる式
                base_x = screen_x - (abs(self.u) / 2)
                # ====================================================
                
                pyxel.blt(base_x, base_y, 0, 0, self.w, self.u, 24, 229, scale=scale)
                pyxel.pal()
