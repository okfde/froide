import { getData, postData } from '../../../lib/api'
import { documentUpdate } from '../../../api'

import { pinia } from '../../../lib/pinia'
import { useAttachmentsStore } from './attachments-store'

import ExifReader from 'exifreader'

const store = useAttachmentsStore(pinia)

const makeRelevant = (attachment) => {
  store.addImages([attachment])
  store.removeAttachment(attachment)
}

const convertImage = (imageIndex) => {
  store.isConverting = true
  store.images[imageIndex].isConverting = true
  return postData(
    config.urls.convertAttachments,
    {
      action: 'convert_to_pdf',
      // normalize possible .pdf extension away
      title: store.images[imageIndex].name.replace(/\.pdf$/, ''),
      images: store.images[imageIndex].pages.map((p) => ({
        id: p.id,
        rotate: (p.rotate || 0) + (p.implicitRotate || 0)
      }))
    },
    config.csrfToken
  )
    .then((newAttachment) => {
      newAttachment.new = true
      store.images = store.images.filter((_, i) => i !== imageIndex)
      // append new
      store.allRaw.push(newAttachment)
    })
    .finally(() => {
      store.isConverting = false
    })
}

const createDocument = (attachment) => {
  const createDocumentUrl = config.urls.createDocument.replace(
    '/0/',
    `/${attachment.id}/`
  )
  store.creatingDocumentIds.add(attachment.id)
  return postData(createDocumentUrl, {}, config.csrfToken)
    .then(() => {
      return refetchAttachment(attachment)
    })
    .finally(() => {
      store.creatingDocumentIds.delete(attachment.id)
    })
}

const updateDocument = (attachment, { title, description }) => {
  return documentUpdate({
    path: { id: attachment.document.id },
    body: { title, description },
    throwOnError: true
  })
    .then(() => {
      return refetchAttachment(attachment)
    })
    .catch((err) => {
      store.messages.push({ body: err.detail || config.i18n.error || 'Error', color: 'danger' })
    })
}

// const wait = (ms) => (x) => new Promise(resolve => setTimeout(() => { console.log('#wait<'); resolve(x) }, ms))

// TODO: check how this relates to the post upload API work
const fetchAttachments = (url, csrfToken, paged = false) => {
  store.isFetching = true
  return fetch(url, {
    headers: { 'X-CSRFToken': csrfToken }
  })
    .then((response) => {
      if (!response.ok) {
        console.error('fetch attachment error', url, response)
        // TODO
        throw new Error(response.message)
      }
      return response.json()
    })
    .then((response) => {
      if (!paged) {
        store.$patch({
          allRaw: response.objects
        })
      } else {
        store.allRaw.push(...response.objects)
      }
      if (response.meta.next) {
        return fetchAttachments(response.meta.next, csrfToken, true)
      }
    })
    .finally(() => {
      store.isFetching = false
    })
}

const refetchAttachment = (attachment) => {
  const updateUrl = attachment.resource_uri
  return getData(updateUrl, { 'X-CSRFToken': config.csrfToken })
    .then((response) => {
      const index = store.allRaw.findIndex(att => att.id === attachment.id)
      store.allRaw[index] = response
    })
}

const fetchImagePage = (page) => {
  fetch(page.file_url)
    .then((response) => {
      return response.blob()
    })
    .then((blob) => {
      return Promise.all([blob.arrayBuffer(), createImageBitmap(blob)])
    })
    .then(([ab, v]) => {
      const reader = ExifReader.load(ab, { expanded: true })
      const metadata = {
        exif: true,
        width: v.width,
        heigh: v.height,
        implicitRotate: 0
      }
      const orientation = reader.exif?.Orientation?.value
      if (orientation === 6) {
        metadata.implicitRotate = 90
      } else if (orientation === 8) {
        metadata.implicitRotate = 270
      } else if (orientation === 3) {
        metadata.implicitRotate = 180
      }
      page.metadata = metadata
      page.imgBitmap = v
      page.loaded = true
    })
}

