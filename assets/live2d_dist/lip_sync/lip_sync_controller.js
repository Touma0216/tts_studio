/**
 * Live2Dリップシンク統合制御モジュール
 * Python側のデータとJavaScript側の処理を統合
 */

class LipSyncController {
    constructor(options = {}) {
        this.audioAnalyzer = options.audioAnalyzer || null;
        this.phonemeClassifier = options.phonemeClassifier || null;
        
        // Live2Dモデル
        this.live2dModel = null;
        
        // リップシンク状態
        this.isActive = false;
        this.currentMode = 'tts'; // 'tts' | 'realtime' | 'hybrid'
        this.animationId = null;
        
        // データとタイミング
        this.currentLipSyncData = null;
        this.animationStartTime = 0;
        this.animationSequence = [];
        this.currentFrameIndex = 0;
        
        // 設定
        this.settings = {
            enabled: true,
            mode: 'tts',
            sensitivity: 80,
            smoothingFactor: 0.7,
            responseSpeed: 70,
            mouthOpenScale: 100,
            autoOptimize: true,
            realtimeThreshold: 0.6,
            hybridBlendRatio: 0.5
        };
        
        // パフォーマンス監視
        this.performanceStats = {
            frameCount: 0,
            lastFpsCheck: 0,
            currentFps: 0,
            averageProcessingTime: 0
        };
        
        console.log("🎭 LipSyncController initialized");
    }
    
    /**
     * Live2Dモデルを設定
     * @param {Object} model - Live2Dモデル
     */
    setModel(model) {
        try {
            this.live2dModel = model;
            
            // モデルの利用可能パラメータをチェック
            this.validateModelParameters();
            
            console.log("✅ Live2Dモデル設定完了");
            return true;
            
        } catch (error) {
            console.error("❌ モデル設定エラー:", error);
            return false;
        }
    }
    
    /**
     * モデルパラメータの検証
     */
    validateModelParameters() {
        if (!this.live2dModel) {
            return;
        }
        
        try {
            const requiredParams = [
                'ParamMouthOpenY',
                'ParamMouthForm',
                'ParamMouthOpenX'
            ];
            
            const availableParams = this.getAvailableParameters();
            const missing = requiredParams.filter(param => 
                !availableParams.some(p => p.id === param)
            );
            
            if (missing.length > 0) {
                console.warn("⚠️ 一部のリップシンクパラメータが見つかりません:", missing);
                console.log("📋 利用可能パラメータ:", availableParams.map(p => p.id));
                
                // 🔥 代替パラメータを検索
                const alternativeParams = this.findAlternativeParameters(availableParams);
                if (alternativeParams.length > 0) {
                    console.log("🔍 代替パラメータを発見:", alternativeParams);
                } else {
                    console.warn("⚠️ 代替パラメータも見つかりません");
                }
            } else {
                console.log("✅ 必要なリップシンクパラメータが全て利用可能です");
            }
            
        } catch (error) {
            console.error("⚠️ パラメータ検証エラー:", error);
        }
    }
    
    /**
     * 代替パラメータを検索
     * @param {Array} availableParams - 利用可能パラメータ
     * @returns {Array} 代替パラメータリスト
     */
    findAlternativeParameters(availableParams) {
        const alternatives = [];
        
        // 口関連パラメータを検索
        const mouthKeywords = ['mouth', 'lip', '口', 'kuchi', 'Mouth', 'Lip'];
        
        availableParams.forEach(param => {
            const paramId = param.id.toLowerCase();
            if (mouthKeywords.some(keyword => paramId.includes(keyword.toLowerCase()))) {
                alternatives.push({
                    id: param.id,
                    type: this.guessParameterType(param.id),
                    ...param
                });
            }
        });
        
        return alternatives;
    }
    
