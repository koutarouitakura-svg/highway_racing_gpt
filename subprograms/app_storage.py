from .common import IS_WEB, json, os

try:
    import js  # type: ignore
except ImportError:
    js = None


class AppStorageMixin:
    def load_best_times(self):
        if IS_WEB:
            try:
                data = js.window.localStorage.getItem("highway_racer_best_times")
                if data:
                    return json.loads(data)
            except Exception:
                pass
            return {}

        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_best_times(self):
        if IS_WEB:
            try:
                js.window.localStorage.setItem(
                    "highway_racer_best_times", json.dumps(self.best_times)
                )
            except Exception:
                pass
            return

        try:
            with open(self.save_file, "w") as f:
                json.dump(self.best_times, f)
        except Exception:
            pass

    def _ghost_file_path(self):
        name = self.COURSES[self.selected_course]["name"].replace(" ", "_")
        return os.path.join(os.path.dirname(self.save_file), f"ghost_{name}.json")

    def save_ghost(self, frames):
        sample = 2 if len(frames) > 6000 else 1
        data = {"frames": frames[::sample], "sample": sample}

        if IS_WEB:
            try:
                key = f"highway_racer_ghost_{self.COURSES[self.selected_course]['name']}"
                js.window.localStorage.setItem(key, json.dumps(data))
            except Exception:
                pass
            return

        try:
            with open(self._ghost_file_path(), "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def load_ghost(self):
        raw = None

        if IS_WEB:
            try:
                key = f"highway_racer_ghost_{self.COURSES[self.selected_course]['name']}"
                data = js.window.localStorage.getItem(key)
                if data:
                    raw = json.loads(data)
            except Exception:
                pass
        else:
            path = self._ghost_file_path()
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        raw = json.load(f)
                except Exception:
                    pass

        if raw is None:
            return [], 1
        if isinstance(raw, dict) and "frames" in raw:
            return raw["frames"], int(raw.get("sample", 1))
        if isinstance(raw, list):
            return raw, 5
        return [], 1

    def _online_broadcast_settings(self):
        if self.online_client and self.online_client.connected:
            self.online_client.send_priority(
                {
                    "type": "settings",
                    "player_id": self.online_my_id,
                    "course_idx": self.selected_course,
                    "night": self.is_night_mode,
                    "laps": self.goal_laps,
                    "course_name": self.COURSES[self.selected_course]["name"],
                }
            )

    def _set_share_msg(self, msg, frames=150):
        self._share_msg = msg
        self._share_msg_timer = frames

    def export_ghost(self):
        return None

    def import_ghost(self):
        return None

    def export_course(self):
        return None

    def import_course(self):
        return None

    def _ta_ranking_key(self, idx=None):
        i = self.selected_course if idx is None else idx
        return f"ta_ranking_{self.COURSES[i]['name']}"

    def get_ta_ranking(self, idx=None):
        return self.best_times.get(self._ta_ranking_key(idx), [])

    def add_ta_record(self, lap_time):
        key = self._ta_ranking_key()
        ranking = self.best_times.get(key, [])
        old_best = ranking[0] if ranking else None
        ranking.append(lap_time)
        ranking.sort()
        ranking = ranking[:5]
        self.best_times[key] = ranking
        self.best_lap_time = ranking[0]
        self.best_times[self._course_key()] = ranking[0]
        self.save_best_times()
        return old_best is None or lap_time < old_best

    def load_credits(self):
        bonus = self._initial_credit_bonus()
        if IS_WEB:
            try:
                data = js.window.localStorage.getItem("highway_racer_credits")
                if data:
                    return int(json.loads(data)) + bonus
            except Exception:
                pass
            return bonus

        if os.path.exists(self.credits_file):
            try:
                with open(self.credits_file, "r") as f:
                    return int(json.load(f)) + bonus
            except Exception:
                pass
        return bonus

    def save_credits(self):
        if IS_WEB:
            try:
                js.window.localStorage.setItem(
                    "highway_racer_credits", json.dumps(self.credits)
                )
            except Exception:
                pass
            return

        try:
            with open(self.credits_file, "w") as f:
                json.dump(self.credits, f)
        except Exception:
            pass

    def load_stats(self):
        default = {
            "race_count": 0,
            "first_count": 0,
            "total_credits": 0,
            "total_distance": 0.0,
            "total_frames": 0,
            "player_level": 0,
            "player_xp": 0,
            "grand_prix_results": {},
        }

        if IS_WEB:
            try:
                data = js.window.localStorage.getItem("highway_racer_stats")
                if data:
                    default.update(json.loads(data))
            except Exception:
                pass
            return default

        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r") as f:
                    default.update(json.load(f))
            except Exception:
                pass
        return default

    def save_stats(self):
        if IS_WEB:
            try:
                js.window.localStorage.setItem(
                    "highway_racer_stats", json.dumps(self.stats)
                )
            except Exception:
                pass
            return

        try:
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f)
        except Exception:
            pass

    def load_options(self):
        default = {
            "map_pixel_size": 1,
            "wheel_sensitivity": 5,
            "player_name": "PLAYER",
        }

        if IS_WEB:
            try:
                data = js.window.localStorage.getItem("highway_racer_options")
                if data:
                    default.update(json.loads(data))
            except Exception:
                pass
        else:
            if os.path.exists(self.options_file):
                try:
                    with open(self.options_file, "r") as f:
                        default.update(json.load(f))
                except Exception:
                    pass

        self.map_pixel_size = max(1, min(4, int(default.get("map_pixel_size", 1))))
        self.wheel_sensitivity = max(
            1, min(10, int(default.get("wheel_sensitivity", 5)))
        )

        name = str(default.get("player_name", "PLAYER")).strip()
        self.player_name = name[:12] if name else "PLAYER"
        self.player_name_input = self.player_name
        self.player_name_editing = False

    def save_options(self):
        data = {
            "map_pixel_size": self.map_pixel_size,
            "wheel_sensitivity": self.wheel_sensitivity,
            "player_name": getattr(self, "player_name", "PLAYER"),
        }

        if IS_WEB:
            try:
                js.window.localStorage.setItem("highway_racer_options", json.dumps(data))
            except Exception:
                pass
            return

        try:
            with open(self.options_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def load_car_data(self):
        default = {
            "engine_lv": 1,
            "brake_lv": 1,
            "weight_lv": 1,
            "owned_colors": [0],
            "color_idx": 0,
        }

        if IS_WEB:
            try:
                data = js.window.localStorage.getItem("highway_racer_car_data")
                if data:
                    default.update(json.loads(data))
            except Exception:
                pass
        else:
            if os.path.exists(self.car_data_file):
                try:
                    with open(self.car_data_file, "r") as f:
                        default.update(json.load(f))
                except Exception:
                    pass

        idx = default.get("color_idx", 0)
        if 0 <= idx < len(self.CAR_COLORS):
            self.car_color = self.CAR_COLORS[idx]["col"]
        return default

    def save_car_data(self):
        self.car_data["color_idx"] = self.cust_color_sel

        if IS_WEB:
            try:
                js.window.localStorage.setItem(
                    "highway_racer_car_data", json.dumps(self.car_data)
                )
            except Exception:
                pass
            return

        try:
            with open(self.car_data_file, "w") as f:
                json.dump(self.car_data, f)
        except Exception:
            pass

    def get_perf_mult(self):
        def lv_to_mult(lv):
            return 0.60 + (lv - 1) * (0.60 / 9.0)

        eng = lv_to_mult(self.car_data["engine_lv"])
        brk = lv_to_mult(self.car_data["brake_lv"])
        wgt = lv_to_mult(self.car_data["weight_lv"])
        eng_handling_pen = 1.0 - (self.car_data["engine_lv"] - 1) * 0.025

        return {
            "accel": eng * wgt,
            "max_vel": eng * wgt,
            "brake": brk * wgt,
            "handling": eng_handling_pen * wgt,
            "grip": wgt,
        }
