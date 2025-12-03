// register.js

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('register-form');
    
    if (form) {
        form.addEventListener('submit', handleRegistration);
    }
});

async function handleRegistration(event) {
    event.preventDefault(); // 画面リロードを阻止 (必須)
    
    const messageArea = document.getElementById('messageArea'); 
    const formElement = event.target; 
    messageArea.innerHTML = ''; // メッセージエリアをクリア

    // 1. フォームデータの取得
    const formData = new FormData(formElement);
    const data = Object.fromEntries(formData.entries()); 
    
    // 2. クライアントサイドでの簡易パスワードチェック
    if (data.password !== data.password_confirm) {
        messageArea.innerHTML = '<p style="color: red;">パスワードが一致しません。</p>';
        return;
    }
    
    // 3. サーバーが期待する形式に整形 (password_confirm は不要なので削除)
    delete data.password_confirm;

    // --- API呼び出し ---
    try {
        const response = await fetch('/api/register_user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data) // ★ JSON形式の文字列に変換して送信 ★
        });

        const result = await response.json(); 

        // --- 結果の処理 ---

        if (response.ok) { // 成功時 (201 Created)
            formElement.reset(); 
            messageArea.innerHTML = '<p style="color: green; font-weight: bold;">✅ 登録が完了しました！ログイン画面へ移動します。</p>';
            
            // 3秒後にログイン画面へ遷移
            setTimeout(() => {
                window.location.href = '/'; 
            }, 3000);

        } else if (response.status === 422) { // Pydanticによるバリデーションエラー
            // エラーを解析して表示
            const errorDetails = result.details.map(err => {
                const fieldName = err.loc ? err.loc.join('.') : '不明なフィールド';
                return `<li>[${fieldName}]: ${err.msg}</li>`;
            }).join('');

            messageArea.innerHTML = `<div style="color: red;"><strong>入力エラー:</strong><ul>${errorDetails}</ul></div>`;
            
        } else { // その他のサーバーエラー (400, 500など)
            messageArea.innerHTML = `<p style="color: red;">登録中にエラーが発生しました: ${result.message}</p>`;
        }

    } catch (error) {
        messageArea.innerHTML = `<p style="color: red;">サーバーとの通信に失敗しました。</p>`;
        console.error('Fetch Error:', error);
    }
}