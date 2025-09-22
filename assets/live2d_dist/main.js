import * as PIXI from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display';

// PIXIをグローバルスコープに公開
window.PIXI = PIXI;

let app;
let currentModel;

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
    
    console.log("✅ Live2D Viewer Initialized.");
}

window.loadLive2DModel = async function(modelJsonPath) {
    try {
        console.log("モデル読み込み開始:", modelJsonPath);
        
        if (currentModel) {
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
        
        // 初期配置：頭から足まで適切に表示
        const modelBounds = currentModel.getBounds();
        
        // 画面の90%を使用して全身を表示
        const scaleX = (window.innerWidth * 0.9) / modelBounds.width;
        const scaleY = (window.innerHeight * 0.9) / modelBounds.height;
        const scale = Math.min(scaleX, scaleY);
        
        currentModel.scale.set(scale);
        currentModel.anchor.set(0.5, 1.0);  // 足元基準
        currentModel.x = window.innerWidth / 2;
        currentModel.y = window.innerHeight * 0.9;  // 足元を画面下部90%位置に
        
        console.log("モデル配置完了 - サイズ:", currentModel.width, "x", currentModel.height, "スケール:", scale);
        return true;
        
    } catch (e) {
        console.error("❌ モデル読み込みエラー:", e);
        console.error("エラー詳細:", e.message);
        console.error("スタック:", e.stack);
        return false;
    }
};

window.setLipSyncValue = function(volume) {
    if (currentModel && currentModel.internalModel) {
        try {
            // より自然な音量処理
            const normalizedVolume = Math.max(0, Math.min(1.0, volume * 0.8));
            
            // スムーズ補間のための減衰
            const smoothedVolume = normalizedVolume * 0.7 + (window.lastLipVolume || 0) * 0.3;
            window.lastLipVolume = smoothedVolume;
            
            // 複数のリップシンクパラメータを試行
            const lipParams = ['ParamMouthOpenY', 'PARAM_MOUTH_OPEN_Y', 'MouthOpenY'];
            for (const param of lipParams) {
                try {
                    currentModel.internalModel.coreModel.setParameterValueById(param, smoothedVolume);
                    break;
                } catch (e) {
                    // 次のパラメータを試行
                }
            }
        } catch (e) {
            console.error("リップシンクエラー:", e);
        }
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
            // ベーススケール（全身表示用）を取得
            const modelBounds = currentModel.getBounds();
            const baseScaleX = (window.innerWidth * 0.9) / (modelBounds.width / currentModel.scale.x);
            const baseScaleY = (window.innerHeight * 0.9) / (modelBounds.height / currentModel.scale.y);
            const baseScale = Math.min(baseScaleX, baseScaleY);
            
            if (settings.scale !== undefined) {
                // 80%-300%対応：適切なズーム範囲
                currentModel.scale.set(baseScale * settings.scale);
            }
            if (settings.position_x !== undefined) {
                currentModel.x = window.innerWidth / 2 + (settings.position_x * window.innerWidth / 3);
            }
            if (settings.position_y !== undefined) {
                // 画像表示と同じ座標系：下スライダー→キャラ下移動→顔が見える
                const baseY = window.innerHeight * 0.9;  // 足元基準位置
                const moveRange = window.innerHeight * 0.5;  // 移動範囲を調整
                currentModel.y = baseY + (settings.position_y * moveRange);
            }
        } catch (e) {
            console.error("モデル設定更新エラー:", e);
        }
    }
};

window.setBackgroundVisible = function(visible) {
    if (app && app.renderer) {
        try {
            if (visible) {
                app.renderer.background.color = 0x000000;
                app.renderer.background.alpha = 1;
            } else {
                app.renderer.background.alpha = 0;
            }
        } catch (e) {
            console.error("背景設定エラー:", e);
        }
    }
};

// リサイズ処理
window.addEventListener('resize', () => {
    if (app && app.renderer) {
        app.renderer.resize(window.innerWidth, window.innerHeight);
        
        if (currentModel) {
            // リサイズ時にモデルを再配置（全身表示維持）
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

// エラーハンドリング
window.addEventListener('error', (event) => {
    console.error("JavaScript Error:", event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error("Unhandled Promise Rejection:", event.reason);
});

// 初期化実行
initialize();