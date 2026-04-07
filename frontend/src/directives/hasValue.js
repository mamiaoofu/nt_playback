// Directive v-has-value
// - When attached to an input or its wrapper (.input-group), it keeps the
//   parent `.input-group` updated with `has-value` class based on the field value.
// - This ensures floating labels ('.title-label') move to the floated position
//   when the input has content, matching behavior of :valid or focus.
//
// Thai:
// directive นี้จะคอยตรวจสอบค่าใน input และสลับคลาส `has-value` ให้กับ
// parent (เช่น `.input-group`) เมื่อมีค่าหรือเมื่อมีการพิมพ์ เพื่อให้ label
// ลอยอยู่ในตำแหน่งที่ถูกต้องเมื่อช่องมีค่า

export default {
  mounted(el) {
    // If the directive is used directly on an input, use it; otherwise find an input inside
    const input = el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT'
      ? el
      : el.querySelector('input, textarea, select')
    if (!input) return

    const parent = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') ? el.parentNode : el

    const update = () => {
      try {
        const val = input.value
        const has = val !== null && String(val).trim() !== ''
        parent.classList.toggle('has-value', has)
      } catch (e) {
        // ignore
      }
    }

    // update on user input events
    input.addEventListener('input', update)
    input.addEventListener('change', update)

    // initialize
    update()

    // Also watch for programmatic changes (e.g. v-model or flatpickr setting .value)
    // Use a MutationObserver for attribute changes (best-effort) and a small
    // polling loop to reliably detect property updates.
    let lastVal = input.value
    const pollInterval = 200
    const pollId = setInterval(() => {
      try {
        const cur = input.value
        if (cur !== lastVal) {
          lastVal = cur
          update()
        }
      } catch (e) {}
    }, pollInterval)

    let observer = null
    try {
      observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
          if (m.type === 'attributes' && m.attributeName === 'value') {
            update()
            break
          }
        }
      })
      observer.observe(input, { attributes: true, attributeFilter: ['value'] })
    } catch (e) {
      observer = null
    }

    el._hasValue_cleanup = () => {
      try { input.removeEventListener('input', update) } catch (e) {}
      try { input.removeEventListener('change', update) } catch (e) {}
      try { clearInterval(pollId) } catch (e) {}
      try { if (observer) observer.disconnect() } catch (e) {}
    }
  },

  beforeUnmount(el) {
    if (el._hasValue_cleanup) {
      try { el._hasValue_cleanup() } catch (e) {}
      delete el._hasValue_cleanup
    }
  }
}
