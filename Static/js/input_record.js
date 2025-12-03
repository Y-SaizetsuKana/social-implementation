// input_record.js (廃棄記録用)

document.addEventListener('DOMContentLoaded', () => {
    // フォームIDが 'input-form' であることを想定
    const form = document.getElementById('input-form');
    
    // フォームの送信動作を、handleRecordSubmission 関数に任せる
    if (form) {
        form.addEventListener('submit', handleRecordSubmission);
    }
});

async function handleRecordSubmission(event) {
    event.preventDefault(); // 画面リロードを停止
    
    // エラーメッセージ表示用のコンテナ (HTMLに <div id="messageArea"></div> があることを前提)
    const messageArea = document.getElementById('messageArea'); 
    const formElement = event.target; 
    
    // ユーザーIDはセッションで取得されるため、ここではテストIDを使用 (実際はセッションから取得するAPIが必要)
    const TEST_USER_ID = 1; 

    // 1. フォームデータの取得と変換 (HTMLフォームのname属性に対応)
    const formData = new FormData(formElement);
    const rawData = Object.fromEntries(formData.entries()); 
    
    // 2. バックエンドが期待するJSON形式にデータを整形
    const requestBody = {
        // user_id はバックエンドがセッションから取得するが、このAPIではJSONに含めておく (開発時の簡略化)
        user_id: TEST_USER_ID, 
        item_name: rawData.item_name,       // inputのname="waste1"から取得
        weight_grams: parseFloat(rawData.weight_grams), // inputのname="amount1"からfloatに変換
        reason_text: rawData.reason_text    // radioボタンのname="reason1"から取得
    };

    // --- API呼び出し ---
    try {
        const response = await fetch('/api/add_loss_record', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody) // JSON文字列に変換
        });

        const result = await response.json(); 

        // --- ステップ C: 結果の処理 ---

        if (response.ok) { // 200番台（成功）
            // 成功時: 画面にメッセージを表示し、フォームをリセット
            formElement.reset(); 
            messageArea.innerHTML = '<p style="color: green; font-weight: bold;">✅ 記録が完了しました！</p>';
            
        } else if (response.status === 422) { // バリデーションエラー
            // 失敗時: Pydanticからのエラーを解析して表示
            const errorDetails = result.details.map(err => {
                const fieldName = err.loc ? err.loc.join('.') : '不明なフィールド';
                return `<li>[${fieldName}]: ${err.msg}</li>`;
            }).join('');

            messageArea.innerHTML = `
                <div style="color: red; border: 1px solid red; padding: 10px; margin-top: 10px;">
                    <strong>入力データに問題があります:</strong>
                    <ul>${errorDetails}</ul>
                </div>`;
            
        } else { // その他のサーバーエラー
            messageArea.innerHTML = `<p style="color: red;">エラーが発生しました: ${result.message}</p>`;
        }

    } catch (error) {
        // 通信エラー
        messageArea.innerHTML = `<p style="color: red;">サーバーとの通信に失敗しました。ネットワークを確認してください。</p>`;
        console.error('Fetch Error:', error);
    }
}