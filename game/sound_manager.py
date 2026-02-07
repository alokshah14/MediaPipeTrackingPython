"""Sound manager for game audio effects."""

import pygame
import os
import math
import struct
import wave
import io
import random


class SoundManager:
    """Manages game sound effects."""

    def __init__(self):
        """Initialize the sound manager."""
        self.enabled = True
        self.volume = 0.7
        self.sounds = {}

        # Initialize pygame mixer if not already done
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except pygame.error as e:
                print(f"Could not initialize sound mixer: {e}")
                self.enabled = False
                return

        # Generate and load sounds
        self._generate_sounds()

    def _generate_sounds(self):
        """Generate sound effects programmatically."""
        try:
            # Generate fire sound (short laser-like sound)
            self.sounds['fire'] = self._create_fire_sound()

            # Generate explosion sound
            self.sounds['explosion'] = self._create_explosion_sound()

            # Generate hit sound (successful hit)
            self.sounds['hit'] = self._create_hit_sound()

            # Generate miss sound (wrong finger)
            self.sounds['miss'] = self._create_miss_sound()

            # Generate life lost sound
            self.sounds['life_lost'] = self._create_life_lost_sound()

            # Generate collect sound (for Egg Catcher)
            self.sounds['collect'] = self._create_collect_sound()

            # Generate drop sound (for Egg Catcher)
            self.sounds['drop'] = self._create_drop_sound()

            # Generate paddle hit sound (for Ping Pong)
            self.sounds['paddle_hit'] = self._create_paddle_hit_sound()

            # Generate wall hit sound (for Ping Pong)
            self.sounds['wall_hit'] = self._create_wall_hit_sound()

            # Generate celebration sound (for new high score)
            self.sounds['celebration'] = self._create_celebration_sound()

            print("Sound effects generated successfully.")

        except Exception as e:
            print(f"Error generating sounds: {e}")
            self.enabled = False

    def _create_sound_from_samples(self, samples, sample_rate=44100):
        """Create a pygame Sound object from sample data."""
        # Convert to 16-bit signed integers
        max_val = max(abs(min(samples)), abs(max(samples)))
        if max_val > 0:
            samples = [int(s / max_val * 32767) for s in samples]

        # Create stereo samples (duplicate mono to both channels)
        stereo_samples = []
        for s in samples:
            stereo_samples.extend([s, s])  # Left and right channel

        # Pack as bytes
        raw_data = struct.pack(f'{len(stereo_samples)}h', *stereo_samples)

        # Create sound from buffer
        sound = pygame.mixer.Sound(buffer=raw_data)
        return sound

    def _create_fire_sound(self):
        """Create a laser/fire sound effect."""
        sample_rate = 44100
        duration = 0.15  # 150ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Descending frequency sweep (800Hz to 200Hz)
            freq = 800 - (600 * t / duration)
            # Envelope: quick attack, decay
            envelope = math.exp(-t * 20)
            # Generate sample
            sample = envelope * math.sin(2 * math.pi * freq * t)
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.4)
        return sound

    def _create_explosion_sound(self):
        """Create an explosion sound effect."""
        sample_rate = 44100
        duration = 0.4  # 400ms
        num_samples = int(sample_rate * duration)

        import random
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Envelope: quick attack, slow decay
            envelope = math.exp(-t * 5)
            # Mix of noise and low frequency rumble
            noise = random.uniform(-1, 1)
            rumble = math.sin(2 * math.pi * 60 * t) + math.sin(2 * math.pi * 40 * t)
            sample = envelope * (0.7 * noise + 0.3 * rumble)
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.6)
        return sound

    def _create_hit_sound(self):
        """Create a hit/success sound effect."""
        sample_rate = 44100
        duration = 0.2  # 200ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Rising pitch with harmonics
            freq1 = 400 + (200 * t / duration)
            freq2 = 600 + (300 * t / duration)
            envelope = math.exp(-t * 10)
            sample = envelope * (0.6 * math.sin(2 * math.pi * freq1 * t) +
                               0.4 * math.sin(2 * math.pi * freq2 * t))
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.5)
        return sound

    def _create_miss_sound(self):
        """Create a miss/error sound effect."""
        sample_rate = 44100
        duration = 0.25  # 250ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Descending dissonant tone
            freq1 = 300 - (100 * t / duration)
            freq2 = 350 - (150 * t / duration)
            envelope = math.exp(-t * 8)
            sample = envelope * (0.5 * math.sin(2 * math.pi * freq1 * t) +
                               0.5 * math.sin(2 * math.pi * freq2 * t))
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.4)
        return sound

    def _create_life_lost_sound(self):
        """Create a life lost sound effect."""
        sample_rate = 44100
        duration = 0.5  # 500ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Deep descending tone
            freq = 200 - (100 * t / duration)
            envelope = math.exp(-t * 4)
            # Add some grit
            sample = envelope * (math.sin(2 * math.pi * freq * t) +
                               0.3 * math.sin(2 * math.pi * freq * 2 * t))
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.6)
        return sound

    def _create_collect_sound(self):
        """Create a sound for collecting an item (e.g., catching an egg)."""
        sample_rate = 44100
        duration = 0.1  # 100ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            freq = 880  # A5 note
            envelope = math.exp(-t * 25)
            sample = envelope * math.sin(2 * math.pi * freq * t)
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.4)
        return sound

    def _create_drop_sound(self):
        """Create a sound for dropping/missing an item (e.g., missing an egg)."""
        sample_rate = 44100
        duration = 0.2  # 200ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            freq = 110 - (50 * t / duration) # Descending low frequency
            envelope = math.exp(-t * 10)
            sample = envelope * (0.8 * math.sin(2 * math.pi * freq * t) + 0.2 * random.uniform(-1,1)) # Add some noise
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.5)
        return sound

    def _create_paddle_hit_sound(self):
        """Create a sound for the ball hitting the paddle in Ping Pong."""
        sample_rate = 44100
        duration = 0.08  # 80ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            freq = 1200 # High pitched, sharp sound
            envelope = math.exp(-t * 50)
            sample = envelope * math.sin(2 * math.pi * freq * t)
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.7)
        return sound

    def _create_wall_hit_sound(self):
        """Create a sound for the ball hitting a wall in Ping Pong."""
        sample_rate = 44100
        duration = 0.05  # 50ms
        num_samples = int(sample_rate * duration)

        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            freq = 600 # Lower pitched than paddle hit
            envelope = math.exp(-t * 60)
            sample = envelope * math.sin(2 * math.pi * freq * t)
            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.6)
        return sound

    def _create_celebration_sound(self):
        """Create a celebration/fanfare sound effect for high scores."""
        sample_rate = 44100
        duration = 0.8  # 800ms
        num_samples = int(sample_rate * duration)

        samples = []
        # Create a triumphant ascending arpeggio
        notes = [
            (0.0, 0.15, 523),   # C5
            (0.1, 0.15, 659),   # E5
            (0.2, 0.15, 784),   # G5
            (0.3, 0.5, 1047),   # C6 (hold)
        ]

        for i in range(num_samples):
            t = i / sample_rate
            sample = 0

            for start, dur, freq in notes:
                if start <= t < start + dur:
                    note_t = t - start
                    # Envelope for each note
                    envelope = math.exp(-note_t * 5) * (1 - math.exp(-note_t * 50))
                    # Add harmonics for richer sound
                    sample += envelope * (
                        0.6 * math.sin(2 * math.pi * freq * t) +
                        0.3 * math.sin(2 * math.pi * freq * 2 * t) +
                        0.1 * math.sin(2 * math.pi * freq * 3 * t)
                    )

            samples.append(sample)

        sound = self._create_sound_from_samples(samples, sample_rate)
        sound.set_volume(0.7)
        return sound

    def play(self, sound_name: str):
        """Play a sound effect by name."""
        if not self.enabled:
            return

        sound = self.sounds.get(sound_name)
        if sound:
            sound.play()

    def play_fire(self):
        """Play the fire sound."""
        self.play('fire')

    def play_explosion(self):
        """Play the explosion sound."""
        self.play('explosion')

    def play_hit(self):
        """Play the hit sound."""
        self.play('hit')

    def play_miss(self):
        """Play the miss sound."""
        self.play('miss')

    def play_life_lost(self):
        """Play the life lost sound."""
        self.play('life_lost')

    def play_celebration(self):
        """Play the celebration sound."""
        self.play('celebration')

    def play_collect(self):
        """Play the collect sound (e.g., egg caught)."""
        self.play('collect')

    def play_drop(self):
        """Play the drop sound (e.g., egg missed)."""
        self.play('drop')

    def play_paddle_hit(self):
        """Play the paddle hit sound."""
        self.play('paddle_hit')

    def play_wall_hit(self):
        """Play the wall hit sound."""
        self.play('wall_hit')

    def set_volume(self, volume: float):
        """Set master volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.volume * 0.7)

    def toggle_sound(self):
        """Toggle sound on/off."""
        self.enabled = not self.enabled
        return self.enabled

    def is_enabled(self) -> bool:
        """Check if sound is enabled."""
        return self.enabled
