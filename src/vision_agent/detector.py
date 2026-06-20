"""
src/vision_agent/detector.py

Lightweight, CPU-only detector. Per Green AI constraints (no heavy
GPU-dependent models), this uses classical computer vision rather than a
deep object detector:

  - Frame sampling at config["vision_agent"]["frame_sample_rate_hz"]
    (default 4 Hz) instead of full framerate.
  - Downscale to config["vision_agent"]["resize_to"] before any processing.
  - Background-subtraction-based motion detection (MOG2) to find moving
    regions (personnel / forklifts) and color/contour heuristics to
    approximate the policy's observable indicators:
      * pedestrian_movement      -> motion outside a defined "safe lane"
                                     band in the frame
      * equipment_intervention   -> motion close to a fixed "equipment
                                     zone" without a high-visibility
                                     (bright yellow/orange) color blob
                                     overlapping it
      * electrical_panel_management -> a fixed "panel zone" whose
                                     average brightness/edge-density
                                     indicates "open" vs "closed" state
      * forklift_load_management -> stacked-rectangle contour counting
                                     in a "load zone" to approximate
                                     block count

This is a deliberately simple, fully-documented, swappable baseline —
docs/GREEN_AI.md and the README state plainly that this is a heuristic
CPU detector, not a trained model, and that swapping in an ONNX model
later only requires changing this file's `detect_clip()` internals, not
its public interface.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from src.common.logging_utils import get_logger

logger = get_logger(__name__)

# Normalized (0-1) zone boxes (x1,y1,x2,y2) — placeholders representing a
# fixed-angle camera's typical zone layout. In a real deployment these are
# calibrated per camera; here they are config-overridable defaults so the
# detector is functional out of the box on the provided dataset.
DEFAULT_ZONES = {
    "walkway": (0.0, 0.6, 1.0, 1.0),
    "equipment": (0.35, 0.2, 0.75, 0.7),
    "panel": (0.0, 0.0, 0.2, 0.35),
    "forklift_load": (0.55, 0.1, 1.0, 0.55),
}

HI_VIS_LOWER = np.array([15, 120, 120])   # yellow/orange HSV lower bound
HI_VIS_UPPER = np.array([35, 255, 255])


@dataclass
class RawDetection:
    behavior_class: str
    timestamp_sec: float
    zone: str
    confidence: float
    personnel_present: bool
    description: str


def _zone_pixels(frame_shape, zone_norm):
    h, w = frame_shape[:2]
    x1, y1, x2, y2 = zone_norm
    return int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)


def _motion_in_zone(fg_mask, zone_px) -> float:
    x1, y1, x2, y2 = zone_px
    region = fg_mask[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    return float(np.count_nonzero(region)) / float(region.size)


def _hi_vis_ratio_in_zone(frame_bgr, zone_px) -> float:
    x1, y1, x2, y2 = zone_px
    region = frame_bgr[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, HI_VIS_LOWER, HI_VIS_UPPER)
    return float(np.count_nonzero(mask)) / float(mask.size)


def _panel_open_score(frame_gray, zone_px) -> float:
    x1, y1, x2, y2 = zone_px
    region = frame_gray[y1:y2, x1:x2]
    if region.size == 0:
        return 0.0
    edges = cv2.Canny(region, 50, 150)
    return float(np.count_nonzero(edges)) / float(edges.size)


def _stacked_block_count(frame_bgr, zone_px) -> int:
    x1, y1, x2, y2 = zone_px
    region = frame_bgr[y1:y2, x1:x2]
    if region.size == 0:
        return 0
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 40, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    big = [c for c in contours if cv2.contourArea(c) > 400]
    return len(big)


def detect_clip(
    clip_path: str,
    config: dict,
    zones: dict | None = None,
) -> list[RawDetection]:
    """
    Runs the full lightweight detection pass over one clip. Returns a list
    of RawDetection — one per frame-sample where a candidate violation
    pattern was found. The caller (VisionAgent) is responsible for mapping
    behavior_class -> the policy-derived label and grounding it via the
    PolicyAgent; this function only does the visual pattern matching.
    """
    va_cfg = config["vision_agent"]
    zones = zones or DEFAULT_ZONES
    sample_hz = va_cfg.get("frame_sample_rate_hz", 4)
    resize_to = tuple(va_cfg.get("resize_to", [640, 360]))
    uncertainty_margin = va_cfg.get("uncertainty_margin", 0.15)

    cap = cv2.VideoCapture(clip_path)
    if not cap.isOpened():
        logger.warning(f"Could not open clip {clip_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_interval = max(1, int(round(fps / sample_hz)))

    bg_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=200, varThreshold=25, detectShadows=False
    )

    detections: list[RawDetection] = []
    frame_idx = 0
    sample_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval != 0:
            frame_idx += 1
            continue

        frame = cv2.resize(frame, resize_to)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fg_mask = bg_subtractor.apply(frame)
        timestamp_sec = frame_idx / fps

        # --- pedestrian_movement: motion detected outside the walkway zone
        walkway_px = _zone_pixels(frame.shape, zones["walkway"])
        walkway_motion = _motion_in_zone(fg_mask, walkway_px)
        full_motion = float(np.count_nonzero(fg_mask)) / float(fg_mask.size)
        off_walkway_motion = max(0.0, full_motion - walkway_motion)
        if off_walkway_motion > 0.015:
            conf = min(1.0, off_walkway_motion * 20)
            detections.append(RawDetection(
                behavior_class="pedestrian_movement",
                timestamp_sec=timestamp_sec,
                zone="Zone-Walkway",
                confidence=conf,
                personnel_present=True,
                description="Motion detected outside the designated walkway boundary.",
            ))

        # --- equipment_intervention: motion in equipment zone, low hi-vis overlap
        eq_px = _zone_pixels(frame.shape, zones["equipment"])
        eq_motion = _motion_in_zone(fg_mask, eq_px)
        hi_vis_ratio = _hi_vis_ratio_in_zone(frame, eq_px)
        if eq_motion > 0.02 and hi_vis_ratio < 0.03:
            conf = min(1.0, eq_motion * 15)
            detections.append(RawDetection(
                behavior_class="equipment_intervention",
                timestamp_sec=timestamp_sec,
                zone="Zone-Equipment",
                confidence=conf,
                personnel_present=True,
                description="Personnel detected near active equipment without high-visibility PPE indicator.",
            ))

        # --- electrical_panel_management: high edge density => panel appears open
        panel_px = _zone_pixels(frame.shape, zones["panel"])
        panel_score = _panel_open_score(gray, panel_px)
        if panel_score > 0.12:
            conf = min(1.0, panel_score * 3)
            detections.append(RawDetection(
                behavior_class="electrical_panel_management",
                timestamp_sec=timestamp_sec,
                zone="Zone-Panel",
                confidence=conf,
                personnel_present=False,
                description="Electrical panel zone shows an open/unsecured state signature.",
            ))

        # --- forklift_load_management: stacked block contour count > 2
        load_px = _zone_pixels(frame.shape, zones["forklift_load"])
        block_count = _stacked_block_count(frame, load_px)
        if block_count >= 2:
            # 2 contours is borderline (uncertainty band); 3+ is high confidence
            conf = 0.5 + uncertainty_margin if block_count == 2 else min(1.0, 0.6 + 0.15 * block_count)
            detections.append(RawDetection(
                behavior_class="forklift_load_management",
                timestamp_sec=timestamp_sec,
                zone="Zone-Forklift",
                confidence=conf,
                personnel_present=False,
                description=f"Forklift load zone shows approximately {block_count} stacked block contour(s).",
            ))

        frame_idx += 1
        sample_idx += 1

    cap.release()
    logger.info(f"{clip_path}: {len(detections)} raw candidate detection(s) over {sample_idx} sampled frame(s)")
    return detections
