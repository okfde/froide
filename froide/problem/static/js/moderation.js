(function() {

  const HEARTBEAT_INVERAL = 30 * 1000;

  let socket, retryInterval, heartBeatInterval

function connectSocket() {
  socket = createSocket();
  if (retryInterval) {
    window.clearInterval(retryInterval);
    retryInterval = undefined;
  }
  socket.onopen = () => {
    heartBeatInterval = setInterval(() => {
      if (socket && socket.readyState === 1) {
        socket.send(JSON.stringify({type: 'heartbeat'}));
      } else {
        window.clearInterval(heartBeatInterval);
        heartBeatInterval = undefined;
      }
    }, HEARTBEAT_INVERAL);
  };

  socket.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.userlist) {
      document.getElementById('moderators').innerText = data.userlist.join(', ')
    }
  };
  socket.onclose = () => {
    console.error('Chat socket closed unexpectedly');
    window.clearInterval(heartBeatInterval);
    heartBeatInterval = undefined;
    if (retryInterval === undefined) {
      retryInterval = window.setInterval(connectSocket, 3000);
    }
  };
}

function createSocket() {
  let prot = 'ws';
  if (document.location.protocol === 'https:') {
    prot = 'wss';
  }
  return new WebSocket(
    `${prot}://${window.location.host}/ws/moderation/`);
}



function ready(fn) {
  if (document.readyState != 'loading'){
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
}

ready(connectSocket)

}())
