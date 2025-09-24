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
        
        const modelBounds = currentModel.getBounds();
        const scaleX = (window.innerWidth * 0.9) / modelBounds.width;
        const scaleY = (window.innerHeight * 0.9) / modelBounds.height;
        const scale = Math.min(scaleX, scaleY);
        
        currentModel.scale.set(scale);
        currentModel.anchor.set(0.5, 1.0);
        currentModel.x = window.innerWidth / 2;
        currentModel.y = window.innerHeight * 0.9;
        
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

window.addEventListener('error', (event) => {
    console.error("JavaScript Error:", event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error("Unhandled Promise Rejection:", event.reason);
});

initialize();