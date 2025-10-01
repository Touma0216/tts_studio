// assets/live2d_dist/modeling/preset_manager.js
// プリセット管理：モーション・表情の読み込みと適用

class PresetManager {
    constructor() {
        this.expressionsList = [];
        this.motionGroups = {};
        this.currentExpression = null;
        this.model3JsonData = null;
    }

    /**
     * model3.jsonからプリセット情報を読み込み
     * @param {string} model3JsonPath - model3.jsonのパス
     */
    async loadModelPresets(model3JsonPath) {
        try {
            console.log(`📋 model3.json読み込み: ${model3JsonPath}`);
            
            const response = await fetch(model3JsonPath);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            this.model3JsonData = await response.json();
            
            // 表情一覧を取得
            if (this.model3JsonData.FileReferences?.Expressions) {
                this.expressionsList = this.model3JsonData.FileReferences.Expressions.map(exp => ({
                    name: exp.Name,
                    file: exp.File
                }));
                console.log(`✅ 表情読み込み: ${this.expressionsList.length}個`);
            }

            // モーション一覧を取得
            if (this.model3JsonData.FileReferences?.Motions) {
                this.motionGroups = this.model3JsonData.FileReferences.Motions;
                const totalMotions = Object.values(this.motionGroups)
                    .reduce((sum, group) => sum + group.length, 0);
                console.log(`✅ モーション読み込み: ${totalMotions}個 (${Object.keys(this.motionGroups).length}グループ)`);
            }

            return true;
        } catch (error) {
            console.error('❌ プリセット読み込みエラー:', error);
            return false;
        }
    }

    /**
     * 表情一覧を取得
     * @returns {Array} - [{name: string, file: string}, ...]
     */
    getExpressionList() {
        return this.expressionsList;
    }

    /**
     * モーショングループ一覧を取得
     * @returns {Object} - {groupName: [{File: string}, ...], ...}
     */
    getMotionGroups() {
        return this.motionGroups;
    }

    /**
     * 表情を設定
     * @param {string} expressionName - 表情名（例: "f01"）
     */
    setExpression(expressionName) {
        try {
            if (!window.currentModel) {
                console.warn('⚠️ モデル未読み込み');
                return false;
            }

            const expression = this.expressionsList.find(exp => exp.name === expressionName);
            if (!expression) {
                console.warn(`⚠️ 表情が見つかりません: ${expressionName}`);
                return false;
            }

            // Live2D SDKの表情設定機能を使用
            const expressionManager = window.currentModel.internalModel.motionManager.expressionManager;
            if (expressionManager) {
                // 表情インデックスを取得
                const expressionIndex = this.expressionsList.findIndex(exp => exp.name === expressionName);
                if (expressionIndex !== -1) {
                    expressionManager.setExpression(expressionIndex);
                    this.currentExpression = expressionName;
                    console.log(`😊 表情設定: ${expressionName}`);
                    return true;
                }
            }

            return false;
        } catch (error) {
            console.error(`❌ 表情設定エラー (${expressionName}):`, error);
            return false;
        }
    }

    /**
     * モーションを再生
     * @param {string} groupName - モーショングループ名（例: "Idle"）
     * @param {number} index - グループ内のインデックス（デフォルト: 0）
     */
    playMotion(groupName, index = 0) {
        try {
            if (!window.currentModel) {
                console.warn('⚠️ モデル未読み込み');
                return false;
            }

            const motionGroup = this.motionGroups[groupName];
            if (!motionGroup || motionGroup.length === 0) {
                console.warn(`⚠️ モーショングループが見つかりません: ${groupName}`);
                return false;
            }

            if (index >= motionGroup.length) {
                console.warn(`⚠️ インデックスが範囲外: ${index} (最大: ${motionGroup.length - 1})`);
                return false;
            }

            // Live2D SDKのモーション再生機能を使用
            const motionManager = window.currentModel.internalModel.motionManager;
            if (motionManager) {
                // モーションを再生（優先度: 2 = 通常）
                motionManager.startMotion(groupName, index, 2);
                console.log(`🎭 モーション再生: ${groupName}[${index}]`);
                return true;
            }

            return false;
        } catch (error) {
            console.error(`❌ モーション再生エラー (${groupName}[${index}]):`, error);
            return false;
        }
    }

    /**
     * モーションをランダム再生
     * @param {string} groupName - モーショングループ名
     */
    playRandomMotion(groupName) {
        const motionGroup = this.motionGroups[groupName];
        if (!motionGroup || motionGroup.length === 0) {
            return false;
        }

        const randomIndex = Math.floor(Math.random() * motionGroup.length);
        return this.playMotion(groupName, randomIndex);
    }

    /**
     * 表情をリセット（デフォルト表情に戻す）- レイヤークリア版
     */
    resetExpression() {
        try {
            if (!window.currentModel) {
                console.warn('⚠️ モデル未読み込み');
                return false;
            }

            console.log('🔍 表情リセット開始（レイヤークリア方式）');
            
            const model = window.currentModel.internalModel;
            const expressionManager = model.motionManager?.expressionManager;
            
            if (!expressionManager) {
                console.warn('⚠️ expressionManager が見つかりません');
                return false;
            }

            // 🔧 重要：全ての表情のウェイトを0にして影響を完全除去
            const expressions = expressionManager.expressions;
            console.log(`📋 表情数: ${expressions.length}個`);
            
            if (expressions && expressions.length > 0) {
                // 各表情のウェイトを0に設定
                expressions.forEach((exp, index) => {
                    if (exp && exp.fadeWeight !== undefined) {
                        exp.fadeWeight = 0;
                        console.log(`  表情[${index}] fadeWeight → 0`);
                    }
                });
                
                // currentExpressionもnullにする
                if (expressionManager._currentExpression !== undefined) {
                    expressionManager._currentExpression = null;
                }
                if (expressionManager.currentExpression !== undefined) {
                    expressionManager.currentExpression = null;
                }
                
                // 念のため、expressionManager自体をupdateして反映
                if (typeof expressionManager.update === 'function') {
                    expressionManager.update(model, 0);
                }
            }
            
            // さらに念のため：パラメータを強制的にデフォルト値に戻す
            const coreModel = model.coreModel;
            if (coreModel) {
                const paramCount = coreModel.getParameterCount();
                console.log(`🔧 ${paramCount}個のパラメータをデフォルト値に復元`);
                
                for (let i = 0; i < paramCount; i++) {
                    const paramId = coreModel.getParameterId(i);
                    const defaultValue = coreModel.getParameterDefaultValue(i);
                    coreModel.setParameterValueById(paramId, defaultValue);
                }
            }
            
            this.currentExpression = null;
            console.log('✅ 表情リセット完了（レイヤー完全クリア）');
            return true;
            
        } catch (error) {
            console.error('❌ 表情リセットエラー:', error);
            console.error('スタックトレース:', error.stack);
            return false;
        }
    }

    /**
     * 現在の表情名を取得
     */
    getCurrentExpression() {
        return this.currentExpression;
    }
}

// グローバルインスタンス作成
window.presetManager = new PresetManager();

// グローバル関数として公開（Python側から呼び出し用）
window.setExpression = (expressionName) => window.presetManager.setExpression(expressionName);
window.playMotion = (groupName, index = 0) => window.presetManager.playMotion(groupName, index);
window.playRandomMotion = (groupName) => window.presetManager.playRandomMotion(groupName);
window.resetExpression = () => window.presetManager.resetExpression();
window.getExpressionList = () => window.presetManager.getExpressionList();
window.getMotionGroups = () => window.presetManager.getMotionGroups();

console.log('✅ preset_manager.js 読み込み完了');