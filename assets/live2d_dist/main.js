import * as PIXI from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display';

// PIXIをグローバルスコープに公開
window.PIXI = PIXI;

let app;
let currentModel;

// リップシンク関連
let lipSyncController = null;
let isLipSyncEnabled = false;
let currentLipSyncData = null;

async function initialize() {
    const canvas = document.getElementById('live2d-canvas');
    
    app = new PIXI.Application({
        view: canvas,
        width: window.innerWidth,
        height: window.innerHeight,
        autoStart: true,
        backgroundAlpha: 0,
        resizeTo: window,
    });
    
    // リップシンクコントローラー初期化
    await initializeLipSyncController();
    
    console.log("✅ Live2D Viewer Initialized.");
}

// リップシンクコントローラーの初期化
async function initializeLipSyncController() {
    try {
        // リップシンクモジュールの動的インポート
        const { LipSyncController } = await import('./lip_sync/lip_sync_controller.js');
        const { PhonemeClassifier } = await import('./lip_sync/phoneme_classifier.js');
        const { AudioAnalyzer } = await import('./lip_sync/audio_analyzer.js');
        
        // コンポーネント初期化
        const audioAnalyzer = new AudioAnalyzer();
        const phonemeClassifier = new PhonemeClassifier();
        
        // 音素モデルを読み込み（非同期）
        await phonemeClassifier.loadPhonemeModel();
        
        lipSyncController = new LipSyncController({
            audioAnalyzer,
            phonemeClassifier
        });
        
        console.log("✅ LipSync Controller initialized.");
        
    } catch (error) {
        console.warn("⚠️ LipSync modules not found, using fallback mode:", error);
        lipSyncController = new FallbackLipSyncController();
    }
}

// フォールバック用リップシンクコントローラー
class FallbackLipSyncController {
    constructor() {
        this.isEnabled = false;
        this.model = null;
        console.log("📱 Fallback LipSync Controller active");
    }
    
    setModel(model) {
        this.model = model;
        console.log("🎭 Fallback controller connected to model");
    }
    
    startLipSync(lipSyncData) {
        console.log("⚠️ LipSync not available in fallback mode");
        console.log("📝 LipSync data received:", {
            text: lipSyncData?.text || 'No text',
            duration: lipSyncData?.total_duration || 0,
            frameCount: lipSyncData?.vowel_frames?.length || 0
        });
        return false;
    }
    
    stopLipSync() {
        console.log("⏹️ Fallback LipSync stop");
        return true;
    }
    
    setParameters(params) {
        // パラメータ設定のみ実行
        if (this.model) {
            Object.keys(params).forEach(paramId => {
                try {
                    const model = this.model.internalModel;
                    if (model && model.coreModel) {
                        model.coreModel.setParameterValueById(paramId, params[paramId]);
                        console.log(`🔧 Fallback parameter set: ${paramId} = ${params[paramId]}`);
                    }
                } catch (e) {
                    console.warn(`⚠️ Fallback parameter ${paramId} failed:`, e);
                }
            });
        }
    }
    
    updateSettings(settings) {
        console.log("📝 Fallback mode: settings updated", settings);
    }
    
    getStatus() {
        return {
            isActive: false,
            currentMode: 'fallback',
            hasModel: !!this.model,
            hasAudioAnalyzer: false,
            hasPhonemeClassifier: false
        };
    }
}

