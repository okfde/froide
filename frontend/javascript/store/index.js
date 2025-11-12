import { createStore } from 'vuex'

import {
  ADD_PUBLICBODY_ID,
  CACHE_LAWS,
  CACHE_PUBLICBODIES,
  CLEAR_PUBLICBODIES,
  CLEAR_SEARCHRESULTS,
  REMOVE_PUBLICBODY_ID,
  SET_CONFIG,
  SET_PUBLICBODIES,
  SET_PUBLICBODY,
  SET_PUBLICBODY_ID,
  SET_SEARCHRESULTS,
  SET_STEP,
  SET_STEP_NO_HISTORY,
  SET_STEP_REQUEST,
  SET_STEP_ACCOUNT,
  SET_STEP_REVIEW_PUBLICBODY,
  SET_STEP_SELECT_PUBLICBODY,
  SET_USER,
  STEPS,
  UPDATE_ADDRESS,
  UPDATE_ADDRESS_VALIDITY,
  UPDATE_ADDRESS_CHANGED,
  UPDATE_BODY,
  UPDATE_BODY_VALIDITY,
  UPDATE_BODY_CHANGED,
  UPDATE_EMAIL,
  UPDATE_EMAIL_VALIDITY,
  UPDATE_EMAIL_CHANGED,
  UPDATE_FIRST_NAME_VALIDITY,
  UPDATE_FIRST_NAME_CHANGED,
  UPDATE_FIRST_NAME,
  UPDATE_FULL_TEXT,
  UPDATE_LAST_NAME,
  UPDATE_LAST_NAME_VALIDITY,
  UPDATE_LAST_NAME_CHANGED,
  UPDATE_LAW_TYPE,
  UPDATE_PRIVATE,
  UPDATE_TERMS,
  UPDATE_TERMS_VALIDITY,
  UPDATE_TERMS_CHANGED,
  UPDATE_CONFIRM,
  UPDATE_CONFIRM_VALIDITY,
  UPDATE_SUBJECT,
  UPDATE_SUBJECT_VALIDITY,
  UPDATE_SUBJECT_CHANGED,
  UPDATE_USER_ID,
  UPDATE_REQUEST_PUBLIC,
  UPDATE_SIMILAR_REQUEST_SEARCH,
} from './mutation_types'

import { FroideAPI } from '../lib/api'
import { selectBestLaw } from '../lib/law-select'

const persistStorage = window.sessionStorage
const persistKeyPrefix = 'froide-store-'

