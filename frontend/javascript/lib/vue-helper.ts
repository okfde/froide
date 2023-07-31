import { VueElement, createApp } from 'vue'

type PropValue = string | boolean | Record<string, unknown> | Array<unknown>
type Props = Record<string, PropValue>
type Slots = Record<string, string>
interface OtherAttrs {
  attrs: Record<string, string>
  class: Record<string, boolean>
}

function snakeToCamel(s: string) {
  return s.replace(/(-\w)/g, function (m) {
    return m[1].toUpperCase()
  })
}

function getPropsFromElement(el: HTMLElement): Props {
  const attrs = el.attributes
  const props: Props = {}

  for (let i = 0; i < attrs.length; i += 1) {
    const attr = attrs[i]
    if (attr.name[0] === 'v' && attr.name[1] === '-') {
      continue
    }
    if (attr.name === 'id' || attr.name === 'class') {
      continue
    }
    let val: PropValue = attr.value
    let name = attr.name
    if (attr.name[0] === ':') {
      name = attr.name.substring(1)
      if (attr.value[0] === '{' || attr.value[0] === '[') {
        val = JSON.parse(attr.value)
      }
      if (attr.value === 'true') {
        val = true
      } else if (attr.value === 'false') {
        val = false
      }
    }
    props[snakeToCamel(name)] = val
  }
  return props
}

function getSlotData(el: HTMLElement): Slots {
  const slotEls = el.querySelectorAll('template')
  const slots: Slots = {}
  for (let i = 0; i < slotEls.length; i += 1) {
    const slotEl = slotEls[i]
    const attrs = slotEl.attributes
    let slotName = null
    for (let i = 0; i < attrs.length; i++) {
      if (attrs[i].name.startsWith('v-slot:')) {
        slotName = attrs[i].name.replace('v-slot:', '')
        break
      }
    }
    if (slotName === null) {
      continue
    }
    slots[slotName] = slotEl.innerHTML
  }
  return slots
}
function getOtherAttrs(el: HTMLElement): OtherAttrs {
  const other: OtherAttrs = {
    attrs: {},
    class: {}
  }
  if (el.id) {
    other.attrs = {
      id: el.id
    }
  }
  if (el.className) {
    const classes = el.className.split(' ')
    classes.forEach((c) => {
      other.class[c.trim()] = true
    })
  }
  return other
}

function createAppWithProps(el: string | HTMLElement, component: VueElement) {
  /*
    Fake VueJS compiler which does only the following:
    - takes class and id attributes and sets them on new element
    - takes other attributes of element and makes them to props object
    - takes containing slot content elements and
      adds them as *static* slots with their innerhtml
  */
  let checkedEl: HTMLElement | null = null
  if (typeof el === 'string') {
    checkedEl = document.querySelector(el)
  } else {
    checkedEl = el
  }
  if (checkedEl === null) {
    return
  }
  const props = getPropsFromElement(checkedEl)
  const slotData = getSlotData(checkedEl)
  const otherAttrs = getOtherAttrs(checkedEl)

  return createApp(component, {
    slots: slotData,
    ...props,
    ...otherAttrs
  })
}

export { createAppWithProps }
