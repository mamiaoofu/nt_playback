// Directive v-number-only
// Restricts input to digits only. Can be applied directly to an <input>
// or to a wrapper (.input-group) and will find the first input inside.

export default {
  mounted(el) {
    const input = (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el : el.querySelector('input, textarea')
    if (!input) return

    const onInput = () => {
      try {
        const old = input.value || ''
        const cleaned = String(old).replace(/\D+/g, '')
        if (cleaned !== old) {
          const selStart = input.selectionStart || 0
          input.value = cleaned
          // try to preserve caret roughly at end of insertion
          try { input.setSelectionRange(Math.min(cleaned.length, selStart), Math.min(cleaned.length, selStart)) } catch (e) {}
          input.dispatchEvent(new Event('input'))
        }
      } catch (e) {}
    }

    const onKeyDown = (e) => {
      try {
        const allowed = ['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Tab', 'Home', 'End']
        if (allowed.includes(e.key)) return
        if (e.ctrlKey || e.metaKey) return
        if (/^[0-9]$/.test(e.key)) return
        // Prevent other keys
        e.preventDefault()
      } catch (e) {}
    }

    const onPaste = (e) => {
      try {
        const text = (e.clipboardData || window.clipboardData).getData('text') || ''
        const cleaned = text.replace(/\D+/g, '')
        if (cleaned !== text) {
          e.preventDefault()
          const start = input.selectionStart || 0
          const end = input.selectionEnd || 0
          const val = input.value || ''
          const newVal = val.slice(0, start) + cleaned + val.slice(end)
          input.value = newVal
          input.dispatchEvent(new Event('input'))
          try { input.setSelectionRange(start + cleaned.length, start + cleaned.length) } catch (err) {}
        }
      } catch (e) {}
    }

    input.addEventListener('input', onInput)
    input.addEventListener('keydown', onKeyDown)
    input.addEventListener('paste', onPaste)

    el._numberOnly_cleanup = () => {
      try { input.removeEventListener('input', onInput) } catch (e) {}
      try { input.removeEventListener('keydown', onKeyDown) } catch (e) {}
      try { input.removeEventListener('paste', onPaste) } catch (e) {}
    }
  },

  beforeUnmount(el) {
    if (el._numberOnly_cleanup) {
      try { el._numberOnly_cleanup() } catch (e) {}
      delete el._numberOnly_cleanup
    }
  }
}
