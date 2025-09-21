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
        
        // モデルサイズと位置の調整
        const modelBounds = currentModel.getBounds();
        const scaleX = (window.innerWidth * 0.8) / modelBounds.width;
        const scaleY = (window.innerHeight * 0.8) / modelBounds.height;
        const scale = Math.min(scaleX, scaleY);
        
        currentModel.scale.set(scale);
        currentModel.anchor.set(0.5, 0.5);
        currentModel.x = window.innerWidth / 2;
        currentModel.y = window.innerHeight / 2;
        
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
            const clampedVolume = Math.max(0, Math.min(1.0, volume * 1.5));
            // 複数のリップシンクパラメータを試行
            const lipParams = ['ParamMouthOpenY', 'PARAM_MOUTH_OPEN_Y', 'MouthOpenY'];
            for (const param of lipParams) {
                try {
                    currentModel.internalModel.coreModel.setParameterValueById(param, clampedVolume);
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
            if (settings.scale !== undefined) {
                const baseScale = Math.min(window.innerWidth / 800, window.innerHeight / 600);
                currentModel.scale.set(baseScale * settings.scale);
            }
            if (settings.position_x !== undefined) {
                currentModel.x = window.innerWidth / 2 + (settings.position_x * window.innerWidth / 4);
            }
            if (settings.position_y !== undefined) {
                currentModel.y = window.innerHeight / 2 + (settings.position_y * window.innerHeight / 4);
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
            // リサイズ時にモデルを再配置
            const modelBounds = currentModel.getBounds();
            const scaleX = (window.innerWidth * 0.8) / (modelBounds.width / currentModel.scale.x);
            const scaleY = (window.innerHeight * 0.8) / (modelBounds.height / currentModel.scale.y);
            const scale = Math.min(scaleX, scaleY);
            
            currentModel.scale.set(scale);
            currentModel.x = window.innerWidth / 2;
            currentModel.y = window.innerHeight / 2;
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