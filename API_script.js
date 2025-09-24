document.addEventListener('DOMContentLoaded', function() {
  //受信(バックエンド→フロントエンド)
  fetch('/get_data', {[
    method: 'POST',
  })
  .then(response => response.json())
  .then(data => {
    console.log()
});
