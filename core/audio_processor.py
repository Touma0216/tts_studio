# core/audio_processor.py
class AudioProcessor:
    def __init__(self):
        self.filters = {
            'declipping': True,
            'denoise': True, 
            'dehum': True,
            'normalize': True
        }
    
    def process_audio(self, audio, sample_rate):
        # チェーンで処理
        processed = audio
        if self.filters['declipping']:
            processed = self.fix_clipping(processed, sample_rate)
        if self.filters['dehum']:
            processed = self.remove_hum(processed, sample_rate)
        if self.filters['denoise']:
            processed = self.reduce_noise(processed, sample_rate)
        if self.filters['normalize']:
            processed = self.normalize_loudness(processed, sample_rate)
        return processed