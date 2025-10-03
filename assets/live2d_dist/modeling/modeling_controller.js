// assets/live2d_dist/modeling/modeling_controller.js
// モデリング制御：パラメータ設定のメイン処理（完全修正版）

/**
 * 単一パラメータをLive2Dモデルに設定
 * @param {string} paramId - パラメータID（例: "ParamAngleX"）
 * @param {number} value - 設定値
 * @returns {boolean} - 成功したらtrue
 */
window.setLive2DParameter = function(paramId, value) {
    try {
        if (!window.currentModel) {
            console.warn('⚠️ モデル未読み込み');
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        
        // パラメータIDからインデックスを取得
        const paramIndex = model.getParameterIndex(paramId);
        if (paramIndex === -1) {
            console.warn(`⚠️ パラメータが見つかりません: ${paramId}`);
            return false;
        }

        // インデックスを使ってパラメータ設定
        model.setParameterValueByIndex(paramIndex, value);
        
        console.log(`🔧 パラメータ設定: ${paramId} = ${value.toFixed(3)}`);
        return true;
    } catch (error) {
        console.error(`❌ パラメータ設定エラー (${paramId}):`, error);
        return false;
    }
};

/**
 * 複数パラメータを一括設定
 * @param {Object} parameters - {paramId: value, ...}の形式
 * @returns {boolean} - 成功したらtrue
 */
window.setLive2DParameters = function(parameters) {
    try {
        if (!window.currentModel) {
            console.warn('⚠️ モデル未読み込み');
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        let successCount = 0;

        for (const [paramId, value] of Object.entries(parameters)) {
            const paramIndex = model.getParameterIndex(paramId);
            if (paramIndex === -1) continue;

            model.setParameterValueByIndex(paramIndex, value);
            successCount++;
        }

        console.log(`🎨 パラメータ一括設定: ${successCount}個`);
        return true;
    } catch (error) {
        console.error('❌ パラメータ一括設定エラー:', error);
        return false;
    }
};

/**
 * パラメータをデフォルト値にリセット
 */
window.resetLive2DParameter = function(paramId) {
    try {
        if (!window.currentModel) return false;

        const model = window.currentModel.internalModel.coreModel;
        const paramIndex = model.getParameterIndex(paramId);
        if (paramIndex === -1) return false;

        const defaultValue = model.getParameterDefaultValueByIndex(paramIndex);
        model.setParameterValueByIndex(paramIndex, defaultValue);
        
        console.log(`↺ リセット: ${paramId} = ${defaultValue.toFixed(3)}`);
        return true;
    } catch (error) {
        console.error(`❌ リセットエラー (${paramId}):`, error);
        return false;
    }
};

/**
 * 全パラメータをデフォルト値にリセット
 */
window.resetAllLive2DParameters = function() {
    try {
        if (!window.currentModel) return false;

        const model = window.currentModel.internalModel.coreModel;
        const paramCount = model.getParameterCount();
        let resetCount = 0;

        for (let i = 0; i < paramCount; i++) {
            const defaultValue = model.getParameterDefaultValueByIndex(i);
            model.setParameterValueByIndex(i, defaultValue);
            resetCount++;
        }

        console.log(`🔄 全パラメータリセット: ${resetCount}個`);
        return true;
    } catch (error) {
        console.error('❌ 全リセットエラー:', error);
        return false;
    }
};

/**
 * 現在のパラメータ値を取得
 */
window.getLive2DParameterValue = function(paramId) {
    try {
        if (!window.currentModel) return null;

        const model = window.currentModel.internalModel.coreModel;
        const paramIndex = model.getParameterIndex(paramId);
        if (paramIndex === -1) return null;

        return model.getParameterValueByIndex(paramIndex);
    } catch (error) {
        console.error(`❌ パラメータ取得エラー (${paramId}):`, error);
        return null;
    }
};

/**
 * 全パラメータの現在値を取得
 */
window.getAllLive2DParameterValues = function() {
    try {
        if (!window.currentModel) return {};

        const model = window.currentModel.internalModel.coreModel;
        const paramCount = model.getParameterCount();
        const values = {};

        for (let i = 0; i < paramCount; i++) {
            const paramId = model.getParameterId(i);
            const value = model.getParameterValueByIndex(i);
            values[paramId] = value;
        }

        return values;
    } catch (error) {
        console.error('❌ 全パラメータ取得エラー:', error);
        return {};
    }
};

console.log('✅ modeling_controller.js 読み込み完了');

// =============================================================================
// アイドルモーション機能（完全修正版）
// =============================================================================

class IdleMotionManager {
    constructor() {
        this.motions = {
            blink: {
                enabled: false,
                period: 3.0,
                lastTime: 0,
                duration: 0.15,
                isBlinking: false,
                blinkStartTime: 0
            },
            gaze: {
                enabled: false,
                range: 0.5,
                targetX: 0,
                targetY: 0,
                currentX: 0,
                currentY: 0,
                changeInterval: 2.0,
                lastChangeTime: 0,
                smoothness: 0.05
            },
            wind: {
                enabled: false,
                strength: 1.0,
                phase: 0,
                frequency: 1.0,
                isOverriding: false
            }
        };
        
        this.animationFrameId = null;
        this.isRunning = false;
        this.physicsOriginalState = null;
    }
    
    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.animate();
        console.log('🌟 アイドルモーション開始');
    }
    
    stop() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        
        if (this.motions.wind.isOverriding) {
            this.restorePhysics();
        }
        
        console.log('⏹️ アイドルモーション停止');
    }
    
    toggleMotion(motionType, enabled) {
        if (!this.motions[motionType]) {
            console.warn(`⚠️ 不明なモーションタイプ: ${motionType}`);
            return;
        }
        
        // 風揺れのON/OFF時に物理演算を制御
        if (motionType === 'wind') {
            if (enabled) {
                this.disablePhysics();
            } else {
                this.restorePhysics();
            }
        }
        
        this.motions[motionType].enabled = enabled;
        console.log(`🌟 ${motionType}: ${enabled ? 'ON' : 'OFF'}`);
        
        const anyEnabled = Object.values(this.motions).some(m => m.enabled);
        if (anyEnabled && !this.isRunning) {
            this.start();
        } else if (!anyEnabled && this.isRunning) {
            this.stop();
        }
    }
    
    setMotionParam(paramName, value) {
        if (paramName === 'blink_period') {
            this.motions.blink.period = value;
        } else if (paramName === 'gaze_range') {
            this.motions.gaze.range = value;
        } else if (paramName === 'wind_strength') {
            this.motions.wind.strength = value;
        }
    }
    
    animate() {
        if (!this.isRunning) return;
        
        try {
            const currentTime = Date.now() / 1000;
            
            if (this.motions.blink.enabled) {
                this.updateBlink(currentTime);
            }
            
            if (this.motions.gaze.enabled) {
                this.updateGaze(currentTime);
            }
            
            if (this.motions.wind.enabled) {
                this.updateWind(currentTime);
            }
            
        } catch (error) {
            console.error('❌ アイドルモーションエラー:', error);
        }
        
        this.animationFrameId = requestAnimationFrame(() => this.animate());
    }
    
    updateBlink(currentTime) {
        const blink = this.motions.blink;
        
        if (blink.isBlinking) {
            const elapsed = currentTime - blink.blinkStartTime;
            
            if (elapsed < blink.duration / 2) {
                const progress = elapsed / (blink.duration / 2);
                const eyeOpen = 1.0 - progress;
                this.setEyeOpen(eyeOpen);
            } else if (elapsed < blink.duration) {
                const progress = (elapsed - blink.duration / 2) / (blink.duration / 2);
                const eyeOpen = progress;
                this.setEyeOpen(eyeOpen);
            } else {
                blink.isBlinking = false;
                this.setEyeOpen(1.0);
                blink.lastTime = currentTime;
            }
        } else {
            if (currentTime - blink.lastTime >= blink.period) {
                blink.isBlinking = true;
                blink.blinkStartTime = currentTime;
            }
        }
    }
    
    updateGaze(currentTime) {
        const gaze = this.motions.gaze;
        
        if (currentTime - gaze.lastChangeTime >= gaze.changeInterval) {
            gaze.targetX = (Math.random() - 0.5) * 2 * gaze.range;
            gaze.targetY = (Math.random() - 0.5) * 2 * gaze.range;
            gaze.lastChangeTime = currentTime;
        }
        
        gaze.currentX += (gaze.targetX - gaze.currentX) * gaze.smoothness;
        gaze.currentY += (gaze.targetY - gaze.currentY) * gaze.smoothness;
        
        this.setEyeBallPosition(gaze.currentX, gaze.currentY);
    }
    
    updateWind(currentTime) {
        const wind = this.motions.wind;
        
        // サイン波で風の動きを生成
        wind.phase += 0.02 * wind.frequency;
        const windX = Math.sin(wind.phase) * wind.strength;
        const windY = Math.cos(wind.phase * 0.7) * wind.strength * 0.5;
        
        // 直接パラメータを設定（物理演算は既に無効化済み）
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamHairFront', windX * 0.8);
            window.setLive2DParameter('ParamHairSide', windX);
            window.setLive2DParameter('ParamHairBack', windX * 0.6);
            window.setLive2DParameter('ParamBodyAngleX', windX * 0.3);
        }
    }
    
    setEyeOpen(value) {
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamEyeLOpen', value);
            window.setLive2DParameter('ParamEyeROpen', value);
        }
    }
    
    setEyeBallPosition(x, y) {
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamEyeBallX', x);
            window.setLive2DParameter('ParamEyeBallY', y);
        }
    }
    
    /**
     * 物理演算を無効化
     */
    disablePhysics() {
        try {
            const model = window.currentModel;
            if (!model) return;
            
            if (model.internalModel && model.internalModel.physics) {
                this.physicsOriginalState = {
                    enabled: true,
                    physicsObject: model.internalModel.physics
                };
                
                // 物理演算を完全無効化
                model.internalModel.physics = null;
                this.motions.wind.isOverriding = true;
                
                console.log('💨 物理演算を無効化（風揺れ制御開始）');
            }
        } catch (error) {
            console.warn('⚠️ 物理演算無効化失敗:', error);
        }
    }
    
    /**
     * 物理演算を復元
     */
    restorePhysics() {
        try {
            const model = window.currentModel;
            if (!model || !this.physicsOriginalState) return;
            
            if (model.internalModel && this.physicsOriginalState.physicsObject) {
                model.internalModel.physics = this.physicsOriginalState.physicsObject;
                this.motions.wind.isOverriding = false;
                this.physicsOriginalState = null;
                
                console.log('♻️ 物理演算を復元');
            }
        } catch (error) {
            console.warn('⚠️ 物理演算復元失敗:', error);
        }
    }
}

// グローバルインスタンス作成
window.idleMotionManager = new IdleMotionManager();

/**
 * アイドルモーションのON/OFF切り替え（Python側から呼び出し）
 */
window.toggleIdleMotion = function(motionType, enabled) {
    try {
        console.log(`🌟 toggleIdleMotion: ${motionType} = ${enabled}`);
        
        if (!window.idleMotionManager) {
            console.error('❌ idleMotionManager未初期化');
            return false;
        }
        
        window.idleMotionManager.toggleMotion(motionType, enabled);
        return true;
    } catch (error) {
        console.error(`❌ toggleIdleMotionエラー:`, error);
        return false;
    }
};

/**
 * アイドルモーションパラメータ設定（Python側から呼び出し）
 */
window.setIdleMotionParam = function(paramName, value) {
    try {
        if (!window.idleMotionManager) {
            console.error('❌ idleMotionManager未初期化');
            return false;
        }
        
        window.idleMotionManager.setMotionParam(paramName, value);
        return true;
    } catch (error) {
        console.error(`❌ setIdleMotionParamエラー:`, error);
        return false;
    }
};

console.log('✅ アイドルモーション機能（修正版）を追加');