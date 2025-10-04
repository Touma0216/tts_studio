import * as PIXI from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display';
import './animation_player.js';

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

// 背景制御関連
let backgroundSettings = {
    mode: 'transparent',
    color: '#000000',
    alpha: 0,
    previewAlpha: 0,
    imageFit: 'contain',
    imageRepeat: 'no-repeat'
};
let backgroundApplyPending = false;

function clampAlpha(value) {
    if (value === undefined || value === null || Number.isNaN(value)) {
        return 0;
    }
    return Math.max(0, Math.min(1, Number(value)));
}

function parseColorToNumber(color) {
    if (typeof color === 'number' && Number.isFinite(color)) {
        return color;
    }
    if (typeof color === 'string') {
        try {
            return PIXI.utils.string2hex(color);
        } catch (error) {
            console.warn('⚠️ 背景カラー解析失敗:', color, error);
        }
    }
    return PIXI.utils.string2hex('#000000');
}

function colorToCss(color, alpha) {
    const value = parseColorToNumber(color);
    const r = (value >> 16) & 0xff;
    const g = (value >> 8) & 0xff;
    const b = value & 0xff;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function resetBackgroundStyles(body, canvas) {
    body.style.background = '';
    body.style.backgroundColor = 'transparent';
    body.style.backgroundImage = '';
    body.style.backgroundSize = '';
    body.style.backgroundRepeat = '';
    body.style.backgroundPosition = '';

    canvas.style.background = 'transparent';
    canvas.style.backgroundColor = 'transparent';
    canvas.style.backgroundImage = '';
    canvas.style.backgroundSize = '';
    canvas.style.backgroundRepeat = '';
}

function applyBackgroundSettings() {
    const body = document.body;
    const canvas = document.getElementById('live2d-canvas');

    if (!body || !canvas) {
        backgroundApplyPending = true;
        return { success: false, pending: true, message: 'Live2D canvas not ready' };
    }

    resetBackgroundStyles(body, canvas);

    const mode = backgroundSettings.mode || 'default';
    const renderAlpha = clampAlpha(backgroundSettings.alpha);
    const previewAlpha = clampAlpha(
        backgroundSettings.previewAlpha !== undefined ? backgroundSettings.previewAlpha : renderAlpha
    );

    if (app && app.renderer) {
        if (mode === 'image') {
            app.renderer.background.alpha = renderAlpha;
        } else if (mode === 'default') {
            app.renderer.background.alpha = renderAlpha;
            app.renderer.background.color = parseColorToNumber('#000000');
        } else {
            app.renderer.background.alpha = renderAlpha;
            app.renderer.background.color = parseColorToNumber(backgroundSettings.color || '#000000');
        }
    }

    if (mode === 'image') {
        const dataUrl = backgroundSettings.imageDataUrl;
        if (!dataUrl) {
            backgroundApplyPending = true;
            return { success: false, pending: true, message: 'Background image data not ready' };
        }
        body.style.backgroundImage = `url(${dataUrl})`;
        body.style.backgroundSize = backgroundSettings.imageFit || 'contain';
        body.style.backgroundRepeat = backgroundSettings.imageRepeat || 'no-repeat';
        body.style.backgroundPosition = 'center center';
        canvas.style.backgroundColor = 'rgba(0,0,0,0)';
    } else if (mode === 'transparent') {
        const cssColor = colorToCss(backgroundSettings.color || '#000000', previewAlpha);
        body.style.backgroundColor = cssColor;
        canvas.style.backgroundColor = cssColor;
    } else if (mode === 'white_alpha' || mode === 'chroma') {
        const cssColor = colorToCss(backgroundSettings.color || '#ffffff', previewAlpha);
        body.style.backgroundColor = cssColor;
        canvas.style.backgroundColor = cssColor;
    } else {
        body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        canvas.style.backgroundColor = colorToCss('#000000', 0);
    }

    backgroundApplyPending = false;
    return { success: true, appliedSettings: { ...backgroundSettings } };
}

window.setLive2DBackground = function(config = {}) {
    try {
        if (!config || typeof config !== 'object') {
            return { success: false, message: 'Invalid background configuration' };
        }

        backgroundSettings = {
            ...backgroundSettings,
            ...config
        };

        if (!backgroundSettings.mode) {
            backgroundSettings.mode = 'default';
        }

        if (backgroundSettings.mode !== 'image') {
            delete backgroundSettings.imageDataUrl;
            delete backgroundSettings.imageFit;
            delete backgroundSettings.imageRepeat;
        }

        const result = applyBackgroundSettings();

        if (result && result.pending) {
            return { success: false, pending: true, message: result.message };
        }

        return result || { success: true, appliedSettings: { ...backgroundSettings } };
    } catch (error) {
        console.error('❌ 背景設定エラー:', error);
        backgroundApplyPending = true;
        return { success: false, message: error?.message || String(error) };
    }
};

window.getLive2DBackground = function() {
    return { ...backgroundSettings };
};

async function initialize() {
    const canvas = document.getElementById('live2d-canvas');
    
    app = new PIXI.Application({
        view: canvas,
        width: window.innerWidth,
        height: window.innerHeight,
        autoStart: true,
        backgroundAlpha: 0,
        resizeTo: window,
        // 🔥 高画質設定を追加
        resolution: window.devicePixelRatio || 2,  // デバイス解像度に対応（最低2倍）
        antialias: true,  // アンチエイリアス有効化
        autoDensity: true  // CSS解像度を自動調整
    });
    
    // リップシンクコントローラー初期化
    await initializeLipSyncController();

    applyBackgroundSettings();
    
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
                
                // 🔥 追加：グローバル変数に登録
                window.currentModelForDebug = currentModel;
                window.currentModel = currentModel;  // 🔥 これを追加
                window.live2dModel = currentModel;   // 🔥 これも追加

                console.log("モデル作成成功:", currentModel);
                console.log("✅ グローバル変数登録完了");
                
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
        
        // 🔥🔥🔥 ここから追加 🔥🔥🔥
        
        // 1. モデル読み込み完了イベントを発火（ドラッグ制御の初期化に必要）
        window.dispatchEvent(new CustomEvent('live2d-model-loaded', {
            detail: { modelPath: modelJsonPath, model: currentModel }
        }));
        console.log("✅ live2d-model-loaded イベント発火");
        
        // 2. プリセット情報を読み込み（表情・モーション一覧を取得）
        if (window.presetManager) {
            try {
                await window.presetManager.loadModelPresets(modelJsonPath);
                console.log("✅ プリセット情報読み込み完了");
            } catch (error) {
                console.warn("⚠️ プリセット読み込み失敗（スキップ）:", error);
            }
        } else {
            console.warn("⚠️ presetManager が見つかりません");
        }
        
        // 3. パラメータ情報をPython側に送信
        if (window.getLive2DParameters) {
            try {
                const parameters = window.getLive2DParameters();
                console.log(`📋 パラメータ情報: ${parameters.length}個`);
                
                // Python側に通知（オプション：character_display.pyで受け取る想定）
                window.dispatchEvent(new CustomEvent('parameters-loaded', {
                    detail: { parameters }
                }));
            } catch (error) {
                console.warn("⚠️ パラメータ取得失敗:", error);
            }
        }
        
        // 🔥🔥🔥 追加ここまで 🔥🔥🔥
        
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

window.resetExpression = function() {
    if (!window.currentModelForDebug) {
        console.warn("⚠️ モデル未読み込み");
        return false;
    }
    
    try {
        const model = window.currentModelForDebug;
        const internalModel = model.internalModel;
        
        if (!internalModel || !internalModel.motionManager) {
            console.warn("⚠️ モーションマネージャーにアクセスできません");
            return false;
        }
        
        const expressionManager = internalModel.motionManager.expressionManager;
        
        if (!expressionManager) {
            console.warn("⚠️ 表情マネージャーが見つかりません");
            return false;
        }
        
        // 🔥 表情を強制リセット
        // 方法1: 現在の表情をリセット
        if (typeof expressionManager.resetExpression === 'function') {
            expressionManager.resetExpression();
            console.log("✅ 表情リセット完了（resetExpression）");
        }
        // 方法2: 表情を空に設定
        else if (expressionManager.expressions && expressionManager.expressions.length > 0) {
            expressionManager.expressions = [];
            console.log("✅ 表情リセット完了（表情配列クリア）");
        }
        // 方法3: 現在の表情インデックスをリセット
        else {
            expressionManager.currentIndex = -1;
            expressionManager.currentExpression = null;
            console.log("✅ 表情リセット完了（インデックスリセット）");
        }
        
        return true;
        
    } catch (e) {
        console.error("❌ 表情リセット失敗:", e);
        return false;
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

function applyModelSettings(settings) {
    if (!currentModel || !settings) return false;

    try {
        if (typeof settings.scale === 'number' && currentModel.scale) {
            currentModel.scale.set(settings.scale);
        }

        if (typeof settings.x === 'number') {
            currentModel.x = settings.x;
        }

        if (typeof settings.y === 'number') {
            currentModel.y = settings.y;
        }

        if (settings.anchor && typeof settings.anchor.x === 'number' && typeof settings.anchor.y === 'number' && currentModel.anchor) {
            currentModel.anchor.set(settings.anchor.x, settings.anchor.y);
        }

        return true;
    } catch (error) {
        console.warn("⚠️ モデル設定適用失敗:", error);
        return false;
    }
}

window.updateModelSettings = function(settings) {
    // 🔍 絶対に出力される確実なログ
    const logData = {
        settings: settings,
        before: currentModel ? {
            scale: currentModel.scale.x,
            x: currentModel.x,
            y: currentModel.y
        } : null
    };
    
    // Pythonに送信（確実に見える）
    fetch('http://127.0.0.1:' + window.location.port + '/debug_log', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({type: 'updateModelSettings', data: logData})
    }).catch(() => {});
    
    if (!currentModel) return;
    
    try {
        // 🔍 変更前の位置を記録
        console.log('📍 変更前:', {
            scale: currentModel.scale.x,
            x: currentModel.x,
            y: currentModel.y
        });
        
        // ---- スケール更新 ----
        if (settings.scale !== undefined) {
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

        const baseX = window.innerWidth / 2;
        const baseY = viewHeight * 0.9;

        const padding = viewHeight * 0.2;
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
        
        // 🔍 変更後の位置を記録
        console.log('📍 変更後:', {
            scale: currentModel.scale.x,
            x: currentModel.x,
            y: currentModel.y
        });

    } catch (e) {
        console.error("モデル設定更新エラー:", e);
    }
};

window.addEventListener('resize', () => {
    if (app && app.renderer) {
        app.renderer.resize(window.innerWidth, window.innerHeight);
        
        // 🔧 修正：モデルの位置は維持し、レンダラーのサイズだけ変更
        // currentModel の位置やスケールは変更しない
        console.log('🔄 ウィンドウリサイズ：モデル位置は維持');
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

window.getLive2DParameters = function() {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return [];
        }
        
        const parameters = [];
        const internalModel = currentModel.internalModel;
        
        if (!internalModel || !internalModel.coreModel) {
            console.warn("⚠️ コアモデルにアクセスできません");
            return [];
        }
        
        const coreModel = internalModel.coreModel;
        
        // 🔥 修正：Live2D Cubism SDK 5.x用のアクセス方法
        const model = coreModel._model;  // 内部モデルオブジェクトを取得
        
        if (!model) {
            console.warn("⚠️ 内部モデルが見つかりません");
            return [];
        }
        
        // パラメータ数を取得
        const paramCount = model.parameters ? model.parameters.count : 0;
        console.log(`📋 パラメータ総数: ${paramCount}個`);
        
        if (paramCount === 0) {
            console.warn("⚠️ パラメータが0個です");
            return [];
        }
        
        // 各パラメータ情報を取得
        for (let i = 0; i < paramCount; i++) {
            try {
                const paramId = model.parameters.ids[i];
                const currentValue = model.parameters.values[i];
                const defaultValue = model.parameters.defaultValues ? model.parameters.defaultValues[i] : 0;
                const minValue = model.parameters.minimumValues ? model.parameters.minimumValues[i] : -10;
                const maxValue = model.parameters.maximumValues ? model.parameters.maximumValues[i] : 10;
                
                parameters.push({
                    id: paramId,
                    index: i,
                    currentValue: currentValue,
                    defaultValue: defaultValue,
                    minValue: minValue,
                    maxValue: maxValue
                });
                
            } catch (e) {
                console.warn(`⚠️ パラメータ ${i} 取得失敗:`, e);
            }
        }
        
        console.log(`✅ パラメータ取得成功: ${parameters.length}個`);
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

// =============================================================================
// 🔥 追加：シンプルリップシンク関数群（main.jsの最後に追加）
// =============================================================================

// assets/live2d_dist/main.js の window.startSimpleLipSync 関数を置き換えてください

/**
 * シンプルなリップシンク開始（表示リセット完全防止版）
 * @param {Object} lipSyncData - シンプルなリップシンクデータ
 * @returns {boolean} 成功時true
 */
window.startSimpleLipSync = function(lipSyncData) {
    try {
        debugger; // ★★★ この一行を追加してください ★★★

        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }

        // 既存のアニメーションループが動いていれば、静かに停止させる
        if (window.currentSimpleLipSync) {
            window.currentSimpleLipSync.isActive = false;
        }
        
        // --- ★★★ これが最後の修正点です ★★★ ---
        // 表示リセットの原因となっていた stopLipSync() と、
        // それに伴う位置の保存・復元処理を完全に削除します。
        
        if (lipSyncData.frames && lipSyncData.frames.length > 0) {
            // 新しいリップシンクデータでグローバル変数を上書き
            window.currentSimpleLipSync = {
                data: lipSyncData,
                startTime: Date.now() / 1000,
                isActive: true
            };
            
            // 新しいデータでアニメーションループを開始
            window.runSimpleLipSyncLoop();
            
            console.log(`✅ 表示を維持したままリップシンク開始: ${lipSyncData.frames.length}フレーム`);
            return true;
        } else {
            console.warn("⚠️ フレームデータがありません");
            return false;
        }

    } catch (error) {
        console.error("❌ シンプルリップシンク開始エラー:", error);
        return false;
    }
};

/**
 * シンプルリップシンクアニメーションループ
 */
window.runSimpleLipSyncLoop = function() {
    if (!window.currentSimpleLipSync || !window.currentSimpleLipSync.isActive) {
        return;
    }
    
    try {
        const lipSync = window.currentSimpleLipSync;
        const currentTime = Date.now() / 1000;
        const elapsedTime = currentTime - lipSync.startTime;
        
        // 現在時刻のフレームを検索
        const activeFrame = lipSync.data.frames.find(frame => 
            frame.time <= elapsedTime && 
            elapsedTime < (frame.time + frame.duration)
        );
        
        if (activeFrame) {
            // 🔥 音素に基づいてパラメータ設定
            const params = window.getVowelParameters(activeFrame.vowel, activeFrame.intensity);
            window.setLive2DParametersDirect(params);
        } else {
            // 口を閉じる
            window.setLive2DParametersDirect({
                'ParamMouthOpenY': 0.0,
                'ParamMouthForm': 0.0
            });
        }
        
        // 終了判定
        if (elapsedTime > lipSync.data.duration + 0.2) {
            window.stopSimpleLipSync();
            return;
        }
        
        // 次のフレーム
        requestAnimationFrame(window.runSimpleLipSyncLoop);
        
    } catch (error) {
        console.error("⚠️ シンプルリップシンクループエラー:", error);
        window.stopSimpleLipSync();
    }
};

/**
 * 🔥 音素から Live2D パラメータを取得（0-1範囲）
 * @param {string} vowel - 母音 ('a', 'i', 'u', 'e', 'o', 'n')
 * @param {number} intensity - 強度 (0.0-1.0)
 * @returns {Object} Live2Dパラメータ
 */
window.getVowelParameters = function(vowel, intensity = 1.0) {
    // 🔥 グローバル設定から取得（Python側で設定済み）
    const settings = window.lipSyncSettings || {};
    const vowelSettings = settings.vowels || {};
    
    // デフォルト値（Python側の正規化後の値）
    const defaultVowels = {
        'a': { open: 0.75, form: 0.0 },    // 150/200 = 0.75
        'i': { open: 0.225, form: -0.75 }, // 45/200, -150/200
        'u': { open: 0.3, form: -0.525 },  // 60/200, -105/200
        'e': { open: 0.45, form: -0.225 }, // 90/200, -45/200
        'o': { open: 0.6, form: 0.525 },   // 120/200, 105/200
        'n': { open: 0.075, form: 0.0 },   // 15/200, 0/200
        'sil': { open: 0.0, form: 0.0 }
    };
    
    // 設定値または デフォルト値を使用
    const vowelData = vowelSettings[vowel] || defaultVowels[vowel] || defaultVowels['sil'];
    
    // 強度とスケールを適用
    const scale = (settings.mouth_scale || 1.0) * intensity;
    
    const params = {
        'ParamMouthOpenY': vowelData.open * scale,
        'ParamMouthForm': vowelData.form * scale
    };
    
    console.log(`🗣️ ${vowel}: 開き${params.ParamMouthOpenY.toFixed(3)}, 形${params.ParamMouthForm.toFixed(3)}`);
    return params;
};

/**
 * 複数のLive2Dパラメータを一括設定（Cubism 2.x/3.x/4.x対応版）
 * @param {Object} parameters - パラメータの連想配列 { 'ParamAngleX': 0.5, 'ParamMouthOpenY': 0.8, ... }
 * @returns {boolean} 成功時true
 */
window.setLive2DParameters = function(parameters) {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }
        
        let successCount = 0;
        const coreModel = currentModel.internalModel?.coreModel;
        
        if (coreModel) {
            Object.keys(parameters).forEach(paramId => {
                try {
                    const paramIndex = coreModel.getParameterIndex(paramId);
                    if (paramIndex >= 0) {
                        const value = parameters[paramId];
                        
                        // 🔥 Cubism 2.x/3.x/4.x 両対応：APIの存在チェック
                        let clampedValue = value;
                        
                        // 新しいSDK（Cubism 3.x/4.x）の場合のみ範囲チェック
                        if (typeof coreModel.getParameterMinValueByIndex === 'function' &&
                            typeof coreModel.getParameterMaxValueByIndex === 'function') {
                            const minValue = coreModel.getParameterMinValueByIndex(paramIndex);
                            const maxValue = coreModel.getParameterMaxValueByIndex(paramIndex);
                            clampedValue = Math.max(minValue, Math.min(maxValue, value));
                        }
                        
                        coreModel.setParameterValueByIndex(paramIndex, clampedValue);
                        successCount++;
                    } else {
                        // 代替パラメータを試す
                        const alternatives = window.getAlternativeParamNames(paramId);
                        let found = false;
                        for (const altName of alternatives) {
                            const altIndex = coreModel.getParameterIndex(altName);
                            if (altIndex >= 0) {
                                const value = parameters[paramId];
                                
                                // 新しいSDKの場合のみ範囲チェック
                                let clampedValue = value;
                                if (typeof coreModel.getParameterMinValueByIndex === 'function' &&
                                    typeof coreModel.getParameterMaxValueByIndex === 'function') {
                                    const minValue = coreModel.getParameterMinValueByIndex(altIndex);
                                    const maxValue = coreModel.getParameterMaxValueByIndex(altIndex);
                                    clampedValue = Math.max(minValue, Math.min(maxValue, value));
                                }
                                
                                coreModel.setParameterValueByIndex(altIndex, clampedValue);
                                console.log(`🔄 代替パラメータ使用: ${paramId} → ${altName}`);
                                successCount++;
                                found = true;
                                break;
                            }
                        }
                        if (!found) {
                            console.warn(`⚠️ パラメータが見つかりません: ${paramId}`);
                        }
                    }
                } catch (e) {
                    console.warn(`⚠️ パラメータ設定失敗 ${paramId}:`, e);
                }
            });
        }
        
        console.log(`🎨 パラメータ一括設定完了: ${successCount}/${Object.keys(parameters).length}個`);
        return successCount > 0;
        
    } catch (error) {
        console.error("❌ パラメータ一括設定エラー:", error);
        return false;
    }
};

/**
 * 代替パラメータ名を取得
 * @param {string} paramId - 元のパラメータID
 * @returns {Array} 代替パラメータ名配列
 */
window.getAlternativeParamNames = function(paramId) {
    const alternatives = {
        'ParamMouthOpenY': [
            'PARAM_MOUTH_OPEN_Y', 'MouthOpenY', 'Mouth_Open_Y', 
            'mouth_open_y', '口開き', 'ParamMouthOpen'
        ],
        'ParamMouthForm': [
            'PARAM_MOUTH_FORM', 'MouthForm', 'Mouth_Form',
            'mouth_form', '口の形', 'ParamMouthShape'
        ],
        'ParamMouthOpenX': [
            'PARAM_MOUTH_OPEN_X', 'MouthOpenX', 'Mouth_Open_X',
            'mouth_open_x', 'ParamMouthWidth'
        ]
    };
    
    return alternatives[paramId] || [];
};

/**
 * ⚡ 位置保護状態でも口パラメータを優先して直接適用するユーティリティ
 * @param {Object} parameters - 適用するパラメータの連想配列
 * @returns {boolean} 成功時 true
 */
window.setLive2DParametersDirect = function(parameters) {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }

        const coreModel = currentModel.internalModel?.coreModel;
        if (!coreModel) {
            console.warn("⚠️ コアモデルにアクセスできません");
            return false;
        }

        const shouldApplyParam = (paramId) => {
            if (!isPositionProtected) {
                return true;
            }
            const id = paramId.toLowerCase();
            return id.includes('mouth') || id.includes('lip') || id.includes('口');
        };

        let successCount = 0;
        Object.entries(parameters).forEach(([paramId, value]) => {
            if (!shouldApplyParam(paramId)) {
                return;
            }

            const applyValueToIndex = (index) => {
                let clampedValue = value;
                if (typeof coreModel.getParameterMinValueByIndex === 'function' &&
                    typeof coreModel.getParameterMaxValueByIndex === 'function') {
                    const minValue = coreModel.getParameterMinValueByIndex(index);
                    const maxValue = coreModel.getParameterMaxValueByIndex(index);
                    clampedValue = Math.max(minValue, Math.min(maxValue, value));
                }
                coreModel.setParameterValueByIndex(index, clampedValue);
                successCount++;
            };

            try {
                const paramIndex = coreModel.getParameterIndex(paramId);
                if (paramIndex >= 0) {
                    applyValueToIndex(paramIndex);
                    return;
                }

                const alternatives = window.getAlternativeParamNames(paramId);
                for (const altName of alternatives) {
                    const altIndex = coreModel.getParameterIndex(altName);
                    if (altIndex >= 0) {
                        applyValueToIndex(altIndex);
                        console.log(`🔄 代替パラメータ使用(Direct): ${paramId} → ${altName}`);
                        return;
                    }
                }

                console.warn(`⚠️ パラメータが見つかりません(Direct): ${paramId}`);
            } catch (error) {
                console.warn(`⚠️ パラメータ直接設定失敗 ${paramId}:`, error);
            }
        });

        if (typeof currentModel.update === 'function') {
            currentModel.update(0);
        }

        return successCount > 0;

    } catch (error) {
        console.error("❌ パラメータ直接設定エラー:", error);
        return false;
    }
};


/**
 * シンプルリップシンクを停止
 * @returns {boolean} 成功時true
 */
window.stopSimpleLipSync = function() {
    try {
        if (window.currentSimpleLipSync) {
            window.currentSimpleLipSync.isActive = false;
            window.currentSimpleLipSync = null;
        }
        
        // 口をリセット
        window.setLive2DParametersDirect({
            'ParamMouthOpenY': 0.0,
            'ParamMouthForm': 0.0
        });
        
        console.log("⏹️ シンプルリップシンク停止");
        return true;
        
    } catch (error) {
        console.error("❌ シンプルリップシンク停止エラー:", error);
        return false;
    }
};

/**
 * シンプルリップシンクテスト開始
 * @param {Object} testData - テストデータ
 * @returns {boolean} 成功時true
 */
window.startSimpleLipSyncTest = function(testData) {
    try {
        console.log("🧪 シンプルリップシンクテスト開始:", testData);
        
        // 通常のシンプルリップシンクを使用
        return window.startSimpleLipSync(testData);
        
    } catch (error) {
        console.error("❌ シンプルテスト開始エラー:", error);
        return false;
    }
};

/**
 * 基本的なリップシンクテスト（フォールバック）
 * @param {Object} testData - テストデータ
 * @returns {boolean} 成功時true
 */
window.testBasicLipSync = function(testData) {
    try {
        console.log("🔧 基本リップシンクテスト:", testData);
        
        if (!currentModel) {
            console.warn("⚠️ モデル未読み込み");
            return false;
        }
        
        // 🔥 段階的テスト実行
        let testIndex = 0;
        const testVowels = ['a', 'i', 'u', 'e', 'o'];
        
        const runStepTest = () => {
            if (testIndex >= testVowels.length) {
                // テスト完了：口をリセット
                window.setLive2DParametersDirect({
                    'ParamMouthOpenY': 0.0,
                    'ParamMouthForm': 0.0
                });
                console.log("✅ 基本テスト完了");
                return;
            }
            
            const vowel = testVowels[testIndex];
            const params = window.getVowelParameters(vowel, 0.8);
            window.setLive2DParametersDirect(params);
            
            console.log(`🔤 テスト: ${vowel} - ${JSON.stringify(params)}`);
            testIndex++;
            
            // 500ms後に次のテスト
            setTimeout(runStepTest, 500);
        };
        
        // テスト開始
        runStepTest();
        return true;
        
    } catch (error) {
        console.error("❌ 基本テストエラー:", error);
        return false;
    }
};

/**
 * リップシンクテストを停止
 */
window.stopLipSyncTest = function() {
    try {
        // シンプルリップシンクを停止
        window.stopSimpleLipSync();
        
        // 従来のリップシンクも停止
        if (typeof window.stopLipSync === 'function') {
            window.stopLipSync();
        }
        
        console.log("🛑 全リップシンクテスト停止");
        return true;
        
    } catch (error) {
        console.error("❌ テスト停止エラー:", error);
        return false;
    }
};

/**
 * 🔍 デバッグ用：現在のパラメータ値を表示
 */
window.debugCurrentParameters = function() {
    if (!currentModel) {
        console.log("❌ モデル未読み込み");
        return;
    }
    
    try {
        const coreModel = currentModel.internalModel?.coreModel;
        if (coreModel) {
            const mouthParams = ['ParamMouthOpenY', 'ParamMouthForm', 'ParamMouthOpenX'];
            const values = {};
            
            mouthParams.forEach(paramId => {
                const paramIndex = coreModel.getParameterIndex(paramId);
                if (paramIndex >= 0) {
                    values[paramId] = coreModel.getParameterValueByIndex(paramIndex);
                }
            });
            
            console.log("🔍 現在の口パラメータ:", values);
            return values;
        }
    } catch (error) {
        console.error("❌ デバッグ取得エラー:", error);
    }
    
    return null;
};

// 🔥 グローバル変数初期化
window.currentSimpleLipSync = null;
window.lipSyncSettings = window.lipSyncSettings || {};

console.log("✅ シンプルリップシンク関数群を追加しました");

/**
 * 全パラメータをデフォルト値にリセット（Cubism 2.x/3.x/4.x対応版）
 * @returns {boolean} 成功時true
 */
window.resetAllParameters = function() {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }
        
        const coreModel = currentModel.internalModel?.coreModel;
        if (!coreModel) {
            console.warn("⚠️ コアモデルにアクセスできません");
            return false;
        }
        
        const paramCount = coreModel.getParameterCount();
        let resetCount = 0;
        
        for (let i = 0; i < paramCount; i++) {
            try {
                // 🔥 新しいSDKの場合のみデフォルト値を取得
                let defaultValue = 0; // フォールバック値
                
                if (typeof coreModel.getParameterDefaultValueByIndex === 'function') {
                    defaultValue = coreModel.getParameterDefaultValueByIndex(i);
                }
                
                coreModel.setParameterValueByIndex(i, defaultValue);
                resetCount++;
            } catch (e) {
                console.warn(`⚠️ パラメータ ${i} のリセット失敗:`, e);
            }
        }
        
        console.log(`🔄 全パラメータリセット完了: ${resetCount}個`);
        return true;
        
    } catch (error) {
        console.error("❌ 全パラメータリセットエラー:", error);
        return false;
    }
};

