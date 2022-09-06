import { createStore } from 'vuex'

import {
  SET_CONFIG,
  SET_STEP,
  SET_STEP_SELECT_PUBLICBODY,
  SET_STEP_REVIEW_PUBLICBODY,
  SET_STEP_REQUEST,
  STEPS,
  SET_PUBLICBODY,
  SET_PUBLICBODIES,
  SET_PUBLICBODY_ID,
  ADD_PUBLICBODY_ID,
  REMOVE_PUBLICBODY_ID,
  CLEAR_PUBLICBODIES,
  CACHE_PUBLICBODIES,
  CACHE_LAWS,
  SET_SEARCHRESULTS,
  CLEAR_SEARCHRESULTS,
  UPDATE_LAW_TYPE,
  SET_USER,
  UPDATE_SUBJECT,
  UPDATE_BODY,
  UPDATE_FULL_TEXT,
  UPDATE_FIRST_NAME,
  UPDATE_LAST_NAME,
  UPDATE_EMAIL,
  UPDATE_ADDRESS,
  UPDATE_PRIVATE,
  UPDATE_USER_ID
} from './mutation_types'

import { FroideAPI } from '../lib/api'
import { selectBestLaw } from '../lib/law-select'

const debug = process.env.NODE_ENV !== 'production'

