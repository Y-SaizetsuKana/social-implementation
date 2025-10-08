// async/await を使って非同期処理を記述
async function main() {
  // HTML要素を取得
  const initialDataElem = document.getElementById('initialData');
  const messageInput = document.getElementById('messageInput');
  const sendMessageButton = document.getElementById('sendMessageButton');
  const responseMessageElem = document.getElementById('responseMessage');

  // 1. ページ読み込み時にバックエンドからデータを取得 (受信)
  try {
    const response = await fetch('/get_data', { method: 'POST' });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    console.log('バックエンドからの初期データ:', data);
    initialDataElem.textContent = data.message; // 画面に表示
  } catch (error) {
    console.error('初期データの取得に失敗:', error);
    initialDataElem.textContent = 'エラーが発生しました。';
  }

  // 2. ボタンクリックでバックエンドにデータを送信
  sendMessageButton.addEventListener('click', async () => {
    const message = messageInput.value;
    if (!message) {
      alert('メッセージを入力してください。');
      return;
    }

    const dataToPython = { message: message };

    try {
      const response = await fetch('/receive_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dataToPython),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      console.log('サーバーからの返信:', data);
      responseMessageElem.textContent = data.reply; // 画面に表示
    } catch (error) {
      console.error('データの送信に失敗:', error);
      responseMessageElem.textContent = 'エラーが発生しました。';
    }
  });
}

// DOMの読み込みが完了したらmain関数を実行
document.addEventListener('DOMContentLoaded', main);
