from .app_course import AppCourseMixin
from .app_storage import AppStorageMixin
from .app_runtime import AppRuntimeMixin
from .app_update import AppUpdateMixin
from .app_draw import AppDrawMixin
from .app_maker import AppMakerMixin
import math
import pyxel


_PAVED_NARROW = {
    "road_outer": 5,
    "road_mid": 4,
    "road_inner": 3,
    "out_distance": 50,
    "col_outer": 8,
    "col_mid": 7,
    "col_inner": 5,
    "col_ground": 11,
    "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
}

_PAVED_TIGHT = {
    "road_outer": 4,
    "road_mid": 3,
    "road_inner": 2,
    "out_distance": 42,
    "col_outer": 8,
    "col_mid": 7,
    "col_inner": 5,
    "col_ground": 11,
    "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
}

_PAVED_FLOW = {
    "road_outer": 6,
    "road_mid": 5,
    "road_inner": 4,
    "out_distance": 58,
    "col_outer": 8,
    "col_mid": 7,
    "col_inner": 5,
    "col_ground": 11,
    "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
}

_PAVED_FAST = {
    "road_outer": 7,
    "road_mid": 6,
    "road_inner": 5,
    "out_distance": 68,
    "col_outer": 8,
    "col_mid": 7,
    "col_inner": 5,
    "col_ground": 11,
    "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
}

_OFFROAD_STYLE = {
    "road_outer": 3,
    "road_mid": 2,
    "road_inner": 1,
    "out_distance": 40,
    "col_outer": 4,
    "col_mid": 9,
    "col_inner": 4,
    "col_ground": 3,
    "night_remap": {3: 1, 4: 2, 9: 4},
}

_OFFROAD_TIGHT = {
    "road_outer": 2,
    "road_mid": 2,
    "road_inner": 1,
    "out_distance": 32,
    "col_outer": 4,
    "col_mid": 9,
    "col_inner": 4,
    "col_ground": 3,
    "night_remap": {3: 1, 4: 2, 9: 4},
}

_OFFROAD_FAST = {
    "road_outer": 4,
    "road_mid": 3,
    "road_inner": 2,
    "out_distance": 52,
    "col_outer": 4,
    "col_mid": 9,
    "col_inner": 4,
    "col_ground": 3,
    "night_remap": {3: 1, 4: 2, 9: 4},
}


def _build_point_course(name, control_points, style, *, checkpoint_indices=None, scenery=None):
    points = [tuple(pt) for pt in control_points]
    sx, sy = points[0]
    nx, ny = points[1]
    start_angle = math.atan2(ny - sy, nx - sx)

    if checkpoint_indices is None:
        count = 6 if len(points) >= 18 else 5
        checkpoint_indices = [round(len(points) * i / count) % len(points) for i in range(1, count)]
        checkpoint_indices.append(0)

    checkpoints = [points[idx % len(points)] for idx in checkpoint_indices]
    course = {
        "name": name,
        "control_points": points,
        "checkpoints": checkpoints,
        "start_pos": (float(sx), float(sy)),
        "start_angle": start_angle,
        "start_line": [float(sx), float(sy), float(start_angle), style["road_outer"]],
        "scenery": scenery or {"theme": "default"},
    }
    course.update(style)
    return course


def _build_wave_course(
    name,
    style,
    *,
    base_radius,
    amplitudes,
    frequencies,
    phases,
    count=24,
    center=(128, 128),
    stretch=(1.0, 0.82),
    angle_offset=-90,
    scenery=None,
):
    points = []
    for i in range(count):
        deg = angle_offset + (360.0 * i / count)
        ang = math.radians(deg)
        radius = base_radius
        for amp, freq, phase in zip(amplitudes, frequencies, phases):
            radius += amp * math.sin(math.radians(freq * deg) + phase)
        x = center[0] + math.cos(ang) * radius * stretch[0]
        y = center[1] + math.sin(ang) * radius * stretch[1]
        points.append((int(round(max(18, min(238, x)))), int(round(max(18, min(238, y))))))

    start_idx = max(range(len(points)), key=lambda idx: points[idx][1])
    points = points[start_idx:] + points[:start_idx]
    return _build_point_course(name, points, style, scenery=scenery)


