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
    const userOnChange = (typeof raw === 'function') ? raw : value.onChange
    const isDurationRange = value.mode === 'duration_range'

    const instance = fp(el, opts)

    if (instance && instance.config && Array.isArray(instance.config.onChange)) {
      // Track whether the current value has been explicitly applied by the user
      let applied = !!(el && el.value)
      // Keep last applied value so we can restore it if flatpickr writes a default (00:00:00) on close
      let lastAppliedValue = (el && el.value) ? el.value : ''

      // create a small action bar appended to flatpickr's calendar container
      try {
        const actions = document.createElement('div')
        actions.className = 'flatpickr-actions'

        const actionBtn = document.createElement('button')
        actionBtn.type = 'button'
        actionBtn.className = 'flatpickr-action-btn'
        actionBtn.textContent = applied ? ' ' : 'Apply'
        actionBtn.dataset.state = applied ? 'clear' : 'apply'

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
                    actionBtn.textContent = 'Apply'
                    actionBtn.dataset.state = 'apply'
                  } catch (e) {}
                })
              })
            }
            setupClonedInput(toTimeContainer)
            rowTo.appendChild(toTimeContainer)

            wrapper.appendChild(rowFrom)
            wrapper.appendChild(rowTo)
            el._flatpickrToContainer = toTimeContainer // Store ref

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
            finalStr = el.value || (instance && instance.selectedDates && instance.selectedDates.length ? instance.formatDate(instance.selectedDates[0], instance.config.dateFormat) : '')
          }

          if (target && key) try { target[key] = finalStr } catch(e){}
          el.value = finalStr
          applied = true
          lastAppliedValue = finalStr
          // actionBtn.textContent = 'Clear'
          // actionBtn.dataset.state = 'clear'
          try { instance.close() } catch(e){}
        }

        const doClear = () => {
          try { instance.clear() } catch(e){}
          if (isDurationRange && el._flatpickrToContainer) {
            const inputs = el._flatpickrToContainer.querySelectorAll('input')
            inputs.forEach(i => i.value = '00')
          }
          if (target && key) try { target[key] = '' } catch(e){}
          el.value = ''
          applied = false
          lastAppliedValue = ''
          // Remove visual has-value state from the input wrapper (for from-to duration range)
          try {
            const parent = el && el.parentNode
            parent && parent.classList.remove('has-value')
          } catch (e) {}
          actionBtn.textContent = 'Apply'
          actionBtn.dataset.state = 'apply'
          try { instance.close() } catch(e){}
        }

        const onActionClick = (ev) => {
          ev && ev.stopPropagation()
          if (actionBtn.dataset.state === 'clear') doClear(); else doApply()
        }

        actionBtn.addEventListener('click', onActionClick)

        // update button state when user changes selection
          instance.config.onChange.push((selectedDates, dateStr) => {
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

            // Build preview string but only write to the input when the calendar
            // is open (preview) or when a value is already applied. This prevents
            // committing the preview to the input when the user closes without Apply.
            let preview = ''
            if (fromPresent && toPresent) preview = `${fromStr} - ${toStr}`
            else if (fromPresent) preview = fromStr
            else if (toPresent) preview = toStr

            if ((instance && instance.isOpen) || applied) {
              el.value = preview
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

          // when a new selection or time edit is made it becomes pending (needs Apply)
            if (selectedDates && selectedDates.length) {
            applied = false
            actionBtn.textContent = 'Apply'
            actionBtn.dataset.state = 'apply'
          }

          // If binding.value was a function, call it directly
          if (typeof userOnChange === 'function') {
            try { userOnChange(selectedDates, dateStr) } catch (e) {}
          }
        })

        // ensure button reflects input value when calendar closes or input blurs
        try {
          instance.config.onClose = Array.isArray(instance.config.onClose) ? instance.config.onClose : []
          instance.config.onClose.push((selectedDates, dateStr) => {
            try {
              // If the user hasn't applied the pending change and flatpickr wrote a default value
              // (e.g. "00:00:00"), restore the last applied value instead of overwriting it.
              if (!applied) {
                const val = el && el.value
                const isDefaultTime = val && typeof val === 'string' && /^0{1,2}(:0{2}){1,2}$/.test(val)
                if (!val || isDefaultTime) {
                  if (el) el.value = lastAppliedValue || ''
                }
              }

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
                // Do not flip `applied` to true here — only clicking Apply should do that.
                // Update button text to reflect pending state
                if (applied) {
                  actionBtn.textContent = 'Clear'
                  actionBtn.dataset.state = 'clear'
                } else {
                  actionBtn.textContent = 'Apply'
                  actionBtn.dataset.state = 'apply'
                }
              } else {
                // no visible value -> show Apply state
                actionBtn.textContent = 'Apply'
                actionBtn.dataset.state = 'apply'
              }
            } catch (e) {}
          })
        } catch (e) {}

        const onBlur = () => {
          try {
            // Do not mark values as applied on blur. Only update button label to
            // reflect whether there is an already-applied value.
            if (applied) {
              actionBtn.textContent = 'Clear'
              actionBtn.dataset.state = 'clear'
            } else {
              actionBtn.textContent = 'Apply'
              actionBtn.dataset.state = 'apply'
            }
          } catch (e) {}
        }
        el.addEventListener('blur', onBlur)

        // store references for cleanup
        el._flatpickrActionCleanup = () => {
          try { actionBtn.removeEventListener('click', onActionClick )  } catch(e){}
          try { el.removeEventListener('blur', onBlur) } catch(e){}
          try { actions.remove() } catch(e){}
        }
      } catch (e) {
        // fail silently if action bar cannot be attached
      }
    }

    // initialize has-value when value present
    // Thai: ใส่คลาส has-value ให้กับ parent ถ้ามีค่าเริ่มต้นใน input
    try { 
      if (el && el.value) {
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
            if (el.value && el.value.includes(' - ') && el._flatpickrToContainer) {
                const parts = el.value.split(' - ')
                if (parts[1]) {
                  const [h, m, s] = parts[1].split(':')
                  const inputs = el._flatpickrToContainer.querySelectorAll('input')
                  if (inputs[0]) inputs[0].value = h || '00'
                  if (inputs[1]) inputs[1].value = m || '00'
                  if (inputs[2]) inputs[2].value = s || '00'
                }
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
  }
}
