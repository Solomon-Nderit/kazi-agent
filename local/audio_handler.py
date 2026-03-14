import pyaudio
import asyncio

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

class AudioHandler:
    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.audio_stream = None
        self.play_stream = None
        
    def start_recording(self):
        mic_info = self.pya.get_default_input_device_info()
        self.audio_stream = self.pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        # return chunk generator
        return self.audio_stream
        
    def start_playback(self):
        self.play_stream = self.pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        
    def play_chunk(self, data: bytes):
        if self.play_stream:
            self.play_stream.write(data)

    def close(self):
        if self.audio_stream:
            self.audio_stream.close()
        if self.play_stream:
            self.play_stream.close()
        self.pya.terminate()
