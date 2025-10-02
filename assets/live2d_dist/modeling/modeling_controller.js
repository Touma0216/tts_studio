// assets/live2d_dist/modeling/modeling_controller.js
// モデリング制御：パラメータ設定のメイン処理

/**
 * 単一パラメータをLive2Dモデルに設定
 * @param {string} paramId - パラメータID（例: "ParamAngleX"）
 * @param {number} value - 設定値
 * @returns {boolean} - 成功したらtrue
 */
window.setLive2DParameter = function(paramId, value) {
    try {
        if (!window.currentModel) {
            console.warn('⚠️ モデル未読み込み：パラメータ設定スキップ');
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        
        // パラメータIDの存在確認
        const paramIndex = model.getParameterIndex(paramId);
        if (paramIndex === -1) {
            console.warn(`⚠️ パラメータが見つかりません: ${paramId}`);
            return false;
        }

        // パラメータ設定
        model.setParameterValueById(paramId, value);
        
        // デバッグログ（詳細版：初回のみ）
        if (!window._paramSetCount) window._paramSetCount = {};
        if (!window._paramSetCount[paramId]) {
            console.log(`✅ パラメータ設定: ${paramId} = ${value.toFixed(3)}`);
            window._paramSetCount[paramId] = true;
        }

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
            console.warn('⚠️ モデル未読み込み：パラメータ一括設定スキップ');
            return false;
        }

        if (!parameters || typeof parameters !== 'object') {
            console.error('❌ パラメータが無効な形式です');
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        let successCount = 0;
        let failCount = 0;

        // 全パラメータを設定
        for (const [paramId, value] of Object.entries(parameters)) {
            const paramIndex = model.getParameterIndex(paramId);
            if (paramIndex === -1) {
                failCount++;
                continue;
            }

            model.setParameterValueById(paramId, value);
            successCount++;
        }

        console.log(`🎨 パラメータ一括設定: 成功${successCount}個, 失敗${failCount}個`);
        return true;
    } catch (error) {
        console.error('❌ パラメータ一括設定エラー:', error);
        return false;
    }
};

/**
 * パラメータをデフォルト値にリセット
 * @param {string} paramId - パラメータID
 * @returns {boolean} - 成功したらtrue
 */
window.resetLive2DParameter = function(paramId) {
    try {
        if (!window.currentModel) {
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramIndex = model.getParameterIndex(paramId);
        
        if (paramIndex === -1) {
            return false;
        }

        // デフォルト値を取得して設定
        const defaultValue = model.getParameterDefaultValueById(paramId);
        model.setParameterValueById(paramId, defaultValue);
        
        console.log(`↺ リセット: ${paramId} = ${defaultValue.toFixed(3)}`);
        return true;
    } catch (error) {
        console.error(`❌ リセットエラー (${paramId}):`, error);
        return false;
    }
};

/**
 * 全パラメータをデフォルト値にリセット
 * @returns {boolean} - 成功したらtrue
 */
window.resetAllLive2DParameters = function() {
    try {
        if (!window.currentModel) {
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramCount = model.getParameterCount();
        let resetCount = 0;

        for (let i = 0; i < paramCount; i++) {
            const paramId = model.getParameterId(i);
            const defaultValue = model.getParameterDefaultValueById(paramId);
            model.setParameterValueById(paramId, defaultValue);
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
 * @param {string} paramId - パラメータID
 * @returns {number|null} - パラメータ値、取得失敗時はnull
 */
window.getLive2DParameterValue = function(paramId) {
    try {
        if (!window.currentModel) {
            return null;
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramIndex = model.getParameterIndex(paramId);
        
        if (paramIndex === -1) {
            return null;
        }

        return model.getParameterValueById(paramId);
    } catch (error) {
        console.error(`❌ パラメータ取得エラー (${paramId}):`, error);
        return null;
    }
};

/**
 * 全パラメータの現在値を取得
 * @returns {Object} - {paramId: value, ...}の形式
 */
window.getAllLive2DParameterValues = function() {
    try {
        if (!window.currentModel) {
            return {};
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramCount = model.getParameterCount();
        const values = {};

        for (let i = 0; i < paramCount; i++) {
            const paramId = model.getParameterId(i);
            const value = model.getParameterValueById(paramId);
            values[paramId] = value;
        }

        return values;
    } catch (error) {
        console.error('❌ 全パラメータ取得エラー:', error);
        return {};
    }
};

console.log('✅ modeling_controller.js 読み込み完了');

// assets/live2d_dist/modeling/modeling_controller.js
// 既存のコードの末尾に以下を追加

// =============================================================================
// アイドルモーション機能
// =============================================================================

/**
 * アイドルモーション管理クラス
 */
class IdleMotionManager {
    constructor() {
        this.motions = {
            blink: {
                enabled: false,
                period: 3.0,  // 秒
                lastTime: 0,
                duration: 0.15,  // 瞬きの長さ
                isBlinking: false,
                blinkStartTime: 0
            },
            gaze: {
                enabled: false,
                range: 0.5,  // 視線移動範囲（0.0-1.0）
                targetX: 0,
                targetY: 0,
                currentX: 0,
                currentY: 0,
                changeInterval: 2.0,  // 秒
                lastChangeTime: 0,
                smoothness: 0.05  // 移動の滑らかさ
            },
            wind: {
                enabled: false,
                strength: 0.5,  // 風の強さ（0.0-1.0）
                windX: 0,
                windY: 0,
                phase: 0,
                frequency: 1.0  // 風の周波数
            }
        };
        
        this.animationFrameId = null;
        this.isRunning = false;
    }
    
    /**
     * アイドルモーション開始
     */
    start() {
        if (this.isRunning) return;
        
        this.isRunning = true;
        this.animate();
        console.log('🌟 アイドルモーション開始');
    }
    
    /**
     * アイドルモーション停止
     */
    stop() {
        if (!this.isRunning) return;
        
        this.isRunning = false;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        console.log('⏹️ アイドルモーション停止');
    }
    
    /**
     * モーションのON/OFF切り替え
     */
    toggleMotion(motionType, enabled) {
        if (!this.motions[motionType]) {
            console.warn(`⚠️ 不明なモーションタイプ: ${motionType}`);
            return;
        }
        
        this.motions[motionType].enabled = enabled;
        console.log(`🌟 ${motionType}: ${enabled ? 'ON' : 'OFF'}`);
        
        // いずれかのモーションが有効なら開始、全て無効なら停止
        const anyEnabled = Object.values(this.motions).some(m => m.enabled);
        if (anyEnabled && !this.isRunning) {
            this.start();
        } else if (!anyEnabled && this.isRunning) {
            this.stop();
        }
    }
    
    /**
     * モーションパラメータ設定
     */
    setMotionParam(paramName, value) {
        // パラメータ名から対応するモーションを特定
        if (paramName === 'blink_period') {
            this.motions.blink.period = value;
        } else if (paramName === 'gaze_range') {
            this.motions.gaze.range = value;
        } else if (paramName === 'wind_strength') {
            this.motions.wind.strength = value;
        } else {
            console.warn(`⚠️ 不明なパラメータ: ${paramName}`);
        }
    }
    
    /**
     * アニメーションループ
     */
    animate() {
        if (!this.isRunning) return;
        
        try {
            const currentTime = Date.now() / 1000;
            
            // 瞬き処理
            if (this.motions.blink.enabled) {
                this.updateBlink(currentTime);
            }
            
            // 視線揺れ処理
            if (this.motions.gaze.enabled) {
                this.updateGaze(currentTime);
            }
            
            // 風揺れ処理
            if (this.motions.wind.enabled) {
                this.updateWind(currentTime);
            }
            
        } catch (error) {
            console.error('❌ アイドルモーションエラー:', error);
        }
        
        this.animationFrameId = requestAnimationFrame(() => this.animate());
    }
    
    /**
     * 瞬き更新
     */
    updateBlink(currentTime) {
        const blink = this.motions.blink;
        
        if (blink.isBlinking) {
            // 瞬き中
            const elapsed = currentTime - blink.blinkStartTime;
            
            if (elapsed < blink.duration / 2) {
                // 閉じる
                const progress = elapsed / (blink.duration / 2);
                const eyeOpen = 1.0 - progress;
                this.setEyeOpen(eyeOpen);
            } else if (elapsed < blink.duration) {
                // 開く
                const progress = (elapsed - blink.duration / 2) / (blink.duration / 2);
                const eyeOpen = progress;
                this.setEyeOpen(eyeOpen);
            } else {
                // 瞬き終了
                blink.isBlinking = false;
                this.setEyeOpen(1.0);
                blink.lastTime = currentTime;
            }
        } else {
            // 次の瞬きまで待機
            if (currentTime - blink.lastTime >= blink.period) {
                blink.isBlinking = true;
                blink.blinkStartTime = currentTime;
            }
        }
    }
    
    /**
     * 視線揺れ更新
     */
    updateGaze(currentTime) {
        const gaze = this.motions.gaze;
        
        // 一定間隔で新しいターゲット位置を設定
        if (currentTime - gaze.lastChangeTime >= gaze.changeInterval) {
            gaze.targetX = (Math.random() - 0.5) * 2 * gaze.range;
            gaze.targetY = (Math.random() - 0.5) * 2 * gaze.range;
            gaze.lastChangeTime = currentTime;
        }
        
        // 現在位置をターゲットに向けて滑らかに移動
        gaze.currentX += (gaze.targetX - gaze.currentX) * gaze.smoothness;
        gaze.currentY += (gaze.targetY - gaze.currentY) * gaze.smoothness;
        
        // Live2Dに反映
        this.setEyeBallPosition(gaze.currentX, gaze.currentY);
    }
    
    /**
     * 風揺れ更新
     */
    updateWind(currentTime) {
        const wind = this.motions.wind;
        
        // サイン波で風の動きを生成
        wind.phase += 0.02 * wind.frequency;
        wind.windX = Math.sin(wind.phase) * wind.strength;
        wind.windY = Math.cos(wind.phase * 0.7) * wind.strength * 0.5;
        
        // Live2Dに反映
        this.setHairSway(wind.windX, wind.windY);
    }
    
    /**
     * 目の開閉設定
     */
    setEyeOpen(value) {
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamEyeLOpen', value);
            window.setLive2DParameter('ParamEyeROpen', value);
        }
    }
    
    /**
     * 目玉位置設定
     */
    setEyeBallPosition(x, y) {
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamEyeBallX', x);
            window.setLive2DParameter('ParamEyeBallY', y);
        }
    }
    
    /**
     * 髪揺れ設定
     */
    setHairSway(x, y) {
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamHairFront', x * 0.8);
            window.setLive2DParameter('ParamHairSide', x);
            window.setLive2DParameter('ParamHairBack', x * 0.6);
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
        if (!window.idleMotionManager) {
            console.error('❌ idleMotionManager未初期化');
            return false;
        }
        
        window.idleMotionManager.toggleMotion(motionType, enabled);
        return true;
    } catch (error) {
        console.error(`❌ toggleIdleMotionエラー (${motionType}):`, error);
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
        console.error(`❌ setIdleMotionParamエラー (${paramName}):`, error);
        return false;
    }
};

console.log('✅ アイドルモーション機能を追加しました');