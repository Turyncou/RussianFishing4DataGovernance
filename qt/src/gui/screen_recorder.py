"""
Full screen screen recorder with global hotkey support.
Supports custom hotkeys, configurable save path, and audio recording.
Recording overlay shows duration but is not included in the final recording.
Uses Qt signals for proper completion callback on main thread.
"""
import os
import sys
# Disable output buffering so logs show up immediately on Windows
sys.stdout.reconfigure(line_buffering=True)
import time
import datetime
import threading
import subprocess
import numpy as np
import pyautogui
import cv2
import keyboard
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject, Slot, Signal


class ScreenRecorder(QObject):
    """Full screen screen recorder that runs in background thread with overlay.

    Emits:
        recording_finished(str): when recording is complete, with final output path
    """

    recording_finished = Signal(str)  # final output path

    def __init__(self, start_hotkey: str = "ctrl+shift+r", stop_hotkey: str = "ctrl+shift+s",
                 save_path: str = None, record_mic: bool = False, record_system: bool = False):
        """Initialize screen recorder"""
        super().__init__()
        self.start_hotkey = start_hotkey
        self.stop_hotkey = stop_hotkey
        self._default_save_path = save_path
        self.record_mic = record_mic
        self.record_system = record_system

        # Recording state
        self.is_recording = False
        self._recording_thread = None
        self._audio_thread = None
        self._video_writer = None
        self._save_path = None
        self._temp_audio_path = None
        self._final_path = None

        # Hotkeys registered flag
        self._hotkeys_registered = False

        # Recording overlay (created when needed on main thread)
        self._overlay = None
        self._overlay_visible = False

    @Slot()
    def _create_overlay_on_main_thread(self):
        """Create overlay on main thread"""
        from .screen_recorder_overlay import RecordingOverlay
        if self._overlay is None:
            self._overlay = RecordingOverlay(
                record_mic_enabled=self.record_mic,
                record_system_enabled=self.record_system
            )
            self._overlay.audio_toggled.connect(self._on_overlay_audio_toggled)
            print("Recording overlay created")

    def _ensure_overlay_created(self):
        """Ensure overlay is created - must be called from main thread"""
        if self._overlay is None:
            from PySide6.QtCore import QMetaObject, Qt
            app = QApplication.instance()
            if app and app.thread() is not threading.current_thread():
                # We are on background thread, invoke creation on main thread
                QMetaObject.invokeMethod(
                    self,
                    "_create_overlay_on_main_thread",
                    Qt.ConnectionType.BlockingQueuedConnection
                )
            else:
                # Already on main thread
                self._create_overlay_on_main_thread()

    def setup_hotkeys(self) -> bool:
        """Setup global hotkeys. Returns True if successful, False otherwise"""
        try:
            # Unregister any existing hotkeys first
            if self._hotkeys_registered:
                self.unregister_hotkeys()

            keyboard.add_hotkey(self.start_hotkey, self.start_recording)
            keyboard.add_hotkey(self.stop_hotkey, self.stop_recording)
            self._hotkeys_registered = True
            return True
        except Exception as e:
            print(f"Failed to register hotkeys: {e}")
            self._hotkeys_registered = False
            return False

    def unregister_hotkeys(self):
        """Unregister all hotkeys"""
        try:
            if self._hotkeys_registered:
                keyboard.remove_hotkey(self.start_hotkey)
                keyboard.remove_hotkey(self.stop_hotkey)
                self._hotkeys_registered = False
        except Exception:
            pass

        # Cleanup overlay
        if self._overlay:
            self._overlay.close()
            self._overlay = None

    def update_settings(self, start_hotkey: str = None, stop_hotkey: str = None,
                       save_path: str = None, record_mic: bool = None, record_system: bool = None):
        """Update settings and re-register hotkeys"""
        if start_hotkey is not None:
            self.start_hotkey = start_hotkey
        if stop_hotkey is not None:
            self.stop_hotkey = stop_hotkey
        if save_path is not None:
            self._default_save_path = save_path
        if record_mic is not None:
            self.record_mic = record_mic
        if record_system is not None:
            self.record_system = record_system
        # Re-setup hotkeys with new settings
        self.setup_hotkeys()

    def _create_output_folder(self) -> str:
        """Create output folder with today's date"""
        base_path = self._default_save_path
        if not base_path:
            # Default to user's Videos folder
            base_path = os.path.join(os.path.expanduser('~'), 'Videos')

        today = datetime.date.today()
        folder_name = today.strftime('%Y-%m-%d')
        folder_path = os.path.join(base_path, 'RF4_Recordings', folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def start_recording(self):
        """Start screen recording - called by hotkey or manual"""
        # NO OUTPUT WHATSOEVER in hotkey callback!
        # On Windows, any output in keyboard hotkey callback will cause
        # stdout buffering to hang until next key press - this is a keyboard library issue.
        # We must return IMMEDIATELY after starting background thread.
        if self.is_recording:
            # Even print here can cause hanging - skip output
            return

        # ALL actual work AND all output must happen on a separate background thread
        # This lets keyboard hotkey callback return immediately and avoids hanging
        start_thread = threading.Thread(
            target=self._start_recording_full,
            daemon=True
        )
        start_thread.start()

    def _start_recording_full(self):
        """Full start recording initialization - runs on background thread.

        All actual work and output are done here so keyboard hotkey callback
        can return immediately, avoiding stdout buffering hanging on Windows.
        """
        try:
            print(f"Starting full screen recording...")
            sys.stdout.flush()
            self._start_time_real = time.time()
            self._start_timestamp = time.strftime('%H-%M-%S')
            self.is_recording = True

            # Create output directory and file
            save_folder = self._create_output_folder()
            video_name = f"RF4_录屏_{self._start_timestamp}"
            self._save_path = os.path.join(save_folder, f"{video_name}_video.tmp.mp4")
            if self.record_mic or self.record_system:
                self._temp_audio_path = os.path.join(save_folder, f"{video_name}_audio.tmp.wav")
            else:
                self._temp_audio_path = None

            # Final path will include start and end time when we stop
            print(f"Recording started at: {self._start_timestamp}")
            print(f"Recording in progress... (final filename will include start/end time and duration when stopped)")
            sys.stdout.flush()

            # Get screen resolution
            screen_width, screen_height = pyautogui.size()
            print(f"Screen size: {screen_width}x{screen_height}")
            sys.stdout.flush()

            # Create overlay (if not exists) and start on main thread
            from PySide6.QtCore import QMetaObject, Qt
            self._ensure_overlay_created()
            if self._overlay:
                # Use queued connection, no blocking to avoid deadlock
                QMetaObject.invokeMethod(
                    self._overlay,
                    "start_recording",
                    Qt.ConnectionType.QueuedConnection
                )
                # Give a tiny delay to let overlay process on main thread
                time.sleep(0.1)

            # Start recording in background thread
            self._recording_thread = threading.Thread(
                target=self._recording_loop,
                args=(screen_width, screen_height),
                daemon=True
            )
            self._recording_thread.start()

            # Start audio recording if needed
            if (self.record_mic or self.record_system) and self._temp_audio_path:
                self._audio_thread = threading.Thread(
                    target=self._audio_recording_loop,
                    args=(self._temp_audio_path,),
                    daemon=True
                )
                self._audio_thread.start()

            print(f"Recording started successfully")
            sys.stdout.flush()
        except Exception as e:
            print(f"ERROR starting recording: {e}")
            sys.stdout.flush()
            self.is_recording = False

    def _recording_loop(self, screen_width: int, screen_height):
        """Recording loop that runs in background thread

        Note: On Windows, the overlay is already excluded from screen capture
        using Windows API SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE),
        so it never appears in screenshots - no need to hide/show anymore!
        This completely eliminates flickering.
        """
        # Video encoding
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(
            self._save_path, fourcc, 20.0, (screen_width, screen_height)
        )

        # Overlay is already excluded from capture by Windows API on Windows
        # No need to hide/show anymore - no flicker!

        # pyautogui.screenshot() is slow on high resolution screens (0.2-1s per frame
        # We cannot achieve 20 FPS in practice - just capture as fast as possible
        # Actual FPS will be around 2-5 on 4K screens, which is acceptable for screen recording
        self._frame_count = 0
        start_time = time.time()

        while self.is_recording:
            try:
                # Check flag again BEFORE capturing - exit immediately if stopped
                if not self.is_recording:
                    break

                # Capture screenshot - this is the slow part
                screenshot = pyautogui.screenshot()

                # Check flag AGAIN after screenshot completes - exit immediately if stopped
                if not self.is_recording:
                    break

                frame = np.array(screenshot)
                # Convert RGB to BGR for OpenCV
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self._video_writer.write(frame)
                self._frame_count += 1

                # Sleep very briefly just to check stop flag more frequently
                # Don't try to hit a target FPS we can't actually achieve
                if self.is_recording:
                    time.sleep(0.01)

            except Exception as e:
                print(f"Error during recording: {e}")
                break

        # Always release the video writer when done
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None
            total_elapsed = time.time() - start_time
            actual_fps = self._frame_count / total_elapsed if total_elapsed > 0 else 0
            print(f"Video writer released: {self._frame_count} frames in {total_elapsed:.1f}s, {actual_fps:.1f} FPS")

    def _on_overlay_audio_toggled(self, is_mic: bool, enabled: bool):
        """Callback from overlay when user toggles audio on/off"""
        if is_mic:
            self.record_mic = enabled
            print(f"Microphone {'enabled' if enabled else 'disabled'}")
        else:
            self.record_system = enabled
            print(f"System audio {'enabled' if enabled else 'disabled'}")

    def _audio_recording_loop(self, output_path: str):
        """Audio recording loop for microphone and/or system audio
        Supports dynamic toggling via overlay controls during recording

        ### Important note about system audio recording on Windows:
        To record system audio (game sound, etc.), you need to:
        1. Enable "Stereo Mix" or "What U Hear" in your sound card settings
        2. Set Stereo Mix as the default recording device
        3. If your sound card doesn't support Stereo Mix, you can use third-party
           software like VB-Cable to create a virtual audio device that captures system output

        For microphone recording: just ensure your mic is connected and set as default.
        """
        need_audio = self.record_mic or self.record_system
        if not need_audio:
            return

        # Try to import required libraries
        try:
            import wave
            if self.record_mic:
                import pyaudio
            if self.record_system:
                import sounddevice as sd
                import soundfile as sf
        except ImportError as e:
            print(f"Audio recording libraries missing: {e}")
            print("Please install: pip install pyaudio sounddevice soundfile")
            return

        sample_rate = 44100

        if self.record_mic and not self.record_system:
            # Only microphone with pyaudio, support dynamic toggling
            try:
                import pyaudio
                chunk_size = 1024
                p = pyaudio.PyAudio()

                # Get default input device info
                info = p.get_default_input_device_info()
                print(f"Recording microphone from default device: {info.get('name')}")

                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=chunk_size
                )

                audio_frames = []
                while self.is_recording:
                    if self.record_mic:
                        # Mic enabled, read actual data
                        data = stream.read(chunk_size, exception_on_overflow=False)
                        audio_frames.append(data)
                    else:
                        # Mic disabled, write silence
                        silence = b'\x00' * (2 * chunk_size)  # 16-bit = 2 bytes per sample
                        audio_frames.append(silence)
                        time.sleep(chunk_size / sample_rate)

                stream.stop_stream()
                stream.close()
                p.terminate()

                # Save as WAV
                if audio_frames:
                    wf = wave.open(output_path, 'wb')
                    wf.setnchannels(1)
                    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(audio_frames))
                    wf.close()
                    print(f"Microphone recording saved: {output_path} ({len(audio_frames)} frames)")
            except Exception as e:
                print(f"Microphone recording error: {e}")
                print("Tip: Check that your microphone is connected and enabled")

        elif self.record_system and not self.record_mic:
            # Use sounddevice to capture system audio from loopback devices
            # Simpler callback-based approach that avoids memory allocation issues
            # Automatically finds all input devices including Stereo Mix / What U Hear / VB-Cable / Intelligo VAC etc.
            try:
                import sounddevice as sd
                import soundfile as sf
                import numpy as np

                # Query all devices
                print(f"Scanning for input/loopback devices...")
                device_list = sd.query_devices()

                # Find all available input devices (any device with input channels)
                # This includes loopback devices like Stereo Mix, VB-Cable, Intelligo VAC, etc.
                input_devices = []
                for i, dev in enumerate(device_list):
                    if dev['max_input_channels'] > 0:
                        name = dev['name']
                        channels = dev['max_input_channels']
                        sample_rate = dev['default_samplerate']
                        input_devices.append((i, dev))
                        print(f"  Device {i}: {name} (channels: {channels}, rate: {int(sample_rate)})")

                if not input_devices:
                    print("Error: No input devices found! System audio recording disabled.")
                    return

                # Prefer devices that look like loopback devices
                # Common loopback device names contain keywords
                loopback_keywords = [
                    'stereo', 'mix', 'what', 'cable', 'output', 'loopback',
                    'virtual', 'line', 'vac',
                    '混音', '捕获', '输出', '虚拟', '捕获'
                ]
                # Exclude microphones - we only want system loopback
                exclude_keywords = [
                    'mic', 'microphone', '麦克风', '麦克风阵列'
                ]

                selected_devices = []

                for dev_idx, dev in input_devices:
                    name = dev['name']
                    name_lower = name.lower()

                    # Skip microphones - we don't want them in system audio capture
                    if any(keyword in name_lower for keyword in exclude_keywords):
                        continue

                    # Check if it matches loopback keywords
                    is_loopback = any(keyword in name_lower for keyword in loopback_keywords)

                    # Include if it matches loopback keywords
                    if is_loopback:
                        selected_devices.append((dev_idx, dev))

                # If no devices selected, fall back to all non-microphone input devices
                if not selected_devices:
                    print("No explicit loopback device found, falling back to all non-microphone input devices")
                    for dev_idx, dev in input_devices:
                        name_lower = dev['name'].lower()
                        if not any(keyword in name_lower for keyword in exclude_keywords):
                            selected_devices.append((dev_idx, dev))

                # If no loopback device found, just use all input devices
                if not selected_devices:
                    print("No explicit loopback device found, trying all input devices")
                    selected_devices = input_devices
                else:
                    print(f"Found {len(selected_devices)} candidate loopback device(s)")

                # Check if we have any devices after selection
                if not selected_devices:
                    print("Error: No candidate devices found!")
                    return

                # Check if only "主声音捕获驱动程序" is selected - this is usually useless
                # Open privacy settings immediately since it's likely a permission issue
                if len(selected_devices) == 1:
                    dev_name = selected_devices[0][1]['name']
                    if '主声音捕获驱动程序' in dev_name:
                        print("\nNote: Only '主声音捕获驱动程序' was found. This device usually doesn't capture actual audio.")
                        print("This likely means other loopback devices are blocked by Windows privacy settings.")
                        print("Opening Windows Microphone Privacy Settings...")
                        print("\nPlease enable microphone access for this application, then try again.")
                        try:
                            import subprocess
                            subprocess.run(['start', 'ms-settings:privacy-microphone'], shell=True)
                        except Exception:
                            pass

                # We'll record from all successfully opened devices and mix them
                # Store (buffer_list, dev_samplerate, name) along with the stream
                active_streams_data = []
                sample_rate = 44100  # Common output sample rate
                channels = 1  # Output mixed to mono

                # Create a callback for each stream that appends to its buffer
                def create_callback(buffer_list):
                    def callback(indata, frames, time, status):
                        if status:
                            print(status)
                        if self.record_system and self.is_recording:
                            # Mix to mono if input is stereo
                            if indata.shape[1] > 1:
                                mono = indata.mean(axis=1)
                            else:
                                mono = indata.flatten()
                            buffer_list.append(mono.copy())
                    return callback

                # Try to open a stream for each candidate device
                for dev_idx, dev in selected_devices:
                    max_in_ch = int(dev['max_input_channels'])
                    dev_channels = min(max_in_ch, 2)  # Use max 2 channels
                    dev_samplerate = dev['default_samplerate']

                    buffer_list = []
                    try:
                        stream = sd.InputStream(
                            device=dev_idx,
                            channels=dev_channels,
                            samplerate=dev_samplerate,
                            callback=create_callback(buffer_list)
                        )
                        active_streams_data.append((stream, buffer_list, dev_samplerate, dev['name']))
                        print(f"✓ Opened stream for: {dev['name']} ({int(dev_samplerate)}Hz)")
                    except Exception as e:
                        print(f"✗ Failed to open device {dev_idx} ({dev['name']}): {e}")

                if not active_streams_data:
                    print("Error: Could not open any input devices!")
                    print("\nThis is likely caused by Windows microphone privacy settings blocking access.")
                    print("Opening Windows Microphone Privacy Settings...")
                    print("\nPlease enable microphone access in:")
                    print("   Start → Settings → Privacy → Microphone")
                    print("\nOr enable Stereo Mix in Windows Sound settings:")
                    print("   Right-click speaker icon → Sounds → Recording → Enable '立体声混音'")
                    try:
                        import subprocess
                        subprocess.run(['start', 'ms-settings:privacy-microphone'], shell=True)
                    except Exception:
                        pass
                    return

                print(f"Starting system audio capture from {len(active_streams_data)} device(s)...")
                sys.stdout.flush()

                # Start all streams
                for stream, _, _, _ in active_streams_data:
                    stream.start()

                print(f"Recording...")
                sys.stdout.flush()
                # Just wait while recording is active
                # Check flag very frequently to exit immediately when stopped
                while self.is_recording:
                    time.sleep(0.001)  # Check 1000 times per second - exit instantly when stopped

                print(f"Stopping streams...")
                sys.stdout.flush()

                # 【CRITICAL FIX】First collect ALL audio data we've already captured from buffers
                # We already have all the data, so DO NOT wait for streams to close
                # Collect and save the audio FIRST, then close streams in background
                # This prevents hanging if stream closing blocks indefinitely on Windows
                print(f"  Collecting audio data from buffers...")
                sys.stdout.flush()

                # Collect all non-empty recordings NOW before closing anything
                recordings = []
                total_samples = 0
                collected = 0
                for stream, buffer_list, dev_samplerate, name in active_streams_data:
                    collected += 1
                    if not buffer_list or len(buffer_list) == 0:
                        print(f"    No data from {name}, skipping")
                        continue
                    # We already have all the data in memory - just concatenate it
                    full_rec = np.concatenate(buffer_list, axis=0)
                    recordings.append((full_rec, dev_samplerate))
                    total_samples += len(full_rec)
                    print(f"    Got {len(full_rec)} samples from {name}")

                print(f"  Already got data from {collected} of {len(active_streams_data)} streams")
                sys.stdout.flush()

                # Now process and save audio immediately while streams are still open
                # We don't need to close them to use the data we already have!
                print(f"Processing and saving audio...")
                sys.stdout.flush()

                try:
                    if not recordings:
                        print("Warning: No audio data captured from any device!")
                        print("\nThis is usually caused by Windows privacy settings blocking microphone access.")
                        print("Opening Windows Microphone Privacy Settings...")
                        sys.stdout.flush()
                        try:
                            import subprocess
                            subprocess.run(['start', 'ms-settings:privacy-microphone'], shell=True)
                        except Exception:
                            pass
                        # STILL close streams in background before returning
                        def cleanup_streams_bg():
                            for stream, _, _, name in active_streams_data:
                                try:
                                    stream.stop()
                                    stream.close()
                                except Exception:
                                    pass
                        cleanup_thread = threading.Thread(target=cleanup_streams_bg, daemon=True)
                        cleanup_thread.start()
                        return

                    # Resample all recordings to target 44100Hz and mix
                    target_rate = 44100
                    max_len = 0
                    resampled = []
                    print(f"    Target rate: {target_rate}Hz")
                    sys.stdout.flush()

                    # Keep only recordings that actually have signal (not silent)
                    # Many devices found by Windows are actually silent input devices
                    # Filtering them out improves volume a lot
                    active_recordings = []
                    for i, (arr, src_rate) in enumerate(recordings):
                        print(f"    Resampling device {i+1}/{len(recordings)} from {src_rate}Hz...")
                        sys.stdout.flush()
                        if src_rate == target_rate:
                            resampled_arr = arr
                        else:
                            # Simple linear resampling
                            ratio = src_rate / target_rate
                            new_len = int(len(arr) / ratio)
                            indices = np.arange(new_len) * ratio
                            resampled_arr = np.interp(indices, np.arange(len(arr)), arr)

                        # Check if this device actually has audio signal (not all silence)
                        # If the max absolute value is very low, it's just silence - skip it
                        if len(resampled_arr) > 0:
                            max_amp = np.max(np.abs(resampled_arr))
                            if max_amp < 0.001:
                                print(f"    Device {i+1} is silent - skipping")
                                continue
                            else:
                                print(f"    Device {i+1} has signal (max amp: {max_amp:.4f})")
                                active_recordings.append(resampled_arr)
                                if len(resampled_arr) > max_len:
                                    max_len = len(resampled_arr)
                        else:
                            print(f"    Device {i+1} is empty - skipping")

                    print(f"Final buffer size: {max_len} samples at {target_rate}Hz")
                    sys.stdout.flush()

                    if not active_recordings:
                        print("Warning: All devices are silent!")
                        # Still create silent output rather than failing
                        mixed = np.zeros(max_len, dtype=np.float64)
                    else:
                        resampled = active_recordings
                        print(f"  {len(resampled)} devices with active signal, {len(recordings) - len(resampled)} silent devices skipped")

                        # Mix all active recordings
                        print(f"  Mixing {len(resampled)} active streams...")
                        sys.stdout.flush()
                        mixed = np.zeros(max_len, dtype=np.float64)
                        for arr in resampled:
                            padded = np.zeros(max_len, dtype=np.float64)
                            padded[:len(arr)] = arr
                            mixed += padded

                        # Auto-normalize volume to match the loudest device
                        # This ensures output volume similar to what you get with a single device
                        peak = np.max(np.abs(mixed))
                        if peak > 0:
                            # Normalize to 0.8 peak (leaves some headroom to avoid clipping)
                            target_peak = 0.8
                            mixed = mixed * (target_peak / peak)
                            print(f"  Auto-normalized volume from peak {peak:.4f} to {target_peak:.1f}")

                    # Clamp to [-1, 1] to avoid clipping distortion
                    mixed = np.clip(mixed, -1.0, 1.0)

                    # Convert to int16 for WAV
                    mixed_int16 = (mixed * 32767).astype(np.int16)

                    # Check if completely silent
                    if np.all(mixed_int16 == 0):
                        print("Warning: Captured audio is completely silent!")
                        print("\nThis is usually caused by Windows privacy settings blocking microphone access.")
                        print("Opening Windows Microphone Privacy Settings...")
                        try:
                            import subprocess
                            subprocess.run(['start', 'ms-settings:privacy-microphone'], shell=True)
                        except Exception:
                            pass
                        # Close streams in background before returning
                        def cleanup_streams_bg():
                            for stream, _, _, name in active_streams_data:
                                try:
                                    stream.stop()
                                    stream.close()
                                except Exception:
                                    pass
                        cleanup_thread = threading.Thread(target=cleanup_streams_bg, daemon=True)
                        cleanup_thread.start()
                        return

                    # Save as WAV using soundfile - this is what we need for merging
                    print(f"Saving audio to: {output_path}")
                    sys.stdout.flush()
                    sf.write(output_path, mixed_int16, target_rate, 'PCM_16')
                    duration = len(mixed_int16) / target_rate
                    print(f"✓ System audio saved: {output_path}")
                    print(f"   Duration: {duration:.1f}s, Devices: {len(recordings)}")
                    print(f"   Audio is preserved as separate WAV file even if merging fails")
                    sys.stdout.flush()

                    # NOW - after audio is ALREADY saved to disk - close streams in background
                    # If closing hangs, it doesn't matter because we're done and the thread is daemon
                    def cleanup_streams_bg():
                        for stream, _, _, name in active_streams_data:
                            try:
                                stream.stop()
                                stream.close()
                            except Exception:
                                # If closing fails, just ignore - we already saved the audio!
                                pass
                    cleanup_thread = threading.Thread(target=cleanup_streams_bg, daemon=True)
                    cleanup_thread.start()

                except Exception as e:
                    print(f"Error during audio processing/saving: {e}")
                    print("Audio will be missing from final recording.")
                    # Always try to close streams in background
                    try:
                        def cleanup_streams_bg():
                            for stream, _, _, name in active_streams_data:
                                try:
                                    stream.stop()
                                    stream.close()
                                except Exception:
                                    pass
                        cleanup_thread = threading.Thread(target=cleanup_streams_bg, daemon=True)
                        cleanup_thread.start()
                    except Exception:
                        pass

            except ImportError as e:
                print(f"sounddevice/soundfile not installed: {e}")
                print("To capture system audio:")
                print("   pip install sounddevice soundfile")
            except Exception as e:
                print(f"System audio capture error: {e}")

        elif self.record_mic and self.record_system:
            # Both mic and system - this requires proper audio routing
            # Best way is to have a device that already captures both
            try:
                import sounddevice as sd
                import soundfile as sf
                import numpy as np

                default_device = sd.default.device[0]
                device_info = sd.query_devices(default_device)
                channels = max(2, device_info['max_input_channels'])
                print(f"Recording both mic + system audio from device: {device_info['name']}")
                print("Note: This requires a single input device that captures both")

                recording = []

                def callback(indata, frames, time, status):
                    if status:
                        print(status)
                    recording.append(indata.copy())
                    if not self.is_recording:
                        return None, sd.CallbackStop

                with sd.InputStream(samplerate=sample_rate, channels=channels, callback=callback):
                    while self.is_recording:
                        sd.sleep(100)

                if recording:
                    full_recording = np.concatenate(recording, axis=0)
                    sf.write(output_path, full_recording, sample_rate)
                    print(f"Combined audio recording saved: {output_path}")
            except Exception as e:
                print(f"Combined audio recording error: {e}")

    def stop_recording(self):
        """Stop screen recording - called by hotkey or manual"""
        # NO OUTPUT WHATSOEVER in hotkey callback!
        # On Windows, any output in keyboard hotkey callback will cause
        # stdout buffering to hang until next key press - this is a keyboard library issue.
        # We must return IMMEDIATELY after starting background thread.
        if not self.is_recording:
            # Even print here can cause hanging - skip output
            return

        # ALL actual work AND all output must happen on a separate background thread
        # This lets keyboard hotkey callback return immediately and avoids hanging
        post_process_thread = threading.Thread(
            target=self._stop_post_processing_full,
            daemon=True
        )
        post_process_thread.start()

    def _stop_post_processing_full(self):
        """Full stop and post-processing - runs on background thread.

        This is the full version that does ALL work after stop recording.
        All work is done here so keyboard hotkey callback can return immediately
        which fixes stdout buffering hanging on Windows.
        """
        try:
            print("Stopping recording...")
            sys.stdout.flush()

            # Set flag to stop recording loops
            self.is_recording = False
            self._end_time_real = time.time()
            self._end_timestamp = time.strftime('%H-%M-%S')

            # Calculate duration
            duration_seconds = int(self._end_time_real - self._start_time_real)
            duration_minutes = duration_seconds // 60
            duration_seconds_remaining = duration_seconds % 60
            self._duration_str = f"{duration_minutes}m{duration_seconds_remaining}s"

            # Stop overlay - use queued connection, no blocking
            # BlockingQueuedConnection can cause deadlock when called from background thread
            if self._overlay:
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self._overlay,
                    "stop_recording",
                    Qt.ConnectionType.QueuedConnection
                )
                # Give a tiny delay to let overlay process on main thread
                time.sleep(0.1)

            # Create final filename with start time, end time, and duration
            save_folder = os.path.dirname(self._save_path)
            final_filename = f"RF4_录屏_{self._start_timestamp}_{self._end_timestamp}_{self._duration_str}.mp4"
            self._final_path = os.path.join(save_folder, final_filename)

            # Wait for recording thread to finish with timeout
            # On high resolution screens, pyautogui.screenshot() can be slow
            # Give enough time for the current screenshot to complete
            if self._recording_thread and self._recording_thread.is_alive():
                print("Waiting for recording thread to finish...")
                sys.stdout.flush()
                self._recording_thread.join(timeout=10.0)
                if self._recording_thread.is_alive():
                    print("Note: Video thread timed out after 10s, continuing...")
                    sys.stdout.flush()

            # Wait for audio thread to finish with timeout
            # Audio must finish saving the WAV file before we can merge
            # Give shorter timeout because audio data is already in memory
            # and saving is fast - if it times out, it's stuck due to
            # Windows keyboard library buffering issues, we can still continue
            if self._audio_thread and self._audio_thread.is_alive():
                print("Waiting for audio thread to finish...")
                sys.stdout.flush()
                self._audio_thread.join(timeout=15.0)
                if self._audio_thread.is_alive():
                    print("Note: Audio thread taking longer than expected - continuing in background")
                    print("Audio capture should still work, merging will proceed shortly")
                    sys.stdout.flush()
                    # Detach the audio thread - it will finish eventually
                    self._audio_thread = None

            # Ensure video writer is released even if thread timed out
            if self._video_writer is not None:
                self._video_writer.release()
                self._video_writer = None
                print("Video writer released")
                sys.stdout.flush()

            self._recording_thread = None
            self._audio_thread = None

            # Emit signal so main thread can handle post-processing if needed
            self.recording_finished.emit(self._final_path)

            print(f"Stopping recording, finalizing output in background...")
            sys.stdout.flush()

            # Finalize saving (merge audio/video, cleanup temp files)
            self._finalize_saving()
        except Exception as e:
            # Catch ANY exception during post-processing and ensure we at least get the video
            print(f"ERROR during post-processing: {e}")
            print("Ensuring video file is saved...")
            sys.stdout.flush()
            # Emergency fallback: just copy temp video to final location
            if os.path.exists(self._save_path) and os.path.getsize(self._save_path) > 0:
                try:
                    if os.path.exists(self._final_path):
                        os.remove(self._final_path)
                    os.rename(self._save_path, self._final_path)
                    print(f"Emergency fallback: saved video to: {self._final_path}")
                    print("No audio included because post-processing failed")
                    if self._temp_audio_path and os.path.exists(self._temp_audio_path) and os.path.getsize(self._temp_audio_path) > 0:
                        print(f"\n✓ Audio was successfully captured and saved as separate WAV: {self._temp_audio_path}")
                except Exception:
                    # If rename fails, at least leave temp file where it is
                    print(f"Could not rename, temp video remains at: {self._save_path}")
            else:
                print(f"ERROR: No temp video file found at: {self._save_path}")
            sys.stdout.flush()

    def _stop_post_processing(self):
        """Legacy post-processing - kept for compatibility, now unused"""
        self._stop_post_processing_full()

    def _finalize_saving(self):
        """Finalize saving after recording stopped"""
        # Merge audio if we recorded audio
        merge_success = False
        if self._temp_audio_path:
            if os.path.exists(self._temp_audio_path) and os.path.getsize(self._temp_audio_path) > 0:
                size_mb = os.path.getsize(self._temp_audio_path) / (1024*1024)
                print(f"\n✓ Audio is already captured and saved: {self._temp_audio_path} ({size_mb:.2f} MB)")
                print(f"Merging audio into final video...")
                sys.stdout.flush()
                merge_success = self._merge_audio_video(self._save_path, self._temp_audio_path, self._final_path)
                # Check if output was created and merge succeeded
                if merge_success and os.path.exists(self._final_path) and os.path.getsize(self._final_path) > 0:
                    # Cleanup both temp video file and temp audio file
                    # Audio is already merged into final video, so temp files are not needed
                    try:
                        if os.path.exists(self._save_path):
                            os.remove(self._save_path)
                        if os.path.exists(self._temp_audio_path):
                            os.remove(self._temp_audio_path)
                        print(f"✓ Merge successful, all temporary files cleaned up")
                    except Exception as e:
                        print(f"Warning: Failed to cleanup some temp files: {e}")
                    merge_success = True
                else:
                    print(f"Warning: Merge output not found, audio file kept at: {self._temp_audio_path}")
            else:
                print(f"Warning: Audio file missing or empty: {self._temp_audio_path}")
                sys.stdout.flush()

        if not merge_success:
            # No audio or merge failed - just copy temp to final
            if os.path.exists(self._save_path) and os.path.getsize(self._save_path) > 0:
                try:
                    import shutil
                    if os.path.exists(self._final_path):
                        try:
                            os.remove(self._final_path)
                        except Exception:
                            pass
                    # Use copy2 instead of rename - works even if original is still locked
                    shutil.copy2(self._save_path, self._final_path)
                    # Try to delete original only after copying
                    try:
                        os.remove(self._save_path)
                    except Exception:
                        # If delete fails, leave it - no big deal
                        print(f"Note: Could not delete temp file (still locked), leaving at: {self._save_path}")
                    print(f"Copied temp video to final: {self._final_path}")
                    print(f"Final output saved: {self._final_path} (no audio)")
                    if self._temp_audio_path and os.path.exists(self._temp_audio_path) and os.path.getsize(self._temp_audio_path) > 0:
                        print(f"\n✓ Audio was successfully captured and saved as separate WAV: {self._temp_audio_path}")
                        print(f"  You can open this file directly to verify audio recording works")
                except Exception as e:
                    print(f"Failed to copy temp file: {e}")
                    # If copy fails, just keep the temp name
                    self._final_path = self._save_path
                    print(f"Final output remains at temp location: {self._final_path} (no audio)")
            else:
                print(f"ERROR: Temp video file is empty or missing: {self._save_path}")
        else:
            # Merge was successful, confirm final path
            print(f"\n✅ Done! Final recording: {self._final_path}")
        sys.stdout.flush()

    def _merge_audio_video(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """Merge video and audio using ffmpeg if available"""

        # Normalize all paths to native OS format - fixes mixed slashes on Windows
        video_path = os.path.abspath(video_path)
        audio_path = os.path.abspath(audio_path)
        output_path = os.path.abspath(output_path)

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        print(f"Merge debug info:")
        print(f"  Input video: {video_path} ({os.path.getsize(video_path)} bytes)")
        print(f"  Input audio: {audio_path} ({os.path.getsize(audio_path)} bytes)")
        print(f"  Output: {output_path}")
        sys.stdout.flush()

        # Verify input files exist
        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            print(f"✗ Input video file missing or empty: {video_path}")
            return False
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            print(f"✗ Input audio file missing or empty: {audio_path}")
            return False

        # Try to find ffmpeg
        ffmpeg_path = self._find_ffmpeg()
        if ffmpeg_path:
            ffmpeg_path = os.path.abspath(ffmpeg_path)
            print(f"Found FFmpeg at: {ffmpeg_path}")
            sys.stdout.flush()

            # Delete output if exists to ensure we create fresh
            if os.path.exists(output_path):
                os.remove(output_path)
            # Use system ffmpeg - faster and more reliable
            try:
                # Calculate actual FPS based on recording duration and frame count
                # Because pyautogui.screenshot() is slow on high resolution screens
                # we cannot achieve 20 FPS - actual FPS is much lower
                # We need to fix the FPS metadata so video duration is correct
                total_elapsed = self._end_time_real - self._start_time_real
                frame_count = getattr(self, '_frame_count', 0)
                if frame_count > 0 and total_elapsed > 0:
                    actual_fps = frame_count / total_elapsed
                else:
                    actual_fps = 10.0

                print(f"Fixing video duration: {frame_count} frames in {total_elapsed:.1f}s → {actual_fps:.2f} FPS")
                sys.stdout.flush()

                # Convert paths to absolute and quoted - handles spaces in paths on Windows
                # Use ffmpeg to merge: copy video stream, convert audio to AAC
                # -r {actual_fps} before input sets the input frame rate so duration is correct
                cmd = [
                    ffmpeg_path,
                    '-y',  # Overwrite output if exists
                    '-v', 'info',  # Show informational messages
                    '-r', f'{actual_fps}',  # Set correct input frame rate to fix duration
                    '-i', video_path,  # Input video
                    '-i', audio_path,  # Input audio
                    '-c:v', 'copy',  # Copy video stream without re-encoding - keeps quality, fast
                    '-c:a', 'aac',  # Encode audio to AAC (MP4 standard)
                    '-b:a', '192k',  # Audio bitrate - good quality
                    '-map', '0:v:0',  # Use video from first input
                    '-map', '1:a:0',  # Use audio from second input
                    '-movflags', '+faststart',  # Put MOOV atom at start for better compatibility
                    output_path
                ]
                print(f"Running FFmpeg:\n  {' '.join(cmd)}")
                sys.stdout.flush()
                result = subprocess.run(cmd, capture_output=True, timeout=300)
                if result.returncode == 0:
                    # Check output
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"✓ Successfully merged video and audio into: {output_path}")
                        print(f"   Video size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
                        return True
                    else:
                        print(f"✗ FFmpeg output is empty or missing")
                        sys.stdout.flush()
                else:
                    print(f"✗ FFmpeg merge failed with copy codec, return code: {result.returncode}")
                    if result.stdout:
                        print(f"   stdout:\n{result.stdout.decode()}")
                    if result.stderr:
                        print(f"   stderr:\n{result.stderr.decode()}")
                    print(f"   Retrying with video re-encoding...")
                    sys.stdout.flush()

                    # Try again with full re-encoding - sometimes copy doesn't work with OpenCV mp4v
                    # Add the same correct FPS fix for duration
                    cmd = [
                        ffmpeg_path,
                        '-y',
                        '-v', 'info',
                        '-r', f'{actual_fps}',
                        '-i', video_path,
                        '-i', audio_path,
                        '-c:v', 'libx264',
                        '-crf', '23',
                        '-preset', 'fast',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        '-map', '0:v:0',
                        '-map', '1:a:0',
                        '-movflags', '+faststart',
                        output_path
                    ]
                    print(f"Retrying with re-encoding:\n  {' '.join(cmd)}")
                    sys.stdout.flush()
                    result = subprocess.run(cmd, capture_output=True, timeout=600)
                    if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        print(f"✓ Successfully merged with re-encoding")
                        print(f"   Video size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
                        return True
                    else:
                        print(f"✗ Re-encoding also failed")
                        if result.stderr:
                            print(f"   stderr: {result.stderr.decode()}")
                        sys.stdout.flush()

                # Third attempt: simpler command - just copy everything without complex options
                print(f"   Trying simpler FFmpeg command as third attempt...")
                sys.stdout.flush()
                cmd_simple = [
                    ffmpeg_path,
                    '-y',
                    '-i', video_path,
                    '-i', audio_path,
                    output_path
                ]
                print(f"Simple FFmpeg:\n  {' '.join(cmd_simple)}")
                sys.stdout.flush()
                result = subprocess.run(cmd_simple, capture_output=True, timeout=600)
                if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"✓ Successfully merged with simple FFmpeg command")
                    print(f"   Video size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
                    return True
                else:
                    print(f"✗ Simple command also failed")
                    sys.stdout.flush()

                print(f"   Trying moviepy fallback as last resort...")
                sys.stdout.flush()
            except Exception as e:
                print(f"✗ FFmerge failed with exception: {e}")
                print(f"   Trying moviepy fallback as last resort...")
                sys.stdout.flush()

        # Fallback: use moviepy if available
        print(f"\nTrying moviepy for audio/video merging...")
        sys.stdout.flush()
        print("\nNote: First run with moviepy will automatically download ffmpeg (≈50MB)...")
        print("      This may take 1-2 minutes depending on your internet connection.")
        print("      Please wait...\n")
        sys.stdout.flush()
        try:
            # Calculate correct actual FPS to fix duration
            # Because OpenCV wrote wrong FPS metadata, we need to correct it
            total_elapsed = self._end_time_real - self._start_time_real
            frame_count = getattr(self, '_frame_count', 0)
            if frame_count > 0 and total_elapsed > 0:
                actual_fps = frame_count / total_elapsed
            else:
                actual_fps = 10.0

            print(f"Fixing video duration: {frame_count} frames in {total_elapsed:.1f}s → {actual_fps:.2f} FPS")
            sys.stdout.flush()

            # Import moviepy
            try:
                # moviepy >= 2.0 exports directly from moviepy module
                from moviepy import VideoFileClip, AudioFileClip
            except ImportError:
                # Older moviepy imports from moviepy.editor
                from moviepy.editor import VideoFileClip, AudioFileClip

            print(f"  Loading video: {video_path}")
            sys.stdout.flush()
            video_clip = VideoFileClip(video_path)
            print(f"  Original: duration: {video_clip.duration:.2f}s, fps: {video_clip.fps}")
            sys.stdout.flush()

            print(f"  Loading audio: {audio_path}")
            sys.stdout.flush()
            audio_clip = AudioFileClip(audio_path)
            print(f"  Audio: duration: {audio_clip.duration:.2f}s")
            sys.stdout.flush()

            print(f"  Merging audio to video...")
            sys.stdout.flush()
            # Newer moviepy uses .with_audio(), older uses .set_audio()
            try:
                final_clip = video_clip.with_audio(audio_clip)
            except AttributeError:
                final_clip = video_clip.set_audio(audio_clip)

            print(f"  Writing output file with corrected FPS...")
            sys.stdout.flush()

            # Multiple tries with different parameters for different moviepy versions
            # Good video bitrate to avoid too much compression
            # Write file first, then close clips - ensure everything is flushed
            try:
                print(f"  Starting write with libx264...")
                sys.stdout.flush()
                # Explicit parameters to ensure audio is included
                # crf not supported on older moviepy versions, just use bitrate
                final_clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    audio_bitrate='192k',
                    fps=actual_fps,
                    bitrate='5000k',  # Minimum video bitrate for good quality
                    logger=None
                )
                print(f"  Write completed, closing clips...")
                sys.stdout.flush()
                final_clip.close()
                video_clip.close()
                audio_clip.close()
            except TypeError as te:
                if 'logger' in str(te):
                    # Try 2: without logger parameter
                    print(f"  Retrying without logger parameter...")
                    sys.stdout.flush()
                    final_clip.write_videofile(
                        output_path,
                        codec='libx264',
                        audio_codec='aac',
                        audio_bitrate='192k',
                        fps=actual_fps,
                        bitrate='5000k'
                    )
                    final_clip.close()
                    video_clip.close()
                    audio_clip.close()
                elif 'crf' in str(te):
                    # Just retry without crf for older versions
                    print(f"  Retrying without crf parameter...")
                    sys.stdout.flush()
                    final_clip.write_videofile(
                        output_path,
                        codec='libx264',
                        audio_codec='aac',
                        audio_bitrate='192k',
                        fps=actual_fps,
                        bitrate='5000k',
                        logger=None
                    )
                    final_clip.close()
                    video_clip.close()
                    audio_clip.close()
                else:
                    raise

            # Force sync to disk
            import gc
            gc.collect()

            # Verify output was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                size_mb = os.path.getsize(output_path) / (1024*1024)
                print(f"✓ Successfully merged video and audio with moviepy: {output_path}")
                print(f"   Video size: {size_mb:.1f} MB")
                # Sanity check - if output is too small, something is wrong
                if size_mb < os.path.getsize(video_path) * 0.2:
                    print(f"⚠ Warning: Output is much smaller than input - this might be a problem")
                    print(f"   Input: {os.path.getsize(video_path) / (1024*1024):.1f} MB, Output: {size_mb:.1f} MB")
                sys.stdout.flush()
                return True
            else:
                print(f"✗ Moviepy: Output file not created or empty")
                sys.stdout.flush()
                return False

        except ImportError as e:
            print(f"\n✗ ImportError when loading moviepy: {e}")
            print("\n" + "=" * 60)
            print("WARNING: Cannot merge audio and video!")
            print("Neither system ffmpeg nor moviepy available.")
            print("\nTo enable automatic merging, install moviepy:")
            print("   pip install moviepy")
            print("\nmoviepy will automatically download ffmpeg on first use - no manual setup needed!")
            print("=" * 60 + "\n")
            print(f"Video (no audio) saved to: {output_path}")
            print(f"Audio saved separately to: {audio_path}")
            sys.stdout.flush()
            # Just copy video to output
            try:
                import shutil
                shutil.copy2(video_path, output_path)
            except Exception as e:
                print(f"Failed to copy video: {e}")
                sys.stdout.flush()
            return False
        except Exception as e:
            import traceback
            print(f"\n✗ Moviepy merge failed with exception:")
            print(f"   {type(e).__name__}: {e}")
            print("   Full traceback:")
            traceback.print_exc()
            print(f"\nVideo (no audio) saved to: {output_path}")
            print(f"Audio saved separately to: {audio_path}")
            sys.stdout.flush()
            return False

    def _find_ffmpeg(self) -> str | None:
        """Try to find ffmpeg in system path and moviepy's downloaded copy.
        If moviepy is already installed, it definitely has FFmpeg - just get it from there.
        """
        import shutil
        # First check system PATH
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            print(f"  Found FFmpeg in system PATH: {ffmpeg}")
            return ffmpeg

        # If moviepy is installed, try to get FFmpeg path from it directly
        # This is 100% reliable because moviepy already has it
        try:
            # Try imageio-ffmpeg which is what moviepy uses now
            try:
                from imageio_ffmpeg import get_ffmpeg_exe
                ffmpeg_path = get_ffmpeg_exe()
                if ffmpeg_path and os.path.exists(ffmpeg_path):
                    print(f"  Found FFmpeg from imageio-ffmpeg: {ffmpeg_path}")
                    return ffmpeg_path
            except ImportError:
                pass

            # Check common imageio-ffmpeg installation paths
            import site
            for site_pkg in site.getsitepackages():
                candidates = [
                    os.path.join(site_pkg, 'imageio_ffmpeg', 'bin', 'ffmpeg.exe'),
                    os.path.join(site_pkg, 'imageio-ffmpeg', 'imageio_ffmpeg', 'bin', 'ffmpeg.exe'),
                ]
                for candidate in candidates:
                    if os.path.exists(candidate):
                        print(f"  Found FFmpeg in imageio-ffmpeg package: {candidate}")
                        return candidate
        except Exception:
            pass

        # Try to find moviepy's downloaded ffmpeg in all common locations
        # moviepy stores ffmpeg in different places depending on version
        user_home = os.path.expanduser('~')
        appdata = os.getenv('APPDATA')
        local_appdata = os.getenv('LOCALAPPDATA')

        moviepy_paths = []

        # Classic moviepy location (APPDATA)
        if appdata:
            moviepy_paths.append(os.path.join(appdata, 'moviepy', 'ffmpeg', 'ffmpeg.exe'))
            moviepy_paths.append(os.path.join(appdata, 'local', 'moviepy', 'ffmpeg', 'ffmpeg.exe'))

        # Local appdata location
        if local_appdata:
            moviepy_paths.append(os.path.join(local_appdata, 'moviepy', 'ffmpeg', 'ffmpeg.exe'))

        # User home locations
        moviepy_paths.extend([
            os.path.join(user_home, '.moviepy', 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(user_home, '.moviepy', 'ffmpeg', 'ffmpeg.exe'),
            os.path.join(user_home, 'AppData', 'Roaming', 'moviepy', 'ffmpeg', 'ffmpeg.exe'),
            os.path.join(user_home, 'AppData', 'Local', 'moviepy', 'ffmpeg', 'ffmpeg.exe'),
        ])

        # Common Windows locations
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\ffmpeg\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
            r'C:\Users\{}\ffmpeg\bin\ffmpeg.exe'.format(os.getenv('USERNAME', '')),
            r'D:\ffmpeg\bin\ffmpeg.exe',
            r'D:\Program Files\ffmpeg\bin\ffmpeg.exe',
        ]
        moviepy_paths.extend(common_paths)

        # Check all paths
        for path in moviepy_paths:
            if os.path.exists(path):
                print(f"  Found FFmpeg at: {path}")
                return path

        print(f"  No FFmpeg found, will try moviepy fallback")
        return None

    def is_currently_recording(self) -> bool:
        """Check if currently recording"""
        return self.is_recording