const getInitialStep = () => {
  // if (document.location.hash === '#step-submit') return STEPS.PREVIEW_SUBMIT
  return STEPS.INTRO
}

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
      step: getInitialStep(),
      subject: '',
      subjectValid: undefined,
      subjectChanged: false,
      body: '',
      bodyValid: undefined,
      bodyChanged: false,
      fullText: false,
      requestPublic: false,
      addressValid: undefined,
      addressChanged: false,
      firstNameValid: undefined,
      firstNameChanged: false,
      lastNameValid: undefined,
      lastNameChanged: false,
      emailValid: undefined,
      emailChanged: false,
      similarRequestSearch: {},
    }
  },
  getters: {
    getPublicBodyByScope: (_state, getters) => (scope) => {
      const pbs = getters.getPublicBodiesByScope(scope)
      if (pbs.length === 0) {
        return null
      }
      return pbs[0]
    },
    getPublicBodiesByScope: (state) => (scope) => {
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
    getScopedSearchResults: (state) => (scope) => {
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
    subjectValid: (state) => state.subjectValid,
    subjectChanged: (state) => state.subjectChanged,
    getSubject: (state) => () => state.subject,
    body: (state) => state.body,
    bodyValid: (state) => state.bodyValid,
    bodyChanged: (state) => state.bodyChanged,
    fullText: (state) => state.fullText,
    stepSelectPublicBody: (state) => state.step === STEPS.SELECT_PUBLICBODY,
    stepSelectPublicBodyDone: (state) => state.step > STEPS.SELECT_PUBLICBODY,
    stepReviewPublicBodies: (state) => state.step === STEPS.REVIEW_PUBLICBODY,
    stepReviewPublicBodiesDone: (state) => state.step > STEPS.REVIEW_PUBLICBODY,
    stepWriteRequest: (state) => state.step === STEPS.WRITE_REQUEST,
    stepWriteRequestDone: (state) => state.step > STEPS.WRITE_REQUEST,
    step: (state) => state.step,
    lawType: (state) => state.lawType,
    userValid: (state) => {
      if (state.user.id) return true
      return state.firstNameValid && state.lastNameValid && state.emailValid
    },
    termsValid: (state) => state.termsValid,
    termsChanged: (state) => state.termsChanged,
    confirmValid: (state) => state.user.confirm && state.confirmValid,
    firstNameValid: (state) => state.firstNameValid,
    firstNameChanged: (state) => state.firstNameChanged,
    lastNameValid: (state) => state.lastNameValid,
    lastNameChanged: (state) => state.lastNameChanged,
    emailValid: (state) => state.emailValid,
    emailChanged: (state) => state.emailChanged,
    addressValid: (state) => state.addressValid,
    addressChanged: (state) => state.addressChanged,
    requestPublic: (state) => state.requestPublic,
    stepCanContinue: (state, getters) => (scope) => {
      switch (state.step) {
        case STEPS.SELECT_PUBLICBODY:
        case STEPS.REVIEW_PUBLICBODY:
          return getters.getPublicBodiesByScope(scope).length > 0
        case STEPS.CREATE_ACCOUNT:
          if (!getters.addressValid) return false
          // authenticated user only needs valid address
          if (state.user.id) return true
          if (!getters.userValid) return false
          if (!getters.termsValid) return false
          return true
        case STEPS.WRITE_REQUEST:
          if (!getters.subjectValid) return false
          if (!getters.bodyValid) return false
          if (!getters.confirmValid) return false
          return true
        default:
          return true
      }
    }
  },
  mutations: {
    [SET_CONFIG](state, config) {
      if (state.config === null || state.config === undefined) {
        state.config = config
      }
    },
    [SET_STEP](state, step) {
      state.step = step
      window.history.pushState({ step: state.step }, '', '#step-' + state.step)
    },
    [SET_STEP_NO_HISTORY](state, step) {
      state.step = step
    },
    [SET_STEP_SELECT_PUBLICBODY](state) {
      state.step = STEPS.SELECT_PUBLICBODY
    },
    [SET_STEP_REVIEW_PUBLICBODY](state) {
      state.step = STEPS.REVIEW_PUBLICBODY
    },
    [SET_STEP_ACCOUNT](state) {
      state.step = STEPS.CREATE_ACCOUNT
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
    [SET_PUBLICBODIES](state, { publicBodies, scopedPublicBodies, scope }) {
      publicBodies = publicBodies || scopedPublicBodies
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
    [UPDATE_SUBJECT_VALIDITY](state, validity) {
      state.subjectValid = validity
    },
    [UPDATE_SUBJECT_CHANGED](state, changed) {
      state.subjectChanged = changed
    },
    [UPDATE_BODY](state, body) {
      state.body = body
    },
    [UPDATE_BODY_VALIDITY](state, validity) {
      state.bodyValid = validity
    },
    [UPDATE_BODY_CHANGED](state, changed) {
      state.bodyChanged = changed
    },
    [UPDATE_FIRST_NAME](state, firstName) {
      state.user.first_name = firstName
    },
    [UPDATE_FIRST_NAME_VALIDITY](state, validity) {
      state.firstNameValid = validity
    },
    [UPDATE_FIRST_NAME_CHANGED](state, changed) {
      state.firstNameChanged = changed
    },
    [UPDATE_LAST_NAME](state, lastName) {
      state.user.last_name = lastName
    },
    [UPDATE_LAST_NAME_VALIDITY](state, validity) {
      state.lastNameValid = validity
    },
    [UPDATE_LAST_NAME_CHANGED](state, changed) {
      state.lastNameChanged = changed
    },
    [UPDATE_ADDRESS](state, address) {
      state.user.address = address
    },
    [UPDATE_ADDRESS_VALIDITY](state, validity) {
      state.addressValid = validity
    },
    [UPDATE_ADDRESS_CHANGED](state, changed) {
      state.addressChanged = changed
    },
    [UPDATE_EMAIL](state, email) {
      state.user.email = email
    },
    [UPDATE_EMAIL_VALIDITY](state, validity) {
      state.emailValid = validity
    },
    [UPDATE_EMAIL_CHANGED](state, changed) {
      state.emailChanged = changed
    },
    [UPDATE_PRIVATE](state, val) {
      state.user.private = val
    },
    [UPDATE_USER_ID](state, val) {
      state.user.id = val
    },
    [UPDATE_TERMS](state, val) {
      state.user.terms = val
    },
    [UPDATE_TERMS_VALIDITY](state, validity) {
      state.termsValid = validity
    },
    [UPDATE_TERMS_CHANGED](state, changed) {
      state.termsChanged = changed
    },
    [UPDATE_CONFIRM](state, val) {
      state.user.confirm = val
    },
    [UPDATE_CONFIRM_VALIDITY](state, validity) {
      state.confirmValid = validity
    },
    [UPDATE_REQUEST_PUBLIC](state, val) {
      state.requestPublic = val
    },
    [UPDATE_SIMILAR_REQUEST_SEARCH](state, v) {
      state.similarRequestSearch = v
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
    writeToStorage({ state }, { scope }) {
      // TODO publicbodies might need special handling
      /*
      const scopedPublicBodesIds = Object.keys(state.scopedPublicBodies)
        .reduce((acc, cur) => {
          acc[cur] = state.scopedPublicBodies[cur].map(pb => pb.id)
          return acc
        }, {})
        console.log('###', scopedPublicBodesIds)
        */
      const reduced = {
        // scopedPublicBodies: state.scopedPublicBodies,
        lawType: state.lawType,
        step: state.step,
        subject: state.subject,
        body: state.body,
        // publicBodiesIds: state.scopedPublicBodies[scope].map(pb => pb.id),
        publicBodies: state.scopedPublicBodies[scope],
        public: state.requestPublic,
        address: state.user.address,
        user_email: state.user.email,
        first_name: state.user.first_name,
        last_name: state.user.last_name,
        private: state.user.private,
        terms: state.user.terms,
        confirm: state.user.confirm,
        similarRequestSearch: state.similarRequestSearch,
      }
      try {
        persistStorage.setItem(persistKeyPrefix + scope, JSON.stringify(reduced))
      } catch (err) {
        console.warn('failed to persist state', persistStorage, reduced, err)
      }
    },
    // also called directly from makerequest.js
    purgeStorage({ state }, { scope, keepStep }) {
      const purged = keepStep
        ? { step: state.step }
        : null
      try {
        // persistStorage.removeItem(persistKey)
        if (purged) {
          persistStorage.setItem(persistKeyPrefix + scope, JSON.stringify(purged))
          console.log('purged, keeping', persistKeyPrefix + scope, purged)
        } else {
          persistStorage.removeItem(persistKeyPrefix + scope)
          console.log('purged, removed', persistKeyPrefix + scope)
        }
      } catch (err) {
        console.warn('failed to purge persisted state', persistKeyPrefix + scope, err)
      }
    },
    initStoreValues({ commit }, { formFields, formCoerce, mutationMap, propMap, preferStorage, scope, scoped }) {
      // TODO cache me, scoped: if ! scope in storage try...
      let storage
      try {
        storage = JSON.parse(persistStorage.getItem(persistKeyPrefix + scope))
      } catch (err) {
        console.warn('failed to load persisted state', persistStorage, persistKeyPrefix + scope, err)
      }
      for (const key in mutationMap) {
        const mutation = mutationMap[key]
        let value
        if (preferStorage && storage && storage[key] !== undefined) {
          value = storage[key]
          console.log('got', key, 'from storage', value)
        } else if (propMap && propMap[key]) {
          // prop has precedence over formField, e.g. for publicBodies
          value = propMap[key]
          console.log('got', key, 'from prop')
        } else if (formFields && formFields[key] !== undefined) {
          value = formFields[key].value
          if (value === undefined || value === null) value = formFields[key].initial
          if (formCoerce && formCoerce[key]) {
            value = formCoerce[key](value)
          }
          console.log('got', key, 'from form', value)
        } else {
          console.log('could not get', key)
        }
        if (value === undefined) continue
        if (scoped) {
          commit(mutation, { [key]: value, scope })
        } else {
          commit(mutation, value)
        }
      }
    },
    setSearchResults({ commit, dispatch }, { scope, results }) {
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
    getSearchResultsUrl({ commit, state, dispatch }, { scope, url }) {
      commit(CLEAR_SEARCHRESULTS, { scope })
      const searcher = new FroideAPI(state.config)
      return searcher.getJson(url).then((results) => {
        dispatch('setSearchResults', { results, scope })
      })
    },
    getNextSearchResults({ getters, dispatch }, scope) {
      const meta = getters.getScopedSearchMeta(scope)
      return dispatch('getSearchResultsUrl', { url: meta.next, scope })
    },
    getPreviousSearchResults({ getters, dispatch }, scope) {
      const meta = getters.getScopedSearchMeta(scope)
      return dispatch('getSearchResultsUrl', {
        url: meta.previous,
        scope
      })
    }
  },
  strict: false
})