window.loadLive2DModel = async function(modelJsonPath) {
    try {
        console.log("モデル読み込み開始:", modelJsonPath);
        
        if (currentModel) {
            // リップシンク停止
            if (lipSyncController) {
                lipSyncController.stopLipSync();
            }
            
            app.stage.removeChild(currentModel);
            currentModel.destroy({ children: true });
        }
        
        currentModel = await Live2DModel.from(modelJsonPath, {
            autoUpdate: true,
            autoHitTest: false,
            autoFocus: false
        });
        
        console.log("モデル作成成功:", currentModel);
        
        app.stage.addChild(currentModel);
        
        const modelBounds = currentModel.getBounds();
        const scaleX = (window.innerWidth * 0.9) / modelBounds.width;
        const scaleY = (window.innerHeight * 0.9) / modelBounds.height;
        const scale = Math.min(scaleX, scaleY);
        
        currentModel.scale.set(scale);
        currentModel.anchor.set(0.5, 1.0);
        currentModel.x = window.innerWidth / 2;
        currentModel.y = window.innerHeight * 0.9;
        
        // リップシンクコントローラーにモデルを設定
        if (lipSyncController) {
            lipSyncController.setModel(currentModel);
            console.log("🎭 LipSync controller connected to model");
        }
        
        console.log("モデル配置完了 - サイズ:", currentModel.width, "x", currentModel.height, "スケール:", scale);
        return true;
        
    } catch (e) {
        console.error("❌ モデル読み込みエラー:", e);
        return false;
    }
};

window.playMotion = function(motionName) {
    if (currentModel) {
        try {
            currentModel.motion(motionName);
        } catch (e) {
            console.error("モーション再生エラー:", e);
        }
    }
};

window.setExpression = function(expressionName) {
    if (currentModel) {
        try {
            currentModel.expression(expressionName);
        } catch (e) {
            console.error("表情設定エラー:", e);
        }
    }
};

window.updateModelSettings = function(settings) {
    if (currentModel) {
        try {
            if (settings.scale !== undefined) {
                const modelBounds = currentModel.getBounds();
                const baseScaleX = (window.innerWidth * 0.9) / (modelBounds.width / currentModel.scale.x);
                const baseScaleY = (window.innerHeight * 0.9) / (modelBounds.height / currentModel.scale.y);
                const baseScale = Math.min(baseScaleX, baseScaleY);
                currentModel.scale.set(baseScale * settings.scale);
            }

            const modelHeight = currentModel.getBounds().height;
            const viewHeight = window.innerHeight;
            const overflowHeight = Math.max(0, modelHeight - viewHeight);
            const baseY = viewHeight * 0.9;

            // 上下の移動範囲に少し「余裕（パディング）」を追加
            const padding = viewHeight * 0.1; 
            
            // 新しい移動範囲を「はみ出した高さ + 余裕」で計算
            const moveRange = (overflowHeight + padding) / 2;

            let finalX = window.innerWidth / 2;
            if (settings.position_x !== undefined) {
                const moveRangeX = window.innerWidth / 3;
                finalX = (window.innerWidth / 2) + (settings.position_x * moveRangeX);
            }
            
            let finalY = baseY;
            if (settings.position_y !== undefined) {
                const offsetY = settings.position_y * moveRange;
                finalY = baseY + offsetY;
            }

            currentModel.x = finalX;
            currentModel.y = finalY;

        } catch (e) {
            console.error("モデル設定更新エラー:", e);
        }
    }
};

window.setBackgroundVisible = function(visible) {
    if (app && app.renderer) {
        try {
            app.renderer.background.alpha = visible ? 1 : 0;
        } catch (e) {
            console.error("背景設定エラー:", e);
        }
    }
};

window.addEventListener('resize', () => {
    if (app && app.renderer) {
        app.renderer.resize(window.innerWidth, window.innerHeight);
        
        if (currentModel) {
            const modelBounds = currentModel.getBounds();
            const scaleX = (window.innerWidth * 0.9) / (modelBounds.width / currentModel.scale.x);
            const scaleY = (window.innerHeight * 0.9) / (modelBounds.height / currentModel.scale.y);
            const scale = Math.min(scaleX, scaleY);
            
            currentModel.scale.set(scale);
            currentModel.x = window.innerWidth / 2;
            currentModel.y = window.innerHeight * 0.9;
        }
    }
});

// =============================================================================
// リップシンク関連API
// =============================================================================

