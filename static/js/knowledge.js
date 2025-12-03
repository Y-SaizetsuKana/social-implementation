document.addEventListener('DOMContentLoaded', () => {
    // 1. すべての豆知識アイテムを取得
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    
    // 2. すべてのモーダルを取得
    const detailModals = document.querySelectorAll('.detail-modal');
    
    // 3. すべての閉じるボタンを取得
    const closeButtons = document.querySelectorAll('.close-btn');
    
    // アイテムクリック時の処理
    knowledgeItems.forEach(item => {
        item.addEventListener('click', () => {
            // クリックされたアイテムの data-target 属性からモーダルのIDを取得
            const targetId = item.getAttribute('data-target');
            const targetModal = document.getElementById(targetId);
            
            if (targetModal) {
                // 対象のモーダルを表示
                targetModal.style.display = 'block';
                // (オプション) bodyにクラスを追加して背景のスクロールを止める
                document.body.classList.add('modal-open'); 
            }
        });
    });
    
    // 閉じるボタンクリック時の処理
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            // 親要素（モーダル）を非表示にする
            const modal = button.closest('.detail-modal');
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        });
    });

    // モーダルの外側をクリックしたときの処理
    detailModals.forEach(modal => {
        modal.addEventListener('click', (event) => {
            // クリックされた要素がモーダル自体であるか確認
            if (event.target === modal) {
                modal.style.display = 'none';
                document.body.classList.remove('modal-open');
            }
        });
    });
});