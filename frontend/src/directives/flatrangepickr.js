// Vue 3 directive to attach flatpickr in range mode and write "start - end" to target
// Usage: v-flatrangepickr="{ target: obj, key: 'range', options: { ... }, onChange: fn }"
// Arg form: v-flatrangepickr:range="filters"
export default {
  mounted(el, binding) {
    const fp = (typeof window !== 'undefined' && window.flatpickr) || (typeof flatpickr !== 'undefined' && flatpickr)
    if (!fp) return

    const raw = binding.value
    const value = (raw && typeof raw === 'object') ? raw : {}
    const target = (binding.arg && raw && typeof raw === 'object') ? raw : (value.target || null)
    const key = binding.arg ? binding.arg : value.key
    // Default: date range only (no time shown). Backend times will be synthesized as 00:00 / 23:59.
    // If caller passes `time: true` (or sets `options.enableTime`), enable time selection and include time in formats.
    const useTime = (value && value.time) === true || (value && value.options && value.options.enableTime === true)
    const defaultOpts = { mode: 'range', enableTime: useTime, dateFormat: useTime ? 'Y-m-d H:i' : 'Y-m-d', time_24hr: true, defaultHour: 0, defaultMinute: 0 }
    const opts = Object.assign(defaultOpts, value.options || {})
    const userOnChange = (typeof raw === 'function') ? raw : value.onChange

    const instance = fp(el, opts)

    // If there is no explicit default date provided via options or the target/key,
    // ensure the input remains empty on init (flatpickr may show today's date otherwise).
    try {
      const hasDefaultDate = (value && value.options && (value.options.defaultDate !== undefined && value.options.defaultDate !== null)) || (target && key && target[key])
      if (!hasDefaultDate) {
        if (instance && typeof instance.clear === 'function') {
          try { instance.clear() } catch (e) {}
        }
        try { el.value = '' } catch (e) {}
      }
    } catch (e) {}

    if (instance && instance.config && Array.isArray(instance.config.onChange)) {
      instance.config.onChange.push((selectedDates) => {
        let displayOut = ''
        let displayStart = ''
        let displayEnd = ''
        // Backend-ready timestamps
        let backendStart = ''
        let backendEnd = ''

        if (Array.isArray(selectedDates) && selectedDates.length >= 2) {
          if (opts.enableTime) {
            displayStart = instance.formatDate(selectedDates[0], 'Y-m-d H:i')
            displayEnd = instance.formatDate(selectedDates[1], 'Y-m-d H:i')
            displayOut = `${displayStart} - ${displayEnd}`
            backendStart = instance.formatDate(selectedDates[0], 'Y-m-d H:i')
            backendEnd = instance.formatDate(selectedDates[1], 'Y-m-d H:i')
          } else {
            displayStart = instance.formatDate(selectedDates[0], 'Y-m-d')
            displayEnd = instance.formatDate(selectedDates[1], 'Y-m-d')
            displayOut = `${displayStart} - ${displayEnd}`
            backendStart = `${displayStart} 00:00`
            backendEnd = `${displayEnd} 23:59`
          }
        } else if (selectedDates && selectedDates.length === 1) {
          if (opts.enableTime) {
            displayStart = instance.formatDate(selectedDates[0], 'Y-m-d H:i')
            displayEnd = displayStart
            displayOut = displayStart
            backendStart = instance.formatDate(selectedDates[0], 'Y-m-d H:i')
            backendEnd = instance.formatDate(selectedDates[0], 'Y-m-d H:i')
          } else {
            displayStart = instance.formatDate(selectedDates[0], 'Y-m-d')
            displayEnd = displayStart
            displayOut = displayStart
            backendStart = `${displayStart} 00:00`
            backendEnd = `${displayEnd} 23:59`
          }
        } else {
          displayOut = ''
        }

        if (target && key) {
          try { target[key] = displayOut } catch (e) {}
          try { target[`${key}_start`] = backendStart } catch (e) {}
          try { target[`${key}_end`] = backendEnd } catch (e) {}
        }
        try { el.value = displayOut } catch (e) {}

        if (typeof userOnChange === 'function') {
          try { userOnChange(selectedDates, { display: displayOut, start: backendStart, end: backendEnd }) } catch (e) {}
        }
      })
    }

    // store instance for cleanup
    el._flatpickrRangeInstance = instance
  },

  beforeUnmount(el) {
    try {
      if (el._flatpickrRangeInstance && typeof el._flatpickrRangeInstance.destroy === 'function') el._flatpickrRangeInstance.destroy()
    } catch (e) {}
    delete el._flatpickrRangeInstance
  }
}
