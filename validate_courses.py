import math
import argparse
from dataclasses import dataclass

from subprograms.app_course import AppCourseMixin
from subprograms.game_app import App


@dataclass
class Issue:
    kind: str
    course: str
    seg_a: int
    seg_b: int
    value: float


class _CourseTools(AppCourseMixin):
    pass


def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p, eps=1e-9):
    return (
        min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps
        and abs(_orient(a, b, p)) <= eps
    )


def _segments_intersect(a1, a2, b1, b2):
    o1 = _orient(a1, a2, b1)
    o2 = _orient(a1, a2, b2)
    o3 = _orient(b1, b2, a1)
    o4 = _orient(b1, b2, a2)

    if (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0):
        return True

    return (
        _on_segment(a1, a2, b1)
        or _on_segment(a1, a2, b2)
        or _on_segment(b1, b2, a1)
        or _on_segment(b1, b2, a2)
    )


def _point_segment_distance(p, a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    len2 = dx * dx + dy * dy
    if len2 <= 1e-9:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2
    t = max(0.0, min(1.0, t))
    proj = (a[0] + dx * t, a[1] + dy * t)
    return math.hypot(p[0] - proj[0], p[1] - proj[1])


def _segment_distance(a1, a2, b1, b2):
    if _segments_intersect(a1, a2, b1, b2):
        return 0.0
    return min(
        _point_segment_distance(a1, b1, b2),
        _point_segment_distance(a2, b1, b2),
        _point_segment_distance(b1, a1, a2),
        _point_segment_distance(b2, a1, a2),
    )


def _cyclic_gap(i, j, total):
    diff = abs(i - j)
    return min(diff, total - diff)


def validate_course(course, tools):
    issues = []
    points = tools._calc_smooth_points(course["control_points"])
    total = len(points)
    road_outer = float(course["road_outer"])
    overlap_limit = road_outer * 2.2

    for i in range(total):
        a1 = points[i]
        a2 = points[(i + 1) % total]
        for j in range(i + 1, total):
            if _cyclic_gap(i, j, total) <= 8:
                continue
            if _cyclic_gap(i + 1, j, total) <= 8:
                continue
            b1 = points[j]
            b2 = points[(j + 1) % total]

            if _segments_intersect(a1, a2, b1, b2):
                issues.append(Issue("intersect", course["name"], i, j, 0.0))
                continue

            dist = _segment_distance(a1, a2, b1, b2)
            if dist < overlap_limit:
                issues.append(Issue("overlap", course["name"], i, j, dist))

    return issues


def _raster_overlap_pairs(points, road_outer):
    local_gap = 18
    grid = [[None for _ in range(256)] for _ in range(256)]
    overlaps = set()

    for i, (x, y) in enumerate(points):
        cx = int(round(x))
        cy = int(round(y))
        r = int(math.ceil(road_outer))
        for py in range(max(0, cy - r), min(255, cy + r) + 1):
            for px in range(max(0, cx - r), min(255, cx + r) + 1):
                if (px - x) * (px - x) + (py - y) * (py - y) > road_outer * road_outer:
                    continue
                prev = grid[py][px]
                if prev is None:
                    grid[py][px] = i
                    continue
                if _cyclic_gap(prev, i, len(points)) > local_gap:
                    a, b = sorted((prev, i))
                    overlaps.add((a, b))
    return overlaps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--course", help="Only validate one course name")
    args = parser.parse_args()

    tools = _CourseTools()
    issues = []
    for course in App.COURSES:
        if args.course and course["name"].upper() != args.course.upper():
            continue
        issues.extend(validate_course(course, tools))
        points = tools._calc_smooth_points(course["control_points"])
        for seg_a, seg_b in sorted(_raster_overlap_pairs(points, float(course["road_outer"]))):
            issues.append(Issue("raster_overlap", course["name"], seg_a, seg_b, 0.0))

    if not issues:
        print("No intersections or overlap-risk pairs detected.")
        return

    priority = {"intersect": 0, "raster_overlap": 1, "overlap": 2}
    issues.sort(key=lambda item: (item.course, priority.get(item.kind, 9), item.value))
    for issue in issues[:200]:
        if issue.kind == "intersect":
            print(
                f"{issue.course}: INTERSECT seg {issue.seg_a} with seg {issue.seg_b}"
            )
        elif issue.kind == "raster_overlap":
            print(
                f"{issue.course}: ROAD_OVERLAP sample {issue.seg_a} with sample {issue.seg_b}"
            )
        else:
            print(
                f"{issue.course}: OVERLAP seg {issue.seg_a} with seg {issue.seg_b}"
                f" distance={issue.value:.2f}"
            )

    if len(issues) > 200:
        print(f"... {len(issues) - 200} more issues omitted")


if __name__ == "__main__":
    main()