/**
 * 特定のパラメータグループをリセット
 * @param {string} groupName - グループ名 ('angle', 'eye', 'brow', 'mouth', 'body')
 * @returns {boolean} 成功時true
 */
window.resetParameterGroup = function(groupName) {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return false;
        }
        
        const groupPatterns = {
            'angle': ['Angle'],
            'eye': ['Eye'],
            'brow': ['Brow'],
            'mouth': ['Mouth'],
            'body': ['Body', 'Breath']
        };
        
        const patterns = groupPatterns[groupName.toLowerCase()];
        if (!patterns) {
            console.warn(`⚠️ 不明なグループ名: ${groupName}`);
            return false;
        }
        
        const coreModel = currentModel.internalModel?.coreModel;
        if (!coreModel) {
            return false;
        }
        
        const paramCount = coreModel.getParameterCount();
        let resetCount = 0;
        
        for (let i = 0; i < paramCount; i++) {
            try {
                const paramId = coreModel.getParameterId(i);
                const matchesGroup = patterns.some(pattern => paramId.includes(pattern));
                
                if (matchesGroup) {
                    const defaultValue = coreModel.getParameterDefaultValueByIndex(i);
                    coreModel.setParameterValueByIndex(i, defaultValue);
                    resetCount++;
                }
            } catch (e) {
                console.warn(`⚠️ パラメータ ${i} のリセット失敗:`, e);
            }
        }
        
        console.log(`🔄 ${groupName}グループリセット完了: ${resetCount}個`);
        return true;
        
    } catch (error) {
        console.error(`❌ ${groupName}グループリセットエラー:`, error);
        return false;
    }
};

