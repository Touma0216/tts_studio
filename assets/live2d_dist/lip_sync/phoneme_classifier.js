/**
 * 音素分類・予測エンジン (JavaScript)
 * Python側からの音素データをLive2Dパラメータに変換
 */

class PhonemeClassifier {
    constructor() {
        this.isInitialized = false;
        this.phonemeModel = null;
        this.vowelMapping = this.getDefaultVowelMapping();
        
        // 母音補間用の状態
        this.currentVowel = 'sil';
        this.targetVowel = 'sil';
        this.transitionProgress = 1.0;
        this.smoothingFactor = 0.8;
        
        console.log("🔤 PhonemeClassifier initialized");
    }
    
    /**
     * デフォルト母音マッピング
     */
    getDefaultVowelMapping() {
        return {
            'a': {
                'ParamMouthOpenY': 1.0,      // あ：大きく開く
                'ParamMouthForm': 0.0,       // 口の形：中立
                'ParamMouthOpenX': 0.0       // 横幅：標準
            },
            'i': {
                'ParamMouthOpenY': 0.3,      // い：少し開く
                'ParamMouthForm': -1.0,      // 口の形：横に広げる
                'ParamMouthOpenX': -0.8      // 横幅：広げる
            },
            'u': {
                'ParamMouthOpenY': 0.4,      // う：小さく開く
                'ParamMouthForm': -0.7,      // 口の形：すぼめる
                'ParamMouthOpenX': 0.6       // 横幅：狭める
            },
            'e': {
                'ParamMouthOpenY': 0.6,      // え：中程度に開く
                'ParamMouthForm': -0.3,      // 口の形：やや横
                'ParamMouthOpenX': -0.2      // 横幅：やや広げる
            },
            'o': {
                'ParamMouthOpenY': 0.8,      // お：大きく開く
                'ParamMouthForm': 0.7,       // 口の形：丸く
                'ParamMouthOpenX': 0.4       // 横幅：やや狭める
            },
            'n': {
                'ParamMouthOpenY': 0.1,      // ん：ほぼ閉じる
                'ParamMouthForm': 0.0,       // 口の形：中立
                'ParamMouthOpenX': 0.0       // 横幅：標準
            },
            'sil': {
                'ParamMouthOpenY': 0.0,      // 無音：完全に閉じる
                'ParamMouthForm': 0.0,       // 口の形：中立
                'ParamMouthOpenX': 0.0       // 横幅：標準
            }
        };
    }
    
    /**
     * 音素モデルを読み込み
     * @param {string} modelPath - モデルファイルのパス
     */
    async loadPhonemeModel(modelPath = './lip_sync/models/phoneme_model.json') {
        try {
            const response = await fetch(modelPath);
            
            if (!response.ok) {
                console.warn(`⚠️ 音素モデル読み込み失敗: ${response.status}`);
                console.log("📝 デフォルト設定を使用します");
                this.isInitialized = true;
                return true;
            }
            
            this.phonemeModel = await response.json();
            
            // カスタムマッピングがある場合は更新
            if (this.phonemeModel.vowel_mapping) {
                this.vowelMapping = { ...this.vowelMapping, ...this.phonemeModel.vowel_mapping };
                console.log("🔧 カスタム母音マッピング適用");
            }
            
            console.log("✅ 音素モデル読み込み完了");
            this.isInitialized = true;
            return true;
            
        } catch (error) {
            console.warn("⚠️ 音素モデル読み込みエラー:", error);
            console.log("📝 デフォルト設定を使用します");
            this.isInitialized = true;
            return false;
        }
    }
    