const addFromUppy = ({ uppy, response, file }, imageDefaultFilename = '') => {
  const uploadUrl = response.uploadURL
  return postData(
    config.urls.convertAttachments,
    {
      action: 'add_tus_attachment',
      upload: uploadUrl
    },
    config.csrfToken
  )
    .then((result) => {
      if (result.error) {
        // replace to cheaply "strip_tags" because this is a form snippet at the moment
        store.messages.push({ body: result.message.replace(/<.*?>/g, ' '), color: 'danger' })
        return
      }
      const att = result.added[0]
      if (att.is_image) {
        store.addImages([att], { imageDefaultFilename })
      } else {
        store.allRaw.push({ ...att, new: true })
      }
    })
    .then(() => {
      uppy.removeFile(file.id)
    })
}

const handleErrorAndRefresh = (err) => {
  console.error(err)
  if (confirm(`${config.i18n.value.genericErrorReload}\n\n(${err.message})`) === true) {
    refresh()
  }
}

const deleteAttachment = (attachment) => {
  const deleteUrl = config.urls.deleteAttachment.replace('/0/', `/${attachment.id}/`)
  // optimistically...
  store.removeAttachment(attachment)
  return postData(deleteUrl, {}, config.csrfToken, 'POST', true)
    .then(() => {
      store.messages.push({ body: `${config.i18n.value.attachmentDeleted} (${attachment.name})`, color: 'success-subtle' })
    })
    .catch(handleErrorAndRefresh)
}

const approveAttachment = (attachment) => {
  const approveUrl = config.urls.approveAttachment.replace('/0/', `/${attachment.id}/`)
  store.approvingIds.add(attachment.id)
  return postData(approveUrl, {}, config.csrfToken, 'POST', true)
    .then(() => {
      refetchAttachment(attachment, config.csrfToken)
    })
    .catch(handleErrorAndRefresh)
    .finally(() => {
      store.approvingIds.delete(attachment.id)
    })
}

const approveAllUnredactedAttachments = (excludeIds = []) => {
  const approvable = store.all.filter(att =>
    !att.approved &&
    att.can_approve &&
    !att.redacted &&
    !att.is_redacted &&
    !excludeIds.includes(att.id)
  )
  return Promise.all(approvable.map(attachment => {
    const approveUrl = config.urls.approveAttachment.replace('/0/', `/${attachment.id}/`)
    return postData(approveUrl, {}, config.csrfToken, 'POST')
  }))
}

const config = {}

const refresh = () => fetchAttachments(config.urls.getAttachment, config.csrfToken)
  .catch(handleErrorAndRefresh)

store.$subscribe(() => {
  store.images.forEach(image => {
    image.pages.forEach(page => {
      if (!page.loaded && !page.loading) {
        fetchImagePage(page)
      }
    })
  })
})

const rotatePage = (page) => {
  page.rotate = ((page.rotate || 0) + 90) % 360
}

const getRedactUrl = (attachment) => {
  return config.urls.redactAttachment.replace('/0/', `/${attachment.id}/`)
}

export function useAttachments({ urls = null, csrfToken = null, i18n = null} = {}) {
  // urls, token and i18n could possibly overwrite what has been set before
  // they shall only be used in the most-parent, ancestral component,
  // like <post-upload> and <attachment-manager>
  // they could also Object.extend, or throw an error/warning if already set...
  if (urls) config.urls = urls
  if (csrfToken) config.csrfToken = csrfToken
  if (i18n) config.i18n = i18n
  return {
    pinia,
    refresh,
    attachments: store,
    convertImage,
    createDocument,
    updateDocument,
    splitPages: store.splitPages,
    rotatePage,
    addFromUppy,
    makeRelevant,
    deleteAttachment,
    approveAttachment,
    approveAllUnredactedAttachments,
    getRedactUrl
  }
}
