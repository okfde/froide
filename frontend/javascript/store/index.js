import Vue from 'vue'
import Vuex from 'vuex'

import {
  SET_CONFIG,
  SET_STEP, SET_STEP_BY_URL, SET_STEP_PUBLICBODY, SET_STEP_REQUEST,
  STEPS, URLS_TO_STEP,
  SET_PUBLICBODY, SET_PUBLICBODIES,
  SET_PUBLICBODY_ID, ADD_PUBLICBODY_ID, REMOVE_PUBLICBODY_ID,
  CLEAR_PUBLICBODIES,
  CACHE_PUBLICBODIES,
  SET_SEARCHRESULTS, CLEAR_SEARCHRESULTS,
  SET_USER,
  UPDATE_SUBJECT, UPDATE_BODY, UPDATE_FULL_TEXT,
  UPDATE_FIRST_NAME, UPDATE_LAST_NAME, UPDATE_EMAIL, UPDATE_ADDRESS,
  UPDATE_PRIVATE, UPDATE_USER_ID
} from './mutation_types'

import {FroideSearch} from '../lib/search'

Vue.use(Vuex)

const debug = process.env.NODE_ENV !== 'production'

export default new Vuex.Store({
  state: {
    config: null,
    scopedSearchResults: {},
    scopedSearchFacets: {},
    scopedSearchMeta: {},
    scopedPublicBodies: {},
    publicBodies: {},
    user: {},
    step: STEPS.SELECT_PUBLICBODY,
    subject: '',
    body: '',
    fullText: false
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
      let pbs = state.scopedPublicBodies[scope]
      if (pbs === undefined) {
        return []
      }
      return pbs
    },
    isPublicBodySelectedByScope: (state, getters) => (scope, id) => {
      let pbs = state.scopedPublicBodies[scope]
      if (pbs === undefined) {
        return false
      }
      return pbs.some((r) => r.id === id)
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
    getScopedSearchFacets: (state, getters) => (scope) => {
      let facets = state.scopedSearchFacets[scope]
      if (facets === undefined) {
        return null
      }
      return facets
    },
    getScopedSearchMeta: (state, getters) => (scope) => {
      let meta = state.scopedSearchMeta[scope]
      if (meta === undefined) {
        return null
      }
      return meta
    },
    defaultLaw: (state) => {
      var key = null
      for (key in state.scopedPublicBodies) {}
      let pbs = state.scopedPublicBodies[key]
      let sameLaw = true
      for (let i = 0; i < pbs.length - 1; i += 1) {
        let a = pbs[i]
        let b = pbs[i + 1]
        if (a.default_law.id !== b.default_law.id) {
          sameLaw = false
          break
        }
      }
      if (sameLaw && pbs.length > 0) {
        return pbs[0].default_law
      } else {
        return null
      }
    },
    user: state => {
      return state.user
    },
    subject: state => state.subject,
    getSubject: state => () => state.subject,
    body: state => state.body,
    fullText: state => state.fullText,
    stepSelectPublicBody: state => state.step === STEPS.SELECT_PUBLICBODY,
    stepReviewReady: state => state.step >= STEPS.WRITE_REQUEST
  },
  mutations: {
    [SET_CONFIG] (state, config) {
      state.config = config
    },
    [SET_STEP] (state, step) {
      state.step = step
    },
    [SET_STEP_PUBLICBODY] (state) {
      state.step = STEPS.SELECT_PUBLICBODY
    },
    [SET_STEP_REQUEST] (state) {
      state.step = STEPS.WRITE_REQUEST
    },
    [SET_PUBLICBODY] (state, {publicBody, scope}) {
      Vue.set(state.scopedPublicBodies, scope, [publicBody])
    },
    [SET_PUBLICBODIES] (state, {publicBodies, scope}) {
      Vue.set(state.scopedPublicBodies, scope, publicBodies)
    },
    [SET_PUBLICBODY_ID] (state, {publicBodyId, scope}) {
      let pb = state.publicBodies[publicBodyId]
      Vue.set(state.scopedPublicBodies, scope, [pb])
    },
    [ADD_PUBLICBODY_ID] (state, {publicBodyId, scope}) {
      let pb = state.publicBodies[publicBodyId]
      if (pb === undefined) {
        return
      }
      let pbs = state.scopedPublicBodies[scope]
      if (pbs === undefined) {
        Vue.set(state.scopedPublicBodies, scope, [pb])
      } else {
        let contains = pbs.some((p) => p.id === pb.id)
        if (!contains) {
          Vue.set(state.scopedPublicBodies, scope, [
            ...pbs,
            ...[pb]
          ])
        }
      }
    },
    [REMOVE_PUBLICBODY_ID] (state, {publicBodyId, scope}) {
      let pbs = state.scopedPublicBodies[scope]
      if (pbs === undefined) {
        return
      }
      pbs = pbs.filter((p) => p.id !== publicBodyId)
      Vue.set(state.scopedPublicBodies, scope, pbs)
    },
    [CLEAR_PUBLICBODIES] (state, {scope}) {
      Vue.set(state.scopedPublicBodies, scope, [])
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
    [SET_SEARCHRESULTS] (state, {searchResults, searchFacets, searchMeta, scope}) {
      Vue.set(state.scopedSearchResults, scope, searchResults)
      Vue.set(state.scopedSearchFacets, scope, searchFacets)
      Vue.set(state.scopedSearchMeta, scope, searchMeta)
    },
    [CLEAR_SEARCHRESULTS] (state, {scope}) {
      Vue.set(state.scopedSearchResults, scope, [])
      Vue.set(state.scopedSearchFacets, scope, {})
      Vue.set(state.scopedSearchMeta, scope, null)
    },
    [UPDATE_FULL_TEXT] (state, val) {
      state.fullText = val
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
  actions: {
    [SET_STEP_BY_URL] ({commit, getters}, {hash, scope}) {
      let step = URLS_TO_STEP[hash]
      if (step === undefined) {
        return
      }
      let pbs = getters.getPublicBodiesByScope(scope)
      if (step > STEPS.SELECT_PUBLICBODY && pbs.length === 0) {
        return
      }
      commit(SET_STEP, step)
    },
    setSearchResults ({ commit }, {scope, results}) {
      commit(SET_SEARCHRESULTS, {
        searchResults: results.objects.results,
        searchFacets: results.objects.facets.fields,
        searchMeta: results.meta,
        scope: scope
      })
      commit(CACHE_PUBLICBODIES, results.objects.results)
    },
    getSearchResults ({ commit, state, dispatch }, {scope, search, filters}) {
      commit(CLEAR_SEARCHRESULTS, {scope})
      let searcher = new FroideSearch(state.config)
      return searcher.searchPublicBodies(search, filters).then((results) => {
        dispatch('setSearchResults', {results, scope})
      })
    },
    getSearchResultsUrl ({ commit, state, getters, dispatch }, { scope, url }) {
      commit(CLEAR_SEARCHRESULTS, {scope})
      let searcher = new FroideSearch(state.config)
      return searcher.getJson(url).then((results) => {
        dispatch('setSearchResults', {results, scope})
      })
    },
    getNextSearchResults ({ state, getters, dispatch }, scope) {
      let meta = getters.getScopedSearchMeta(scope)
      return dispatch('getSearchResultsUrl', {url: meta.next, scope: scope})
    },
    getPreviousSearchResults ({ state, getters, dispatch }, scope) {
      let meta = getters.getScopedSearchMeta(scope)
      return dispatch('getSearchResultsUrl', {url: meta.previous, scope: scope})
    }
  },
  strict: debug
})
