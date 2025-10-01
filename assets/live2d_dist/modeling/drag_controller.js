// assets/live2d_dist/modeling/drag_controller.js
// ドラッグ操作：キャンバスドラッグで角度X/Y制御（修正版：変数名統一）

class DragController {
    constructor() {
        this.isDragging = false;
        this.lastX = 0;
        this.lastY = 0;
        this.currentAngleX = 0;
        this.currentAngleY = 0;
        this.sensitivity = 0.3; // ドラッグ感度
        this.maxAngle = 30; // 最大角度
        this.enabled = false; // デフォルトは無効
        
        this.canvas = null;
        this.boundMouseDown = this.onMouseDown.bind(this);
        this.boundMouseMove = this.onMouseMove.bind(this);
        this.boundMouseUp = this.onMouseUp.bind(this);
    }

    /**
     * ドラッグ制御を初期化
     */
    init() {
        try {
            // キャンバス要素を取得
            this.canvas = document.querySelector('#live2d-canvas') || 
                         document.querySelector('canvas');
            
            if (!this.canvas) {
                console.warn('⚠️ キャンバスが見つかりません（ドラッグ制御無効）');
                return false;
            }

            // イベントリスナー追加
            this.canvas.addEventListener('mousedown', this.boundMouseDown);
            document.addEventListener('mousemove', this.boundMouseMove);
            document.addEventListener('mouseup', this.boundMouseUp);
            
            console.log('✅ ドラッグ制御初期化完了');
            return true;
        } catch (error) {
            console.error('❌ ドラッグ制御初期化エラー:', error);
            return false;
        }
    }

    /**
     * ドラッグ制御を有効化/無効化
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        if (this.canvas) {
            this.canvas.style.cursor = enabled ? 'grab' : 'default';
        }
        console.log(`🎯 ドラッグ制御: ${enabled ? '有効' : '無効'}`);
    }

    /**
     * マウス押下時
     */
    onMouseDown(event) {
        // 🔥 修正：window.currentModel → window.currentModelForDebug
        if (!this.enabled || !window.currentModelForDebug) {
            return;
        }

        this.isDragging = true;
        this.lastX = event.clientX;
        this.lastY = event.clientY;

        if (this.canvas) {
            this.canvas.style.cursor = 'grabbing';
        }
        
        console.log('🎯 ドラッグ開始');
    }

    /**
     * マウス移動時
     */
    onMouseMove(event) {
        // 🔥 修正：window.currentModel → window.currentModelForDebug
        if (!this.isDragging || !this.enabled || !window.currentModelForDebug) {
            return;
        }

        // マウス移動量を計算
        const deltaX = event.clientX - this.lastX;
        const deltaY = event.clientY - this.lastY;

        // 角度に変換（感度を適用）
        this.currentAngleX += deltaX * this.sensitivity;
        this.currentAngleY -= deltaY * this.sensitivity; // Y軸は反転

        // 角度を範囲内に制限
        this.currentAngleX = Math.max(-this.maxAngle, 
                                      Math.min(this.maxAngle, this.currentAngleX));
        this.currentAngleY = Math.max(-this.maxAngle, 
                                      Math.min(this.maxAngle, this.currentAngleY));

        // Live2Dに反映
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamAngleX', this.currentAngleX);
            window.setLive2DParameter('ParamAngleY', this.currentAngleY);
            console.log(`🎯 角度更新: X=${this.currentAngleX.toFixed(1)}, Y=${this.currentAngleY.toFixed(1)}`);
        }

        // 位置を更新
        this.lastX = event.clientX;
        this.lastY = event.clientY;
    }

    /**
     * マウス解放時
     */
    onMouseUp(event) {
        if (!this.enabled) {
            return;
        }

        if (this.isDragging) {
            console.log('🎯 ドラッグ終了');
        }

        this.isDragging = false;

        if (this.canvas) {
            this.canvas.style.cursor = 'grab';
        }
    }

    /**
     * 現在の角度をリセット
     */
    resetAngles() {
        this.currentAngleX = 0;
        this.currentAngleY = 0;

        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamAngleX', 0);
            window.setLive2DParameter('ParamAngleY', 0);
        }

        console.log('↺ 角度リセット');
    }

    /**
     * 感度を設定
     */
    setSensitivity(value) {
        this.sensitivity = Math.max(0.1, Math.min(1.0, value));
        // ログ削除：スライダー操作で大量に出るため
    }

    /**
     * 最大角度を設定
     */
    setMaxAngle(value) {
        this.maxAngle = Math.max(10, Math.min(90, value));
        console.log(`📐 最大角度: ${this.maxAngle}°`);
    }

    /**
     * クリーンアップ
     */
    destroy() {
        if (this.canvas) {
            this.canvas.removeEventListener('mousedown', this.boundMouseDown);
        }
        document.removeEventListener('mousemove', this.boundMouseMove);
        document.removeEventListener('mouseup', this.boundMouseUp);
        
        console.log('🧹 ドラッグ制御クリーンアップ完了');
    }
}

// グローバルインスタンス作成
window.dragController = new DragController();

// モデル読み込み後に初期化
window.addEventListener('live2d-model-loaded', () => {
    window.dragController.init();
});

// グローバル関数として公開
window.enableDragControl = (enabled) => window.dragController.setEnabled(enabled);
window.resetDragAngles = () => window.dragController.resetAngles();
window.setDragSensitivity = (value) => window.dragController.setSensitivity(value);

console.log('✅ drag_controller.js 読み込み完了');