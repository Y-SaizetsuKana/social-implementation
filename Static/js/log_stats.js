// log_stats.js (グラフゼロ表示優先の最終版)

let statsContent = null; 

document.addEventListener('DOMContentLoaded', () => {
    statsContent = document.querySelector('.stats-content'); 

    if (!statsContent) {
        console.error("致命的エラー: HTMLコンテナ '.stats-content' が見つかりません。");
        document.body.innerHTML = '<p style="color: red;">重大エラー：画面の表示エリアが見つかりません。</p>';
        return; 
    }
    
    fetchWeeklyStats(); 
});


async function fetchWeeklyStats() {
    
    // URLパラメータの取得
    const urlParams = new URLSearchParams(window.location.search);
    const dateParam = urlParams.get('date');

    // APIエンドポイントの定義
    let apiEndpoint = `/api/weekly_stats`; 
    if (dateParam) {
        apiEndpoint += `?date=${dateParam}`;
    }
    
    try {
        const response = await fetch(apiEndpoint);
        
        if (!response.ok) {
            throw new Error(`APIエラー: ${response.status}`);
        }
        
        const data = await response.json();

        // ★ 修正点: データがない場合の特別なテキスト表示を削除 ★
        // データがあってもなくても、常にグラフと表の描画を試みる
        
        // 1. グラフ描画（データがない場合は全て0のグラフが描画される）
        renderBarChart(data.daily_graph_data);
        
        // 2. 表の描画（データがない場合は「記録なし」行が表示される）
        renderDishTable(data.dish_table); 

    } catch (error) {
        console.error('統計データの取得に失敗しました:', error);
        // エラー発生時は、データコンテナ全体をエラーメッセージで上書き
        statsContent.innerHTML = 
            `<p style="color: red; text-align: center;">統計データを読み込めませんでした。エラー: ${error.message}</p>`;
    }
}

// --- 棒グラフ描画ロジック (修正版) ---
function renderBarChart(dailyData) {
    const labels = dailyData.map(d => d.day);
    const grams = dailyData.map(d => d.total_grams);
    
    // Canvas要素を取得
    const ctx = document.getElementById('dailyLossChart');
    if (!ctx) {
        console.error("Canvas要素 #dailyLossChart が見つかりません。");
        return;
    }
    
    // ★ 修正点1: 以前の Chart.js インスタンスがあれば破棄する ★
    // これにより、データ更新時や再読み込み時にグラフが正しく再描画される
    if (Chart.getChart(ctx)) {
        Chart.getChart(ctx).destroy();
    }
    
    // グラフを初期化して描画
    new Chart(ctx, {
        type: 'bar', 
        data: {
            labels: labels,
            datasets: [{
                label: '1日あたりの廃棄重量 (g)',
                data: grams,
                backgroundColor: 'rgba(255, 159, 64, 0.7)',
                borderColor: 'rgba(255, 159, 64, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '廃棄量 (グラム)'
                    }
                },
                x: { // ★ 修正点2: X軸を明示的に定義する ★
                    display: true,
                    title: {
                        display: true,
                        text: '曜日'
                    }
                }
            }
        }
    });
}
// --- 表データ描画ロジック ---
function renderDishTable(dishTableData) {
    const tbody = document.querySelector('#dishTable tbody');
    tbody.innerHTML = ''; // 既存のデータをクリア
    
    // ★ 修正点: データがなければ「記録なし」の行を表示 ★
    if (dishTableData && dishTableData.length > 0) {
        dishTableData.forEach(item => {
            const row = tbody.insertRow();
            row.insertCell().textContent = item.date;
            row.insertCell().textContent = item.dish_name;
            row.insertCell().textContent = item.weight_grams + ' g';
            row.insertCell().textContent = item.reason; 
        });
    } else {
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4; // 4列を結合
        cell.textContent = "この週の廃棄品目の記録はありません。";
        cell.style.textAlign = 'center';
    }
}