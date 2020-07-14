import Room from "./lib/websocket.ts"

const room = new Room('/ws/moderation/')

room.connect().on('userlist', (data) => {
  document.getElementById('moderators').innerText = data.userlist.join(', ')
})