    /**
     * パラメータタイプを推測
     * @param {string} paramId - パラメータID
     * @returns {string} パラメータタイプ
     */
    guessParameterType(paramId) {
        const id = paramId.toLowerCase();
        
        if (id.includes('open') || id.includes('y')) {
            return 'mouth_open_y';
        } else if (id.includes('form') || id.includes('shape')) {
            return 'mouth_form';
        } else if (id.includes('x')) {
            return 'mouth_open_x';
        }
        
        return 'unknown';
    }
    
    /**
     * リップシンクを開始
     * @param {Object} lipSyncData - Python側からのリップシンクデータ
     * @returns {boolean} 成功時true
     */
    async startLipSync(lipSyncData) {
        try {
            console.log("🎵 リップシンク開始:", lipSyncData);
            
            if (!this.live2dModel) {
                throw new Error("Live2Dモデルが設定されていません");
            }
            
            if (!this.settings.enabled) {
                console.log("📝 リップシンクは無効です");
                return false;
            }
            
            // 既存のアニメーション停止
            this.stopLipSync();
            
            // データ設定
            this.currentLipSyncData = lipSyncData;
            this.animationStartTime = Date.now() / 1000;
            this.currentFrameIndex = 0;
            
            // モード別処理
            switch (this.settings.mode) {
                case 'tts':
                    return this.startTTSMode(lipSyncData);
                
                case 'realtime':
                    return this.startRealtimeMode();
                
                case 'hybrid':
                    return this.startHybridMode(lipSyncData);
                
                default:
                    console.warn("⚠️ 未知のモード:", this.settings.mode);
                    return this.startTTSMode(lipSyncData);
            }
            
        } catch (error) {
            console.error("❌ リップシンク開始エラー:", error);
            return false;
        }
    }
    
    /**
     * TTSモード開始（音素データベース）
     * @param {Object} lipSyncData - リップシンクデータ
     */
    startTTSMode(lipSyncData) {
        try {
            console.log("🔤 TTSモード開始");
            
            if (!this.phonemeClassifier) {
                throw new Error("PhonemeClassifier が利用できません");
            }
            
            // アニメーションシーケンス生成
            if (lipSyncData.keyframes) {
                this.animationSequence = this.phonemeClassifier.generateLipSyncSequence(lipSyncData.keyframes);
            } else {
                this.animationSequence = this.generateSequenceFromVowelFrames(lipSyncData);
            }
            
            if (this.animationSequence.length === 0) {
                console.warn("⚠️ アニメーションシーケンスが空です");
                return false;
            }
            
            // アニメーション開始
            this.isActive = true;
            this.currentMode = 'tts';
            this.animateTTSMode();
            
            console.log(`✅ TTSアニメーション開始: ${this.animationSequence.length}フレーム`);
            return true;
            
        } catch (error) {
            console.error("❌ TTSモード開始エラー:", error);
            return false;
        }
    }
    
    /**
     * リアルタイムモード開始
     */
    async startRealtimeMode() {
        try {
            console.log("🎤 リアルタイムモード開始");
            
            if (!this.audioAnalyzer) {
                throw new Error("AudioAnalyzer が利用できません");
            }
            
            // マイク音声解析開始
            const success = await this.audioAnalyzer.startAnalysis();
            if (!success) {
                throw new Error("音声解析の開始に失敗しました");
            }
            
            // 分析結果コールバック設定
            this.audioAnalyzer.addAnalysisCallback(
                this.handleRealtimeAnalysis.bind(this)
            );
            
            this.isActive = true;
            this.currentMode = 'realtime';
            
            console.log("✅ リアルタイムリップシンク開始");
            return true;
            
        } catch (error) {
            console.error("❌ リアルタイムモード開始エラー:", error);
            return false;
        }
    }
    
    /**
     * ハイブリッドモード開始
     * @param {Object} lipSyncData - リップシンクデータ
     */
    async startHybridMode(lipSyncData) {
        try {
            console.log("🔀 ハイブリッドモード開始");
            
            // TTSとリアルタイム両方を開始
            const ttsSuccess = this.startTTSMode(lipSyncData);
            const realtimeSuccess = await this.startRealtimeMode();
            
            if (!ttsSuccess && !realtimeSuccess) {
                throw new Error("TTSもリアルタイムも開始できませんでした");
            }
            
            this.currentMode = 'hybrid';
            
            console.log("✅ ハイブリッドリップシンク開始");
            return true;
            
        } catch (error) {
            console.error("❌ ハイブリッドモード開始エラー:", error);
            return false;
        }
    }
    
