// assets/live2d_dist/animation_player.js
// Live2Dアニメーション再生エンジン

class AnimationPlayer {
    constructor() {
        this.currentAnimation = null;
        this.isPlaying = false;
        this.startTime = 0;
        this.currentTime = 0;
        this.animationFrameId = null;
        this.loop = false;
        this.speed = 1.0; // 再生速度（1.0 = 通常）
    }

    /**
     * アニメーションを読み込み
     * @param {Object} animationData - JSONアニメーションデータ
     * @returns {boolean} 成功時true
     */
    loadAnimation(animationData) {
        try {
            // バリデーション
            if (!animationData || !animationData.keyframes) {
                console.error('❌ 無効なアニメーションデータ');
                return false;
            }

            if (!Array.isArray(animationData.keyframes) || animationData.keyframes.length === 0) {
                console.error('❌ キーフレームが空です');
                return false;
            }

            // キーフレームを時間順にソート
            animationData.keyframes.sort((a, b) => a.time - b.time);

            this.currentAnimation = animationData;
            this.loop = animationData.loop || false;
            
            console.log(`✅ アニメーション読み込み: ${animationData.metadata?.name || '無名'}`);
            console.log(`   - 時間: ${animationData.metadata?.duration || 0}秒`);
            console.log(`   - キーフレーム数: ${animationData.keyframes.length}`);
            
            return true;

        } catch (error) {
            console.error('❌ アニメーション読み込みエラー:', error);
            return false;
        }
    }

    /**
     * アニメーション再生開始
     * @returns {boolean} 成功時true
     */
    play() {
        if (!this.currentAnimation) {
            console.warn('⚠️ アニメーションが読み込まれていません');
            return false;
        }

        if (this.isPlaying) {
            console.warn('⚠️ 既に再生中です');
            return false;
        }

        this.isPlaying = true;
        this.startTime = Date.now() / 1000;
        this.currentTime = 0;
        
        this.animate();
        
        console.log('▶️ アニメーション再生開始');
        return true;
    }

    /**
     * アニメーション一時停止
     */
    pause() {
        if (!this.isPlaying) return;
        
        this.isPlaying = false;
        
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        
        console.log('⏸️ アニメーション一時停止');
    }

    /**
     * アニメーション停止（最初から）
     */
    stop() {
        this.pause();
        this.currentTime = 0;
        
        // 最初のキーフレームに戻す
        if (this.currentAnimation && this.currentAnimation.keyframes.length > 0) {
            this.applyKeyframe(this.currentAnimation.keyframes[0]);
        }
        
        console.log('⏹️ アニメーション停止');
    }

    /**
     * アニメーションフレーム更新
     */
    animate() {
        if (!this.isPlaying || !this.currentAnimation) {
            return;
        }

        try {
            const now = Date.now() / 1000;
            const elapsed = (now - this.startTime) * this.speed;
            this.currentTime = elapsed;

            const duration = this.currentAnimation.metadata?.duration || 
                           this.currentAnimation.keyframes[this.currentAnimation.keyframes.length - 1].time;

            // ループ処理
            if (this.currentTime >= duration) {
                if (this.loop) {
                    this.currentTime = 0;
                    this.startTime = now;
                } else {
                    this.stop();
                    return;
                }
            }

            // 現在時刻のパラメータを計算して適用
            this.updateParameters(this.currentTime);

        } catch (error) {
            console.error('❌ アニメーション更新エラー:', error);
            this.stop();
            return;
        }

        // 次のフレーム
        this.animationFrameId = requestAnimationFrame(() => this.animate());
    }

    /**
     * 指定時刻のパラメータを計算して適用
     * @param {number} time - 現在時刻（秒）
     */
    updateParameters(time) {
        if (!this.currentAnimation || !window.currentModel) {
            return;
        }

        const keyframes = this.currentAnimation.keyframes;

        // 現在時刻の前後のキーフレームを探す
        let prevFrame = keyframes[0];
        let nextFrame = keyframes[keyframes.length - 1];

        for (let i = 0; i < keyframes.length - 1; i++) {
            if (keyframes[i].time <= time && time < keyframes[i + 1].time) {
                prevFrame = keyframes[i];
                nextFrame = keyframes[i + 1];
                break;
            }
        }

        // 補間計算
        const t = (time - prevFrame.time) / (nextFrame.time - prevFrame.time);
        const easing = nextFrame.easing || 'linear';
        const progress = this.applyEasing(t, easing);

        // 全パラメータを補間して適用
        const parameters = this.interpolateParameters(
            prevFrame.parameters,
            nextFrame.parameters,
            progress
        );

        this.applyParameters(parameters);
    }

