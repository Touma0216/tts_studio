// assets/live2d_dist/background_image_editor.js
class BackgroundImageEditor {
    constructor() {
        this.enabled = false;
        this.frameBox = null;
        this.handles = [];
        this.isDragging = false;
        this.isResizing = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.startPosX = 0;
        this.startPosY = 0;
        this.startWidth = 0;
        this.startHeight = 0;
        this.resizeHandle = null;
        
        console.log('✅ BackgroundImageEditor初期化完了');
    }
    
    setEnabled(enabled) {
        this.enabled = enabled;
        
        if (enabled) {
            this.createFrame();
        } else {
            this.destroyFrame();
        }
    }
    
    createFrame() {
        // 現在の背景設定を取得
        const bgPos = getComputedStyle(document.body).backgroundPosition.split(' ');
        const bgSize = getComputedStyle(document.body).backgroundSize.split(' ');
        
        let posX = parseInt(bgPos[0]) || window.innerWidth / 2;
        let posY = parseInt(bgPos[1]) || window.innerHeight / 2;
        let width = parseInt(bgSize[0]) || window.innerWidth * 0.8;
        let height = parseInt(bgSize[1]) || window.innerHeight * 0.8;
        
        // 枠線ボックス作成
        this.frameBox = document.createElement('div');
        this.frameBox.style.cssText = `
            position: absolute;
            left: ${posX}px;
            top: ${posY}px;
            width: ${width}px;
            height: ${height}px;
            border: 3px solid #4a90e2;
            cursor: move;
            z-index: 9999;
        `;
        
        document.body.appendChild(this.frameBox);
        
        this.createHandles();
        
        this.frameBox.addEventListener('mousedown', this.onMouseDown.bind(this));
        document.addEventListener('mousemove', this.onMouseMove.bind(this));
        document.addEventListener('mouseup', this.onMouseUp.bind(this));
        
        console.log('✅ 背景編集モード: ON');
    }
    
    createHandles() {
        const positions = [
            { name: 'nw', cursor: 'nw-resize', x: '0%', y: '0%' },
            { name: 'n', cursor: 'n-resize', x: '50%', y: '0%' },
            { name: 'ne', cursor: 'ne-resize', x: '100%', y: '0%' },
            { name: 'e', cursor: 'e-resize', x: '100%', y: '50%' },
            { name: 'se', cursor: 'se-resize', x: '100%', y: '100%' },
            { name: 's', cursor: 's-resize', x: '50%', y: '100%' },
            { name: 'sw', cursor: 'sw-resize', x: '0%', y: '100%' },
            { name: 'w', cursor: 'w-resize', x: '0%', y: '50%' }
        ];
        
        positions.forEach(pos => {
            const handle = document.createElement('div');
            handle.dataset.position = pos.name;
            handle.style.cssText = `
                position: absolute;
                width: 16px;
                height: 16px;
                background: white;
                border: 3px solid #4a90e2;
                border-radius: 50%;
                cursor: ${pos.cursor};
                left: ${pos.x};
                top: ${pos.y};
                transform: translate(-50%, -50%);
            `;
            
            handle.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                this.startResize(e, pos.name);
            });
            
            this.frameBox.appendChild(handle);
            this.handles.push(handle);
        });
    }
    
    onMouseDown(e) {
        if (!this.enabled || this.isResizing) return;
        
        this.isDragging = true;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        
        const rect = this.frameBox.getBoundingClientRect();
        this.startPosX = rect.left;
        this.startPosY = rect.top;
        
        this.frameBox.style.cursor = 'grabbing';
        e.preventDefault();
    }
    
    startResize(e, position) {
        if (!this.enabled) return;
        
        this.isResizing = true;
        this.resizeHandle = position;
        this.dragStartX = e.clientX;
        this.dragStartY = e.clientY;
        
        const rect = this.frameBox.getBoundingClientRect();
        this.startPosX = rect.left;
        this.startPosY = rect.top;
        this.startWidth = rect.width;
        this.startHeight = rect.height;
        
        e.preventDefault();
    }
    
    onMouseMove(e) {
        if (!this.enabled) return;
        
        if (this.isDragging) {
            const deltaX = e.clientX - this.dragStartX;
            const deltaY = e.clientY - this.dragStartY;
            
            const newX = this.startPosX + deltaX;
            const newY = this.startPosY + deltaY;
            
            this.frameBox.style.left = newX + 'px';
            this.frameBox.style.top = newY + 'px';
            
            // リアルタイムで背景更新
            document.body.style.backgroundPosition = `${newX}px ${newY}px`;
            
        } else if (this.isResizing) {
            const deltaX = e.clientX - this.dragStartX;
            const deltaY = e.clientY - this.dragStartY;
            
            let newWidth = this.startWidth;
            let newHeight = this.startHeight;
            let newX = this.startPosX;
            let newY = this.startPosY;
            
            switch (this.resizeHandle) {
                case 'se':
                    newWidth = Math.max(100, this.startWidth + deltaX);
                    newHeight = Math.max(100, this.startHeight + deltaY);
                    break;
                case 'nw':
                    newWidth = Math.max(100, this.startWidth - deltaX);
                    newHeight = Math.max(100, this.startHeight - deltaY);
                    newX = this.startPosX + deltaX;
                    newY = this.startPosY + deltaY;
                    break;
                case 'ne':
                    newWidth = Math.max(100, this.startWidth + deltaX);
                    newHeight = Math.max(100, this.startHeight - deltaY);
                    newY = this.startPosY + deltaY;
                    break;
                case 'sw':
                    newWidth = Math.max(100, this.startWidth - deltaX);
                    newHeight = Math.max(100, this.startHeight + deltaY);
                    newX = this.startPosX + deltaX;
                    break;
                case 'e':
                    newWidth = Math.max(100, this.startWidth + deltaX);
                    break;
                case 'w':
                    newWidth = Math.max(100, this.startWidth - deltaX);
                    newX = this.startPosX + deltaX;
                    break;
                case 'n':
                    newHeight = Math.max(100, this.startHeight - deltaY);
                    newY = this.startPosY + deltaY;
                    break;
                case 's':
                    newHeight = Math.max(100, this.startHeight + deltaY);
                    break;
            }
            
            this.frameBox.style.left = newX + 'px';
            this.frameBox.style.top = newY + 'px';
            this.frameBox.style.width = newWidth + 'px';
            this.frameBox.style.height = newHeight + 'px';
            
            // リアルタイムで背景更新
            document.body.style.backgroundPosition = `${newX}px ${newY}px`;
            document.body.style.backgroundSize = `${newWidth}px ${newHeight}px`;
        }
    }
    
    onMouseUp(e) {
        if (this.isDragging) {
            this.isDragging = false;
            this.frameBox.style.cursor = 'move';
        }
        
        if (this.isResizing) {
            this.isResizing = false;
            this.resizeHandle = null;
        }
    }
    
    destroyFrame() {
        if (this.frameBox) {
            this.frameBox.remove();
            this.frameBox = null;
            this.handles = [];
        }
        console.log('🔒 背景編集モード: OFF');
    }
}

window.backgroundImageEditor = new BackgroundImageEditor();
window.enableBackgroundEdit = (enabled) => window.backgroundImageEditor.setEnabled(enabled);

console.log('✅ background_image_editor.js 読み込み完了');