    /**
     * リップシンクを停止
     */
    stopLipSync() {
        try {
            console.log("⏹️ リップシンク停止");
            
            this.isActive = false;
            
            // アニメーション停止
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
                this.animationId = null;
            }
            
            // リアルタイム解析停止
            if (this.audioAnalyzer && this.currentMode !== 'tts') {
                this.audioAnalyzer.stopAnalysis();
                this.audioAnalyzer.removeAnalysisCallback(this.handleRealtimeAnalysis.bind(this));
            }
            
            // パラメータをリセット
            this.resetMouthParameters();
            
            // データクリア
            this.currentLipSyncData = null;
            this.animationSequence = [];
            this.currentFrameIndex = 0;
            
            console.log("✅ リップシンク停止完了");
            return true;
            
        } catch (error) {
            console.error("❌ リップシンク停止エラー:", error);
            return false;
        }
    }
    
    /**
     * TTSモードのアニメーション処理
     */
    animateTTSMode() {
        if (!this.isActive || this.currentMode !== 'tts' && this.currentMode !== 'hybrid') {
            return;
        }
        
        try {
            const currentTime = Date.now() / 1000;
            const elapsedTime = currentTime - this.animationStartTime;
            
            // 現在時刻に対応するフレームを検索
            const activeFrame = this.findActiveFrame(elapsedTime);
            
            if (activeFrame) {
                let parameters = activeFrame.parameters;
                
                // ハイブリッドモードの場合は重み付き合成
                if (this.currentMode === 'hybrid' && this.lastRealtimeParameters) {
                    parameters = this.blendParameters(
                        activeFrame.parameters,
                        this.lastRealtimeParameters,
                        this.settings.hybridBlendRatio
                    );
                }
                
                // パラメータ適用
                this.applyParametersToModel(parameters);
            } else {
                // アニメーション終了判定
                const totalDuration = this.currentLipSyncData?.total_duration || 0;
                if (elapsedTime > totalDuration + 0.5) {
                    this.stopLipSync();
                    return;
                }
                
                // デフォルトパラメータ適用
                this.resetMouthParameters();
            }
            
            // 次のフレームをスケジュール
            this.animationId = requestAnimationFrame(() => this.animateTTSMode());
            
            // パフォーマンス統計更新
            this.updatePerformanceStats();
            
        } catch (error) {
            console.error("⚠️ TTSアニメーションエラー:", error);
            this.animationId = requestAnimationFrame(() => this.animateTTSMode());
        }
    }
    
    /**
     * リアルタイム解析結果を処理
     * @param {Object} analysisResult - 音声解析結果
     */
    handleRealtimeAnalysis(analysisResult) {
        if (!this.isActive || (!this.currentMode !== 'realtime' && this.currentMode !== 'hybrid')) {
            return;
        }
        
        try {
            // 音量チェック
            if (analysisResult.volume < this.settings.realtimeThreshold / 100.0) {
                if (this.currentMode === 'realtime') {
                    this.resetMouthParameters();
                }
                return;
            }
            
            // 母音推定結果から Live2D パラメータを生成
            let parameters = {};
            
            if (this.phonemeClassifier && analysisResult.vowelCandidate) {
                const vowelResult = {
                    vowel: analysisResult.vowelCandidate,
                    intensity: Math.min(1.0, analysisResult.volume * (this.settings.sensitivity / 100.0)),
                    confidence: analysisResult.confidence
                };
                
                parameters = this.phonemeClassifier.processRealtimeVowelResult(vowelResult);
            } else {
                // フォールバック：基本的な口の開閉
                parameters = this.generateFallbackParameters(analysisResult);
            }
            
            // モード別処理
            if (this.currentMode === 'realtime') {
                this.applyParametersToModel(parameters);
            } else if (this.currentMode === 'hybrid') {
                // ハイブリッドモードでは後で使用するために保存
                this.lastRealtimeParameters = parameters;
            }
            
        } catch (error) {
            console.error("⚠️ リアルタイム解析処理エラー:", error);
        }
    }
    
    /**
     * 母音フレームからアニメーションシーケンスを生成
     * @param {Object} lipSyncData - リップシンクデータ
     * @returns {Array} アニメーションシーケンス
     */
    generateSequenceFromVowelFrames(lipSyncData) {
        if (!lipSyncData.vowel_frames || !this.phonemeClassifier) {
            return [];
        }
        
        const sequence = [];
        const fps = 30; // 30fps
        const totalDuration = lipSyncData.total_duration || 1.0;
        const totalFrames = Math.ceil(totalDuration * fps);
        
        for (let frame = 0; frame < totalFrames; frame++) {
            const timestamp = frame / fps;
            
            // 該当時間の母音フレームを検索
            const activeFrame = lipSyncData.vowel_frames.find(vf => 
                vf.timestamp <= timestamp && 
                timestamp < (vf.timestamp + vf.duration)
            );
            
            let parameters;
            if (activeFrame) {
                parameters = this.phonemeClassifier.vowelToLive2DParameters(
                    activeFrame.vowel, 
                    activeFrame.intensity
                );
            } else {
                parameters = this.phonemeClassifier.getDefaultParameters();
            }
            
            sequence.push({
                timestamp,
                parameters
            });
        }
        
        return sequence;
    }
    
    /**
     * アクティブなアニメーションフレームを検索
     * @param {number} currentTime - 現在時刻
     * @returns {Object|null} アクティブなフレーム
     */
    findActiveFrame(currentTime) {
        for (const frame of this.animationSequence) {
            if (Math.abs(frame.timestamp - currentTime) < 0.05) { // 50ms許容
                return frame;
            }
        }
        return null;
    }
    
    /**
     * パラメータをブレンド
     * @param {Object} params1 - パラメータ1
     * @param {Object} params2 - パラメータ2  
     * @param {number} ratio - ブレンド比率 (0.0-1.0)
     * @returns {Object} ブレンド結果
     */
    blendParameters(params1, params2, ratio) {
        const blended = {};
        
        const allParams = new Set([...Object.keys(params1), ...Object.keys(params2)]);
        
        allParams.forEach(paramId => {
            const val1 = params1[paramId] || 0;
            const val2 = params2[paramId] || 0;
            blended[paramId] = val1 * (1 - ratio) + val2 * ratio;
        });
        
        return blended;
    }
    
    /**
     * Live2Dモデルにパラメータを適用
     * @param {Object} parameters - パラメータ
     */
    applyParametersToModel(parameters) {
        if (!this.live2dModel) {
            return;
        }
        
        try {
            // 🔥 修正: 正しいパラメータアクセス方法
            const coreModel = this.live2dModel.internalModel?.coreModel;
            
            if (coreModel) {
                Object.keys(parameters).forEach(paramId => {
                    const value = parameters[paramId];
                    
                    try {
                        // パラメータ値にスケールを適用
                        const scaledValue = value * (this.settings.mouthOpenScale / 100.0);
                        
                        // 🔥 修正: インデックスベースのアクセス
                        const paramIndex = coreModel.getParameterIndex(paramId);
                        if (paramIndex >= 0) {
                            coreModel.setParameterValueByIndex(paramIndex, scaledValue);
                        } else {
                            // 代替パラメータを試す
                            this.tryAlternativeParameter(paramId, scaledValue, coreModel);
                        }
                    } catch (e) {
                        // パラメータが存在しない場合は警告（初回のみ）
                        if (!this.warnedParameters) {
                            this.warnedParameters = new Set();
                        }
                        if (!this.warnedParameters.has(paramId)) {
                            console.warn(`⚠️ パラメータ '${paramId}' が見つかりません`);
                            this.warnedParameters.add(paramId);
                        }
                    }
                });
            }
            
        } catch (error) {
            console.error("⚠️ パラメータ適用エラー:", error);
        }
    }
    
    /**
     * 代替パラメータを試す
     * @param {string} originalParamId - 元のパラメータID
     * @param {number} value - 値
     * @param {Object} coreModel - コアモデル
     */
    tryAlternativeParameter(originalParamId, value, coreModel) {
        const alternatives = this.getAlternativeParameterNames(originalParamId);
        
        for (const altParamId of alternatives) {
            const altIndex = coreModel.getParameterIndex(altParamId);
            if (altIndex >= 0) {
                coreModel.setParameterValueByIndex(altIndex, value);
                console.log(`✅ 代替パラメータ使用: ${originalParamId} → ${altParamId}`);
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * 代替パラメータ名を取得
     * @param {string} paramId - パラメータID
     * @returns {Array} 代替パラメータ名リスト
     */
    getAlternativeParameterNames(paramId) {
        const alternatives = [];
        
        switch (paramId) {
            case 'ParamMouthOpenY':
                alternatives.push(
                    'PARAM_MOUTH_OPEN_Y',
                    'MouthOpenY',
                    'Mouth_Open_Y',
                    'mouth_open_y',
                    '口開き',
                    'ParamMouthOpen'
                );
                break;
                
            case 'ParamMouthForm':
                alternatives.push(
                    'PARAM_MOUTH_FORM',
                    'MouthForm',
                    'Mouth_Form',
                    'mouth_form',
                    '口の形',
                    'ParamMouthShape'
                );
                break;
                
            case 'ParamMouthOpenX':
                alternatives.push(
                    'PARAM_MOUTH_OPEN_X',
                    'MouthOpenX',
                    'Mouth_Open_X',
                    'mouth_open_x',
                    'ParamMouthWidth'
                );
                break;
        }
        
        return alternatives;
    }
    
    /**
     * 口のパラメータをリセット
     */
    resetMouthParameters() {
        const defaultParams = {
            'ParamMouthOpenY': 0.0,
            'ParamMouthForm': 0.0,
            'ParamMouthOpenX': 0.0
        };
        
        this.applyParametersToModel(defaultParams);
    }
    
    /**
     * フォールバックパラメータ生成
     * @param {Object} analysisResult - 解析結果
     * @returns {Object} パラメータ
     */
    generateFallbackParameters(analysisResult) {
        const volume = analysisResult.volume || 0;
        const intensity = Math.min(1.0, volume * 2.0);
        
        return {
            'ParamMouthOpenY': intensity * 0.8,
            'ParamMouthForm': 0.0,
            'ParamMouthOpenX': 0.0
        };
    }
    
    /**
     * 利用可能なパラメータを取得
     * @returns {Array} パラメータリスト
     */
    getAvailableParameters() {
        if (!this.live2dModel) {
            return [];
        }
        
        try {
            // 🔥 修正: 正しいパラメータ取得方法
            const coreModel = this.live2dModel.internalModel?.coreModel;
            const parameters = [];
            
            if (coreModel) {
                const paramCount = coreModel.getParameterCount();
                
                for (let i = 0; i < paramCount; i++) {
                    try {
                        const paramId = coreModel.getParameterId(i);
                        const currentValue = coreModel.getParameterValueByIndex(i);
                        const defaultValue = coreModel.getParameterDefaultValueByIndex(i);
                        const minValue = coreModel.getParameterMinValueByIndex(i);
                        const maxValue = coreModel.getParameterMaxValueByIndex(i);
                        
                        parameters.push({
                            id: paramId,
                            index: i,
                            currentValue,
                            defaultValue,
                            minValue,
                            maxValue
                        });
                    } catch (e) {
                        console.warn(`⚠️ パラメータ ${i} の取得失敗:`, e);
                    }
                }
            }
            
            return parameters;
            
        } catch (error) {
            console.error("⚠️ パラメータ取得エラー:", error);
            return [];
        }
    }
    
    /**
     * 直接パラメータ設定（外部API用）
     * @param {Object} parameters - パラメータ
     */
    setParameters(parameters) {
        this.applyParametersToModel(parameters);
    }
    
    /**
     * 設定を更新
     * @param {Object} newSettings - 新しい設定
     */
    updateSettings(newSettings) {
        try {
            // 基本設定更新
            if (newSettings.basic) {
                const basic = newSettings.basic;
                Object.assign(this.settings, {
                    enabled: basic.enabled !== undefined ? basic.enabled : this.settings.enabled,
                    sensitivity: basic.sensitivity || this.settings.sensitivity,
                    responseSpeed: basic.response_speed || this.settings.responseSpeed,
                    mouthOpenScale: basic.mouth_open_scale || this.settings.mouthOpenScale,
                    autoOptimize: basic.auto_optimize !== undefined ? basic.auto_optimize : this.settings.autoOptimize
                });
            }
            
            // 音素設定更新
            if (newSettings.phoneme && this.phonemeClassifier) {
                this.phonemeClassifier.updateVowelMapping(newSettings.phoneme);
            }
            
            // 高度設定更新
            if (newSettings.advanced) {
                const advanced = newSettings.advanced;
                Object.assign(this.settings, {
                    smoothingFactor: (advanced.smoothing_factor || this.settings.smoothingFactor) / 100.0,
                    realtimeThreshold: (advanced.volume_threshold || this.settings.realtimeThreshold * 100) / 100.0
                });
                
                // AudioAnalyzer設定更新
                if (this.audioAnalyzer) {
                    this.audioAnalyzer.updateSettings({
                        volumeThreshold: this.settings.realtimeThreshold,
                        smoothingTimeConstant: this.settings.smoothingFactor
                    });
                }
                
                // PhonemeClassifier設定更新
                if (this.phonemeClassifier) {
                    this.phonemeClassifier.updateSmoothingFactor(this.settings.smoothingFactor);
                }
            }
            
            console.log("🔧 リップシンク設定更新:", this.settings);
            
        } catch (error) {
            console.error("❌ 設定更新エラー:", error);
        }
    }
    
    /**
     * パフォーマンス統計を更新
     */
    updatePerformanceStats() {
        this.performanceStats.frameCount++;
        
        const now = Date.now();
        if (now - this.performanceStats.lastFpsCheck > 1000) {
            this.performanceStats.currentFps = this.performanceStats.frameCount;
            this.performanceStats.frameCount = 0;
            this.performanceStats.lastFpsCheck = now;
        }
    }
    
    /**
     * 現在の状態を取得
     * @returns {Object} 状態情報
     */
    getStatus() {
        return {
            isActive: this.isActive,
            currentMode: this.currentMode,
            hasModel: !!this.live2dModel,
            hasAudioAnalyzer: !!this.audioAnalyzer,
            hasPhonemeClassifier: !!this.phonemeClassifier,
            settings: this.settings,
            currentData: this.currentLipSyncData ? {
                text: this.currentLipSyncData.text,
                duration: this.currentLipSyncData.total_duration,
                frameCount: this.animationSequence.length
            } : null,
            performance: this.performanceStats
        };
    }
    
    /**
     * デバッグ情報を取得
     * @returns {Object} デバッグ情報
     */
    getDebugInfo() {
        const status = this.getStatus();
        const availableParams = this.getAvailableParameters();
        
        return {
            ...status,
            availableParameters: availableParams.slice(0, 10), // 最初の10個のみ
            audioAnalyzerStatus: this.audioAnalyzer ? this.audioAnalyzer.getStatus() : null,
            phonemeClassifierInfo: this.phonemeClassifier ? this.phonemeClassifier.getDebugInfo() : null
        };
    }
}

export { LipSyncController };