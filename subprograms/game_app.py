from .app_course import AppCourseMixin
from .app_storage import AppStorageMixin
from .app_runtime import AppRuntimeMixin
from .app_update import AppUpdateMixin
from .app_draw import AppDrawMixin
from .app_maker import AppMakerMixin
import pyxel

class App(AppRuntimeMixin, AppCourseMixin, AppStorageMixin, AppUpdateMixin, AppDrawMixin, AppMakerMixin):
        DEBUG_INITIAL_CREDITS = 5_000_000   # 初期クレジット上乗せ量

        GEAR_SETTINGS = [
                    {"accel": 1.0,  "max_vel": 0.15},
                    {"accel": 0.7,  "max_vel": 0.30},
                    {"accel": 0.5,  "max_vel": 0.45},
                    {"accel": 0.35, "max_vel": 0.55},
                    {"accel": 0.30,  "max_vel": 0.70},
                ]

        COURSES = [
            {
                # ---- コース0: 筑波サーキット風 (オリジナル) ----
                "name": "TSUKUBA",
                "control_points": [
                    (110, 220), (150, 220), (190, 215), (210, 195),
                    (200, 165), (180, 155), (160, 140), (155, 115),
                    (175, 100), (200, 105), (220, 85),  (210, 50),
                    (185, 35),  (150, 45),  (100, 70),  (50, 95),
                    (30, 130),  (30, 180),  (60, 210)
                ],
                "checkpoints": [(155, 115), (50, 95), (30, 180), (125, 213)],
                "start_pos":   (125.0, 220.0),
                "start_angle": 0.0,
                "start_line":  (125, 213, 2, 15),
                "road_outer":  6,
                "road_mid":    5,
                "road_inner":  4,
                "out_distance": 60,
                "col_outer":   8,
                "col_mid":     7,
                "col_inner":   5,
                "col_ground":  11,
                "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
            },
            {
                # ---- コース1: テクニカルサーキット ----
                "name": "TECHNICAL",
                "control_points": [
                    (165, 178), (188, 172), (210, 168),
                    (228, 162), (238, 150), (232, 138),
                    (225, 120), (228, 95),  (225, 72),
                    (215, 52),  (195, 40),  (172, 36),
                    (148, 38),  (125, 40),  (105, 48),
                    (88, 58),   (75, 72),   (68, 88),
                    (58, 100),  (40, 105),  (28, 118),
                    (30, 132),  (45, 140),  (62, 135),
                    (72, 125),  (82, 140),  (90, 155),
                    (100, 168), (118, 175),
                    (142, 170), (155, 175),
                ],
                "checkpoints": [
                    (238, 150), (172, 36), (28, 118), (45, 140), (142, 170), (165, 178)
                ],
                "start_pos":   (165.0, 178.0),
                "start_angle": 0.0,
                "start_line":  (159, 171, 2, 14),
                "road_outer":  5,
                "road_mid":    4,
                "road_inner":  3,
                "out_distance": 50,
                "col_outer":   8,
                "col_mid":     7,
                "col_inner":   5,
                "col_ground":  11,
                "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
            },
            {
                # ---- コース2: オーバルスピードウェイ ----
                "name": "SPEEDWAY",
                "control_points": [
                    (128, 225), (162, 225), (196, 220), (220, 205),
                    (236, 182), (236, 148), (236, 112), (220, 80),
                    (196, 55),  (162, 40),  (128, 38),  (94, 40),
                    (60, 55),   (36, 80),   (20, 112),  (20, 148),
                    (20, 182),  (36, 205),  (60, 220),  (94, 225)
                ],
                "checkpoints": [
                    (236, 148), (128, 38), (20, 148), (128, 225)
                ],
                "start_pos":   (128.0, 225.0),
                "start_angle": 0.0,
                "start_line":  (122, 218, 2, 14),
                "road_outer":  8,
                "road_mid":    7,
                "road_inner":  6,
                "out_distance": 70,
                "col_outer":   8,
                "col_mid":     7,
                "col_inner":   5,
                "col_ground":  11,
                "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
            },
            {
                # ---- コース3: オフロードダートトレイル ----
                "name": "OFFROAD",
                "control_points": [
                    (120, 220), (148, 218), (172, 210), (190, 192),
                    (196, 168), (188, 144), (170, 128), (156, 105),
                    (162, 82),  (180, 65),  (194, 48),  (175, 30),
                    (148, 26),  (120, 34),  (94, 50),   (70, 70),
                    (55, 95),   (40, 122),  (36, 152),  (44, 178),
                    (62, 198),  (88, 214),  (108, 220)
                ],
                "checkpoints": [
                    (188, 144), (120, 34), (36, 152), (120, 220)
                ],
                "start_pos":   (120.0, 220.0),
                "start_angle": 0.0,
                "start_line":  (114, 213, 2, 14),
                "road_outer":  3,
                "road_mid":    2,
                "road_inner":  1,
                "out_distance": 40,
                "col_outer":   4,   # 暗い茶色(路肩の土)
                "col_mid":     9,   # オレンジ茶(轍の縁)
                "col_inner":   4,   # 茶色ダート路面
                "col_ground":  3,   # 暗い緑(下草・コースアウト色)
                "night_remap": {3: 1, 4: 2, 9: 4},
            },
        ]

        CAR_COLORS = [
            {"col": 195, "name": "WHITE",   "price": 0},    # デフォルト無料
            {"col": 12,  "name": "CYAN",    "price": 500},
            {"col": 10,  "name": "YELLOW",   "price": 500},
            {"col": 11,  "name": "GREEN",  "price": 500},
            {"col": 14,  "name": "PINK",    "price": 500},
            {"col": 8,   "name": "RED",     "price": 500},
            {"col": 9,   "name": "ORANGE",  "price": 500},
            {"col": 6,   "name": "BLUE",    "price": 500},
        ]

        _ROAD_PRESETS = [
            {"label": "NORMAL",  "road_outer": 5, "road_mid": 4, "road_inner": 3,
             "out_distance": 50, "col_outer": 8, "col_mid": 7, "col_inner": 5,
             "col_ground": 11, "night_remap": {11: 21, 5: 1, 7: 13, 8: 2}},
            {"label": "WIDE",    "road_outer": 8, "road_mid": 7, "road_inner": 6,
             "out_distance": 70, "col_outer": 8, "col_mid": 7, "col_inner": 5,
             "col_ground": 11, "night_remap": {11: 21, 5: 1, 7: 13, 8: 2}},
            {"label": "OFFROAD", "road_outer": 3, "road_mid": 2, "road_inner": 1,
             "out_distance": 40, "col_outer": 4, "col_mid": 9, "col_inner": 4,
             "col_ground": 3,  "night_remap": {3: 1, 4: 2, 9: 4}},
        ]

        _CM_DRAW = 0   # コース点

        _CM_CP   = 1   # チェックポイント

        _CM_GOAL = 2   # ゴールライン

        _CM_WALL = 3   # 壁

        _CM_KEYS = {
            pyxel.KEY_A:"A", pyxel.KEY_B:"B", pyxel.KEY_C:"C", pyxel.KEY_D:"D",
            pyxel.KEY_E:"E", pyxel.KEY_F:"F", pyxel.KEY_G:"G", pyxel.KEY_H:"H",
            pyxel.KEY_I:"I", pyxel.KEY_J:"J", pyxel.KEY_K:"K", pyxel.KEY_L:"L",
            pyxel.KEY_M:"M", pyxel.KEY_N:"N", pyxel.KEY_O:"O", pyxel.KEY_P:"P",
            pyxel.KEY_Q:"Q", pyxel.KEY_R:"R", pyxel.KEY_S:"S", pyxel.KEY_T:"T",
            pyxel.KEY_U:"U", pyxel.KEY_V:"V", pyxel.KEY_W:"W", pyxel.KEY_X:"X",
            pyxel.KEY_Y:"Y", pyxel.KEY_Z:"Z",
            pyxel.KEY_0:"0", pyxel.KEY_1:"1", pyxel.KEY_2:"2", pyxel.KEY_3:"3",
            pyxel.KEY_4:"4", pyxel.KEY_5:"5", pyxel.KEY_6:"6", pyxel.KEY_7:"7",
            pyxel.KEY_8:"8", pyxel.KEY_9:"9", pyxel.KEY_MINUS:"-",
        }

        _MK_MAP_X  = 8

        _MK_MAP_Y  = 8

        _MK_MAP_W  = 176

        _MK_MAP_H  = 176

        _MK_SCALE  = 176 / 256.0   # world(0-255) → screen(0-175)