/**
 * リップシンクを開始
 * @param {Object} lipSyncData - Python側からのリップシンクデータ
 * @returns {boolean} 成功時true
 */
window.startLipSync = function(lipSyncData) {
    try {
        console.log("🎵 リップシンク開始:", lipSyncData);
        
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }
        
        if (!lipSyncController) {
            console.warn("⚠️ リップシンクコントローラーが初期化されていません");
            return false;
        }
        
        currentLipSyncData = lipSyncData;
        isLipSyncEnabled = true;
        
        return lipSyncController.startLipSync(lipSyncData);
        
    } catch (error) {
        console.error("❌ リップシンク開始エラー:", error);
        return false;
    }
};

/**
 * リップシンクを停止
 * @returns {boolean} 成功時true
 */
window.stopLipSync = function() {
    try {
        console.log("⏹️ リップシンク停止");
        
        isLipSyncEnabled = false;
        currentLipSyncData = null;
        
        if (lipSyncController) {
            return lipSyncController.stopLipSync();
        }
        
        return true;
        
    } catch (error) {
        console.error("❌ リップシンク停止エラー:", error);
        return false;
    }
};

/**
 * リップシンクパラメータを直接設定
 * @param {Object} parameters - Live2Dパラメータ
 * @returns {boolean} 成功時true
 */
window.setLipSyncParameters = function(parameters) {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }
        
        if (lipSyncController) {
            lipSyncController.setParameters(parameters);
        } else {
            // フォールバック：直接設定
            const model = currentModel.internalModel;
            if (model && model.coreModel) {
                Object.keys(parameters).forEach(paramId => {
                    try {
                        model.coreModel.setParameterValueById(paramId, parameters[paramId]);
                    } catch (e) {
                        console.warn(`⚠️ Parameter ${paramId} not found`);
                    }
                });
            }
        }
        
        return true;
        
    } catch (error) {
        console.error("❌ リップシンクパラメータ設定エラー:", error);
        return false;
    }
};

/**
 * リップシンク設定を更新
 * @param {Object} settings - リップシンク設定
 * @returns {boolean} 成功時true
 */
window.updateLipSyncSettings = function(settings) {
    try {
        console.log("🔧 リップシンク設定更新:", settings);
        
        if (lipSyncController) {
            lipSyncController.updateSettings(settings);
        }
        
        return true;
        
    } catch (error) {
        console.error("❌ リップシンク設定更新エラー:", error);
        return false;
    }
};

/**
 * リップシンク状態を取得
 * @returns {Object} 現在の状態
 */
window.getLipSyncStatus = function() {
    const baseStatus = {
        isEnabled: isLipSyncEnabled,
        hasModel: !!currentModel,
        hasController: !!lipSyncController,
        currentData: currentLipSyncData ? {
            text: currentLipSyncData.text,
            duration: currentLipSyncData.total_duration,
            frameCount: currentLipSyncData.vowel_frames ? currentLipSyncData.vowel_frames.length : 0
        } : null
    };
    
    if (lipSyncController) {
        return {
            ...baseStatus,
            ...lipSyncController.getStatus()
        };
    }
    
    return baseStatus;
};

/**
 * デバッグ用：直接パラメータ設定
 * @param {string} paramId - パラメータID
 * @param {number} value - パラメータ値
 * @returns {boolean} 成功時true
 */
window.setLive2DParameter = function(paramId, value) {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }
        
        // パラメータ設定（複数の方法を試す）
        const model = currentModel.internalModel;
        
        if (model && model.coreModel) {
            // Method 1: Core model direct access
            model.coreModel.setParameterValueById(paramId, value);
        } else if (currentModel.setParameterValue) {
            // Method 2: pixi-live2d-display API
            currentModel.setParameterValue(paramId, value);
        } else {
            console.warn(`⚠️ パラメータ設定方法が見つかりません: ${paramId}`);
            return false;
        }
        
        console.log(`🔧 パラメータ設定: ${paramId} = ${value}`);
        return true;
        
    } catch (error) {
        console.error(`❌ パラメータ設定エラー (${paramId}):`, error);
        return false;
    }
};

