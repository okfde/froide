import Vue from 'vue'
import Vuex from 'vuex'

import {
  SET_PUBLICBODY, SET_PUBLICBODIES,
  CACHE_PUBLICBODIES,
  SET_SEARCHRESULTS, CLEAR_SEARCHRESULTS,
  SET_USER,
  UPDATE_SUBJECT, UPDATE_BODY,
  UPDATE_FIRST_NAME, UPDATE_LAST_NAME, UPDATE_EMAIL, UPDATE_ADDRESS,
  UPDATE_PRIVATE, UPDATE_USER_ID
} from './mutation_types'

Vue.use(Vuex)

const STEPS = {
  SELECT_PUBLICBODY: 1,
  CONFIRM_PURPOSE: 2,
  WRITE_REQUEST: 3,
  COMPLETE_PROFILE: 4,
  CONFIRM_REQUEST: 5
}

const debug = process.env.NODE_ENV !== 'production'

const setPublicbodyDetail = function (state, publicbody, scope) {
  if (state.scopedPublicbodyDetails[scope] === undefined) {
    Vue.set(state.scopedPublicbodyDetails, scope, {
      [publicbody.id]: publicbody
    })
  } else {
    Vue.set(state.scopedPublicbodyDetails, scope, {
      [publicbody.id]: publicbody,
      ...state.scopedPublicbodyDetails[scope]
    })
  }

  state.defaultLaw = publicbody.default_law
}

export default new Vuex.Store({
  state: {
    scopedSearchResults: {},
    scopedSearchMeta: {},
    scopedPublicbodies: {},
    publicBodies: {},
    user: {},
    defaultLaw: null,
    step: STEPS.SELECT_PUBLICBODY,
    subject: '',
    body: ''
  },
  getters: {
    getPublicBodyByScope: (state, getters) => (scope) => {
      let pbs = getters.getPublicBodiesByScope(scope)
      if (pbs.length === 0) {
        return null
      }
      return pbs[0]
    },
    getPublicBodiesByScope: (state, getters) => (scope) => {
      let pbs = state.scopedPublicbodies[scope]
      if (pbs === undefined) {
        return []
      }
      return pbs
    },
    getPublicBody: (state, getters) => (id) => {
      return state.publicBodies[id]
    },
    getScopedSearchResults: (state, getters) => (scope) => {
      let srs = state.scopedSearchResults[scope]
      if (srs === undefined) {
        return []
      }
      return srs
    },
    getScopedSearchMeta: (state, getters) => (scope) => {
      let meta = state.scopedSearchMeta[scope]
      if (meta === undefined) {
        return null
      }
      return meta
    },
    defaultLaw: state => {
      return state.defaultLaw
    },
    user: state => {
      return state.user
    },
    subject: state => state.subject,
    getSubject: state => () => state.subject,
    body: state => state.body,
    stepSelectPublicbody: state => state.step === STEPS.SELECT_PUBLICBODY,
    stepReviewReady: state => state.step >= STEPS.WRITE_REQUEST
  },
  mutations: {
    [SET_PUBLICBODY] (state, {publicbody, scope}) {
      Vue.set(state.scopedPublicbodies, scope, [publicbody])
      state.defaultLaw = publicbody.default_law
      state.step = STEPS.WRITE_REQUEST
    },
    [SET_PUBLICBODIES] (state, {publicbodies, scope}) {
      Vue.set(state.scopedPublicbodies, scope, publicbodies)
      let sameLaw = publicbodies.reduce((a, b) => {
        if (a === null) {
          return true
        }
        return a.id === b.id
      }, null)
      if (sameLaw) {
        state.defaultLaw = publicbodies[0].default_law
      } else {
        state.defaultLaw = null
      }
      state.step = STEPS.WRITE_REQUEST
    },
    [CACHE_PUBLICBODIES] (state, publicBodies) {
      let newPublicBodies = {}
      publicBodies.forEach(function (r) {
        newPublicBodies[r.id] = r
      })
      state.publicBodies = {
        ...state.publicBodies,
        ...newPublicBodies
      }
    },
    [SET_SEARCHRESULTS] (state, {searchResults, searchMeta, scope}) {
      Vue.set(state.scopedSearchResults, scope, searchResults)
      Vue.set(state.scopedSearchMeta, scope, searchMeta)
    },
    [CLEAR_SEARCHRESULTS] (state, {scope}) {
      Vue.set(state.scopedSearchResults, scope, [])
      Vue.set(state.scopedSearchMeta, scope, null)
    },
    [SET_USER] (state, user) {
      state.user = user
    },
    [UPDATE_SUBJECT] (state, subject) {
      state.subject = subject
    },
    [UPDATE_BODY] (state, body) {
      state.body = body
    },
    [UPDATE_FIRST_NAME] (state, firstName) {
      Vue.set(state.user, 'first_name', firstName)
    },
    [UPDATE_LAST_NAME] (state, lastName) {
      Vue.set(state.user, 'last_name', lastName)
    },
    [UPDATE_ADDRESS] (state, address) {
      Vue.set(state.user, 'address', address)
    },
    [UPDATE_EMAIL] (state, email) {
      Vue.set(state.user, 'email', email)
    },
    [UPDATE_PRIVATE] (state, val) {
      Vue.set(state.user, 'private', val)
    },
    [UPDATE_USER_ID] (state, val) {
      Vue.set(state.user, 'id', val)
    }
  },
  strict: debug
})
