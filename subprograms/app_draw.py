from .common import pyxel
from .app_draw_core import AppDrawCoreMixin
from .app_draw_menu import AppDrawMenuMixin
from .app_draw_online import AppDrawOnlineMixin


class AppDrawMixin(
    AppDrawCoreMixin,
    AppDrawMenuMixin,
    AppDrawOnlineMixin,
):
    def draw_course_select_screen(self):
        W, H = pyxel.width, pyxel.height
        pyxel.rect(0, 0, W, H, 0)

        if self.is_grand_prix:
            cup = self.GRAND_PRIX_CUPS[self.selected_cup % len(self.GRAND_PRIX_CUPS)]
            results = self.stats.get("grand_prix_results", {}).get(cup["name"], {})

            pyxel.rect(0, 0, W, 14, 1)
            pyxel.text(W // 2 - 44, 4, "SELECT GRAND PRIX", 10)

            label = f"< {cup['name']}  ({self.selected_cup + 1}/{len(self.GRAND_PRIX_CUPS)}) >"
            pyxel.text((W - len(label) * 4) // 2, 18, label, 14)

            panel_x, panel_y = 18, 32
            panel_w, panel_h = 220, 108
            pyxel.rect(panel_x, panel_y, panel_w, panel_h, 0)
            pyxel.rectb(panel_x, panel_y, panel_w, panel_h, 7)

            for i, course_idx in enumerate(cup["courses"]):
                row_y = panel_y + 10 + i * 22
                pyxel.rect(panel_x + 8, row_y - 2, panel_w - 16, 16, 1 if i % 2 == 0 else 0)
                pyxel.text(panel_x + 14, row_y + 2, f"RACE {i + 1}", 6)
                pyxel.text(panel_x + 62, row_y + 2, self.COURSES[course_idx]["name"], 10 if i == 0 else 7)

            info_x = panel_x + 12
            info_y = panel_y + panel_h + 8
            if results:
                best_rank = results.get("best_rank", "-")
                best_points = results.get("best_points", 0)
                last_rank = results.get("last_rank", "-")
                last_points = results.get("last_points", 0)
                pyxel.text(info_x, info_y,     f"BEST : {best_rank} PLACE / {best_points}PT", 10)
                pyxel.text(info_x, info_y + 10, f"LAST : {last_rank} PLACE / {last_points}PT", 7)
            else:
                pyxel.text(info_x, info_y + 4, "NO CUP DATA YET", 5)

            pyxel.text(4, H - 16, "A/D: CUP", 6)
            blink_col = 10 if (pyxel.frame_count // 15) % 2 == 0 else 7
            pyxel.text((W - 72) // 2, H - 10, "SPACE: SELECT", blink_col)
            pyxel.text(W - 44, H - 16, "ESC: BACK", 5)
            return

        cd = self.COURSES[self.selected_course]
        course_name = cd["name"]
        total = len(self.COURSES)

        pyxel.rect(0, 0, W, 14, 1)
        pyxel.text(W // 2 - 36, 4, "SELECT COURSE", 10)

        label = f"< {course_name}  ({self.selected_course + 1}/{total}) >"
        pyxel.text((W - len(label) * 4) // 2, 18, label, 14)

        map_size = 140
        map_x = (W - map_size) // 2 - 16
        map_y = 28
        pyxel.rect(map_x, map_y, map_size, map_size, 0)
        pyxel.rectb(map_x - 1, map_y - 1, map_size + 2, map_size + 2, 5)
        pyxel.rectb(map_x - 2, map_y - 2, map_size + 4, map_size + 4, 7)

        scale = map_size / 256.0
        pts = self.smooth_points
        for dx_off, dy_off in ((0, 0), (1, 0), (0, 1)):
            for i in range(len(pts)):
                p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                pyxel.line(
                    map_x + p1[0] * scale + dx_off,
                    map_y + p1[1] * scale + dy_off,
                    map_x + p2[0] * scale + dx_off,
                    map_y + p2[1] * scale + dy_off,
                    cd["col_mid"],
                )

        sx = map_x + cd["start_pos"][0] * scale
        sy = map_y + cd["start_pos"][1] * scale
        pyxel.circ(sx, sy, 3, 8)
        pyxel.rectb(int(sx) - 3, int(sy) - 3, 7, 7, 10)

        rx = map_x + map_size + 8
        ry = map_y + 4
        maker_unlocked = self.stats.get("player_level", 0) >= 50
        if self.is_time_attack:
            best_txt = f"BEST:{self.best_lap_time:.2f}s" if self.best_lap_time else "BEST:---.--s"
            pyxel.text(rx, ry, best_txt, 10)

        if not self.is_time_attack and not self.is_grand_prix:
            pyxel.text(rx, ry + 14, f"LAPS: {self.goal_laps}", 11)
            pyxel.text(rx, ry + 22, "W/S:ADJ", 5)
        elif self.is_time_attack:
            pyxel.text(rx, ry + 14, "TIME", 9)
            pyxel.text(rx, ry + 22, "ATTACK", 9)

        if maker_unlocked:
            pyxel.rect(rx - 2, ry + 36, 46, 12, 1)
            pyxel.rectb(rx - 2, ry + 36, 46, 12, 14)
            pyxel.text(rx, ry + 39, "[E] MAKER", 14)

        pyxel.text(4, H - 16, "A/D: COURSE", 6)
        blink_col = 10 if (pyxel.frame_count // 15) % 2 == 0 else 7
        pyxel.text((W - 72) // 2, H - 10, "SPACE: SELECT", blink_col)
        pyxel.text(W - 44, H - 16, "ESC: BACK", 5)
        if self.selected_course >= self.DEFAULT_COURSE_COUNT:
            pyxel.text(4, H - 8, "[DEL]:DELETE", 8)
        if self.is_time_attack:
            pyxel.text(W - 56, H - 8, "[R]:RANKING", 9)

        if self.cs_del_confirm:
            cn = self.COURSES[self.selected_course]["name"]
            dw, dh = 180, 52
            ddx, ddy = (W - dw) // 2, (H - dh) // 2
            pyxel.rect(ddx, ddy, dw, dh, 0)
            pyxel.rectb(ddx, ddy, dw, dh, 8)
            msg = f"DELETE '{cn}'?"
            pyxel.text(ddx + (dw - len(msg) * 4) // 2, ddy + 8, msg, 8)
            pyxel.text(ddx + (dw - 84) // 2, ddy + 20, "This cannot be undone!", 5)
            blink = (pyxel.frame_count // 12) % 2 == 0
            pyxel.text(ddx + 16, ddy + 34, "SPACE/Y : DELETE", 8 if blink else 7)
            pyxel.text(ddx + 104, ddy + 34, "ESC/N", 6)