/**
 * パラメータの現在値・最小値・最大値・デフォルト値を取得（Cubism 2.x/3.x/4.x対応版）
 * @param {string} paramId - パラメータID
 * @returns {Object|null} パラメータ情報
 */
window.getParameterInfo = function(paramId) {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return null;
        }
        
        const coreModel = currentModel.internalModel?.coreModel;
        if (!coreModel) {
            return null;
        }
        
        const paramIndex = coreModel.getParameterIndex(paramId);
        if (paramIndex < 0) {
            console.warn(`⚠️ パラメータが見つかりません: ${paramId}`);
            return null;
        }
        
        const info = {
            id: paramId,
            index: paramIndex,
            currentValue: coreModel.getParameterValueByIndex(paramIndex)
        };
        
        // 🔥 新しいSDK（Cubism 3.x/4.x）の場合のみ追加情報を取得
        if (typeof coreModel.getParameterDefaultValueByIndex === 'function') {
            info.defaultValue = coreModel.getParameterDefaultValueByIndex(paramIndex);
        }
        
        if (typeof coreModel.getParameterMinValueByIndex === 'function') {
            info.minValue = coreModel.getParameterMinValueByIndex(paramIndex);
        }
        
        if (typeof coreModel.getParameterMaxValueByIndex === 'function') {
            info.maxValue = coreModel.getParameterMaxValueByIndex(paramIndex);
        }
        
        return info;
        
    } catch (error) {
        console.error(`❌ パラメータ情報取得エラー (${paramId}):`, error);
        return null;
    }
};