    /**
     * Python側の音素データをLive2Dパラメータに変換
     * @param {Object} phonemeData - Python側からの音素データ
     * @returns {Object} Live2Dパラメータ
     */
    convertToLive2DParameters(phonemeData) {
        try {
            if (!phonemeData || !phonemeData.vowel_frames) {
                return this.getDefaultParameters();
            }
            
            const currentTime = Date.now() / 1000; // 現在時刻（秒）
            const startTime = phonemeData.start_time || 0;
            const elapsedTime = currentTime - startTime;
            
            // 現在時刻に対応する母音フレームを検索
            const activeFrame = this.findActiveVowelFrame(
                phonemeData.vowel_frames, 
                elapsedTime
            );
            
            if (!activeFrame) {
                return this.getDefaultParameters();
            }
            
            // 母音に基づいてLive2Dパラメータを生成
            const parameters = this.vowelToLive2DParameters(
                activeFrame.vowel, 
                activeFrame.intensity
            );
            
            // スムージング適用
            return this.applySmoothingToParameters(parameters);
            
        } catch (error) {
            console.error("❌ 音素変換エラー:", error);
            return this.getDefaultParameters();
        }
    }
    
    /**
     * 指定時間にアクティブな母音フレームを検索
     * @param {Array} vowelFrames - 母音フレームリスト
     * @param {number} currentTime - 現在時刻（秒）
     * @returns {Object|null} アクティブなフレーム
     */
    findActiveVowelFrame(vowelFrames, currentTime) {
        for (const frame of vowelFrames) {
            const frameStart = frame.timestamp;
            const frameEnd = frame.timestamp + frame.duration;
            
            if (frameStart <= currentTime && currentTime < frameEnd) {
                return frame;
            }
        }
        return null;
    }
    
    /**
     * 母音をLive2Dパラメータに変換
     * @param {string} vowel - 母音
     * @param {number} intensity - 強度 (0.0-1.0)
     * @returns {Object} Live2Dパラメータ
     */
    vowelToLive2DParameters(vowel, intensity = 1.0) {
        const vowelParams = this.vowelMapping[vowel] || this.vowelMapping['sil'];
        const parameters = {};
        
        // 強度を適用してパラメータ値を計算
        Object.keys(vowelParams).forEach(paramId => {
            const baseValue = vowelParams[paramId];
            parameters[paramId] = baseValue * intensity;
        });
        
        return parameters;
    }
    
    /**
     * パラメータにスムージングを適用
     * @param {Object} newParameters - 新しいパラメータ
     * @returns {Object} スムージング適用後のパラメータ
     */
    applySmoothingToParameters(newParameters) {
        if (!this.previousParameters) {
            this.previousParameters = { ...newParameters };
            return newParameters;
        }
        
        const smoothed = {};
        
        Object.keys(newParameters).forEach(paramId => {
            const newValue = newParameters[paramId];
            const oldValue = this.previousParameters[paramId] || 0;
            
            // 線形補間でスムージング
            smoothed[paramId] = this.lerp(oldValue, newValue, 1.0 - this.smoothingFactor);
        });
        
        this.previousParameters = { ...smoothed };
        return smoothed;
    }
    
    /**
     * 線形補間
     * @param {number} a - 開始値
     * @param {number} b - 終了値
     * @param {number} t - 補間係数 (0.0-1.0)
     * @returns {number} 補間結果
     */
    lerp(a, b, t) {
        return a + (b - a) * Math.max(0, Math.min(1, t));
    }
    
    /**
     * キーフレームデータからリップシンクシーケンスを生成
     * @param {Object} keyframeData - Python側からのキーフレームデータ
     * @returns {Array} アニメーションシーケンス
     */
    generateLipSyncSequence(keyframeData) {
        try {
            if (!keyframeData || !keyframeData.vowel_keyframes) {
                return [];
            }
            
            const sequence = [];
            const fps = keyframeData.fps || 30;
            const totalFrames = keyframeData.total_frames || 0;
            
            for (let frame = 0; frame < totalFrames; frame++) {
                const timestamp = frame / fps;
                const parameters = {};
                
                // 各母音のキーフレーム値を取得
                Object.keys(keyframeData.vowel_keyframes).forEach(vowel => {
                    const keyframes = keyframeData.vowel_keyframes[vowel];
                    const frameData = keyframes.find(kf => kf.frame === frame);
                    
                    if (frameData && frameData.value > 0) {
                        // アクティブな母音のパラメータを適用
                        const vowelParams = this.vowelToLive2DParameters(vowel, frameData.value);
                        Object.assign(parameters, vowelParams);
                    }
                });
                
                // 口パラメータキーフレームも適用
                if (keyframeData.mouth_params) {
                    ['mouth_open', 'mouth_form'].forEach(paramType => {
                        const keyframes = keyframeData.mouth_params[paramType];
                        const frameData = keyframes.find(kf => kf.frame === frame);
                        
                        if (frameData) {
                            const paramId = paramType === 'mouth_open' ? 'ParamMouthOpenY' : 'ParamMouthForm';
                            parameters[paramId] = frameData.value;
                        }
                    });
                }
                
                sequence.push({
                    timestamp,
                    parameters: parameters || this.getDefaultParameters()
                });
            }
            
            console.log(`✅ リップシンクシーケンス生成: ${sequence.length}フレーム`);
            return sequence;
            
        } catch (error) {
            console.error("❌ シーケンス生成エラー:", error);
            return [];
        }
    }
    