export default createStore({
  state() {
    return {
      config: null,
      scopedSearchResults: {},
      scopedSearchFacets: {},
      scopedSearchMeta: {},
      scopedPublicBodies: {},
      scopedPublicBodiesMap: {},
      lawCache: {},
      publicBodies: {},
      lawType: null,
      user: {},
      step: STEPS.SELECT_PUBLICBODY,
      subject: '',
      body: '',
      fullText: false
    }
  },
  getters: {
    getPublicBodyByScope: (state, getters) => (scope) => {
      const pbs = getters.getPublicBodiesByScope(scope)
      if (pbs.length === 0) {
        return null
      }
      return pbs[0]
    },
    getPublicBodiesByScope: (state, getters) => (scope) => {
      const pbs = state.scopedPublicBodies[scope]
      if (pbs === undefined) {
        return []
      }
      return pbs
    },
    isPublicBodySelectedByScope: (state) => (scope, id) => {
      const pbMap = state.scopedPublicBodiesMap[scope]
      if (pbMap === undefined) {
        return false
      }
      return pbMap[id] !== undefined
    },
    getPublicBody: (state) => (id) => {
      return state.publicBodies[id]
    },
    getScopedSearchResults: (state, getters) => (scope) => {
      const srs = state.scopedSearchResults[scope]
      if (srs === undefined) {
        return []
      }
      return srs
    },
    getScopedSearchFacets: (state) => (scope) => {
      const facets = state.scopedSearchFacets[scope]
      if (facets === undefined) {
        return null
      }
      return facets
    },
    getScopedSearchMeta: (state) => (scope) => {
      const meta = state.scopedSearchMeta[scope]
      if (meta === undefined) {
        return null
      }
      return meta
    },
    getLawsForPublicBody: (state) => (pb) => {
      return pb.laws
        .map((law) => {
          return state.lawCache[law]
        })
        .filter((law) => law !== undefined)
    },
    defaultLaw: (state, getters) => {
      // Get first key in scoped public bodies
      const key = Object.keys(state.scopedPublicBodies)[0]
      const pbs = state.scopedPublicBodies[key] || []
      let lastLaw = null
      let sameLaw = true
      for (let i = 0; i < pbs.length; i += 1) {
        const pb = pbs[i]
        const laws = getters.getLawsForPublicBody(pb)
        const bestLaw = selectBestLaw(laws, state.lawType)
        if (bestLaw === null) {
          continue
        }
        if (i === 0) {
          lastLaw = bestLaw
          continue
        }
        if (lastLaw.id !== bestLaw.id) {
          sameLaw = false
          break
        }
        lastLaw = bestLaw
      }
      if (sameLaw) {
        return lastLaw
      }
      return null
    },
    user: (state) => {
      return state.user
    },
    subject: (state) => state.subject,
    getSubject: (state) => () => state.subject,
    body: (state) => state.body,
    fullText: (state) => state.fullText,
    stepSelectPublicBody: (state) => state.step === STEPS.SELECT_PUBLICBODY,
    stepSelectPublicBodyDone: (state) => state.step > STEPS.SELECT_PUBLICBODY,
    stepReviewPublicBodies: (state) => state.step === STEPS.REVIEW_PUBLICBODY,
    stepReviewPublicBodiesDone: (state) => state.step > STEPS.REVIEW_PUBLICBODY,
    stepWriteRequest: (state) => state.step === STEPS.WRITE_REQUEST,
    stepWriteRequestDone: (state) => state.step > STEPS.WRITE_REQUEST,
    step: (state) => state.step,
    lawType: (state) => state.lawType
  },
  mutations: {
    [SET_CONFIG](state, config) {
      if (state.config === null || state.config === undefined) {
        state.config = config
      }
    },
    [SET_STEP](state, step) {
      state.step = step
    },
    [SET_STEP_SELECT_PUBLICBODY](state) {
      state.step = STEPS.SELECT_PUBLICBODY
    },
    [SET_STEP_REVIEW_PUBLICBODY](state) {
      state.step = STEPS.REVIEW_PUBLICBODY
    },
    [SET_STEP_REQUEST](state) {
      state.step = STEPS.WRITE_REQUEST
    },
    [SET_PUBLICBODY](state, { publicBody, scope }) {
      state.scopedPublicBodies[scope] = [publicBody]
      state.scopedPublicBodiesMap[scope] = { [publicBody.id]: true }
      state.scopedSearchResults[scope].forEach((sr) => {
        if (sr.id === publicBody.id) {
          sr.isSelected = true
        } else {
          sr.isSelected = false
        }
      })
    },
    [SET_PUBLICBODIES](state, { publicBodies, scope }) {
      state.scopedPublicBodies[scope] = publicBodies
      const pbMap = {}
      publicBodies.forEach((pb) => {
        pbMap[pb.id] = true
      })
      state.scopedPublicBodiesMap[scope] = pbMap
      if (state.scopedSearchResults[scope]) {
        state.scopedSearchResults[scope].forEach((sr) => {
          if (pbMap[sr.id] !== undefined) {
            sr.isSelected = true
          } else {
            sr.isSelected = false
          }
        })
      }
    },
    [SET_PUBLICBODY_ID](state, { publicBodyId, scope }) {
      const pb = state.publicBodies[publicBodyId]
      state.scopedPublicBodies[scope] = [pb]
      state.scopedPublicBodiesMap[scope] = { publicBodyId: true }
      if (state.scopedSearchResults[scope]) {
        state.scopedSearchResults[scope].forEach((sr) => {
          if (sr.id === publicBodyId) {
            sr.isSelected = true
          } else {
            sr.isSelected = false
          }
        })
      }
    },
    [ADD_PUBLICBODY_ID](state, { publicBodyId, scope }) {
      const pb = state.publicBodies[publicBodyId]
      if (pb === undefined) {
        return
      }
      const pbs = state.scopedPublicBodies[scope]
      if (pbs === undefined) {
        state.scopedPublicBodies[scope] = [pb]
      } else {
        const contains = pbs.some((p) => p.id === pb.id)
        if (!contains) {
          state.scopedPublicBodies[scope] = [...pbs, ...[pb]]
        }
      }
      state.scopedPublicBodiesMap[scope][publicBodyId] = true
      if (state.scopedSearchResults[scope]) {
        state.scopedSearchResults[scope].forEach((sr) => {
          if (sr.id === publicBodyId) {
            sr.isSelected = true
          }
        })
      }
    },
    [REMOVE_PUBLICBODY_ID](state, { publicBodyId, scope }) {
      let pbs = state.scopedPublicBodies[scope]
      if (pbs === undefined) {
        return
      }
      pbs = pbs.filter((p) => p.id !== publicBodyId)
      state.scopedPublicBodies[scope] = pbs
      state.scopedPublicBodiesMap[scope][publicBodyId] = undefined
      if (state.scopedSearchResults[scope]) {
        state.scopedSearchResults[scope].forEach((sr) => {
          if (sr.id === publicBodyId) {
            sr.isSelected = false
          }
        })
      }
    },
    [CLEAR_PUBLICBODIES](state, { scope }) {
      state.scopedPublicBodies[scope] = []
      state.scopedPublicBodiesMap[scope] = {}
      if (state.scopedSearchResults[scope]) {
        state.scopedSearchResults[scope].forEach((sr) => {
          sr.isSelected = false
        })
      }
    },
    [CACHE_PUBLICBODIES](state, publicBodies) {
      const newPublicBodies = {}
      if (!publicBodies) {
        return
      }
      publicBodies.forEach(function (r) {
        newPublicBodies[r.id] = r
      })
      state.publicBodies = {
        ...state.publicBodies,
        ...newPublicBodies
      }
    },
    [SET_SEARCHRESULTS](
      state,
      { searchResults, searchFacets, searchMeta, scope }
    ) {
      state.scopedPublicBodiesMap[scope] =
        state.scopedPublicBodiesMap[scope] || {}
      searchResults = searchResults.map((sr) => {
        sr.isSelected = state.scopedPublicBodiesMap[scope][sr.id] !== undefined
        return sr
      })
      state.scopedSearchResults[scope] = searchResults
      state.scopedSearchFacets[scope] = searchFacets
      state.scopedSearchMeta[scope] = searchMeta
    },
    [CLEAR_SEARCHRESULTS](state, { scope }) {
      state.scopedSearchResults[scope] = []
      state.scopedSearchFacets[scope] = {}
      state.scopedSearchMeta[scope] = null
    },
    [UPDATE_FULL_TEXT](state, val) {
      state.fullText = val
    },
    [SET_USER](state, user) {
      state.user = user
    },
    [UPDATE_SUBJECT](state, subject) {
      state.subject = subject
    },
    [UPDATE_BODY](state, body) {
      state.body = body
    },
    [UPDATE_FIRST_NAME](state, firstName) {
      state.user.first_name = firstName
    },
    [UPDATE_LAST_NAME](state, lastName) {
      state.user.last_name = lastName
    },
    [UPDATE_ADDRESS](state, address) {
      state.user.address = address
    },
    [UPDATE_EMAIL](state, email) {
      state.user.email = email
    },
    [UPDATE_PRIVATE](state, val) {
      state.user.private = val
    },
    [UPDATE_USER_ID](state, val) {
      state.user.id = val
    },
    [UPDATE_LAW_TYPE](state, val) {
      state.lawType = val
    },
    [CACHE_LAWS](state, { laws }) {
      laws.forEach((law) => {
        state.lawCache[law.resource_uri] = law
      })
    }
  },
  actions: {
    setSearchResults({ commit, state, dispatch }, { scope, results }) {
      commit(SET_SEARCHRESULTS, {
        searchResults: results.objects,
        searchFacets: results.facets.fields,
        searchMeta: results.meta,
        scope
      })
      commit(CACHE_PUBLICBODIES, results.objects)
      dispatch('getLawsForPublicBodies', results.objects)
    },
    cacheLaws({ commit }, { laws }) {
      commit(CACHE_LAWS, {
        laws
      })
    },
    getLawsForPublicBodies({ state, dispatch }, publicBodies) {
      const searcher = new FroideAPI(state.config)
      searcher
        .getLawsForPublicBodies(publicBodies, state.lawCache)
        .then((laws) => {
          dispatch('cacheLaws', { laws })
        })
    },
    getSearchResults({ commit, state, dispatch }, { scope, search, filters }) {
      commit(CLEAR_SEARCHRESULTS, { scope })
      const searcher = new FroideAPI(state.config)
      return searcher.searchPublicBodies(search, filters).then((results) => {
        dispatch('setSearchResults', { results, scope })
      })
    },
    setPublicBodyById({ state, dispatch }, { scope, id }) {
      const searcher = new FroideAPI(state.config)
      return searcher.getPublicBody(id).then((result) => {
        dispatch('setPublicBodyByIdDone', { result, scope, id })
      })
    },
    setPublicBodyByIdDone({ commit, dispatch }, { scope, result, id }) {
      commit(CACHE_PUBLICBODIES, [result])
      commit(SET_PUBLICBODY_ID, { publicBodyId: id, scope })
      commit(SET_STEP_REQUEST)
      dispatch('getLawsForPublicBodies', [result])
    },
    getSearchResultsUrl({ commit, state, getters, dispatch }, { scope, url }) {
      commit(CLEAR_SEARCHRESULTS, { scope })
      const searcher = new FroideAPI(state.config)
      return searcher.getJson(url).then((results) => {
        dispatch('setSearchResults', { results, scope })
      })
    },
    getNextSearchResults({ state, getters, dispatch }, scope) {
      const meta = getters.getScopedSearchMeta(scope)
      return dispatch('getSearchResultsUrl', { url: meta.next, scope })
    },
    getPreviousSearchResults({ state, getters, dispatch }, scope) {
      const meta = getters.getScopedSearchMeta(scope)
      return dispatch('getSearchResultsUrl', {
        url: meta.previous,
        scope
      })
    }
  },
  strict: debug
})