/**
 * 全パラメータの現在値を取得
 * @returns {Object} 全パラメータの現在値
 */
window.getCurrentParameters = function() {
    try {
        if (!currentModel) {
            console.warn("⚠️ モデルが読み込まれていません");
            return {};
        }
        
        const coreModel = currentModel.internalModel?.coreModel;
        if (!coreModel) {
            return {};
        }
        
        const paramCount = coreModel.getParameterCount();
        const parameters = {};
        
        for (let i = 0; i < paramCount; i++) {
            try {
                const paramId = coreModel.getParameterId(i);
                const currentValue = coreModel.getParameterValueByIndex(i);
                parameters[paramId] = currentValue;
            } catch (e) {
                console.warn(`⚠️ パラメータ ${i} の取得失敗:`, e);
            }
        }
        
        return parameters;
        
    } catch (error) {
        console.error("❌ 全パラメータ取得エラー:", error);
        return {};
    }
};
// =============================================================================
// 📸 スクリーンショット連射機能
// =============================================================================

/**
 * スクショ連射を開始（Live2Dモデル全身・高解像度・背景透過PNG）
 * @param {number} intervalMs - 撮影間隔（ミリ秒）
 * @param {number} totalFrames - 撮影枚数
 * @returns {boolean} 成功時true
 */