    /**
     * デフォルトパラメータを取得
     * @returns {Object} デフォルトLive2Dパラメータ
     */
    getDefaultParameters() {
        return {
            'ParamMouthOpenY': 0.0,
            'ParamMouthForm': 0.0,
            'ParamMouthOpenX': 0.0
        };
    }
    
    /**
     * 母音マッピングを更新
     * @param {Object} newMapping - 新しいマッピング設定
     */
    updateVowelMapping(newMapping) {
        try {
            this.vowelMapping = { ...this.vowelMapping, ...newMapping };
            console.log("🔧 母音マッピング更新完了");
        } catch (error) {
            console.error("❌ 母音マッピング更新エラー:", error);
        }
    }
    
    /**
     * スムージング設定を更新
     * @param {number} factor - スムージング係数 (0.0-1.0)
     */
    updateSmoothingFactor(factor) {
        this.smoothingFactor = Math.max(0.0, Math.min(1.0, factor));
        console.log(`🔧 スムージング係数更新: ${this.smoothingFactor}`);
    }
    
    /**
     * リアルタイム母音検出結果を処理
     * @param {Object} vowelResult - リアルタイム母音検出結果
     * @returns {Object} Live2Dパラメータ
     */
    processRealtimeVowelResult(vowelResult) {
        try {
            if (!vowelResult || vowelResult.confidence < 0.5) {
                return this.getDefaultParameters();
            }
            
            // 母音と強度からパラメータを生成
            const parameters = this.vowelToLive2DParameters(
                vowelResult.vowel,
                vowelResult.intensity
            );
            
            // スムージング適用
            return this.applySmoothingToParameters(parameters);
            
        } catch (error) {
            console.error("❌ リアルタイム処理エラー:", error);
            return this.getDefaultParameters();
        }
    }
    
    /**
     * デバッグ用：現在の設定を取得
     * @returns {Object} 現在の設定情報
     */
    getDebugInfo() {
        return {
            isInitialized: this.isInitialized,
            vowelMapping: this.vowelMapping,
            smoothingFactor: this.smoothingFactor,
            currentVowel: this.currentVowel,
            targetVowel: this.targetVowel,
            hasPhonemeModel: !!this.phonemeModel
        };
    }
    
    /**
     * 母音遷移の予測とスムージング
     * @param {string} fromVowel - 開始母音
     * @param {string} toVowel - 目標母音
     * @param {number} duration - 遷移時間（秒）
     * @returns {Function} 遷移関数
     */
    createVowelTransition(fromVowel, toVowel, duration = 0.1) {
        const startParams = this.vowelToLive2DParameters(fromVowel, 1.0);
        const endParams = this.vowelToLive2DParameters(toVowel, 1.0);
        
        return (progress) => {
            const clampedProgress = Math.max(0, Math.min(1, progress));
            const transitionParams = {};
            
            Object.keys(startParams).forEach(paramId => {
                const startValue = startParams[paramId];
                const endValue = endParams[paramId] || 0;
                transitionParams[paramId] = this.lerp(startValue, endValue, clampedProgress);
            });
            
            return transitionParams;
        };
    }
}

export { PhonemeClassifier };