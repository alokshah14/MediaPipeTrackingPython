#!/usr/bin/env python3
"""Standalone MediaPipe camera debug viewer."""

import argparse
import os
import time

from tracking.mediapipe_controller import MediaPipeController, MEDIAPIPE_AVAILABLE, cv2, mp, python, vision


HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

FINGER_TIPS = {4, 8, 12, 16, 20}


def _model_path() -> str:
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "models", "hand_landmarker.task"))


def _open_landmarker():
    if not MEDIAPIPE_AVAILABLE or cv2 is None:
        raise RuntimeError("MediaPipe/OpenCV dependencies are not installed.")

    model_path = _model_path()
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"MediaPipe model not found at {model_path}")

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
    )
    return vision.HandLandmarker.create_from_options(options)


def _draw_hand(frame, landmarks, handedness, mirror: bool):
    height, width = frame.shape[:2]
    points = [(int(lm.x * width), int(lm.y * height)) for lm in landmarks]

    for start_idx, end_idx in HAND_CONNECTIONS:
        cv2.line(frame, points[start_idx], points[end_idx], (0, 220, 255), 2, cv2.LINE_AA)

    for index, point in enumerate(points):
        if index in FINGER_TIPS:
            radius = 7
            fill = (0, 255, 80)
        else:
            radius = 4
            fill = (255, 255, 255)
        cv2.circle(frame, point, radius, fill, -1, cv2.LINE_AA)
        cv2.circle(frame, point, radius + 1, (20, 20, 20), 1, cv2.LINE_AA)

    label = "Hand"
    score = None
    if handedness:
        label = handedness[0].category_name
        score = handedness[0].score
        if mirror:
            label = "Right" if label == "Left" else "Left"

    wrist_x, wrist_y = points[0]
    text = f"{label}"
    if score is not None:
        text += f" {score:.2f}"
    cv2.putText(frame, text, (wrist_x + 10, max(24, wrist_y - 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 80), 2, cv2.LINE_AA)


def _draw_status(frame, camera_index: int, fps: float, hands_count: int, mirror: bool):
    status = f"Camera {camera_index} | {fps:4.1f} FPS | Hands: {hands_count} | M mirror: {'on' if mirror else 'off'} | Q/Esc quit"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 34), (0, 0, 0), -1)
    cv2.putText(frame, status, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                (255, 255, 255), 1, cv2.LINE_AA)


def _print_cameras(max_devices: int):
    cameras = MediaPipeController.list_available_cameras(max_devices=max_devices)
    if not cameras:
        print("No cameras found.")
        return

    print("Available cameras:")
    for camera in cameras:
        print(f"  {camera['index']}: {camera['label']}")


def run_viewer(camera_index: int, width: int | None, height: int | None, mirror: bool):
    cap = MediaPipeController._create_capture(camera_index)
    if not cap or not cap.isOpened():
        raise RuntimeError(f"Could not open camera {camera_index}")

    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not MediaPipeController._wait_for_frame(cap, attempts=10, delay_s=0.1):
        cap.release()
        raise RuntimeError(f"Camera {camera_index} opened but did not produce frames")

    landmarker = _open_landmarker()
    fps = 0.0
    last_time = time.time()
    last_timestamp_ms = 0
    paused = False
    last_frame = None
    last_results = None

    try:
        while True:
            if not paused:
                ok, frame = cap.read()
                if not ok:
                    print("Camera frame read failed.")
                    break

                if mirror:
                    frame = cv2.flip(frame, 1)
                last_frame = frame.copy()

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = max(last_timestamp_ms + 1, int(time.monotonic() * 1000))
                last_timestamp_ms = timestamp_ms
                results = landmarker.detect_for_video(mp_image, timestamp_ms)
                last_results = results

                now = time.time()
                dt = now - last_time
                if dt > 0:
                    fps = fps * 0.85 + (1.0 / dt) * 0.15 if fps else (1.0 / dt)
                last_time = now
            else:
                if last_frame is None:
                    continue
                frame = last_frame.copy()
                results = last_results

            hands_count = 0
            if results and results.hand_landmarks:
                hands_count = len(results.hand_landmarks)
                for index, landmarks in enumerate(results.hand_landmarks):
                    handedness = results.handedness[index] if results.handedness and index < len(results.handedness) else None
                    _draw_hand(frame, landmarks, handedness, mirror)

            _draw_status(frame, camera_index, fps, hands_count, mirror)
            if paused:
                cv2.putText(frame, "PAUSED", (10, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                            (0, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow("MediaPipe Camera Debug", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key == ord("m"):
                mirror = not mirror
            elif key == ord("p"):
                paused = not paused
    finally:
        landmarker.close()
        cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Show webcam feed with MediaPipe hand landmarks.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index to open.")
    parser.add_argument("--width", type=int, default=None, help="Requested camera capture width.")
    parser.add_argument("--height", type=int, default=None, help="Requested camera capture height.")
    parser.add_argument("--no-mirror", action="store_true", help="Do not mirror the camera preview.")
    parser.add_argument("--list-cameras", action="store_true", help="Print detected cameras and exit.")
    parser.add_argument("--max-devices", type=int, default=6, help="Maximum camera indices to scan.")
    args = parser.parse_args()

    if args.list_cameras:
        _print_cameras(args.max_devices)
        return

    run_viewer(
        camera_index=args.camera,
        width=args.width,
        height=args.height,
        mirror=not args.no_mirror,
    )


if __name__ == "__main__":
    main()
