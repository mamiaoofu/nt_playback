// Vue 3 directive to attach flatpickr to inputs in a reusable way
// Usage: v-flatpickr="{ target: filters, key: 'from', options: { ... }, onChange: fn }"
//
// Thai:
// directive นี้สำหรับผูก flatpickr เข้ากับ input ใน Vue 3 แบบ reusable
// ตัวอย่างการใช้งาน: v-flatpickr="{ target: filters, key: 'from', options:{}, onChange: fn }"

export default {
  mounted(el, binding) {
    const fp = (typeof window !== 'undefined' && window.flatpickr) || (typeof flatpickr !== 'undefined' && flatpickr)
    if (!fp) return

    const raw = binding.value

    // Determine binding mode:
    // 1) object form: v-flatpickr="{ target: obj, key: 'from', options:{}, onChange: fn }"
    // 2) arg form: v-flatpickr:from="filters"  --> binding.arg === 'from', binding.value === filters (object)
    // 3) function form: v-flatpickr="(dates, str) => ..."  --> binding.value is a function called on change
    //
    // Thai:
    // ตรวจสอบรูปแบบการผูกที่ directive รองรับ:
    // 1) object form: ส่ง object ที่มี target/key/options/onChange
    // 2) arg form: ใช้ argument เป็นชื่อ property เช่น v-flatpickr:from="filters" (สั้นและแนะนำ)
    // 3) function form: ส่งฟังก์ชันเป็น binding เพื่อรับ event เมื่อวันที่เปลี่ยน
    const value = (raw && typeof raw === 'object') ? raw : {}
    const target = (binding.arg && raw && typeof raw === 'object') ? raw : (value.target || null)
    const key = binding.arg ? binding.arg : value.key
    const opts = Object.assign({ enableTime: true, dateFormat: 'Y-m-d H:i', time_24hr: true, defaultHour: 0, defaultMinute: 0 }, value.options || {})
    // Support a top-level `noTime` flag in the binding value for convenience
    // e.g. v-flatpickr="{ target: filters, key: 'start_date', noTime: true }"
    if (value && value.noTime) {
      opts.enableTime = false
      opts.dateFormat = 'Y-m-d'
      // prevent auto-closing on select so user must click Apply/Clear
      try { opts.closeOnSelect = false } catch (e) {}
      // remove time defaults
      try { delete opts.defaultHour } catch (e) {}
      try { delete opts.defaultMinute } catch (e) {}
      try { delete opts.time_24hr } catch (e) {}
    }
    const userOnChange = (typeof raw === 'function') ? raw : value.onChange
    const isDurationRange = value.mode === 'duration_range'
    const noTime = !!value.noTime

    const instance = fp(el, opts)

    // Helper to force-hide/disable any time UI that may still be present
    // Some versions or plugins may inject .flatpickr-time after init; ensure
    // it's removed when the caller requested `noTime`.
    const hideTimeUI = () => {
      if (!noTime || !instance || !instance.calendarContainer) return
      try {
        // remove any time containers entirely
        instance.calendarContainer.querySelectorAll('.flatpickr-time').forEach(tc => {
          try { tc.remove() } catch (e) {}
        })
      } catch (e) {}
      try {
        // also disable any numeric inputs if present
        instance.calendarContainer.querySelectorAll('input.numInput').forEach(i => {
          try { i.disabled = true } catch (e) {}
        })
      } catch (e) {}
    }

    // run immediately in case flatpickr already rendered time UI
    try { hideTimeUI() } catch (e) {}
    try {
      instance.config.onReady = Array.isArray(instance.config.onReady) ? instance.config.onReady : []
      instance.config.onReady.push(hideTimeUI)
    } catch (e) {}

    if (instance && instance.config && Array.isArray(instance.config.onChange)) {
      // Ensure flatpickr uses the desired range separator for duration ranges
      try { if (isDurationRange) instance.config.rangeSeparator = ' - ' } catch (e) {}
      // Track whether the current value has been explicitly applied by the user
      let applied = !!(el && el.value)
      // Controls whether onClose should actually allow the calendar to close.
      // We require an explicit Apply or Clear to set this to true.
      let allowClose = false
      // Keep last applied value so we can restore it if flatpickr writes a default (00:00:00) on close
      let lastAppliedValue = (el && el.value) ? el.value : ''
      // Normalize to date-only when noTime is requested
      try {
        if (noTime && lastAppliedValue && String(lastAppliedValue).trim() !== '') {
          lastAppliedValue = String(lastAppliedValue).split(' ')[0]
        }
      } catch (e) {}
      // Intercept programmatic writes to `el.value` so we can suppress
      // previews while the calendar is open (only allow writes after Apply)
      let suppressWrites = false
      const protoDesc = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value') || Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')
      const originalValueGetter = protoDesc && protoDesc.get ? protoDesc.get : function () { return this.getAttribute('value') }
      const originalValueSetter = protoDesc && protoDesc.set ? protoDesc.set : function (v) { this.setAttribute('value', v) }
      const installSuppressor = () => {
        try {
          Object.defineProperty(el, 'value', {
            configurable: true,
            enumerable: true,
            get() { return originalValueGetter.call(this) },
            set(v) {
              if (suppressWrites) return
              try {
                if (noTime && typeof v === 'string' && v.indexOf(' ') !== -1) {
                  v = String(v).split(' ')[0]
                }
              } catch (e) {}
              return originalValueSetter.call(this, v)
            }
          })
        } catch (e) {}
      }
      try { installSuppressor() } catch (e) {}

      // Prevent external/property writes from sneaking in while the calendar
      // is open and the selection hasn't been applied. We use event listeners
      // (capture) and a MutationObserver to catch most write paths and restore
      // the last applied value.
      let _mutObserver = null
      const enforceNoWrite = (ev) => {
        try {
          if (!applied && instance && instance.isOpen) {
            const restore = lastAppliedValue || ''
            const norm = noTime ? String(restore).split(' ')[0] : String(restore)
            try { originalValueSetter.call(el, norm) } catch (e) { try { el.value = norm } catch (e) {} }
            try { ev.stopImmediatePropagation && ev.stopImmediatePropagation() } catch (e) {}
            try { ev.preventDefault && ev.preventDefault() } catch (e) {}
          }
        } catch (e) {}
      }
      try {
        el.addEventListener('input', enforceNoWrite, true)
        el.addEventListener('change', enforceNoWrite, true)
        // MutationObserver for attribute changes (setAttribute('value', ...))
        try {
          _mutObserver = new MutationObserver((mutations) => {
            try {
              mutations.forEach(m => {
                if (m.type === 'attributes' && m.attributeName === 'value') enforceNoWrite(m)
              })
            } catch (e) {}
          })
          _mutObserver.observe(el, { attributes: true, attributeFilter: ['value'] })
        } catch (e) { _mutObserver = null }
      } catch (e) {}

      // create a small action bar appended to flatpickr's calendar container
      try {
        const actions = document.createElement('div')
        actions.className = 'flatpickr-actions'

        const actionBtn = document.createElement('button')
        actionBtn.type = 'button'
        actionBtn.className = 'flatpickr-action-btn'
        // Use a single "OK" button to confirm the selection (no Apply/Clear)
        actionBtn.textContent = 'OK'
        actionBtn.dataset.state = 'ok'

        actions.appendChild(actionBtn)

        if (instance && instance.calendarContainer) {
          const timeContainer = instance.calendarContainer.querySelector('.flatpickr-time')
          const wrapper = document.createElement('div')
          wrapper.className = 'flatpickr-footer-group'

          if (isDurationRange && timeContainer) {
            wrapper.classList.add('has-time', 'from-to')
            wrapper.style.display = 'flex'
            wrapper.style.flexDirection = 'column'
            
            // Row From
            const rowFrom = document.createElement('div')
            rowFrom.className = 'time-row from'
            rowFrom.style.display = 'flex'
            rowFrom.style.alignItems = 'center'
            rowFrom.style.justifyContent = 'center'
            rowFrom.style.marginBottom = '5px'
            rowFrom.style.width = '100%'
            rowFrom.style.paddingLeft = '16px'
            const labelFrom = document.createElement('span')
            labelFrom.textContent = 'From'
            labelFrom.style.marginRight = '10px'
            labelFrom.style.fontWeight = 'bold'
            rowFrom.appendChild(labelFrom)
            rowFrom.appendChild(timeContainer)
            
            // Row To
            const rowTo = document.createElement('div')
            rowTo.className = 'time-row to'
            rowTo.style.display = 'flex'
            rowTo.style.alignItems = 'center'
            rowTo.style.justifyContent = 'center'
            rowTo.style.width = '100%'
            rowTo.style.paddingLeft = '16px'
            const labelTo = document.createElement('span')
            labelTo.textContent = 'To'
            labelTo.style.marginRight = '26px'
            labelTo.style.fontWeight = 'bold'
            rowTo.appendChild(labelTo)

            // Clone time container for "To"
            const toTimeContainer = timeContainer.cloneNode(true)
            
            // Setup interaction for cloned inputs
            const setupClonedInput = (container) => {
              const inputs = container.querySelectorAll('input.numInput')
              inputs.forEach(input => {
                const wrapper = input.parentNode
                const up = wrapper.querySelector('.arrowUp')
                const down = wrapper.querySelector('.arrowDown')
                const step = parseFloat(input.step) || 1
                const min = parseFloat(input.min) || 0
                const max = parseFloat(input.max) || 59

                const updateVal = (delta) => {
                  let v = (parseFloat(input.value) || 0) + delta
                  if (v > max) v = min
                  if (v < min) v = max
                  input.value = String(v).padStart(2, '0')
                  // Trigger manual change event to update main input
                  input.dispatchEvent(new Event('change'))
                }

                if (up) up.addEventListener('click', (e) => { e.stopPropagation(); updateVal(step) })
                if (down) down.addEventListener('click', (e) => { e.stopPropagation(); updateVal(-step) })
                input.addEventListener('wheel', (e) => { e.preventDefault(); updateVal(e.deltaY < 0 ? step : -step) })
                input.addEventListener('change', () => {
                  let v = parseFloat(input.value) || 0
                  if (v > max) v = max
                  if (v < min) v = min
                  input.value = String(v).padStart(2, '0')
                  // Update main input value on change
                  if (instance.config.onChange && instance.config.onChange.length) {
                    instance.config.onChange.forEach(fn => fn(instance.selectedDates, instance.input.value))
                  }
                })
                // When the user focuses/clicks a num input we should mark the selection as pending
                // so the action button reflects that an explicit change may be applied.
                input.addEventListener('focus', () => {
                  try {
                    applied = false
                    actionBtn.textContent = 'OK'
                    actionBtn.dataset.state = 'ok'
                  } catch (e) {}
                })
              })
            }
            rowTo.appendChild(toTimeContainer)

            wrapper.appendChild(rowFrom)
            wrapper.appendChild(rowTo)
            el._flatpickrToContainer = toTimeContainer // Store ref

            // If the input already has a value like "HH:MM:SS - HH:MM:SS", initialize
            // both the cloned "To" inputs and the original "From" time inputs.
            try {
              const curVal = (el && (el.value || lastAppliedValue)) ? String(el.value || lastAppliedValue) : ''
              if (curVal && curVal.includes(' - ')) {
                const parts = curVal.split(' - ')
                const fromPart = parts[0] || ''
                const toPart = parts[1] || ''

                // populate From (original timeContainer)
                try {
                  const [fh, fm, fs] = (fromPart || '').split(':')
                  const fromInputs = timeContainer.querySelectorAll('input')
                  if (fromInputs && fromInputs.length) {
                    if (fromInputs[0]) fromInputs[0].value = (fh || '00').padStart(2, '0')
                    if (fromInputs[1]) fromInputs[1].value = (fm || '00').padStart(2, '0')
                    if (fromInputs[2]) fromInputs[2].value = (fs || '00').padStart(2, '0')
                  }
                } catch (e) {}

                // populate To (cloned toTimeContainer)
                try {
                  const [h, m, s] = (toPart || '').split(':')
                  const inputs = toTimeContainer.querySelectorAll('input')
                  if (inputs && inputs.length) {
                    if (inputs[0]) inputs[0].value = (h || '00').padStart(2, '0')
                    if (inputs[1]) inputs[1].value = (m || '00').padStart(2, '0')
                    if (inputs[2]) inputs[2].value = (s || '00').padStart(2, '0')
                  }
                } catch (e) {}
              }
            } catch (e) {}

            // Align actions to left
            actions.style.display = 'flex'
            actions.style.justifyContent = 'center'
            actions.style.width = '100%'
            actions.style.padding = '0 5px 5px 5px'
            actionBtn.style.width = '100%'
          } else if (timeContainer) {
            wrapper.classList.add('has-time')
            wrapper.appendChild(timeContainer)
          }
          wrapper.appendChild(actions)
          instance.calendarContainer.appendChild(wrapper)
          // If the picker was requested as date-only, hide/disable any time UI
          try {
            if (noTime && instance && instance.calendarContainer) {
              const tc = instance.calendarContainer.querySelector('.flatpickr-time')
              if (tc) {
                try { tc.style.display = 'none' } catch (e) {}
                try { tc.querySelectorAll('input').forEach(i => { try { i.disabled = true } catch (e) {} }) } catch (e) {}
              }
              // disable cloned To container if created
              try { if (el._flatpickrToContainer) el._flatpickrToContainer.querySelectorAll('input').forEach(i => { try { i.disabled = true } catch (e) {} }) } catch (e) {}
            }
          } catch (e) {}
        }

        const doApply = () => {
          let finalStr = ''
          if (isDurationRange) {
            // Determine whether a "from" date exists
            const fromPresent = instance && Array.isArray(instance.selectedDates) && instance.selectedDates.length > 0
            const fromStr = fromPresent ? instance.formatDate(instance.latestSelectedDateObj, instance.config.dateFormat) : ''

            // Get To (HH:MM:SS) and check if any value is non-zero
            let toStr = ''
            let toPresent = false
            if (el._flatpickrToContainer) {
              const inputs = el._flatpickrToContainer.querySelectorAll('input')
              const h = (inputs[0] && inputs[0].value) ? String(inputs[0].value).padStart(2, '0') : '00'
              const m = (inputs[1] && inputs[1].value) ? String(inputs[1].value).padStart(2, '0') : '00'
              const s = (inputs[2] && inputs[2].value) ? String(inputs[2].value).padStart(2, '0') : '00'
              toStr = `${h}:${m}:${s}`
              toPresent = !(h === '00' && m === '00' && (s === '00' || s === undefined))
            }

            if (fromPresent && toPresent) finalStr = `${fromStr} - ${toStr}`
            else if (fromPresent) finalStr = fromStr
            else if (toPresent) finalStr = toStr
            else finalStr = ''
          } else {
            // Non-duration picker: format selected date (dateFormat already respects noTime)
            try {
              if (instance && Array.isArray(instance.selectedDates) && instance.selectedDates.length > 0) {
                finalStr = instance.formatDate(instance.selectedDates[0], instance.config.dateFormat)
              } else {
                finalStr = ''
              }
            } catch (e) { finalStr = '' }
          }

          // Commit the selected value as applied
          try { applied = true } catch (e) {}
          try { lastAppliedValue = finalStr } catch (e) {}
          try { if (target && key) target[key] = finalStr } catch (e) {}
          try { originalValueSetter.call(el, finalStr) } catch (e) { try { el.value = finalStr } catch (e) {} }
          try { el.parentNode && el.parentNode.classList.toggle('has-value', (finalStr || '').toString().trim() !== '') } catch (e) {}
          try { actionBtn.textContent = 'OK'; actionBtn.dataset.state = 'ok' } catch (e) {}
          try { suppressWrites = false } catch (e) {}
          try { allowClose = true } catch (e) {}
          try { instance.close() } catch (e) {}
          // reset allowClose shortly after closing to avoid accidental subsequent closes
          try { setTimeout(() => { allowClose = false }, 250) } catch (e) {}
        }

        const doClear = () => {
          // Mark cleared first so any onClose/onChange triggered by clear
          // won't restore the previous value using lastAppliedValue.
          try { applied = false } catch (e) {}
          try { lastAppliedValue = '' } catch (e) {}

          try { instance.clear() } catch (e) {}

          // For duration ranges, fully clear any cloned "To" inputs so no
          // residual time remains visible. Use empty string and dispatch a
          // change event so listeners update preview/state immediately.
          try {
            if (isDurationRange && el._flatpickrToContainer) {
              const inputs = el._flatpickrToContainer.querySelectorAll('input')
              inputs.forEach(i => {
                try { i.value = '' } catch (e) {}
                try { i.dispatchEvent(new Event('change')) } catch (e) {}
              })
            }
          } catch (e) {}

          try { if (target && key) target[key] = '' } catch (e) {}
          try { originalValueSetter.call(el, '') } catch (e) { try { el.value = '' } catch (e) {} }
          try { el.parentNode && el.parentNode.classList.remove('has-value') } catch (e) {}

          try { actionBtn.textContent = 'OK'; actionBtn.dataset.state = 'ok' } catch (e) {}
          try { allowClose = true } catch (e) {}
          try { instance.close() } catch (e) {}
          try { setTimeout(() => { allowClose = false }, 250) } catch (e) {}
        }

        const onActionClick = (ev) => {
          ev && ev.stopPropagation()
          // Always treat the button as confirmation: commit current selection
          try { doApply() } catch (e) {}
        }

        actionBtn.addEventListener('click', onActionClick)

        // update button state when user changes selection
          instance.config.onChange.push((selectedDates, dateStr) => {
          // when a new selection or time edit is made it becomes pending (needs Apply)
          if (selectedDates && selectedDates.length) {
            applied = false
            actionBtn.textContent = 'OK'
            actionBtn.dataset.state = 'ok'
          }

          // For non-duration pickers: suppress programmatic writes while the
          // calendar is open and the user hasn't clicked Apply. We set a
          // suppress flag so our element-level setter blocks preview writes.
          if (!isDurationRange) {
            try {
              if (!applied && instance && instance.isOpen) {
                suppressWrites = true
                try {
                  const toWrite = noTime ? String(lastAppliedValue || '').split(' ')[0] : (lastAppliedValue || '')
                  try { originalValueSetter.call(el, toWrite) } catch (e) { try { el.value = toWrite } catch(e){} }
                } catch (e) {}
                try { el.parentNode && el.parentNode.classList.toggle('has-value', (lastAppliedValue || '').toString().trim() !== '') } catch (e) {}
              } else {
                // allow writes
                suppressWrites = false
              }
            } catch (e) { suppressWrites = false }
          }

          // If user selects the same date that's already applied, treat as toggle -> clear
          try {
            if (!isDurationRange && selectedDates && selectedDates.length) {
              try {
                const newStr = instance.formatDate(selectedDates[0], instance.config.dateFormat)
                const normLast = noTime ? String(lastAppliedValue || '').split(' ')[0] : String(lastAppliedValue || '')
                if (normLast && String(newStr) === String(normLast)) {
                  try { doClear() } catch (e) {}
                  return
                }
              } catch (e) {}
            }
          } catch (e) {}

          // For duration ranges: if both From and To match last applied value, clear everything
          try {
            if (isDurationRange && selectedDates && selectedDates.length) {
              try {
                const fromStr = instance.formatDate(instance.latestSelectedDateObj, instance.config.dateFormat)
                let toStr = ''
                if (el._flatpickrToContainer) {
                  const inputs = el._flatpickrToContainer.querySelectorAll('input')
                  const h = (inputs[0] && inputs[0].value) ? String(inputs[0].value).padStart(2, '0') : '00'
                  const m = (inputs[1] && inputs[1].value) ? String(inputs[1].value).padStart(2, '0') : '00'
                  const s = (inputs[2] && inputs[2].value) ? String(inputs[2].value).padStart(2, '0') : '00'
                  toStr = `${h}:${m}:${s}`
                }
                const combined = (toStr && toStr !== '00:00:00') ? `${fromStr} - ${toStr}` : fromStr
                const normLast = noTime ? String(lastAppliedValue || '').split(' ')[0] : String(lastAppliedValue || '')
                if (normLast && String(combined) === String(normLast)) {
                  try { doClear() } catch (e) {}
                  return
                }
              } catch (e) {}
            }
          } catch (e) {}

          if (isDurationRange) {
            const fromPresent = Array.isArray(selectedDates) && selectedDates.length > 0
            const fromStr = fromPresent ? instance.formatDate(instance.latestSelectedDateObj, instance.config.dateFormat) : ''

            let toStr = ''
            let toPresent = false
            if (el._flatpickrToContainer) {
              const inputs = el._flatpickrToContainer.querySelectorAll('input')
              const h = (inputs[0] && inputs[0].value) ? String(inputs[0].value).padStart(2, '0') : '00'
              const m = (inputs[1] && inputs[1].value) ? String(inputs[1].value).padStart(2, '0') : '00'
              const s = (inputs[2] && inputs[2].value) ? String(inputs[2].value).padStart(2, '0') : '00'
              toStr = `${h}:${m}:${s}`
              toPresent = !(h === '00' && m === '00' && (s === '00' || s === undefined))
            }

            // Build preview string but only write to the input when the value has
            // been explicitly applied. While the calendar is open and the user
            // hasn't clicked Apply, prevent any preview from being written to the
            // input by restoring the last applied value. Still call user handlers
            // with the preview (so external preview logic can use it) but never
            // commit it to the input until Apply is clicked.
            let preview = ''
            if (fromPresent && toPresent) preview = `${fromStr} - ${toStr}`
            else if (fromPresent) preview = fromStr
            else if (toPresent) preview = toStr

            if (!applied && instance && instance.isOpen) {
              try {
                const restore = lastAppliedValue || ''
                const r = noTime ? String(restore).split(' ')[0] : restore
                if (el) el.value = r
                try { el.parentNode && el.parentNode.classList.toggle('has-value', (r || '').toString().trim() !== '') } catch (e) {}
              } catch (e) {}
            } else if (applied) {
              const p = noTime ? String(preview).split(' ')[0] : preview
              el.value = p
              try { el.parentNode && el.parentNode.classList.toggle('has-value', (p || '').toString().trim() !== '') } catch(e) {}
            } else {
              // preserve existing input value until explicit Apply
            }
          }

          try {
            const parent = el && el.parentNode
            if (selectedDates && selectedDates.length) {
              parent && parent.classList.add('has-value')
            } else {
              parent && parent.classList.remove('has-value')
            }
          } catch (e) {}

          // If binding.value was a function, call it directly with our preview
          if (typeof userOnChange === 'function') {
            try { userOnChange(selectedDates, (typeof preview !== 'undefined' ? preview : dateStr)) } catch (e) {}
          }
        })

        // ensure button reflects input value when calendar closes or input blurs
        try {
          instance.config.onClose = Array.isArray(instance.config.onClose) ? instance.config.onClose : []
          instance.config.onClose.push((selectedDates, dateStr) => {
            try {
              // If an external caller explicitly allowed closing (we set
              // `instance._externalClose`), honor that first to avoid reopen loops.
              try {
                if (instance && instance._externalClose) {
                  try { allowClose = true } catch (e) {}
                  try { instance._externalClose = false } catch (e) {}
                }
              } catch (e) {}
                // If a close was attempted without using Apply/Clear, reopen the
                // calendar so the user must explicitly Apply or Clear first.
                try {
                  if (!allowClose) {
                    setTimeout(() => { try { if (!allowClose && instance && instance.open) instance.open() } catch (e) {} }, 0)
                    return
                  }
                } catch (e) {}

                // If we are actually closing now, remove the document click handler
                try { if (el && el._flatpickrDocClickHandler) { document.removeEventListener('mousedown', el._flatpickrDocClickHandler, true); el._flatpickrDocClickHandler = null } } catch (e) {}
              // If the user hasn't applied the pending change, always restore the
              // last applied value (do not commit the preview to the input on close).
              if (!applied) {
                    try {
                      // Only restore a previous applied value if we actually have one.
                      // If lastAppliedValue is empty (user cleared), leave the input empty.
                      if (lastAppliedValue && String(lastAppliedValue).trim() !== '') {
                        const v = lastAppliedValue
                        // normalize separator just in case
                        const norm = noTime ? String(v).split(' ')[0] : String(v).replace(/\s*,\s*/g, ' - ')
                        if (el) el.value = norm
                        try { el.parentNode && el.parentNode.classList.toggle('has-value', (norm || '').toString().trim() !== '') } catch(e) {}
                        // some other handlers may write after onClose; enforce again next tick
                        setTimeout(() => {
                          try {
                            if (el) {
                              const v2 = (lastAppliedValue || '')
                              el.value = noTime ? String(v2).split(' ')[0] : String(v2).replace(/\s*,\s*/g, ' - ')
                            }
                          } catch (e) {}
                        }, 0)
                        // It's possible flatpickr or other listeners still update the
                        // input slightly after onClose; schedule additional enforcement
                        // to ensure the preview never appears when not applied.
                        setTimeout(() => {
                          try {
                            if (!applied && el) {
                              const v2 = (lastAppliedValue || '')
                              el.value = noTime ? String(v2).split(' ')[0] : String(v2).replace(/\s*,\s*/g, ' - ')
                            }
                          } catch (e) {}
                        }, 50)
                        setTimeout(() => {
                          try {
                            if (!applied && el) {
                              const v2 = (lastAppliedValue || '')
                              el.value = noTime ? String(v2).split(' ')[0] : String(v2).replace(/\s*,\s*/g, ' - ')
                            }
                          } catch (e) {}
                        }, 150)
                      } else {
                        // ensure empty state is enforced when there is no last applied value
                        try { if (el) el.value = '' } catch (e) {}
                        try { el.parentNode && el.parentNode.classList.remove('has-value') } catch (e) {}
                      }
                    } catch (e) {}
                  }

                // allow writes again after short delay
                setTimeout(() => { try { suppressWrites = false } catch (e) {} }, 200)

              // Sync "To" picker for visual consistency, but do NOT mark as applied.
                if (el && el.value) {
                if (isDurationRange && el.value.includes(' - ') && el._flatpickrToContainer) {
                  const parts = el.value.split(' - ')
                  if (parts[1]) {
                    const [h, m, s] = parts[1].split(':')
                    const inputs = el._flatpickrToContainer.querySelectorAll('input')
                    if (inputs[0]) inputs[0].value = h || '00'
                    if (inputs[1]) inputs[1].value = m || '00'
                    if (inputs[2]) inputs[2].value = s || '00'
                  }
                }
                // Do not flip `applied` to true here — only clicking OK should do that.
                // Keep the button as confirmation-only ('OK') regardless of pending state
                try { actionBtn.textContent = 'OK'; actionBtn.dataset.state = 'ok' } catch (e) {}
              } else {
                // no visible value -> keep OK confirmation
                try { actionBtn.textContent = 'OK'; actionBtn.dataset.state = 'ok' } catch (e) {}
              }
            } catch (e) {}
          })
        } catch (e) {}

        try {
          instance.config.onOpen = Array.isArray(instance.config.onOpen) ? instance.config.onOpen : []
          instance.config.onOpen.push(() => {
            try {
                try { hideTimeUI() } catch (e) {}
                // When the calendar is open, allow closing by clicking outside.
                try {
                  const onDocClick = (ev) => {
                    try {
                      const node = ev && ev.target
                      if (!node) return
                      // if click is outside the calendar container and outside the input
                      if (instance && instance.calendarContainer && !instance.calendarContainer.contains(node) && el !== node && !el.contains(node)) {
                        try { allowClose = true } catch (e) {}
                        try { if (instance) instance._externalClose = true } catch (e) {}
                        try { instance.close() } catch (e) {}
                      }
                    } catch (e) {}
                  }
                  document.addEventListener('mousedown', onDocClick, true)
                  el._flatpickrDocClickHandler = onDocClick
                } catch (e) {}
              // Ensure only one calendar is open at a time: close other instances
              try {
                Array.from(document.querySelectorAll('input')).forEach(inp => {
                  try {
                    const other = inp && inp._flatpickrInstance
                    if (other && other !== instance && typeof other.close === 'function') {
                      try { if (inp._flatpickrAllowClose) inp._flatpickrAllowClose() } catch(e) {}
                      try { other.close() } catch (e) {}
                    }
                  } catch (e) {}
                })
              } catch (e) {}
              if (isDurationRange && el && el.value && el.value.includes(' - ') && el._flatpickrToContainer) {
                const parts = String(el.value).split(' - ')
                const fromPart = parts[0] || ''
                const toPart = parts[1] || ''

                // populate From (original time container)
                try {
                  const [fh, fm, fs] = (fromPart || '').split(':')
                  const fromContainer = instance && instance.calendarContainer ? instance.calendarContainer.querySelector('.flatpickr-time') : null
                  const fromInputs = fromContainer ? fromContainer.querySelectorAll('input') : []
                  if (fromInputs && fromInputs.length) {
                    if (fromInputs[0]) fromInputs[0].value = (fh || '00').padStart(2, '0')
                    if (fromInputs[1]) fromInputs[1].value = (fm || '00').padStart(2, '0')
                    if (fromInputs[2]) fromInputs[2].value = (fs || '00').padStart(2, '0')
                  }
                } catch (e) {}

                // populate To (cloned toTimeContainer)
                try {
                  const [h, m, s] = (toPart || '').split(':')
                  const inputs = el._flatpickrToContainer.querySelectorAll('input')
                  if (inputs && inputs.length) {
                    if (inputs[0]) inputs[0].value = (h || '00').padStart(2, '0')
                    if (inputs[1]) inputs[1].value = (m || '00').padStart(2, '0')
                    if (inputs[2]) inputs[2].value = (s || '00').padStart(2, '0')
                  }
                } catch (e) {}

                // ensure the preview/input shows normalized separator (and strip time if noTime)
                try {
                  el.value = noTime ? String(el.value).split(' ')[0] : String(el.value).replace(/\s*,\s*/g, ' - ')
                } catch (e) {}
              }
              // When opening the calendar, ensure we suppress preview writes
              // if there is a pending, unapplied selection.
              try { suppressWrites = !applied } catch (e) {}
              // Ensure action button reflects whether a value is already applied
              try {
                applied = !!(el && el.value) || !!lastAppliedValue
                try { actionBtn.textContent = 'OK'; actionBtn.dataset.state = 'ok' } catch (e) {}
              } catch (e) {}
            } catch (e) {}
          })
        } catch (e) {}

        const onBlur = () => {
          try {
            // Do not mark values as applied on blur. Only update button label to
            // reflect whether there is an already-applied value.
            try { actionBtn.textContent = 'OK'; actionBtn.dataset.state = 'ok' } catch (e) {}
          } catch (e) {}
        }
        el.addEventListener('blur', onBlur)

        // store references for cleanup
        el._flatpickrActionCleanup = () => {
          try { actionBtn.removeEventListener('click', onActionClick )  } catch(e){}
          try { el.removeEventListener('blur', onBlur) } catch(e){}
          try { actions.remove() } catch(e){}
          try { el.removeEventListener('input', enforceNoWrite, true) } catch (e) {}
          try { el.removeEventListener('change', enforceNoWrite, true) } catch (e) {}
          try { if (_mutObserver) { _mutObserver.disconnect(); _mutObserver = null } } catch (e) {}
          try { if (el._flatpickrDocClickHandler) { document.removeEventListener('mousedown', el._flatpickrDocClickHandler, true); el._flatpickrDocClickHandler = null } } catch (e) {}
        }
      } catch (e) {
        // fail silently if action bar cannot be attached
      }
    }

    // initialize has-value when value present
    // Thai: ใส่คลาส has-value ให้กับ parent ถ้ามีค่าเริ่มต้นใน input
    try { 
      if (el && el.value) {
        // If noTime requested, normalize existing input value to date-only
        try { if (noTime) el.value = String(el.value).split(' ')[0] } catch (e) {}
        el.parentNode && el.parentNode.classList.add('has-value')
        // If duration range, we might need to sync the "To" picker initially, 
        // but the "To" picker is created in mounted() -> instance creation.
        // We can't sync it here easily before it's created. 
        // However, we added sync logic in the creation block above (but I missed adding it in the diff above, let's add it now).
      }
    } catch(e){}

    // Initial sync for duration range (if value exists on mount)
    if (isDurationRange && el.value && el.value.includes(' - ')) {
       // This will be handled when the calendar opens or we can try to set it if we had access to the container.
       // Since the container is created inside the instance logic, we rely on the onClose/onOpen or manual sync if needed.
       // For now, the onClose handler handles re-syncing visual state, but we might want to ensure the "To" inputs are correct if the user opens it.
       // We added sync logic in onClose. We should also add it to onOpen.
      if (instance) {
      instance.config.onOpen = Array.isArray(instance.config.onOpen) ? instance.config.onOpen : []
      instance.config.onOpen.push(() => {
        try { hideTimeUI() } catch (e) {}
        if (el.value && el.value.includes(' - ') && el._flatpickrToContainer) {
                const parts = el.value.split(' - ')
                const fromPart = parts[0] || ''
                const toPart = parts[1] || ''

                // populate From
                try {
                  const [fh, fm, fs] = (fromPart || '').split(':')
                  const fromContainer = instance && instance.calendarContainer ? instance.calendarContainer.querySelector('.flatpickr-time') : null
                  const fromInputs = fromContainer ? fromContainer.querySelectorAll('input') : []
                  if (fromInputs && fromInputs.length) {
                    if (fromInputs[0]) fromInputs[0].value = (fh || '00').padStart(2, '0')
                    if (fromInputs[1]) fromInputs[1].value = (fm || '00').padStart(2, '0')
                    if (fromInputs[2]) fromInputs[2].value = (fs || '00').padStart(2, '0')
                  }
                } catch (e) {}

                // populate To
                try {
                  if (toPart) {
                    const [h, m, s] = (toPart || '').split(':')
                    const inputs = el._flatpickrToContainer.querySelectorAll('input')
                    if (inputs[0]) inputs[0].value = (h || '00')
                    if (inputs[1]) inputs[1].value = (m || '00')
                    if (inputs[2]) inputs[2].value = (s || '00')
                  }
                } catch (e) {}
            }
         })
       }
    }

    // store instance for cleanup
    // Expose instance and helper on element for external callers (eg. onReset)
    el._flatpickrInstance = instance
    el._flatpickr = instance
    // expose a safe clear that mirrors the internal doClear behaviour
    try { if (typeof doClear === 'function') el._flatpickrDoClear = doClear } catch (e) {}
    // expose helper to temporarily allow external closes (used by other pickers)
    try {
      el._flatpickrAllowClose = function () {
        try { allowClose = true } catch (e) {}
        try { if (instance) instance._externalClose = true } catch (e) {}
        try { setTimeout(() => { try { allowClose = false } catch (e) {} if (instance) try { instance._externalClose = false } catch (e) {} }, 250) } catch (e) {}
      }
    } catch (e) {}
  },

  beforeUnmount(el) {
    try {
      if (el._flatpickrInstance && typeof el._flatpickrInstance.destroy === 'function') el._flatpickrInstance.destroy()
      if (el._flatpickrActionCleanup && typeof el._flatpickrActionCleanup === 'function') el._flatpickrActionCleanup()
    } catch (e) {}
    delete el._flatpickrInstance
    delete el._flatpickr
    delete el._flatpickrDoClear
    try { delete el._flatpickrActionCleanup } catch(e){}
    // If we replaced the element's `value` property, remove it so prototype
    // behaviour is restored.
    try { delete el.value } catch (e) {}
  }
}
