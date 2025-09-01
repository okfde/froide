import store from './store'

// addfrontendbuild'ed by account/new.html and foirequest/sent.html

// note: this won't purge draft-specific storage
// (scope: make-request-draft-123, see RequestPage.created)
// but due to the nature of drafts this does not matter
// (they're both more specific and ephemeral)
store.dispatch('purgeStorage', { scope: 'make-request' })