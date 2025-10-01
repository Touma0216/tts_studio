// assets/live2d_dist/modeling/modeling_controller.js
// モデリング制御：パラメータ設定のメイン処理

/**
 * 単一パラメータをLive2Dモデルに設定
 * @param {string} paramId - パラメータID（例: "ParamAngleX"）
 * @param {number} value - 設定値
 * @returns {boolean} - 成功したらtrue
 */
window.setLive2DParameter = function(paramId, value) {
    try {
        if (!window.currentModel) {
            console.warn('⚠️ モデル未読み込み：パラメータ設定スキップ');
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        
        // パラメータIDの存在確認
        const paramIndex = model.getParameterIndex(paramId);
        if (paramIndex === -1) {
            console.warn(`⚠️ パラメータが見つかりません: ${paramId}`);
            return false;
        }

        // パラメータ設定
        model.setParameterValueById(paramId, value);
        
        // デバッグログ（詳細版：初回のみ）
        if (!window._paramSetCount) window._paramSetCount = {};
        if (!window._paramSetCount[paramId]) {
            console.log(`✅ パラメータ設定: ${paramId} = ${value.toFixed(3)}`);
            window._paramSetCount[paramId] = true;
        }

        return true;
    } catch (error) {
        console.error(`❌ パラメータ設定エラー (${paramId}):`, error);
        return false;
    }
};

/**
 * 複数パラメータを一括設定
 * @param {Object} parameters - {paramId: value, ...}の形式
 * @returns {boolean} - 成功したらtrue
 */
window.setLive2DParameters = function(parameters) {
    try {
        if (!window.currentModel) {
            console.warn('⚠️ モデル未読み込み：パラメータ一括設定スキップ');
            return false;
        }

        if (!parameters || typeof parameters !== 'object') {
            console.error('❌ パラメータが無効な形式です');
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        let successCount = 0;
        let failCount = 0;

        // 全パラメータを設定
        for (const [paramId, value] of Object.entries(parameters)) {
            const paramIndex = model.getParameterIndex(paramId);
            if (paramIndex === -1) {
                failCount++;
                continue;
            }

            model.setParameterValueById(paramId, value);
            successCount++;
        }

        console.log(`🎨 パラメータ一括設定: 成功${successCount}個, 失敗${failCount}個`);
        return true;
    } catch (error) {
        console.error('❌ パラメータ一括設定エラー:', error);
        return false;
    }
};

/**
 * パラメータをデフォルト値にリセット
 * @param {string} paramId - パラメータID
 * @returns {boolean} - 成功したらtrue
 */
window.resetLive2DParameter = function(paramId) {
    try {
        if (!window.currentModel) {
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramIndex = model.getParameterIndex(paramId);
        
        if (paramIndex === -1) {
            return false;
        }

        // デフォルト値を取得して設定
        const defaultValue = model.getParameterDefaultValueById(paramId);
        model.setParameterValueById(paramId, defaultValue);
        
        console.log(`↺ リセット: ${paramId} = ${defaultValue.toFixed(3)}`);
        return true;
    } catch (error) {
        console.error(`❌ リセットエラー (${paramId}):`, error);
        return false;
    }
};

/**
 * 全パラメータをデフォルト値にリセット
 * @returns {boolean} - 成功したらtrue
 */
window.resetAllLive2DParameters = function() {
    try {
        if (!window.currentModel) {
            return false;
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramCount = model.getParameterCount();
        let resetCount = 0;

        for (let i = 0; i < paramCount; i++) {
            const paramId = model.getParameterId(i);
            const defaultValue = model.getParameterDefaultValueById(paramId);
            model.setParameterValueById(paramId, defaultValue);
            resetCount++;
        }

        console.log(`🔄 全パラメータリセット: ${resetCount}個`);
        return true;
    } catch (error) {
        console.error('❌ 全リセットエラー:', error);
        return false;
    }
};

/**
 * 現在のパラメータ値を取得
 * @param {string} paramId - パラメータID
 * @returns {number|null} - パラメータ値、取得失敗時はnull
 */
window.getLive2DParameterValue = function(paramId) {
    try {
        if (!window.currentModel) {
            return null;
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramIndex = model.getParameterIndex(paramId);
        
        if (paramIndex === -1) {
            return null;
        }

        return model.getParameterValueById(paramId);
    } catch (error) {
        console.error(`❌ パラメータ取得エラー (${paramId}):`, error);
        return null;
    }
};

/**
 * 全パラメータの現在値を取得
 * @returns {Object} - {paramId: value, ...}の形式
 */
window.getAllLive2DParameterValues = function() {
    try {
        if (!window.currentModel) {
            return {};
        }

        const model = window.currentModel.internalModel.coreModel;
        const paramCount = model.getParameterCount();
        const values = {};

        for (let i = 0; i < paramCount; i++) {
            const paramId = model.getParameterId(i);
            const value = model.getParameterValueById(paramId);
            values[paramId] = value;
        }

        return values;
    } catch (error) {
        console.error('❌ 全パラメータ取得エラー:', error);
        return {};
    }
};

console.log('✅ modeling_controller.js 読み込み完了');