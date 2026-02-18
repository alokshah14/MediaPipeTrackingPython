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
        self.camera_far = 500.0

        # Hand data for rendering
        self.hand_data: Dict = {}
        self.finger_states: Dict[str, bool] = {}
        self.highlighted_fingers: Set[str] = set()  # Fingers to highlight (targets)

        # Animation
        self.pulse_phase = 0.0
        self.angle_debug_finger = None
        self.show_angle_pip = False
        self.show_angle_mcp = False

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

    def set_angle_debug(self, finger_name: Optional[str], show_pip: bool = True, show_mcp: bool = True):
        """Enable angle debug overlay for a specific finger."""
        self.angle_debug_finger = finger_name
        self.show_angle_pip = show_pip
        self.show_angle_mcp = show_mcp

    def draw(self):
        """Draw the 3D hand visualization."""
        # Save Pygame's current GL state
        glPushAttrib(GL_ALL_ATTRIB_BITS)
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
        scale_x = self.screen_width / WINDOW_WIDTH
        scale_y = self.screen_height / WINDOW_HEIGHT

        # Define the sub-viewports for left and right hands.
        viewport_width = int(WINDOW_WIDTH // 2 * scale_x)
        viewport_height = int(self.hand_area_height * scale_y)
        viewport_y = int((WINDOW_HEIGHT - (self.hand_area_top + self.hand_area_height)) * scale_y)

        # Enable scissor test to limit clears to each viewport
        glEnable(GL_SCISSOR_TEST)

        # Background color for hand area
        glClearColor(0.05, 0.05, 0.1, 1.0)  # Dark blue-gray

        # --- Draw Left Hand Viewport ---
        glViewport(0, viewport_y, viewport_width, viewport_height)
        glScissor(0, viewport_y, viewport_width, viewport_height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._setup_camera_for_hand(viewport_width, viewport_height)

        if self.hand_data.get('left') and self.hand_data['left'].get('valid', False):
            self._draw_single_hand(self.hand_data.get('left'), 'left')

        # --- Draw Right Hand Viewport ---
        right_x = int(WINDOW_WIDTH // 2 * scale_x)
        glViewport(right_x, viewport_y, viewport_width, viewport_height)
        glScissor(right_x, viewport_y, viewport_width, viewport_height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self._setup_camera_for_hand(viewport_width, viewport_height)

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
        # Hand will be centered at origin, so look at (0, 0, 0)
        gluLookAt(0, 50, self.camera_distance,  # Camera position (slightly above)
                  0, 0, 0,                       # Look at origin
                  0, 1, 0)                       # Up vector

    def _draw_single_hand(self, hand_model: Optional[Dict], hand_type: str):
        """Draw a single 3D hand."""
        if not hand_model or not hand_model.get('valid', False):
            return

        glPushMatrix()

        # Scale factor - Leap Motion uses mm, we want hand to fill viewport nicely
        # Typical hand span is ~150-200mm, we want it to appear ~100-150 units
        scale_factor = 0.8

        palm_pos = hand_model.get('palm_position', [0, 0, 0])

        # DON'T translate by absolute palm position - this keeps hand centered
        # Instead, we'll render all bones relative to the palm position
        # Just apply a small rotation to view hand from a good angle
        glRotatef(-60, 1, 0, 0)  # Tilt hand to see it from above

        # Draw palm (simplified as a sphere at origin)
        glColor3f(*tuple(c / 255.0 for c in HAND_COLOR))
        gluSphere(self.quadric, PALM_RADIUS * scale_factor * 0.8, 16, 16)


        # Draw fingers and bones
        for finger_name, finger_data in hand_model.get('fingers', {}).items():
            if not finger_data or not finger_data.get('valid', False):
                continue

            # Check if this finger should be highlighted
            full_finger_name = f"{hand_type}_{finger_name}"
            is_highlighted = full_finger_name in self.highlighted_fingers
            is_pressed = self.finger_states.get(full_finger_name, False)

            # Pulsing effect for highlighted fingers
            pulse = (math.sin(self.pulse_phase * 5) * 0.5 + 0.5) if is_highlighted else 0

            for i in range(4):  # 4 bones per finger: metacarpal, proximal, intermediate, distal
                bone_type = ['metacarpal', 'proximal', 'intermediate', 'distal'][i]
                bone_data = finger_data.get(bone_type)

                if not bone_data:
                    continue

                # Get bone start and end positions in Leap Motion coordinates
                start_pos = bone_data.get('start', [0, 0, 0])
                end_pos = bone_data.get('end', [0, 0, 0])

                # Relative positions from the hand's palm position
                rel_start_pos = [start_pos[j] - palm_pos[j] for j in range(3)]
                rel_end_pos = [end_pos[j] - palm_pos[j] for j in range(3)]

                # Bone vector
                bone_vec = [rel_end_pos[j] - rel_start_pos[j] for j in range(3)]
                bone_length = (bone_vec[0]**2 + bone_vec[1]**2 + bone_vec[2]**2)**0.5

                if bone_length < 0.1:
                    continue

                # Normalize bone vector
                norm_bone_vec = [bone_vec[j] / bone_length for j in range(3)]

                glPushMatrix()
                glTranslatef(rel_start_pos[0] * scale_factor,
                             rel_start_pos[1] * scale_factor,
                             -rel_start_pos[2] * scale_factor)

                # Calculate rotation to orient cylinder along bone
                target_vec_opengl = (norm_bone_vec[0], norm_bone_vec[1], -norm_bone_vec[2])
                z_axis = (0.0, 0.0, 1.0)
                cross_product = [
                    z_axis[1] * target_vec_opengl[2] - z_axis[2] * target_vec_opengl[1],
                    z_axis[2] * target_vec_opengl[0] - z_axis[0] * target_vec_opengl[2],
                    z_axis[0] * target_vec_opengl[1] - z_axis[1] * target_vec_opengl[0]
                ]

                cross_mag = math.sqrt(sum(c * c for c in cross_product))
                dot_product = sum(z_axis[k] * target_vec_opengl[k] for k in range(3))
                angle = math.acos(max(-1.0, min(1.0, dot_product)))

                if cross_mag > 0.001 and angle > 0.001:
                    glRotatef(math.degrees(angle), cross_product[0], cross_product[1], cross_product[2])

                # Set color based on state
                bone_radius = FINGER_JOINT_RADIUS * scale_factor * 0.7

                if is_highlighted:
                    # Highlighted: pulsing yellow/orange
                    r = 1.0
                    g = 0.7 + pulse * 0.3
                    b = 0.0
                    glColor3f(r, g, b)
                elif is_pressed:
                    # Pressed: green
                    glColor3f(0.2, 1.0, 0.2)
                else:
                    # Normal: skin tone
                    glColor3f(*tuple(c / 255.0 for c in FINGER_NORMAL))

                # Draw bone cylinder
                gluCylinder(self.quadric, bone_radius, bone_radius, bone_length * scale_factor, 10, 1)

                # Draw joint sphere at start
                gluSphere(self.quadric, bone_radius * 1.2, 10, 10)

                # Draw fingertip (larger, more visible) on distal bone
                if bone_type == 'distal':
                    glPushMatrix()
                    glTranslatef(0, 0, bone_length * scale_factor)

                    # Fingertip is bigger and brighter when highlighted
                    tip_radius = bone_radius * (2.5 if is_highlighted else 1.8)

                    if is_highlighted:
                        # Bright pulsing fingertip for target
                        glColor3f(1.0, 0.8 + pulse * 0.2, 0.0 + pulse * 0.3)
                    elif is_pressed:
                        glColor3f(0.3, 1.0, 0.3)

                    gluSphere(self.quadric, tip_radius, 12, 12)
                    glPopMatrix()
                else:
                    # Regular joint at end of non-distal bones
                    glPushMatrix()
                    glTranslatef(0, 0, bone_length * scale_factor)
                    gluSphere(self.quadric, bone_radius * 1.2, 10, 10)
                    glPopMatrix()

                glPopMatrix()

            # Angle debug overlay for selected finger
            full_finger_name = f"{hand_type}_{finger_name}"
            if self.angle_debug_finger == full_finger_name:
                self._draw_angle_debug_for_finger(finger_data, palm_pos, scale_factor)

        glPopMatrix()  # Pop hand transformation

    def _draw_angle_debug_for_finger(self, finger_data: Dict, palm_pos: List[float], scale_factor: float):
        """Draw colored lines/points showing MCP and PIP angle segments."""
        def to_rel(pos):
            return [
                (pos[0] - palm_pos[0]) * scale_factor,
                (pos[1] - palm_pos[1]) * scale_factor,
                -(pos[2] - palm_pos[2]) * scale_factor,
            ]

        def draw_segment(start, end, color, width=3.0):
            glDisable(GL_LIGHTING)
            glLineWidth(width)
            glColor3f(*color)
            glBegin(GL_LINES)
            glVertex3f(start[0], start[1], start[2])
            glVertex3f(end[0], end[1], end[2])
            glEnd()
            glEnable(GL_LIGHTING)

        def draw_point(pos, color, radius=3.5):
            glDisable(GL_LIGHTING)
            glPushMatrix()
            glTranslatef(pos[0], pos[1], pos[2])
            glColor3f(*color)
            gluSphere(self.quadric, radius, 8, 8)
            glPopMatrix()
            glEnable(GL_LIGHTING)

        bones = finger_data.get('bones', {})
        metacarpal = bones.get('metacarpal')
        proximal = bones.get('proximal')
        intermediate = bones.get('intermediate')

        # MCP: metacarpal + proximal
        if self.show_angle_mcp and metacarpal and proximal:
            m_start = to_rel(metacarpal['start'])
            m_end = to_rel(metacarpal['end'])
            p_start = to_rel(proximal['start'])
            p_end = to_rel(proximal['end'])
            draw_segment(m_start, m_end, (0.2, 0.6, 1.0), width=3.0)
            draw_segment(p_start, p_end, (0.2, 1.0, 0.6), width=3.0)
            draw_point(m_end, (0.2, 0.6, 1.0))
            draw_point(p_start, (0.2, 1.0, 0.6))

        # PIP: proximal + intermediate
        if self.show_angle_pip and proximal and intermediate:
            p_start = to_rel(proximal['start'])
            p_end = to_rel(proximal['end'])
            i_start = to_rel(intermediate['start'])
            i_end = to_rel(intermediate['end'])
            draw_segment(p_start, p_end, (1.0, 0.2, 0.8), width=2.8)
            draw_segment(i_start, i_end, (1.0, 0.6, 0.2), width=2.8)
            draw_point(p_end, (1.0, 0.2, 0.8))
            draw_point(i_start, (1.0, 0.6, 0.2))

    def update(self, dt: float):
        """Update animations."""
        self.pulse_phase += dt * 0.15  # Animate pulse for highlighting

    def _cleanup(self):
        """Clean up OpenGL resources."""
        gluDeleteQuadric(self.quadric)
