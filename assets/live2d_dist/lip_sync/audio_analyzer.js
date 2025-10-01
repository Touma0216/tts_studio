/**
 * リアルタイム音声解析エンジン (JavaScript)
 * Web Audio APIを使用してマイクからの音声を解析
 */

class AudioAnalyzer {
    constructor() {
        this.audioContext = null;
        this.analyserNode = null;
        this.microphone = null;
        this.dataArray = null;
        this.bufferLength = 0;
        
        this.isAnalyzing = false;
        this.sampleRate = 44100;
        this.fftSize = 2048;
        
        // 音声解析設定
        this.settings = {
            smoothingTimeConstant: 0.8,
            fftSize: 2048,
            minDecibels: -100,
            maxDecibels: -30,
            volumeThreshold: 0.01,
            frequencyRanges: {
                low: { min: 80, max: 500 },      // 低域
                mid: { min: 500, max: 2000 },    // 中域  
                high: { min: 2000, max: 8000 }   // 高域
            }
        };
        
        // 母音検出用フォルマント設定
        this.vowelFormants = {
            'a': { f1: 730, f2: 1090 },  // あ
            'i': { f1: 270, f2: 2290 },  // い
            'u': { f1: 300, f2: 870 },   // う
            'e': { f1: 530, f2: 1840 },  // え
            'o': { f1: 570, f2: 840 }    // お
        };
        
        // 分析結果コールバック
        this.analysisCallbacks = [];
        this.volumeCallbacks = [];
        
        console.log("🎤 AudioAnalyzer initialized");
    }
    
