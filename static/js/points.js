document.addEventListener('DOMContentLoaded', () => {
    // 1. 必要な要素を取得
    const modal = document.getElementById('confirmation-modal');
    const tradeButtons = document.querySelectorAll('.trade-button');
    const closeButton = document.querySelector('.close-button');
    const confirmYes = document.getElementById('confirm-yes');
    const confirmNo = document.getElementById('confirm-no');
    const itemNameDisplay = document.getElementById('item-name');
    const itemCostDisplay = document.getElementById('item-cost');
    // ★追加: トースト通知用の要素を取得
    const toast = document.getElementById('toast-notification');
    const toastMessage = document.getElementById('toast-message');

    // モーダルを閉じる処理を関数化 (変更なし)
    const closeModal = () => {
        modal.style.display = 'none';
    };

    // ★追加: トースト通知を表示する関数
    const showToast = (message) => {
        toastMessage.textContent = message;
        toast.classList.remove('toast-hidden');
        
        // 3秒後に自動的に非表示にする
        setTimeout(() => {
            toast.classList.add('toast-hidden');
        }, 3000);
    };

    // 2. すべての交換ボタンにクリックイベントを追加 (変更なし)
    tradeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // クリックされたボタンのカスタムデータ属性から情報を取得
            const item = this.getAttribute('data-item');
            const cost = this.getAttribute('data-cost');

            // モーダル内の表示テキストを更新
            itemNameDisplay.textContent = item;
            itemCostDisplay.textContent = cost;
            
            // 「はい」ボタンに交換に必要な情報を設定
            confirmYes.setAttribute('data-item', item);
            
            // モーダルを表示
            modal.style.display = 'block';
        });
    });

    // 3. モーダルを閉じる処理を設定 (変更なし)
    closeButton.addEventListener('click', closeModal);
    confirmNo.addEventListener('click', closeModal);

    // モーダルの外側（背景）をクリックしたときに閉じる処理 (変更なし)
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });

    // 4. 「はい」ボタンの処理 (★アラートをトーストに置き換え)
    confirmYes.addEventListener('click', function() {
        const itemToTrade = this.getAttribute('data-item');
        
        // ★★★ ここに実際の交換処理（ポイント減算、サーバーへのデータ送信など）を記述 ★★★
        console.log(`${itemToTrade} の交換処理を実行します。`); 
        
        // 例：交換成功のメッセージを表示してから閉じる
        // alert(`${itemToTrade} を交換しました！`); // 🗑️ 既存のダサいアラートを削除
        showToast(`${itemToTrade} を交換しました！ 🎉`); // ✨ モダンなトースト通知に変更
        closeModal();
    });
});