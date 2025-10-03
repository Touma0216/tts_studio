// assets/live2d_dist/modeling/drag_controller.js
// ドラッグ操作：キャンバスドラッグで角度X/Y制御（修正版：解放後リセット対応）

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
        
        // 🔥 追加：リセットアニメーション用
        this.isResetting = false;
        this.resetAnimationId = null;
        this.resetSpeed = 0.15; // リセット速度（0.1 = ゆっくり、0.3 = 速い）
        
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
        if (!this.enabled || !window.currentModelForDebug) {
            return;
        }

        // 🔥 追加：リセットアニメーション中の場合は停止
        if (this.isResetting) {
            this.stopResetAnimation();
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
        }

        // 位置を更新
        this.lastX = event.clientX;
        this.lastY = event.clientY;
    }

    /**
     * マウス解放時（🔥 修正：リセットアニメーション追加）
     */
    onMouseUp(event) {
        if (!this.enabled) {
            return;
        }

        if (this.isDragging) {
            console.log('🎯 ドラッグ終了 → 正面にリセット開始');
            
            // 🔥 追加：ドラッグ解放後に滑らかに正面に戻る
            this.startResetAnimation();
        }

        this.isDragging = false;

        if (this.canvas) {
            this.canvas.style.cursor = 'grab';
        }
    }

    /**
     * 🔥 追加：リセットアニメーション開始
     */
    startResetAnimation() {
        // 既にリセット中の場合は何もしない
        if (this.isResetting) {
            return;
        }

        this.isResetting = true;
        this.animateReset();
    }

    /**
     * 🔥 追加：リセットアニメーションのフレーム処理
     */
    animateReset() {
        if (!this.isResetting) {
            return;
        }

        // 目標値（正面）に向かって徐々に近づける
        const targetX = 0;
        const targetY = 0;

        // イージング（徐々に減速）
        this.currentAngleX += (targetX - this.currentAngleX) * this.resetSpeed;
        this.currentAngleY += (targetY - this.currentAngleY) * this.resetSpeed;

        // Live2Dに反映
        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamAngleX', this.currentAngleX);
            window.setLive2DParameter('ParamAngleY', this.currentAngleY);
        }

        // 十分に0に近づいたら終了（誤差0.1度以下）
        const distanceFromZero = Math.sqrt(
            this.currentAngleX * this.currentAngleX + 
            this.currentAngleY * this.currentAngleY
        );

        if (distanceFromZero < 0.1) {
            // 完全に0にして終了
            this.currentAngleX = 0;
            this.currentAngleY = 0;
            
            if (window.setLive2DParameter) {
                window.setLive2DParameter('ParamAngleX', 0);
                window.setLive2DParameter('ParamAngleY', 0);
            }

            this.stopResetAnimation();
            console.log('✅ 正面リセット完了');
            return;
        }

        // 次のフレームを予約
        this.resetAnimationId = requestAnimationFrame(() => this.animateReset());
    }

    /**
     * 🔥 追加：リセットアニメーション停止
     */
    stopResetAnimation() {
        this.isResetting = false;
        
        if (this.resetAnimationId) {
            cancelAnimationFrame(this.resetAnimationId);
            this.resetAnimationId = null;
        }
    }

    /**
     * 現在の角度をリセット（即座に0に戻す）
     */
    resetAngles() {
        // アニメーション中の場合は停止
        this.stopResetAnimation();

        this.currentAngleX = 0;
        this.currentAngleY = 0;

        if (window.setLive2DParameter) {
            window.setLive2DParameter('ParamAngleX', 0);
            window.setLive2DParameter('ParamAngleY', 0);
        }

        console.log('↺ 角度リセット（即座）');
    }

    /**
     * 感度を設定
     */
    setSensitivity(value) {
        this.sensitivity = Math.max(0.1, Math.min(1.0, value));
    }

    /**
     * 最大角度を設定
     */
    setMaxAngle(value) {
        this.maxAngle = Math.max(10, Math.min(90, value));
        console.log(`📐 最大角度: ${this.maxAngle}°`);
    }

    /**
     * 🔥 追加：リセット速度を設定
     * @param {number} speed - リセット速度（0.05〜0.5）
     */
    setResetSpeed(speed) {
        this.resetSpeed = Math.max(0.05, Math.min(0.5, speed));
        console.log(`⚡ リセット速度: ${this.resetSpeed.toFixed(2)}`);
    }

    /**
     * クリーンアップ
     */
    destroy() {
        // リセットアニメーションを停止
        this.stopResetAnimation();

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
window.setDragResetSpeed = (speed) => window.dragController.setResetSpeed(speed); // 🔥 追加

console.log('✅ drag_controller.js 読み込み完了（問題2修正版）');