    /**
     * マイクへのアクセス許可を要求し、音声解析を開始
     * @returns {Promise<boolean>} 成功時true
     */
    async startAnalysis() {
        try {
            console.log("🎤 マイクアクセス要求中...");
            
            // ブラウザサポートチェック
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("このブラウザはマイクアクセスをサポートしていません");
            }
            
            // マイクアクセス取得
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: false,
                    sampleRate: this.sampleRate
                }
            });
            
            // AudioContext初期化
            await this.initializeAudioContext(stream);
            
            // 解析開始
            this.isAnalyzing = true;
            this.analyzeAudio();
            
            console.log("✅ 音声解析開始");
            return true;
            
        } catch (error) {
            console.error("❌ 音声解析開始エラー:", error);
            return false;
        }
    }
    
    /**
     * 音声解析を停止
     */
    stopAnalysis() {
        try {
            console.log("⏹️ 音声解析停止中...");
            
            this.isAnalyzing = false;
            
            // マイクストリーム停止
            if (this.microphone && this.microphone.mediaStream) {
                const tracks = this.microphone.mediaStream.getTracks();
                tracks.forEach(track => track.stop());
            }
            
            // AudioContext終了
            if (this.audioContext && this.audioContext.state !== 'closed') {
                this.audioContext.close();
            }
            
            // リセット
            this.audioContext = null;
            this.analyserNode = null;
            this.microphone = null;
            this.dataArray = null;
            
            console.log("✅ 音声解析停止完了");
            
        } catch (error) {
            console.error("❌ 音声解析停止エラー:", error);
        }
    }
    
    /**
     * AudioContextの初期化
     * @param {MediaStream} stream - マイクストリーム
     */
    async initializeAudioContext(stream) {
        try {
            // AudioContext作成
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // AudioContextが停止していたら再開
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            this.sampleRate = this.audioContext.sampleRate;
            
            // マイク入力ソース
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            this.microphone.mediaStream = stream;
            
            // アナライザーノード
            this.analyserNode = this.audioContext.createAnalyser();
            this.analyserNode.fftSize = this.settings.fftSize;
            this.analyserNode.smoothingTimeConstant = this.settings.smoothingTimeConstant;
            this.analyserNode.minDecibels = this.settings.minDecibels;
            this.analyserNode.maxDecibels = this.settings.maxDecibels;
            
            // 接続
            this.microphone.connect(this.analyserNode);
            
            // データ配列初期化
            this.bufferLength = this.analyserNode.frequencyBinCount;
            this.dataArray = new Uint8Array(this.bufferLength);
            
            console.log(`🔧 AudioContext初期化完了 (${this.sampleRate}Hz, FFT:${this.settings.fftSize})`);
            
        } catch (error) {
            console.error("❌ AudioContext初期化エラー:", error);
            throw error;
        }
    }
    
    /**
     * メイン音声解析ループ
     */
    analyzeAudio() {
        if (!this.isAnalyzing || !this.analyserNode) {
            return;
        }
        
        try {
            // 周波数データ取得
            this.analyserNode.getByteFrequencyData(this.dataArray);
            
            // 分析実行
            const analysisResult = this.performFrequencyAnalysis(this.dataArray);
            
            // コールバック実行
            this.notifyAnalysisCallbacks(analysisResult);
            
            // 次のフレームで再実行
            requestAnimationFrame(() => this.analyzeAudio());
            
        } catch (error) {
            console.error("⚠️ 音声解析エラー:", error);
            // エラーが発生しても解析を続行
            requestAnimationFrame(() => this.analyzeAudio());
        }
    }
    
    /**
     * 周波数解析を実行
     * @param {Uint8Array} frequencyData - 周波数データ
     * @returns {Object} 解析結果
     */
    performFrequencyAnalysis(frequencyData) {
        const analysisResult = {
            timestamp: Date.now() / 1000,
            volume: 0,
            dominantFrequency: 0,
            formants: [],
            vowelCandidate: 'sil',
            confidence: 0,
            frequencySpectrum: {
                low: 0,
                mid: 0,
                high: 0
            }
        };
        
        try {
            // 音量計算（RMS）
            analysisResult.volume = this.calculateVolume(frequencyData);
            
            // 音量が閾値以下の場合は無音として扱う
            if (analysisResult.volume < this.settings.volumeThreshold) {
                return analysisResult;
            }
            
            // 主要周波数検出
            analysisResult.dominantFrequency = this.findDominantFrequency(frequencyData);
            
            // 周波数帯域別エネルギー
            analysisResult.frequencySpectrum = this.analyzeFrequencySpectrum(frequencyData);
            
            // フォルマント検出
            analysisResult.formants = this.detectFormants(frequencyData);
            
            // 母音推定
            if (analysisResult.formants.length >= 2) {
                const vowelResult = this.estimateVowel(analysisResult.formants);
                analysisResult.vowelCandidate = vowelResult.vowel;
                analysisResult.confidence = vowelResult.confidence;
            }
            
        } catch (error) {
            console.error("⚠️ 周波数解析処理エラー:", error);
        }
        
        return analysisResult;
    }
    
    /**
     * 音量を計算（RMS）
     * @param {Uint8Array} frequencyData - 周波数データ
     * @returns {number} 音量値 (0.0-1.0)
     */
    calculateVolume(frequencyData) {
        let sum = 0;
        for (let i = 0; i < frequencyData.length; i++) {
            sum += frequencyData[i] * frequencyData[i];
        }
        
        const rms = Math.sqrt(sum / frequencyData.length);
        return rms / 255.0; // 正規化
    }
    
    /**
     * 主要周波数を検出
     * @param {Uint8Array} frequencyData - 周波数データ
     * @returns {number} 主要周波数（Hz）
     */
    findDominantFrequency(frequencyData) {
        let maxIndex = 0;
        let maxValue = 0;
        
        // 80Hz～8000Hzの範囲で検索
        const minBin = Math.floor(80 * this.bufferLength / (this.sampleRate / 2));
        const maxBin = Math.floor(8000 * this.bufferLength / (this.sampleRate / 2));
        
        for (let i = minBin; i < maxBin && i < frequencyData.length; i++) {
            if (frequencyData[i] > maxValue) {
                maxValue = frequencyData[i];
                maxIndex = i;
            }
        }
        
        // ビン番号を周波数に変換
        const frequency = (maxIndex * this.sampleRate) / (2 * this.bufferLength);
        return frequency;
    }
    
    /**
     * 周波数スペクトラム解析
     * @param {Uint8Array} frequencyData - 周波数データ
     * @returns {Object} 各帯域のエネルギー
     */
    analyzeFrequencySpectrum(frequencyData) {
        const spectrum = { low: 0, mid: 0, high: 0 };
        
        const ranges = this.settings.frequencyRanges;
        
        Object.keys(ranges).forEach(band => {
            const range = ranges[band];
            const minBin = Math.floor(range.min * this.bufferLength / (this.sampleRate / 2));
            const maxBin = Math.floor(range.max * this.bufferLength / (this.sampleRate / 2));
            
            let sum = 0;
            let count = 0;
            
            for (let i = minBin; i <= maxBin && i < frequencyData.length; i++) {
                sum += frequencyData[i];
                count++;
            }
            
            spectrum[band] = count > 0 ? (sum / count) / 255.0 : 0;
        });
        
        return spectrum;
    }
    
    /**
     * フォルマント検出
     * @param {Uint8Array} frequencyData - 周波数データ
     * @returns {Array<number>} フォルマント周波数のリスト
     */
    detectFormants(frequencyData) {
        const formants = [];
        
        try {
            // ピーク検出用の閾値
            const threshold = Math.max(...frequencyData) * 0.15;
            
            // 200Hz～3000Hzの範囲でピーク検出
            const minBin = Math.floor(200 * this.bufferLength / (this.sampleRate / 2));
            const maxBin = Math.floor(3000 * this.bufferLength / (this.sampleRate / 2));
            
            const peaks = [];
            
            // ローカルマキシマ検出
            for (let i = minBin + 1; i < maxBin - 1 && i < frequencyData.length - 1; i++) {
                if (frequencyData[i] > frequencyData[i - 1] &&
                    frequencyData[i] > frequencyData[i + 1] &&
                    frequencyData[i] > threshold) {
                    
                    const frequency = (i * this.sampleRate) / (2 * this.bufferLength);
                    peaks.push({
                        frequency: frequency,
                        amplitude: frequencyData[i]
                    });
                }
            }
            
            // 振幅でソート（大きい順）
            peaks.sort((a, b) => b.amplitude - a.amplitude);
            
            // 上位のピークをフォルマントとして採用
            for (let i = 0; i < Math.min(4, peaks.length); i++) {
                formants.push(peaks[i].frequency);
            }
            
            // 周波数順にソート
            formants.sort((a, b) => a - b);
            
        } catch (error) {
            console.error("⚠️ フォルマント検出エラー:", error);
        }
        
        return formants;
    }
    
    /**
     * フォルマントから母音を推定
     * @param {Array<number>} formants - フォルマントリスト
     * @returns {Object} 推定結果 {vowel, confidence}
     */
    estimateVowel(formants) {
        if (formants.length < 2) {
            return { vowel: 'sil', confidence: 0 };
        }
        
        const f1 = formants[0];
        const f2 = formants[1];
        
        let bestVowel = 'a';
        let bestScore = 0;
        
        // 各母音との距離を計算
        Object.keys(this.vowelFormants).forEach(vowel => {
            const target = this.vowelFormants[vowel];
            
            // ユークリッド距離の逆数をスコアとする
            const distance = Math.sqrt(
                Math.pow(f1 - target.f1, 2) + 
                Math.pow(f2 - target.f2, 2)
            );
            
            const score = 1.0 / (1.0 + distance / 1000.0); // 正規化
            
            if (score > bestScore) {
                bestScore = score;
                bestVowel = vowel;
            }
        });
        
        return {
            vowel: bestVowel,
            confidence: Math.min(1.0, bestScore)
        };
    }
    
    /**
     * 分析結果コールバックを追加
     * @param {Function} callback - コールバック関数
     */
    addAnalysisCallback(callback) {
        if (typeof callback === 'function') {
            this.analysisCallbacks.push(callback);
        }
    }
    
    /**
     * 分析結果コールバックを削除
     * @param {Function} callback - 削除するコールバック関数
     */
    removeAnalysisCallback(callback) {
        const index = this.analysisCallbacks.indexOf(callback);
        if (index > -1) {
            this.analysisCallbacks.splice(index, 1);
        }
    }
    
    /**
     * 分析結果をコールバックに通知
     * @param {Object} result - 分析結果
     */
    notifyAnalysisCallbacks(result) {
        this.analysisCallbacks.forEach(callback => {
            try {
                callback(result);
            } catch (error) {
                console.error("⚠️ コールバック実行エラー:", error);
            }
        });
    }
    
    /**
     * 設定を更新
     * @param {Object} newSettings - 新しい設定
     */
    updateSettings(newSettings) {
        try {
            Object.assign(this.settings, newSettings);
            
            // アナライザーの設定を更新
            if (this.analyserNode) {
                if (newSettings.smoothingTimeConstant !== undefined) {
                    this.analyserNode.smoothingTimeConstant = newSettings.smoothingTimeConstant;
                }
                if (newSettings.minDecibels !== undefined) {
                    this.analyserNode.minDecibels = newSettings.minDecibels;
                }
                if (newSettings.maxDecibels !== undefined) {
                    this.analyserNode.maxDecibels = newSettings.maxDecibels;
                }
            }
            
            console.log("🔧 AudioAnalyzer設定更新:", newSettings);
            
        } catch (error) {
            console.error("❌ 設定更新エラー:", error);
        }
    }
    
    /**
     * 現在の状態を取得
     * @returns {Object} 現在の状態
     */
    getStatus() {
        return {
            isAnalyzing: this.isAnalyzing,
            hasAudioContext: !!this.audioContext,
            hasAnalyser: !!this.analyserNode,
            hasMicrophone: !!this.microphone,
            sampleRate: this.sampleRate,
            fftSize: this.settings.fftSize,
            bufferLength: this.bufferLength,
            callbackCount: this.analysisCallbacks.length
        };
    }
    
    /**
     * デバッグ用：現在の周波数スペクトラムを取得
     * @returns {Array<number>} 周波数スペクトラム
     */
    getCurrentSpectrum() {
        if (!this.analyserNode || !this.dataArray) {
            return [];
        }
        
        this.analyserNode.getByteFrequencyData(this.dataArray);
        return Array.from(this.dataArray);
    }
    
    /**
     * デバッグ用：現在の分析情報
     * @returns {Object} デバッグ情報
     */
    getDebugInfo() {
        const spectrum = this.getCurrentSpectrum();
        const analysisResult = spectrum.length > 0 ? this.performFrequencyAnalysis(new Uint8Array(spectrum)) : null;
        
        return {
            status: this.getStatus(),
            settings: this.settings,
            vowelFormants: this.vowelFormants,
            currentSpectrum: spectrum.length > 20 ? spectrum.slice(0, 20) : spectrum, // 最初の20個のみ
            latestAnalysis: analysisResult
        };
    }
}

export { AudioAnalyzer };