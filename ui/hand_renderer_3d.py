"""3D Hand visualization renderer using PyOpenGL."""

import pygame
import math
from OpenGL.GL import *
from OpenGL.GLU import *

from typing import Dict, List, Optional, Set
from game.constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GAME_AREA_BOTTOM, HAND_DISPLAY_HEIGHT,
    FINGER_NAMES, FINGER_DISPLAY_NAMES, PALM_RADIUS,
    FINGER_TIP_RADIUS, FINGER_JOINT_RADIUS, HAND_SCALE
)
from .colors import (
    HAND_COLOR, HAND_OUTLINE, FINGER_NORMAL, FINGER_HIGHLIGHT,
    FINGER_PRESSED, FINGER_COLORS, WHITE, BLACK, GRAY
)


class OpenGLHandRenderer:
    """Renders 3D hand visualization using PyOpenGL."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        # Hand area starts at GAME_AREA_BOTTOM in Pygame coords (y from top)
        self.hand_area_top = GAME_AREA_BOTTOM
        self.hand_area_height = HAND_DISPLAY_HEIGHT

        # Screen dimensions (may differ from game dimensions in fullscreen)
        self.screen_width, self.screen_height = screen.get_size()

        # Initialize OpenGL for this section
        self._init_opengl()

        # Initialize render resources and state
        self.set_screen_size(self.screen_width, self.screen_height)

    def set_screen_size(self, width: int, height: int):
        """Update screen dimensions for fullscreen scaling."""
        self.screen_width = width
        self.screen_height = height

        # Quadric for drawing spheres and cylinders
        self.quadric = gluNewQuadric()
        gluQuadricNormals(self.quadric, GLU_SMOOTH)
        gluQuadricTexture(self.quadric, GL_TRUE)

        # Camera settings
        self.camera_distance = 200  # Distance to fit whole hand
        self.camera_fov = 50
        self.camera_near = 1.0
        self.camera_far = 1000.0

        # Hand data for rendering
        self.view_mode = "bottom"  # "bottom" or "center"
        self.hand_data: Dict = {}
        self.calibrated_hand_data: Dict = {}
        self.finger_states: Dict[str, bool] = {}
        self.highlighted_fingers: Set[str] = set()  # Fingers to highlight (targets)

        # Animation
        self.pulse_phase = 0.0
        self.angle_debug_finger = None
        self.show_angle_pip = False
        self.show_angle_mcp = False
        self.angle_debug_mode = "pip"

    def _init_opengl(self):
        """Initialize OpenGL settings for 3D rendering."""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE) # Normalizes normals after scaling

        glLightfv(GL_LIGHT0, GL_POSITION,  (0, 0, 100, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.7, 0.7, 0.7, 1))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1))

        glClearColor(0.0, 0.0, 0.0, 0.0) # Clear to transparent/black, will be covered by Pygame background

    def set_hand_data(self, hand_data: Dict, finger_states: Dict[str, bool],
                      highlighted_fingers: Set[str] = None):
        """
        Set the hand tracking data for rendering.

        Args:
            hand_data: Dictionary with hand tracking data from HandTracker.get_display_data()
            finger_states: Dictionary mapping finger names to pressed state
            highlighted_fingers: Set of finger names to highlight (e.g., {'left_index', 'right_thumb'})
        """
        self.hand_data = hand_data
        self.finger_states = finger_states
        if highlighted_fingers is not None:
            self.highlighted_fingers = highlighted_fingers

    def set_calibrated_hand_data(self, calibrated_hand_data: Dict):
        """Set the calibrated hand model data for reference rendering."""
        self.calibrated_hand_data = calibrated_hand_data or {}

    def set_angle_debug(self, finger_name: Optional[str], show_pip: bool = True, show_mcp: bool = True, mode: str = "pip"):
        """Enable angle debug overlay for a specific finger."""
        self.angle_debug_finger = finger_name
        self.show_angle_pip = show_pip
        self.show_angle_mcp = show_mcp
        self.angle_debug_mode = mode

    def set_view_mode(self, mode: str):
        """Set the view mode ('bottom' or 'center')."""
        if mode in ("bottom", "center"):
            self.view_mode = mode

    def _screen_rect_for_logical_rect(self, x: float, y: float, width: float, height: float):
        """Convert a top-left logical game rect to an OpenGL bottom-left screen rect."""
        scale = min(self.screen_width / WINDOW_WIDTH, self.screen_height / WINDOW_HEIGHT)
        scaled_game_width = WINDOW_WIDTH * scale
        scaled_game_height = WINDOW_HEIGHT * scale
        offset_x = (self.screen_width - scaled_game_width) / 2.0
        offset_y = (self.screen_height - scaled_game_height) / 2.0

        screen_x = int(round(offset_x + x * scale))
        screen_y = int(round(offset_y + (WINDOW_HEIGHT - y - height) * scale))
        screen_width = max(1, int(round(width * scale)))
        screen_height = max(1, int(round(height * scale)))
        return screen_x, screen_y, screen_width, screen_height

    def draw(self):
        """Draw the 3D hand visualization."""
        # Save only the GL state bits we actually modify (much faster than GL_ALL_ATTRIB_BITS)
        glPushAttrib(GL_ENABLE_BIT | GL_LIGHTING_BIT | GL_COLOR_BUFFER_BIT | GL_VIEWPORT_BIT | GL_SCISSOR_BIT)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        # Set up OpenGL state for 3D rendering
        glDisable(GL_TEXTURE_2D)  # No textures, using solid colors
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        glLightfv(GL_LIGHT0, GL_POSITION, (0, 100, 100, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))

        # Scale viewport to actual screen size
        if self.view_mode == "center":
            # Larger viewports in center.
            logical_y = (WINDOW_HEIGHT - 500) // 2
            left_rect = self._screen_rect_for_logical_rect(0, logical_y, WINDOW_WIDTH // 2, 500)
            right_rect = self._screen_rect_for_logical_rect(WINDOW_WIDTH // 2, logical_y, WINDOW_WIDTH // 2, 500)
            glClearColor(0.01, 0.01, 0.03, 1.0)
        else:
            # Default bottom viewports.
            left_rect = self._screen_rect_for_logical_rect(0, self.hand_area_top, WINDOW_WIDTH // 2, self.hand_area_height)
            right_rect = self._screen_rect_for_logical_rect(
                WINDOW_WIDTH // 2, self.hand_area_top, WINDOW_WIDTH // 2, self.hand_area_height
            )
            glClearColor(0.05, 0.05, 0.1, 1.0)

        # Enable scissor test to limit clears to each viewport
        glEnable(GL_SCISSOR_TEST)

        # --- Draw Left Hand Viewport ---
        left_x, left_y, viewport_width, viewport_height = left_rect
        glViewport(left_x, left_y, viewport_width, viewport_height)
        glScissor(left_x, left_y, viewport_width, viewport_height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._setup_camera_for_hand(viewport_width, viewport_height)

        # Draw calibrated ghost hand first (reference origin)
        if self.view_mode == "center" and self.calibrated_hand_data.get('left'):
            self._draw_single_hand(self.calibrated_hand_data.get('left'), 'left', is_ghost=True)

        # Draw live hand
        if self.hand_data.get('left') and self.hand_data['left'].get('valid', False):
            self._draw_single_hand(self.hand_data.get('left'), 'left')

        # --- Draw Right Hand Viewport ---
        right_x, right_y, viewport_width, viewport_height = right_rect
        glViewport(right_x, right_y, viewport_width, viewport_height)
        glScissor(right_x, right_y, viewport_width, viewport_height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._setup_camera_for_hand(viewport_width, viewport_height)

        # Draw calibrated ghost hand first
        if self.view_mode == "center" and self.calibrated_hand_data.get('right'):
            self._draw_single_hand(self.calibrated_hand_data.get('right'), 'right', is_ghost=True)

        # Draw live hand
        if self.hand_data.get('right') and self.hand_data['right'].get('valid', False):
            self._draw_single_hand(self.hand_data.get('right'), 'right')

        glDisable(GL_SCISSOR_TEST)

        # Restore Pygame's GL state
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glPopAttrib()

    def _setup_camera_for_hand(self, viewport_width: int, viewport_height: int):
        """Set up the projection and modelview matrices for a single hand viewport."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.camera_fov, (viewport_width / viewport_height), self.camera_near, self.camera_far)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # Camera looking at hand from in front and slightly above
        # The reference origin (0,0,0) is the calibrated palm position
        gluLookAt(0, 50, self.camera_distance,
                  0, 0, 0,
                  0, 1, 0)

    def _draw_target_box(self, size: float):
        """Draw a wireframe box at the reference origin to show target palm position."""
        glDisable(GL_LIGHTING)
        glLineWidth(2.0)
        glColor4f(0.0, 1.0, 1.0, 0.6)  # Cyan wireframe
        
        s = size
        glBegin(GL_LINES)
        # Top
        glVertex3f(-s, s, -s); glVertex3f(s, s, -s)
        glVertex3f(s, s, -s); glVertex3f(s, s, s)
        glVertex3f(s, s, s); glVertex3f(-s, s, s)
        glVertex3f(-s, s, s); glVertex3f(-s, s, -s)
        # Bottom
        glVertex3f(-s, -s, -s); glVertex3f(s, -s, -s)
        glVertex3f(s, -s, -s); glVertex3f(s, -s, s)
        glVertex3f(s, -s, s); glVertex3f(-s, -s, s)
        glVertex3f(-s, -s, s); glVertex3f(-s, -s, -s)
        # Verticals
        glVertex3f(-s, s, -s); glVertex3f(-s, -s, -s)
        glVertex3f(s, s, -s); glVertex3f(s, -s, -s)
        glVertex3f(s, s, s); glVertex3f(s, -s, s)
        glVertex3f(-s, s, s); glVertex3f(-s, -s, s)
        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_single_hand(self, hand_model: Optional[Dict], hand_type: str, is_ghost: bool = False):
        """Draw a single 3D hand, optionally as a ghost reference."""
        if not hand_model:
            return
        
        # Use calibrated palm as the origin for both hands to show spatial offset
        cal_hand = self.calibrated_hand_data.get(hand_type)
        if cal_hand and self.view_mode == "center":
            reference_palm = cal_hand.get('palm_position', [0, 0, 0])
        else:
            # If no calibration or not in center view, center the hand on its own palm
            reference_palm = hand_model.get('palm_position', [0, 0, 0])

        # Current palm for this specific model
        palm_pos = hand_model.get('palm_position', [0, 0, 0])
        
        scale_factor = 0.8
        palm_radius = PALM_RADIUS * scale_factor * 0.6

        glPushMatrix()
        # Rotate entire scene to look from above
        glRotatef(-60, 1, 0, 0)

        # Draw target "outline" box only once per hand (when drawing ghost)
        if is_ghost and self.view_mode == "center":
            self._draw_target_box(palm_radius * 1.5)

        # Calculate palm offset relative to reference origin
        rel_palm = [
            (palm_pos[0] - reference_palm[0]) * scale_factor,
            (palm_pos[1] - reference_palm[1]) * scale_factor,
            -(palm_pos[2] - reference_palm[2]) * scale_factor
        ]

        # Draw palm center
        glPushMatrix()
        glTranslatef(rel_palm[0], rel_palm[1], rel_palm[2])
        if is_ghost:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDisable(GL_LIGHTING)
            glColor4f(0.5, 0.8, 1.0, 0.5)
        else:
            glColor3f(*tuple(c / 255.0 for c in HAND_COLOR))
        
        gluSphere(self.quadric, palm_radius, 8, 8)
        
        if is_ghost:
            glEnable(GL_LIGHTING)
            glDisable(GL_BLEND)
        glPopMatrix()

        # Draw fingers and bones
        for finger_name, finger_data in hand_model.get('fingers', {}).items():
            if not finger_data or not finger_data.get('valid', False):
                continue

            full_finger_name = f"{hand_type}_{finger_name}"
            is_highlighted = full_finger_name in self.highlighted_fingers
            is_pressed = self.finger_states.get(full_finger_name, False)
            pulse = (math.sin(self.pulse_phase * 5) * 0.5 + 0.5) if is_highlighted else 0

            for bone_type in ['metacarpal', 'proximal', 'intermediate', 'distal']:
                bone_data = finger_data.get(bone_type)
                if not bone_data: continue

                # Get bone joints and convert to RELATIVE TO REFERENCE
                start_raw = bone_data.get('start') or bone_data.get('prev_joint')
                end_raw = bone_data.get('end') or bone_data.get('next_joint')
                if not start_raw or not end_raw: continue

                rel_start = [
                    (start_raw[0] - reference_palm[0]) * scale_factor,
                    (start_raw[1] - reference_palm[1]) * scale_factor,
                    -(start_raw[2] - reference_palm[2]) * scale_factor
                ]
                rel_end = [
                    (end_raw[0] - reference_palm[0]) * scale_factor,
                    (end_raw[1] - reference_palm[1]) * scale_factor,
                    -(end_raw[2] - reference_palm[2]) * scale_factor
                ]

                # Bone vector and orientation
                bone_vec = [rel_end[j] - rel_start[j] for j in range(3)]
                bone_length = math.sqrt(sum(v*v for v in bone_vec))
                if bone_length < 0.1: continue

                glPushMatrix()
                glTranslatef(rel_start[0], rel_start[1], rel_start[2])

                # Rotate cylinder to match bone direction
                target_vec = [v/bone_length for v in bone_vec]
                z_axis = (0.0, 0.0, 1.0)
                cross_prod = [
                    z_axis[1] * target_vec[2] - z_axis[2] * target_vec[1],
                    z_axis[2] * target_vec[0] - z_axis[0] * target_vec[2],
                    z_axis[0] * target_vec[1] - z_axis[1] * target_vec[0]
                ]
                cross_mag = math.sqrt(sum(c*c for c in cross_prod))
                dot_prod = sum(z_axis[k] * target_vec[k] for k in range(3))
                rot_angle = math.acos(max(-1.0, min(1.0, dot_prod)))

                if cross_mag > 0.001:
                    glRotatef(math.degrees(rot_angle), cross_prod[0], cross_prod[1], cross_prod[2])

                # Styling
                bone_radius = FINGER_JOINT_RADIUS * scale_factor * 0.7
                if is_ghost:
                    glEnable(GL_BLEND)
                    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                    glDisable(GL_LIGHTING)
                    glColor4f(0.5, 0.8, 1.0, 0.5)
                elif is_highlighted:
                    glColor3f(1.0, 0.7 + pulse * 0.3, 0.0)
                elif is_pressed:
                    glColor3f(0.2, 1.0, 0.2)
                else:
                    glColor3f(*tuple(c / 255.0 for c in FINGER_NORMAL))

                # Draw components
                gluCylinder(self.quadric, bone_radius, bone_radius, bone_length, 6, 1)
                gluSphere(self.quadric, bone_radius * 1.2, 6, 6)

                if bone_type == 'distal':
                    glPushMatrix()
                    glTranslatef(0, 0, bone_length)
                    tip_rad = bone_radius * (2.5 if is_highlighted else 1.8)
                    if is_ghost: glColor4f(0.5, 0.8, 1.0, 0.4)
                    gluSphere(self.quadric, tip_rad, 8, 8)
                    glPopMatrix()

                if is_ghost:
                    glEnable(GL_LIGHTING)
                    glDisable(GL_BLEND)
                glPopMatrix()

        glPopMatrix() # Pop rotation and hand offset

    def update(self, dt: float):
        """Update animations."""
        self.pulse_phase += dt * 0.15

    def _cleanup(self):
        """Clean up OpenGL resources."""
        if hasattr(self, 'quadric'):
            gluDeleteQuadric(self.quadric)