/**
 * デバッグ用：利用可能なパラメータ一覧を取得
 * @returns {Array} パラメータリスト
 */
window.getLive2DParameters = function() {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return [];
        }
        
        const model = currentModel.internalModel;
        const parameters = [];
        
        if (model && model.coreModel) {
            const paramCount = model.coreModel.getParameterCount();
            
            for (let i = 0; i < paramCount; i++) {
                const paramId = model.coreModel.getParameterId(i);
                const currentValue = model.coreModel.getParameterValue(i);
                const defaultValue = model.coreModel.getParameterDefaultValue(i);
                const minValue = model.coreModel.getParameterMinValue(i);
                const maxValue = model.coreModel.getParameterMaxValue(i);
                
                parameters.push({
                    id: paramId,
                    index: i,
                    currentValue,
                    defaultValue,
                    minValue,
                    maxValue
                });
            }
        }
        
        console.log("📋 利用可能パラメータ:", parameters);
        return parameters;
        
    } catch (error) {
        console.error("❌ パラメータ取得エラー:", error);
        return [];
    }
};

/**
 * デバッグ用：リップシンクのデバッグ情報を取得
 * @returns {Object} デバッグ情報
 */
window.getLipSyncDebugInfo = function() {
    try {
        const debugInfo = {
            controller: lipSyncController ? lipSyncController.getDebugInfo() : null,
            model: {
                loaded: !!currentModel,
                parametersCount: currentModel ? (
                    currentModel.internalModel?.coreModel?.getParameterCount() || 0
                ) : 0
            },
            system: {
                pixiVersion: PIXI.VERSION || 'unknown',
                browserUserAgent: navigator.userAgent,
                webAudioSupport: !!(window.AudioContext || window.webkitAudioContext),
                es6Support: true // このコードが実行されてれば対応済み
            }
        };
        
        console.log("🔍 LipSync Debug Info:", debugInfo);
        return debugInfo;
        
    } catch (error) {
        console.error("❌ デバッグ情報取得エラー:", error);
        return { error: error.message };
    }
};

/**
 * テスト用：基本的なリップシンクテスト
 * @returns {Promise<boolean>} テスト成功時true
 */
window.testLipSync = async function() {
    try {
        console.log("🧪 リップシンクテスト開始");
        
        if (!currentModel) {
            console.error("❌ モデルが読み込まれていません");
            return false;
        }
        
        // テストデータ
        const testData = {
            text: "あいうえお",
            total_duration: 2.0,
            vowel_frames: [
                { timestamp: 0.0, vowel: 'a', intensity: 0.8, duration: 0.4 },
                { timestamp: 0.4, vowel: 'i', intensity: 0.7, duration: 0.4 },
                { timestamp: 0.8, vowel: 'u', intensity: 0.6, duration: 0.4 },
                { timestamp: 1.2, vowel: 'e', intensity: 0.7, duration: 0.4 },
                { timestamp: 1.6, vowel: 'o', intensity: 0.8, duration: 0.4 }
            ]
        };
        
        // テスト実行
        const success = window.startLipSync(testData);
        
        if (success) {
            console.log("✅ リップシンクテスト成功");
            setTimeout(() => {
                window.stopLipSync();
                console.log("✅ リップシンクテスト完了");
            }, 3000);
            return true;
        } else {
            console.error("❌ リップシンクテスト失敗");
            return false;
        }
        
    } catch (error) {
        console.error("❌ リップシンクテストエラー:", error);
        return false;
    }
};

window.addEventListener('error', (event) => {
    console.error("JavaScript Error:", event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error("Unhandled Promise Rejection:", event.reason);
});

initialize();