from .common import _HAS_JOY, _joy_btn, _joy_hat, _pg, pyxel
from .app_update_menu import AppUpdateMenuMixin
from .app_update_online import AppUpdateOnlineMixin
from .app_update_race import AppUpdateRaceMixin


class AppUpdateMixin(
    AppUpdateMenuMixin,
    AppUpdateOnlineMixin,
    AppUpdateRaceMixin,
):
    def _update_virtual_joystick(self):
        is_play = self.state == self.STATE_PLAY

        if _HAS_JOY:
            _pg.event.pump()

            def edge(btn_idx, attr):
                now = _joy_btn(btn_idx)
                fired = now and not getattr(self, attr, False)
                setattr(self, attr, now)
                return fired

            b5_edge = edge(5, "_jprev_b5")
            b4_edge = edge(4, "_jprev_b4")
            b0_edge = edge(0, "_jprev_b0")
            b1_edge = edge(1, "_jprev_b1")

            hat_x, hat_y = _joy_hat(0)
            hat_x_prev = getattr(self, "_menu_hat_x_prev", 0)
            hat_y_prev = getattr(self, "_menu_hat_y_prev", 0)
            self._menu_hat_x_prev = hat_x
            self._menu_hat_y_prev = hat_y

            self._vjoy_up = (hat_y == 1) and (hat_y_prev != 1)
            self._vjoy_dn = (hat_y == -1) and (hat_y_prev != -1)
            self._vjoy_left = (hat_x == -1) and (hat_x_prev != -1)
            self._vjoy_right = (hat_x == 1) and (hat_x_prev != 1)
            self._vjoy_space = b5_edge
            self._vjoy_esc = b4_edge and not is_play
            self._vjoy_q = b0_edge and not is_play
            self._vjoy_e = b1_edge and not is_play
            return

        self._vjoy_space = False
        self._vjoy_esc = False
        self._vjoy_q = False
        self._vjoy_e = False
        self._vjoy_up = False
        self._vjoy_dn = False
        self._vjoy_left = False
        self._vjoy_right = False

    def _update_fade(self):
        if self.fade_dir == 0:
            return False

        self.fade_alpha += self.fade_dir * self.fade_speed
        if self.fade_dir == 1 and self.fade_alpha >= 255:
            self.fade_alpha = 255
            if self.fade_target is not None:
                self.state = self.fade_target
                if self.state == self.STATE_ONLINE_ENTRY:
                    self.online_join_active = False
                    self.online_join_input = ""
                self.fade_target = None
            self.fade_dir = -1
        elif self.fade_dir == -1 and self.fade_alpha <= 0:
            self.fade_alpha = 0
            self.fade_dir = 0
        return True

    def _update_state_course_select(self):
        maker_unlocked = self.stats.get("player_level", 0) >= 50
        if self.is_grand_prix:
            self.goal_laps = 3

        if self.cs_del_confirm:
            if (
                pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN)
                or self._vjoy_space
                or pyxel.btnp(pyxel.KEY_Y)
            ):
                self._delete_custom_course(self.selected_course)
                self.cs_del_confirm = False
                pyxel.play(1, 1)
            if pyxel.btnp(pyxel.KEY_N) or pyxel.btnp(pyxel.KEY_ESCAPE) or self._vjoy_esc:
                self.cs_del_confirm = False
                pyxel.play(1, 1)
            return

        if self.is_grand_prix:
            if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A) or self._vjoy_left:
                self.selected_cup = (self.selected_cup - 1) % len(self.GRAND_PRIX_CUPS)
                pyxel.play(1, 1)
            if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D) or self._vjoy_right:
                self.selected_cup = (self.selected_cup + 1) % len(self.GRAND_PRIX_CUPS)
                pyxel.play(1, 1)
        else:
            if pyxel.btnp(pyxel.KEY_LEFT) or pyxel.btnp(pyxel.KEY_A) or self._vjoy_left:
                self.selected_course = (self.selected_course - 1) % len(self.COURSES)
                self._build_map(self.selected_course)
                ranking = self.get_ta_ranking()
                self.best_lap_time = ranking[0] if ranking else self.best_times.get(self._course_key(), None)
                pyxel.play(1, 1)
            if pyxel.btnp(pyxel.KEY_RIGHT) or pyxel.btnp(pyxel.KEY_D) or self._vjoy_right:
                self.selected_course = (self.selected_course + 1) % len(self.COURSES)
                self._build_map(self.selected_course)
                ranking = self.get_ta_ranking()
                self.best_lap_time = ranking[0] if ranking else self.best_times.get(self._course_key(), None)
                pyxel.play(1, 1)

        if not self.is_time_attack and not self.is_grand_prix:
            if (
                pyxel.btnp(pyxel.KEY_UP, 10, 2)
                or pyxel.btnp(pyxel.KEY_W, 10, 2)
                or self._vjoy_up
            ):
                self.goal_laps = min(10, self.goal_laps + 1)
                pyxel.play(1, 1)
            if (
                pyxel.btnp(pyxel.KEY_DOWN, 10, 2)
                or pyxel.btnp(pyxel.KEY_S, 10, 2)
                or self._vjoy_dn
            ):
                self.goal_laps = max(1, self.goal_laps - 1)
                pyxel.play(1, 1)

        if pyxel.btnp(pyxel.KEY_SPACE) or self._vjoy_space:
            if self.is_grand_prix:
                self._apply_grand_prix_fixed_settings(self.selected_cup)
                self._prepare_grand_prix_for_start()
                self._prime_grand_prix_race()
                self.reset()
                self._start_fade(self.STATE_PLAY)
            else:
                self.time_sel_focus = 0
                self._start_fade(self.STATE_TIME_SELECT)
            pyxel.play(1, 2)
        if pyxel.btnp(pyxel.KEY_ESCAPE) or self._vjoy_esc:
            self._start_fade(self.STATE_MODE_SELECT)
            pyxel.play(1, 1)
        if (pyxel.btnp(pyxel.KEY_E) or self._vjoy_e) and not self.is_grand_prix:
            if not maker_unlocked:
                pyxel.play(1, 4)
                return
            self._maker_reset()
            self._start_fade(self.STATE_COURSE_MAKER)
            pyxel.play(1, 1)
        if (
            pyxel.btnp(pyxel.KEY_DELETE) or pyxel.btnp(pyxel.KEY_BACKSPACE)
        ) and (not self.is_grand_prix) and self.selected_course >= self.DEFAULT_COURSE_COUNT:
            self.cs_del_confirm = True
            pyxel.play(1, 1)
        if self.is_time_attack and pyxel.btnp(pyxel.KEY_R):
            self._start_fade(self.STATE_RANKING)
            pyxel.play(1, 2)

    def update(self):
        self._update_virtual_joystick()
        if self._update_fade():
            return

        if self.state == self.STATE_NAME_ENTRY:
            self._update_state_name_entry()
        elif self.state == self.STATE_TITLE:
            self._update_state_title()
        elif self.state == self.STATE_MENU:
            self._update_state_menu()
        elif self.state == self.STATE_OPTIONS:
            self._update_state_options()
        elif self.state == self.STATE_MODE_SELECT:
            self._update_state_mode_select()
        elif self.state == self.STATE_COURSE_SELECT:
            self._update_state_course_select()
        elif self.state == self.STATE_TIME_SELECT:
            self._update_state_time_select()
        elif self.state == self.STATE_COURSE_MAKER:
            self._update_state_course_maker()
        elif self.state == self.STATE_STATUS:
            self._update_state_status()
        elif self.state == self.STATE_RANKING:
            self._update_state_ranking()
        elif self.state == self.STATE_ONLINE_ENTRY:
            self._update_state_online_entry()
        elif self.state == self.STATE_ONLINE_LOBBY:
            self._update_state_online_lobby()
        elif self.state == self.STATE_CUSTOMIZE:
            self._update_state_customize()
        elif self.state == self.STATE_PAUSE:
            self._update_state_pause()
        elif self.state == self.STATE_PLAY:
            self._update_state_play()
