// make-request stores PII in sessionStorage -- but it will survive a logout.
// so we use the messages extra_tags "channel" to indicate that a logout has happened,
// and then we bluntly clear *all* storage, unscoped

export function purgeStorageAfterLogout () {
  if (document.querySelector('.alert-loggedout')) {
    console.log('found loggedout message, purging storage')
    try {
      window.sessionStorage.clear()
    } catch (err) {
      console.warn('purging failed', err)
    }
  }
}