class App(AppRuntimeMixin, AppCourseMixin, AppStorageMixin, AppUpdateMixin, AppDrawMixin, AppMakerMixin):
        DEBUG_INITIAL_CREDITS = 5_000_000   # ???????????????????
        GEAR_SETTINGS = [
                    {"accel": 1.0,  "max_vel": 0.15},
                    {"accel": 0.7,  "max_vel": 0.30},
                    {"accel": 0.5,  "max_vel": 0.45},
                    {"accel": 0.35, "max_vel": 0.55},
                    {"accel": 0.30,  "max_vel": 0.70},
                ]

        COURSES = [
            _build_wave_course(
                "TECHNICAL",
                _PAVED_TIGHT,
                base_radius=72,
                amplitudes=(12, 9, 5),
                frequencies=(3, 7, 11),
                phases=(0.2, 1.0, 0.5),
                count=30,
                center=(128, 134),
                stretch=(0.92, 0.92),
                scenery={"theme": "default"},
            ),
            _build_wave_course(
                "HARBOR",
                _PAVED_FAST,
                base_radius=90,
                amplitudes=(8, 4, 3),
                frequencies=(2, 4, 6),
                phases=(0.4, 1.0, 2.0),
                count=24,
                center=(132, 124),
                stretch=(1.18, 0.68),
                scenery={"theme": "harbor"},
            ),
            _build_point_course(
                "CANYON",
                [
                    (132, 210), (156, 210), (178, 206), (192, 194), (198, 176),
                    (202, 156), (214, 138), (228, 122), (236, 102), (232, 76),
                    (218, 56), (194, 44), (170, 46), (150, 42), (130, 46),
                    (110, 42), (90, 46), (68, 42), (42, 46), (24, 60),
                    (18, 84), (24, 108), (42, 120), (58, 132), (62, 150),
                    (54, 168), (36, 180), (18, 196), (14, 220), (24, 242),
                    (48, 252), (80, 248), (104, 234), (120, 220),
                ],
                _PAVED_NARROW,
                checkpoint_indices=[5, 10, 16, 22, 29, 0],
                scenery={"theme": "canyon"},
            ),
            _build_wave_course(
                "LAKESIDE",
                _PAVED_TIGHT,
                base_radius=84,
                amplitudes=(11, 5, 4),
                frequencies=(2, 3, 7),
                phases=(0.7, 2.1, 1.9),
                count=36,
                center=(126, 128),
                stretch=(1.14, 0.88),
                scenery={"theme": "lake"},
            ),
            _build_wave_course(
                "METRO",
                _PAVED_TIGHT,
                base_radius=82,
                amplitudes=(12, 8, 3),
                frequencies=(2, 8, 12),
                phases=(0.6, 1.8, 2.7),
                count=24,
                center=(128, 122),
                stretch=(1.06, 0.70),
                scenery={"theme": "city"},
            ),
            _build_wave_course(
                "PINE RIDGE",
                _PAVED_TIGHT,
                base_radius=74,
                amplitudes=(11, 9, 6),
                frequencies=(3, 6, 9),
                phases=(1.6, 0.3, 0.9),
                count=28,
                center=(122, 132),
                stretch=(0.90, 0.92),
                scenery={"theme": "forest"},
            ),
            _build_wave_course(
                "SEASIDE",
                _PAVED_FAST,
                base_radius=90,
                amplitudes=(14, 9, 5),
                frequencies=(2, 5, 9),
                phases=(0.1, 1.4, 2.3),
                count=30,
                center=(132, 122),
                stretch=(1.18, 0.72),
                scenery={"theme": "coast"},
            ),
            _build_wave_course(
                "SUNSET",
                _PAVED_FLOW,
                base_radius=76,
                amplitudes=(14, 7, 2),
                frequencies=(3, 6, 9),
                phases=(0.6, 1.4, 2.2),
                count=30,
                center=(126, 128),
                stretch=(1.00, 0.78),
                scenery={"theme": "sunset"},
            ),
            _build_point_course(
                "OFFROAD",
                [
                    (122, 224), (92, 220), (64, 210), (42, 194), (30, 170),
                    (32, 142), (46, 120), (68, 108), (92, 98), (108, 84),
                    (106, 64), (90, 48), (66, 44), (46, 56), (36, 78),
                    (40, 102), (56, 122), (82, 136), (112, 142), (144, 142),
                    (170, 132), (188, 114), (204, 98), (222, 104), (230, 126),
                    (226, 152), (208, 172), (184, 186), (162, 198), (150, 214),
                ],
                _OFFROAD_FAST,
                checkpoint_indices=[4, 9, 15, 21, 26, 0],
                scenery={"theme": "desert"},
            ),
            _build_wave_course(
                "DUNE TRAIL",
                _OFFROAD_FAST,
                base_radius=82,
                amplitudes=(12, 8, 4),
                frequencies=(3, 6, 10),
                phases=(0.4, 1.5, 0.7),
                count=28,
                center=(128, 136),
                stretch=(1.02, 0.80),
                scenery={"theme": "dunes"},
            ),
            _build_wave_course(
                "MESA RUN",
                _OFFROAD_TIGHT,
                base_radius=74,
                amplitudes=(10, 8, 5),
                frequencies=(3, 5, 8),
                phases=(0.8, 2.1, 1.2),
                count=26,
                center=(124, 132),
                stretch=(0.94, 0.90),
                scenery={"theme": "mesa"},
            ),
            _build_point_course(
                "FOREST DIRT",
                [
                    (118, 222), (146, 220), (170, 210), (186, 194), (190, 172),
                    (178, 156), (160, 146), (144, 130), (146, 112), (160, 98),
                    (176, 86), (174, 66), (156, 56), (132, 62), (108, 76),
                    (84, 90), (60, 104), (42, 126), (38, 150), (50, 172),
                    (70, 188), (90, 200), (102, 214),
                ],
                _OFFROAD_TIGHT,
                checkpoint_indices=[4, 9, 14, 18, 0],
                scenery={"theme": "forest_dirt"},
            ),
            _build_point_course(
                "BELTWAY",
                [
                    (124, 226), (160, 224), (196, 218), (222, 204), (236, 180),
                    (236, 148), (228, 116), (212, 88), (190, 64), (160, 48),
                    (126, 42), (92, 46), (62, 58), (38, 80), (22, 108),
                    (18, 140), (24, 172), (40, 198), (66, 216), (98, 224),
                ],
                _PAVED_FAST,
                checkpoint_indices=[4, 9, 14, 0],
                scenery={"theme": "beltway"},
            ),
            _build_wave_course(
                "CLIFFSIDE",
                _PAVED_TIGHT,
                base_radius=76,
                amplitudes=(12, 8, 5),
                frequencies=(2, 5, 9),
                phases=(1.0, 0.8, 2.2),
                count=26,
                center=(122, 130),
                stretch=(0.88, 0.96),
                scenery={"theme": "cliff"},
            ),
            _build_point_course(
                "TSUKUBA",
                [
                    (110, 220), (150, 220), (190, 215), (210, 195), (200, 165),
                    (180, 155), (160, 140), (155, 115), (175, 100), (200, 105),
                    (220, 85), (210, 50), (185, 35), (150, 45), (100, 70),
                    (50, 95), (30, 130), (30, 180), (60, 210),
                ],
                {
                    "road_outer": 6, "road_mid": 5, "road_inner": 4,
                    "out_distance": 60, "col_outer": 8, "col_mid": 7,
                    "col_inner": 5, "col_ground": 11,
                    "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
                },
                checkpoint_indices=[7, 15, 17, 0],
                scenery={"theme": "circuit"},
            ),
            _build_point_course(
                "SPEEDWAY",
                [
                    (128, 225), (162, 225), (196, 220), (220, 205), (236, 182),
                    (236, 148), (236, 112), (220, 80), (196, 55), (162, 40),
                    (128, 38), (94, 40), (60, 55), (36, 80), (20, 112),
                    (20, 148), (20, 182), (36, 205), (60, 220), (94, 225),
                ],
                {
                    "road_outer": 8, "road_mid": 7, "road_inner": 6,
                    "out_distance": 70, "col_outer": 8, "col_mid": 7,
                    "col_inner": 5, "col_ground": 11,
                    "night_remap": {11: 21, 5: 1, 7: 13, 8: 2},
                },
                checkpoint_indices=[5, 10, 15, 0],
                scenery={"theme": "oval"},
            ),
        ]
        DEFAULT_COURSE_COUNT = len(COURSES)
        GRAND_PRIX_CUPS = [
            {"name": "CITY CUP", "courses": [0, 1, 2, 3]},
            {"name": "TOURING CUP", "courses": [4, 5, 6, 7]},
            {"name": "DIRT CUP", "courses": [8, 9, 10, 11]},
            {"name": "LEGEND CUP", "courses": [12, 13, 14, 15]},
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

