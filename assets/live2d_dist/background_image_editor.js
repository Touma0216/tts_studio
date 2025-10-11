// assets/live2d_dist/background_image_editor.js
// 背景画像の位置＆サイズ編集機能

class BackgroundImageEditor {
    constructor() {
        this.enabled = false;
        this.imageElement = null;
        this.imageContainer = null;
        this.handles = [];
        this.isDragging = false;
        this.isResizing = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.originalLeft = 0;
        this.originalTop = 0;
        this.originalWidth = 0;
        this.originalHeight = 0;
        this.resizeHandle = null;
        this.aspectRatio = 1;
        
        this.init();
    }
    
    init() {
        // コンテナ作成
        this.imageContainer = document.createElement('div');
        this.imageContainer.id = 'bg-image-container';
        this.imageContainer.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: none;
            cursor: move;
            z-index: 1;
        `;
        
        // 画像要素
        this.imageElement = document.createElement('img');
        this.imageElement.style.cssText = `
            width: 100%;
            height: 100%;
            pointer-events: none;
            user-select: none;
        `;
        
        this.imageContainer.appendChild(this.imageElement);
        document.body.appendChild(this.imageContainer);
        
        // リサイズハンドル作成
        this.createResizeHandles();
        
        // イベント
        this.imageContainer.addEventListener('mousedown', this.onMouseDown.bind(this));
        document.addEventListener('mousemove', this.onMouseMove.bind(this));
        document.addEventListener('mouseup', this.onMouseUp.bind(this));
        
        console.log('✅ BackgroundImageEditor初期化完了');
    }
    
    createResizeHandles() {
        const positions = [
            { name: 'nw', cursor: 'nw-resize', x: 0, y: 0 },
            { name: 'n', cursor: 'n-resize', x: 50, y: 0 },
            { name: 'ne', cursor: 'ne-resize', x: 100, y: 0 },
            { name: 'e', cursor: 'e-resize', x: 100, y: 50 },
            { name: 'se', cursor: 'se-resize', x: 100, y: 100 },
            { name: 's', cursor: 's-resize', x: 50, y: 100 },
            { name: 'sw', cursor: 'sw-resize', x: 0, y: 100 },
            { name: 'w', cursor: 'w-resize', x: 0, y: 50 }
        ];
        
        positions.forEach(pos => {
            const handle = document.createElement('div');
            handle.className = 'resize-handle';
            handle.dataset.position = pos.name;
            handle.style.cssText = `
                position: absolute;
                width: 12px;
                height: 12px;
                background: white;
                border: 2px solid #4a90e2;
                border-radius: 50%;
                cursor: ${pos.cursor};
                left: ${pos.x}%;
                top: ${pos.y}%;
                transform: translate(-50%, -50%);
                z-index: 10;
                display: none;
            `;
            
            handle.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                this.startResize(e, pos.name);
            });
            
            this.imageContainer.appendChild(handle);
            this.handles.push(handle);
        });
    }
    
    setEnabled(enabled) {
        this.enabled = enabled;
        
        if (enabled) {
            this.imageContainer.style.display = 'block';
            this.showHandles();
            console.log('✅ 背景画像編集モード: ON');
        } else {
            this.imageContainer.style.display = 'none';
            this.hideHandles();
            console.log('🔒 背景画像編集モード: OFF');
        }
    }
    
    loadImage(dataUrl) {
        if (!dataUrl) return;
        
        this.imageElement.src = dataUrl;
        this.imageElement.onload = () => {
            this.aspectRatio = this.imageElement.naturalWidth / this.imageElement.naturalHeight;
            
            // 初期サイズ設定
            const maxWidth = window.innerWidth * 0.8;
            const maxHeight = window.innerHeight * 0.8;
            let width = this.imageElement.naturalWidth;
            let height = this.imageElement.naturalHeight;
            
            if (width > maxWidth) {
                width = maxWidth;
                height = width / this.aspectRatio;
            }
            if (height > maxHeight) {
                height = maxHeight;
                width = height * this.aspectRatio;
            }
            
            this.imageContainer.style.width = width + 'px';
            this.imageContainer.style.height = height + 'px';
            
            console.log('🖼️ 背景画像読み込み完了');
        };
    }
    
    showHandles() {
        this.handles.forEach(h => h.style.display = 'block');
    }
    
    hideHandles() {
        this.handles.forEach(h => h.style.display = 'none');
    }
    
    onMouseDown(e) {
        if (!this.enabled || this.isResizing) return;
        
        this.isDragging = true;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        
        const rect = this.imageContainer.getBoundingClientRect();
        this.originalLeft = rect.left + rect.width / 2;
        this.originalTop = rect.top + rect.height / 2;
        
        this.imageContainer.style.cursor = 'grabbing';
        e.preventDefault();
    }
    
    startResize(e, position) {
        if (!this.enabled) return;
        
        this.isResizing = true;
        this.resizeHandle = position;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        
        const rect = this.imageContainer.getBoundingClientRect();
        this.originalWidth = rect.width;
        this.originalHeight = rect.height;
        this.originalLeft = rect.left + rect.width / 2;
        this.originalTop = rect.top + rect.height / 2;
        
        e.preventDefault();
    }
    
    onMouseMove(e) {
        if (!this.enabled) return;
        
        if (this.isDragging) {
            const deltaX = e.clientX - this.dragStartX;
            const deltaY = e.clientY - this.dragStartY;
            
            const newLeft = this.originalLeft + deltaX;
            const newTop = this.originalTop + deltaY;
            
            this.imageContainer.style.left = newLeft + 'px';
            this.imageContainer.style.top = newTop + 'px';
            this.imageContainer.style.transform = 'translate(-50%, -50%)';
            
        } else if (this.isResizing) {
            const deltaX = e.clientX - this.dragStartX;
            const deltaY = e.clientY - this.dragStartY;
            
            let newWidth = this.originalWidth;
            let newHeight = this.originalHeight;
            
            switch (this.resizeHandle) {
                case 'se': // 右下
                    newWidth = this.originalWidth + deltaX;
                    newHeight = newWidth / this.aspectRatio;
                    break;
                case 'nw': // 左上
                    newWidth = this.originalWidth - deltaX;
                    newHeight = newWidth / this.aspectRatio;
                    break;
                case 'ne': // 右上
                    newWidth = this.originalWidth + deltaX;
                    newHeight = newWidth / this.aspectRatio;
                    break;
                case 'sw': // 左下
                    newWidth = this.originalWidth - deltaX;
                    newHeight = newWidth / this.aspectRatio;
                    break;
                case 'e': // 右
                    newWidth = this.originalWidth + deltaX;
                    newHeight = newWidth / this.aspectRatio;
                    break;
                case 'w': // 左
                    newWidth = this.originalWidth - deltaX;
                    newHeight = newWidth / this.aspectRatio;
                    break;
                case 'n': // 上
                    newHeight = this.originalHeight - deltaY;
                    newWidth = newHeight * this.aspectRatio;
                    break;
                case 's': // 下
                    newHeight = this.originalHeight + deltaY;
                    newWidth = newHeight * this.aspectRatio;
                    break;
            }
            
            // 最小サイズ制限
            newWidth = Math.max(100, newWidth);
            newHeight = Math.max(100, newHeight);
            
            this.imageContainer.style.width = newWidth + 'px';
            this.imageContainer.style.height = newHeight + 'px';
        }
    }
    
    onMouseUp(e) {
        if (this.isDragging) {
            this.isDragging = false;
            this.imageContainer.style.cursor = 'move';
        }
        
        if (this.isResizing) {
            this.isResizing = false;
            this.resizeHandle = null;
        }
    }
    
    getSettings() {
        const rect = this.imageContainer.getBoundingClientRect();
        return {
            left: rect.left + rect.width / 2,
            top: rect.top + rect.height / 2,
            width: rect.width,
            height: rect.height
        };
    }
    
    applySettings(settings) {
        if (!settings) return;
        
        this.imageContainer.style.left = settings.left + 'px';
        this.imageContainer.style.top = settings.top + 'px';
        this.imageContainer.style.width = settings.width + 'px';
        this.imageContainer.style.height = settings.height + 'px';
        this.imageContainer.style.transform = 'translate(-50%, -50%)';
    }
}

// グローバルインスタンス
window.backgroundImageEditor = new BackgroundImageEditor();

// グローバル関数
window.enableBackgroundEdit = (enabled) => window.backgroundImageEditor.setEnabled(enabled);
window.loadBackgroundImage = (dataUrl) => window.backgroundImageEditor.loadImage(dataUrl);
window.getBackgroundImageSettings = () => window.backgroundImageEditor.getSettings();
window.applyBackgroundImageSettings = (settings) => window.backgroundImageEditor.applySettings(settings);

console.log('✅ background_image_editor.js 読み込み完了');