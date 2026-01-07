document.addEventListener('DOMContentLoaded', () => {
    // 1. すべての豆知識アイテムを取得
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    
    // 2. すべてのモーダルを取得
    const detailModals = document.querySelectorAll('.detail-modal');
    
    // 3. すべての閉じるボタンを取得
    const closeButtons = document.querySelectorAll('.close-btn');
    
    // --- 【追加】フィルタリングボタンの取得 ---
    const filterButtons = document.querySelectorAll('.filter-btn');
    const triviaContainer = document.getElementById('knowledge-list-container-trivia');
    
    // アイテムクリック時の処理 (変更なし)
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
    
    // 閉じるボタンクリック時の処理 (変更なし)
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            // 親要素（モーダル）を非表示にする
            const modal = button.closest('.detail-modal');
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        });
    });

    // モーダルの外側をクリックしたときの処理 (変更なし)
    detailModals.forEach(modal => {
        modal.addEventListener('click', (event) => {
            // クリックされた要素がモーダル自体であるか確認
            if (event.target === modal) {
                modal.style.display = 'none';
                document.body.classList.remove('modal-open');
            }
        });
    });

    // ----------------------------------------------------
    // --- 【追加】カテゴリフィルタリング機能のロジック ---
    // ----------------------------------------------------
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            const filterCategory = button.getAttribute('data-filter');

            // 1. アクティブクラスの切り替え
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // 2. 豆知識アイテムのフィルタリング
            // アレンジレシピのアイテムを含まないように、ID指定のコンテナからアイテムを取得
            const items = triviaContainer.querySelectorAll('.knowledge-item'); 
            
            items.forEach(item => {
                // HTMLで追加した data-category 属性の値を取得
                const itemCategory = item.getAttribute('data-category');
                
                // data-filter="全て" または カテゴリが一致する場合に表示
                if (filterCategory === '全て' || itemCategory === filterCategory) {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        });
    });

    // ----------------------------------------------------
    // --- 【追加】初期表示設定 ---
    // ----------------------------------------------------
    // ページロード時にデフォルトで「全て表示」または最初のボタンをクリックした状態にする
    const defaultButton = document.querySelector('.filter-buttons .filter-btn:first-child');
    if (defaultButton) {
        defaultButton.click();
    }

    // ----------------------------------------------------
    // --- 〇変更点: アレンジレシピ一覧のクリック処理 ---
    // ----------------------------------------------------
    // 検索処理(fetch)は削除し、サーバー描画されたアイテムへのイベントリスナーのみ実装
    const recipeModal = document.getElementById('recipe-dynamic-modal');
    const recipeModalTitle = document.getElementById('recipe-modal-title');
    const recipeModalContent = document.getElementById('recipe-modal-content');
    
    // サーバー側で描画された .recipe-item をすべて取得
    const recipeItems = document.querySelectorAll('.recipe-item');

    recipeItems.forEach(item => {
        item.addEventListener('click', () => {
            const title = item.getAttribute('data-title');
            const content = item.getAttribute('data-content');
            
            if (title && content) {
                recipeModalTitle.textContent = title;
                recipeModalContent.textContent = content;
                
                // 既存のモーダル表示用CSSクラスを使用
                recipeModal.style.display = 'block';
                document.body.classList.add('modal-open');
            }
        });
    });
    
    // 汎用モーダルの閉じるボタン処理
    const recipeModalClose = document.getElementById('recipe-modal-close');
    if(recipeModalClose) {
        recipeModalClose.addEventListener('click', () => {
            recipeModal.style.display = 'none';
            document.body.classList.remove('modal-open');
        });
    }
    // ----------------------------------------------------
});