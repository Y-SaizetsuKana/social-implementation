document.addEventListener('DOMContentLoaded', function() {
  //受信(バックエンド→フロントエンド)
  fetch('/get_data', {[
    method: 'POST',
  })
  .then(response => response.json())
  .then(data => {
    console.log('Back End', data);
  })
  .catch(error => {
    console.error('Error', error)
  });

  //送信(フロントエンド→バックエンド)
  const dataToPython = {messege: 'Input Data'};
  fetch('/receive_data', {
    method: 'POST',
    headers: [
      'Content-Type': 'application/json',
      },
       body: JSON.stringify(dataToPython),
  })
  .then(response => response.json())
  .then(data => {
    console.log('Back End:', data));
  })
  .catch(error => {
    consoke.error('Error', error);
  });
});
