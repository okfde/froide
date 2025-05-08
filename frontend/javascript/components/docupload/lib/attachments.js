import { postData } from '../../../lib/api'
import {
  attachmentList,
  attachmentRetrieve,
  documentUpdate,
  convertImagesToPdf,
  attachmentDestroy,
  attachmentApproveCreate,
  attachmentToDocumentCreate
} from '../../../api'

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
  const title = (store.images[imageIndex].name || config.i18n.value.documentsUploadDefaultFilename)
    // normalize possible .pdf extension away
    ?.replace(/\.pdf$/, '')
  return convertImagesToPdf({
    body: {
      title,
      images: store.images[imageIndex].pages.map((p) => ({
        attachment: p.resource_uri,
        rotate: (p.rotate || 0) + (p.implicitRotate || 0)
      })),
      message: config.message.resource_uri
    },
    throwOnError: true
  })
    .catch(handleError)
    .then(({ data }) => {
      const newAttachment = data
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
  return attachmentToDocumentCreate({
    path: { id: attachment.id },
    throwOnError: true
  })
    .then(({ data }) => {
      // note: .getById and .all are not reactive, only allRaw
      store.allRaw.find(att => att.id === attachment.id).document = data
    })
    .catch((err) => {
      // TODO where do these land in post-upload?
      store.messages.push({ body: err.detail || config.i18n.error || 'Error', color: 'danger' })
    })
    // note there's no .finally here -- we don't know when it's done
    // for now it remains in process until reload
    // (or until we gain a websocket-y signal)
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

const fetchPagedObjects = (nextUrl, pageCb) => {
  return fetch(nextUrl, {
    headers: { 'X-CSRFToken': config.csrfToken }
  })
    .then((response) => {
      if (!response.ok) {
        console.error('fetch attachment error', response)
        // TODO
        throw new Error(response.message)
      }
      return response.json()
    })
    .then((response) => {
      pageCb(response.objects)
      if (response.meta.next) {
        return fetchPagedObjects(response.meta.next, pageCb)
      }
    })

}

const fetchAttachments = (messageId) => {
  store.isFetching = true
  return attachmentList({ query: { belongs_to: messageId }, throwOnError: true })
    .then((response) => {
      store.$patch({ allRaw: response.data.objects }) //.filter(_ => !_.is_image) })
      // store.$patch({ images: response.data.objects.filter(_ => _.is_image) })
      if (response.data.meta.next) {
        return fetchPagedObjects(
          response.data.meta.next,
          (objects) => {
            store.allRaw.push(...objects) // .filter(_ => !_.is_image))
            // store.images.push(...objects.filter(_ => _.is_image))
          }
        )
      }
    })
    .finally(() => {
      store.isFetching = false
    })
}

const fetchAttachment = (id) => {
  return attachmentRetrieve({
    path: { id },
    throwOnError: true
  })
    .then(({ data }) => addOrReplaceAttachment(data))
    .catch(handleError)
}

const refetchAttachment = (attachment) => {
  return attachmentRetrieve({
    path: { id: attachment.id },
    throwOnError: true
  })
    .then(({ data }) => replaceAttachment(data))
    .catch(handleError)
}

const replaceAttachment = (attachment) => {
  const index = store.allRaw.findIndex(att => att.id === attachment.id)
  if (index === -1) throw new Error(`attachment not found ${attachment.id}`)
  store.allRaw[index] = attachment
  return attachment
}

const addOrReplaceAttachment = (attachment) => {
  const index = store.allRaw.findIndex(att => att.id === attachment.id)
  if (index === -1) {
    store.allRaw.push(attachment)
  } else {
    store.allRaw[index] = attachment
  }
  return attachment
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
  let message = err?.message
  try {
    if (!message) message = JSON.stringify(err)
  } catch {
    message = '…'
  }
  if (confirm(`${config.i18n.value.genericErrorReload}\n\n(${message})`) === true) {
    refresh()
  }
}

const handleError = (err) => {
  console.error(err)
  let message = err?.message
  try {
    if (!message) message = JSON.stringify(err)
  } catch {
    message = '…'
  }
  window.alert(`${config.i18n.value.genericError || 'Error'}\n\n${message}`)
}

const deleteAttachment = (attachment) => {
  // optimistically...
  store.removeAttachment(attachment)
  return attachmentDestroy({
    path: { id: attachment.id },
    throwOnError: true
  })
    .then(() => {
      store.messages.push({ body: `${config.i18n.value.attachmentDeleted} (${attachment.name})`, color: 'success-subtle' })
    })
    .catch(handleErrorAndRefresh)
}

const approveAttachment = (attachment) => {
  store.approvingIds.add(attachment.id)
  return attachmentApproveCreate({
    path: { id: attachment.id },
    throwOnError: true
  })
    .then(({ data }) => replaceAttachment(data))
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
    return attachmentApproveCreate({ path: { id: attachment.id }})
  }))
}

const config = {}

const refresh = (messageId) => fetchAttachments(messageId || config.message.id)
  .catch(handleErrorAndRefresh)

const refreshIfIdNotPresent = (attachment) => {
  if (store.getById(attachment.id)) {
    return Promise.resolve(false)
  }
  return refresh().then(() => true)
}

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

export function useAttachments({ message = null, urls = null, csrfToken = null, i18n = null} = {}) {
  // urls, token and i18n could possibly overwrite what has been set before
  // they shall only be used in the most-parent, ancestral component,
  // like <post-upload> and <attachment-manager>
  // they could also Object.extend, or throw an error/warning if already set...
  if (message) config.message = message
  if (urls) config.urls = urls
  if (csrfToken) config.csrfToken = csrfToken
  if (i18n) config.i18n = i18n
  return {
    pinia,
    attachments: store,
    refresh,
    refreshIfIdNotPresent,
    convertImage,
    createDocument,
    updateDocument,
    splitPages: store.splitPages,
    rotatePage,
    addFromUppy,
    makeRelevant,
    fetchAttachment,
    deleteAttachment,
    approveAttachment,
    approveAllUnredactedAttachments,
    getRedactUrl
  }
}
