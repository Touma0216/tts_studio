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

// 🔧 追加：位置保護機能
let preservedModelSettings = null;
let isPositionProtected = false;

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
                    // 🔥 修正: 正しいAPI使用法
                    if (this.model.internalModel && this.model.internalModel.coreModel) {
                        // パラメータIDからインデックスを取得
                        const paramIndex = this.model.internalModel.coreModel.getParameterIndex(paramId);
                        if (paramIndex >= 0) {
                            this.model.internalModel.coreModel.setParameterValueByIndex(paramIndex, params[paramId]);
                            console.log(`🔧 Fallback parameter set: ${paramId} = ${params[paramId]}`);
                        } else {
                            console.warn(`⚠️ Parameter not found: ${paramId}`);
                        }
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

// 🔧 追加：現在のモデル設定を保存
function preserveCurrentModelSettings() {
    if (!currentModel) return null;
    
    try {
        preservedModelSettings = {
            scale: currentModel.scale.x,
            x: currentModel.x,
            y: currentModel.y,
            anchor: { x: currentModel.anchor.x, y: currentModel.anchor.y }
        };
        console.log("💾 モデル設定を保存:", preservedModelSettings);
        return preservedModelSettings;
    } catch (error) {
        console.warn("⚠️ モデル設定保存失敗:", error);
        return null;
    }
}

// 🔧 追加：保存された設定を復元
function restorePreservedModelSettings() {
    if (!currentModel || !preservedModelSettings) return false;
    
    try {
        currentModel.scale.set(preservedModelSettings.scale);
        currentModel.x = preservedModelSettings.x;
        currentModel.y = preservedModelSettings.y;
        currentModel.anchor.set(preservedModelSettings.anchor.x, preservedModelSettings.anchor.y);
        
        console.log("🔄 モデル設定を復元:", preservedModelSettings);
        return true;
    } catch (error) {
        console.warn("⚠️ モデル設定復元失敗:", error);
        return false;
    }
}

window.updateModelSettings = function(settings) {
    if (!currentModel) return;
    
    try {
        // 🔧 修正：位置保護中の場合は設定を保存してから適用
        if (isPositionProtected) {
            preserveCurrentModelSettings();
        }
        
        // ---- スケール更新 ----
        if (settings.scale !== undefined) {
            // 位置には触らず scale だけ更新
            const modelBounds = currentModel.getBounds();
            const baseScaleX = (window.innerWidth * 0.9) / (modelBounds.width / currentModel.scale.x);
            const baseScaleY = (window.innerHeight * 0.9) / (modelBounds.height / currentModel.scale.y);
            const baseScale = Math.min(baseScaleX, baseScaleY);
            currentModel.scale.set(baseScale * settings.scale);
        }

        // ---- 表示サイズと移動範囲計算 ----
        const modelHeight = currentModel.getBounds().height;
        const viewHeight = window.innerHeight;
        const overflowHeight = Math.max(0, modelHeight - viewHeight);

        // デフォルト基準位置
        const baseX = window.innerWidth / 2;
        const baseY = viewHeight * 0.9;

        // 上下の移動範囲に余裕を追加（10% → 20%）
        const padding = viewHeight * 0.2;

        // 移動範囲の計算を強化（÷2を外してフルに使う）
        const moveRange = overflowHeight + padding;

        // ---- X位置の計算 ----
        let finalX = currentModel.x || baseX;
        if (settings.position_x !== undefined) {
            const moveRangeX = window.innerWidth / 3;
            finalX = baseX + (settings.position_x * moveRangeX);
        }

        // ---- Y位置の計算 ----
        let finalY = currentModel.y || baseY;
        if (settings.position_y !== undefined) {
            const offsetY = settings.position_y * moveRange;
            finalY = baseY + offsetY;
        }

        // ---- 反映 ----
        currentModel.x = finalX;
        currentModel.y = finalY;

        // 🔧 追加：位置保護中の場合は復元された設定を保存
        if (isPositionProtected && preservedModelSettings) {
            preservedModelSettings.scale = currentModel.scale.x;
            preservedModelSettings.x = currentModel.x;
            preservedModelSettings.y = currentModel.y;
        }

    } catch (e) {
        console.error("モデル設定更新エラー:", e);
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
// リップシンク関連API（修正版：位置リセット防止）
// =============================================================================

/**
 * リップシンクを開始（修正版：位置保護機能付き）
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
        
        // 🔧 追加：リップシンク開始前に現在の設定を保護
        console.log("🛡️ 位置保護開始");
        isPositionProtected = true;
        preserveCurrentModelSettings();
        
        currentLipSyncData = lipSyncData;
        isLipSyncEnabled = true;
        
        // リップシンク開始
        const startResult = lipSyncController.startLipSync(lipSyncData);
        
        // 🔧 追加：開始直後に設定を復元（複数回試行）
        if (startResult && preservedModelSettings) {
            // 即座に復元
            setTimeout(() => {
                if (isPositionProtected) {
                    restorePreservedModelSettings();
                    console.log("🔄 位置復元（即座）");
                }
            }, 10);
            
            // 50ms後にも復元
            setTimeout(() => {
                if (isPositionProtected) {
                    restorePreservedModelSettings();
                    console.log("🔄 位置復元（50ms後）");
                }
            }, 50);
            
            // 100ms後にも復元
            setTimeout(() => {
                if (isPositionProtected) {
                    restorePreservedModelSettings();
                    console.log("🔄 位置復元（100ms後）");
                }
            }, 100);
            
            // 200ms後に保護解除
            setTimeout(() => {
                isPositionProtected = false;
                preservedModelSettings = null;
                console.log("🛡️ 位置保護終了");
            }, 200);
        } else {
            // 失敗時は即座に保護解除
            isPositionProtected = false;
            preservedModelSettings = null;
        }
        
        return startResult;
        
    } catch (error) {
        console.error("❌ リップシンク開始エラー:", error);
        isPositionProtected = false;
        preservedModelSettings = null;
        return false;
    }
};

/**
 * リップシンクを停止（修正版：位置保護対応）
 * @returns {boolean} 成功時true
 */
window.stopLipSync = function() {
    try {
        console.log("⏹️ リップシンク停止");
        
        isLipSyncEnabled = false;
        currentLipSyncData = null;
        
        // 🔧 追加：停止時に位置保護を解除
        isPositionProtected = false;
        preservedModelSettings = null;
        
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
 * リップシンクパラメータを直接設定（修正版：位置保護対応）
 * @param {Object} parameters - Live2Dパラメータ
 * @returns {boolean} 成功時true
 */
window.setLipSyncParameters = function(parameters) {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }
        
        // 🔧 追加：位置保護中の場合は口パラメータのみ適用
        if (isPositionProtected) {
            const mouthOnlyParams = {};
            Object.keys(parameters).forEach(paramId => {
                const id = paramId.toLowerCase();
                if (id.includes('mouth') || id.includes('lip') || id.includes('口')) {
                    mouthOnlyParams[paramId] = parameters[paramId];
                }
            });
            parameters = mouthOnlyParams;
            console.log("🛡️ 位置保護中：口パラメータのみ適用", parameters);
        }
        
        if (lipSyncController) {
            lipSyncController.setParameters(parameters);
        } else {
            // フォールバック：直接設定
            Object.keys(parameters).forEach(paramId => {
                try {
                    // 🔥 修正: 正しいAPI使用法
                    if (currentModel.internalModel && currentModel.internalModel.coreModel) {
                        const paramIndex = currentModel.internalModel.coreModel.getParameterIndex(paramId);
                        if (paramIndex >= 0) {
                            currentModel.internalModel.coreModel.setParameterValueByIndex(paramIndex, parameters[paramId]);
                        } else {
                            console.warn(`⚠️ Parameter not found: ${paramId}`);
                        }
                    }
                } catch (e) {
                    console.warn(`⚠️ Parameter ${paramId} not found`);
                }
            });
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
        isPositionProtected: isPositionProtected,
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
        
        // 🔥 修正: 正しいパラメータ設定方法
        if (currentModel.internalModel && currentModel.internalModel.coreModel) {
            const paramIndex = currentModel.internalModel.coreModel.getParameterIndex(paramId);
            if (paramIndex >= 0) {
                currentModel.internalModel.coreModel.setParameterValueByIndex(paramIndex, value);
                console.log(`🔧 パラメータ設定: ${paramId} = ${value}`);
                return true;
            } else {
                console.warn(`⚠️ パラメータが見つかりません: ${paramId}`);
                return false;
            }
        }
        
        console.warn(`⚠️ モデルがアクセス不可能です`);
        return false;
        
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
        
        const parameters = [];
        
        // 🔥 修正: 正しいパラメータ取得方法
        if (currentModel.internalModel && currentModel.internalModel.coreModel) {
            const coreModel = currentModel.internalModel.coreModel;
            const paramCount = coreModel.getParameterCount();
            
            for (let i = 0; i < paramCount; i++) {
                try {
                    // パラメータIDを取得
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
                    console.warn(`⚠️ パラメータ ${i} の情報取得失敗:`, e);
                }
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
            positionProtection: {
                isProtected: isPositionProtected,
                preservedSettings: preservedModelSettings
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
 * テスト用：基本的なリップシンクテスト（修正版：位置保護付き）
 * @returns {Promise<boolean>} テスト成功時true
 */
window.testLipSync = async function() {
    try {
        console.log("🧪 リップシンクテスト開始（位置保護付き）");
        
        if (!currentModel) {
            console.error("❌ モデルが読み込まれていません");
            return false;
        }
        
        // まずパラメータを確認
        console.log("🔍 モデルパラメータ確認中...");
        const params = window.getLive2DParameters();
        console.log(`📋 発見されたパラメータ数: ${params.length}`);
        
        // 口関連パラメータを探す
        const mouthParams = params.filter(p => 
            p.id.toLowerCase().includes('mouth') || 
            p.id.toLowerCase().includes('lip') ||
            p.id.includes('口')
        );
        console.log("👄 口関連パラメータ:", mouthParams.map(p => p.id));
        
        // テストパラメータ設定
        if (mouthParams.length > 0) {
            const testParam = mouthParams[0];
            console.log(`🧪 テストパラメータ: ${testParam.id}`);
            
            // 段階的にテスト
            for (let i = 0; i <= 10; i++) {
                const testValue = (testParam.maxValue - testParam.minValue) * (i / 10) + testParam.minValue;
                window.setLive2DParameter(testParam.id, testValue);
                await new Promise(resolve => setTimeout(resolve, 200));
            }
            
            // 元に戻す
            window.setLive2DParameter(testParam.id, testParam.defaultValue);
            
            console.log("✅ 基本パラメータテスト完了");
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
        
        // テスト実行（位置保護機能付き）
        const success = window.startLipSync(testData);
        
        if (success) {
            console.log("✅ リップシンクテスト成功（位置保護付き）");
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