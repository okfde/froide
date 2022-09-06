import { createApp } from 'vue'

function snakeToCamel(s) {
  return s.replace(/(-\w)/g, function (m) {
    return m[1].toUpperCase()
  })
}

function getPropsFromElement(el) {
  const attrs = el.attributes
  const props = {}

  for (let i = 0; i < attrs.length; i += 1) {
    const attr = attrs[i]
    if (attr.name[0] === 'v' && attr.name[1] === '-') {
      continue
    }
    if (attr.name === 'id' || attr.name === 'class') {
      continue
    }
    let val = attr.value
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

function getSlotData(el) {
  const slotEls = el.querySelectorAll('template')
  const slots = {}
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
function getOtherAttrs(el) {
  const other = {}
  if (el.id) {
    other.attrs = {
      id: el.id
    }
  }
  if (el.className) {
    const classes = el.className.split(' ')
    other.class = {}
    classes.forEach((c) => {
      other.class[c.trim()] = true
    })
  }
  return other
}

function createAppWithProps(el, component) {
  /*
    Fake VueJS compiler which does only the following:
    - takes class and id attributes and sets them on new element
    - takes other attributes of element and makes them to props object
    - takes containing slot content elements and
      adds them as *static* slots with their innerhtml
  */
  if (typeof el === 'string') {
    el = document.querySelector(el)
  }
  const props = getPropsFromElement(el)
  const slotData = getSlotData(el)
  const otherAttrs = getOtherAttrs(el)

  return createApp(component, {
    slots: slotData,
    ...props,
    ...otherAttrs
  })
}

export { createAppWithProps }