    /**
     * 2つのキーフレーム間でパラメータを補間
     * @param {Object} params1 - 開始パラメータ
     * @param {Object} params2 - 終了パラメータ
     * @param {number} t - 補間係数（0.0〜1.0）
     * @returns {Object} 補間されたパラメータ
     */
    interpolateParameters(params1, params2, t) {
        const result = {};

        // params2に存在する全パラメータを処理
        for (const paramId in params2) {
            const value1 = params1[paramId] !== undefined ? params1[paramId] : 0;
            const value2 = params2[paramId];
            
            // 線形補間
            result[paramId] = value1 + (value2 - value1) * t;
        }

        // params1にしかないパラメータも含める
        for (const paramId in params1) {
            if (result[paramId] === undefined) {
                result[paramId] = params1[paramId];
            }
        }

        return result;
    }

    /**
     * イージング関数を適用
     * @param {number} t - 入力値（0.0〜1.0）
     * @param {string} type - イージングタイプ
     * @returns {number} イージング適用後の値（0.0〜1.0）
     */
    applyEasing(t, type) {
        switch (type) {
            case 'linear':
                return t;
            
            case 'ease_in':
                return t * t;
            
            case 'ease_out':
                return t * (2 - t);
            
            case 'ease_in_out':
                return t < 0.5 
                    ? 2 * t * t 
                    : -1 + (4 - 2 * t) * t;
            
            default:
                return t;
        }
    }

    /**
     * パラメータをLive2Dモデルに適用
     * @param {Object} parameters - パラメータ連想配列
     */
    applyParameters(parameters) {
        if (!window.currentModel || !window.setLive2DParameter) {
            return;
        }

        for (const paramId in parameters) {
            window.setLive2DParameter(paramId, parameters[paramId]);
        }
    }

    /**
     * キーフレームを直接適用（補間なし）
     * @param {Object} keyframe - キーフレームオブジェクト
     */
    applyKeyframe(keyframe) {
        if (!keyframe || !keyframe.parameters) return;
        this.applyParameters(keyframe.parameters);
    }

    /**
     * 再生速度を設定
     * @param {number} speed - 再生速度（1.0 = 通常、2.0 = 2倍速）
     */
    setSpeed(speed) {
        this.speed = Math.max(0.1, Math.min(5.0, speed));
        console.log(`⚡ 再生速度: ${this.speed.toFixed(1)}x`);
    }

    /**
     * ループ設定
     * @param {boolean} enabled - ループ有効/無効
     */
    setLoop(enabled) {
        this.loop = enabled;
        console.log(`🔄 ループ: ${enabled ? 'ON' : 'OFF'}`);
    }

    /**
     * 現在の状態を取得
     * @returns {Object} 状態情報
     */
    getStatus() {
        return {
            isPlaying: this.isPlaying,
            currentTime: this.currentTime,
            duration: this.currentAnimation?.metadata?.duration || 0,
            animationName: this.currentAnimation?.metadata?.name || null,
            loop: this.loop,
            speed: this.speed
        };
    }

    /**
     * クリーンアップ
     */
    destroy() {
        this.stop();
        this.currentAnimation = null;
        console.log('🧹 アニメーションプレイヤークリーンアップ完了');
    }
}

// グローバルインスタンス作成
window.animationPlayer = new AnimationPlayer();

// グローバル関数として公開
window.loadAnimation = (data) => window.animationPlayer.loadAnimation(data);
window.playAnimation = () => window.animationPlayer.play();
window.pauseAnimation = () => window.animationPlayer.pause();
window.stopAnimation = () => window.animationPlayer.stop();
window.setAnimationSpeed = (speed) => window.animationPlayer.setSpeed(speed);
window.setAnimationLoop = (enabled) => window.animationPlayer.setLoop(enabled);
window.getAnimationStatus = () => window.animationPlayer.getStatus();

console.log('✅ animation_player.js 読み込み完了');