window.startScreenshotBurst = function(intervalMs, totalFrames) {
    try {
        console.log(`📸 スクショ連射開始: ${totalFrames}枚、${intervalMs}ms間隔`);
        
        if (!currentModel) {
            console.error("❌ Live2Dモデルが読み込まれていません");
            return false;
        }
        
        if (typeof qt === 'undefined' || !qt.webChannelTransport) {
            console.error("❌ QWebChannelが初期化されていません");
            return false;
        }
        
        if (window.screenshotBurstTimer) {
            clearInterval(window.screenshotBurstTimer);
            window.screenshotBurstTimer = null;
        }
        
        let frameCount = 0;
        
        // 🔥 現在のモデル設定を保存
        const originalParent = currentModel.parent;
        const originalX = currentModel.x;
        const originalY = currentModel.y;
        const originalScaleX = currentModel.scale.x;
        const originalScaleY = currentModel.scale.y;
        const originalAnchorX = currentModel.anchor.x;
        const originalAnchorY = currentModel.anchor.y;
        
        // 🔥 モデルのバウンディングボックスを取得（現在のスケール含む）
        const bounds = currentModel.getBounds();
        
        // 🔥 出力サイズを決定（4000px基準）
        const targetSize = 4000;
        const aspectRatio = bounds.width / bounds.height;
        let outputWidth, outputHeight;
        
        if (aspectRatio > 1) {
            outputWidth = targetSize;
            outputHeight = Math.ceil(targetSize / aspectRatio);
        } else {
            outputHeight = targetSize;
            outputWidth = Math.ceil(targetSize * aspectRatio);
        }
        
        console.log(`📏 モデルサイズ: ${Math.ceil(bounds.width)}x${Math.ceil(bounds.height)}px`);
        console.log(`📏 出力サイズ: ${outputWidth}x${outputHeight}px`);
        
        // 連射タイマー
        window.screenshotBurstTimer = setInterval(() => {
            try {
                // 🔥 高解像度の一時canvasを作成
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = outputWidth;
                tempCanvas.height = outputHeight;
                
                // 🔥 一時レンダラーを作成
                const tempRenderer = new PIXI.Renderer({
                    width: outputWidth,
                    height: outputHeight,
                    backgroundAlpha: 0,
                    antialias: true,
                    resolution: 1,
                    view: tempCanvas
                });
                
                // 🔥 一時ステージを作成
                const tempStage = new PIXI.Container();
                
                // 🔥 モデルを一時ステージに移動
                tempStage.addChild(currentModel);
                
                // 🔥 モデルを中央配置
                currentModel.anchor.set(0.5, 0.5);
                currentModel.x = outputWidth / 2;
                currentModel.y = outputHeight / 2;
                
                // 🔥 モデルサイズに合わせてスケール調整
                const scaleX = (outputWidth * 0.95) / bounds.width;
                const scaleY = (outputHeight * 0.95) / bounds.height;
                const scale = Math.min(scaleX, scaleY);
                
                currentModel.scale.set(originalScaleX * scale, originalScaleY * scale);
                
                // レンダリング
                tempRenderer.render(tempStage);
                
                // 🔥 元の状態に戻す
                if (originalParent) {
                    originalParent.addChild(currentModel);
                }
                currentModel.x = originalX;
                currentModel.y = originalY;
                currentModel.scale.set(originalScaleX, originalScaleY);
                currentModel.anchor.set(originalAnchorX, originalAnchorY);
                
                // PNG変換
                const dataURL = tempCanvas.toDataURL('image/png');
                
                // 🔥 一時レンダラーを破棄
                tempRenderer.destroy(true);
                
                // Python側に送信
                if (window.recording_backend && typeof window.recording_backend.receiveFrame === 'function') {
                    window.recording_backend.receiveFrame(dataURL);
                    frameCount++;
                    
                    if (frameCount % 10 === 0) {
                        console.log(`  ✓ [${frameCount}/${totalFrames}] 送信完了 (${outputWidth}x${outputHeight}px)`);
                    }
                } else {
                    console.error("❌ recording_backendが見つかりません");
                    clearInterval(window.screenshotBurstTimer);
                    window.screenshotBurstTimer = null;
                    return;
                }
                
                if (frameCount >= totalFrames) {
                    console.log(`✅ スクショ連射完了: ${frameCount}枚送信 (${outputWidth}x${outputHeight}px)`);
                    clearInterval(window.screenshotBurstTimer);
                    window.screenshotBurstTimer = null;
                }
                
            } catch (error) {
                console.error("❌ スクショ撮影エラー:", error);
                
                // エラー時も元に戻す
                if (originalParent) {
                    originalParent.addChild(currentModel);
                }
                currentModel.x = originalX;
                currentModel.y = originalY;
                currentModel.scale.set(originalScaleX, originalScaleY);
                currentModel.anchor.set(originalAnchorX, originalAnchorY);
                
                clearInterval(window.screenshotBurstTimer);
                window.screenshotBurstTimer = null;
            }
        }, intervalMs);
        
        console.log("✅ スクショ連射タイマー起動");
        return true;
        
    } catch (error) {
        console.error("❌ スクショ連射開始エラー:", error);
        return false;
    }
};

window.stopScreenshotBurst = function() {
    try {
        if (window.screenshotBurstTimer) {
            clearInterval(window.screenshotBurstTimer);
            window.screenshotBurstTimer = null;
            console.log("⏹️ スクショ連射停止");
            return true;
        }
        return false;
    } catch (error) {
        console.error("❌ スクショ連射停止エラー:", error);
        return false;
    }
};

window.takeScreenshot = function() {
    try {
        if (!app || !app.renderer) {
            console.error("❌ PIXIアプリが初期化されていません");
            return null;
        }
        
        const captureCanvas = app.renderer.extract.canvas(app.stage);
        
        if (!captureCanvas) {
            console.error("❌ canvasの抽出に失敗");
            return null;
        }
        
        const dataURL = captureCanvas.toDataURL('image/png');
        console.log("📸 スクショ取得成功");
        return dataURL;
        
    } catch (error) {
        console.error("❌ スクショ取得エラー:", error);
        return null;
    }
};

window.screenshotBurstTimer = null;

console.log("✅ スクリーンショット連射機能を追加しました");