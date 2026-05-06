import { getApiBase } from '../../api/paths'

export function getCookie(name) {
    if (!name || typeof document === 'undefined') return null
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)')
    return v ? v.pop() : null
}
// ensure custom styles for notify/toast exist
function ensureNotifyStyles() {
  if (typeof document === 'undefined') return
  if (document.getElementById('notify-custom-styles')) return
  const css = `
  .swal2-custom-popup { border-radius: 10px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.12); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
  .swal2-custom-title { font-size: 28px; font-weight: 600; color: #333; margin-bottom: 6px; }
  .swal2-custom-content { color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 18px; }
  .swal2-custom-confirm { background: linear-gradient(180deg,#4f86ff,#2b6bff) !important; color: #fff !important; border-radius: 22px !important; padding: 8px 22px !important; box-shadow: 0 3px 0 rgba(0,0,0,0.12); }

  /* Namespaced toast tweaks (use .nt-toast to avoid conflicts with global .toast rules) */
  .nt-toast { position: fixed; right: 18px; top: 18px; display: flex; align-items: center; gap: 12px; background: rgba(0,0,0,0.78); color: #fff; padding: 12px 14px; border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); max-width: 380px; z-index: 9999; opacity: 0; transform: translateY(-8px); transition: opacity .18s ease, transform .18s ease; pointer-events: auto; }
  .nt-toast.show { opacity: 1; transform: translateY(0); }
  .nt-toast .title { font-weight: 700; font-size: 14px; }
  .nt-toast .message { font-size: 13px; color: rgba(255,255,255,0.95); }
  .nt-toast.success { background: linear-gradient(90deg,#36b37e,#2ea36a); }
  .nt-toast.error { background: linear-gradient(90deg,#ff6b6b,#ff4b4b); }
  .nt-toast .icon { font-size: 18px; }
  .nt-toast-progress { height: 3px; background: rgba(255,255,255,0.12); border-radius: 2px; overflow: hidden; margin-top: 8px; }
  .nt-toast-progress-bar { height: 100%; background: rgba(255,255,255,0.9); width: 100%; }
  `
  const style = document.createElement('style')
  style.id = 'notify-custom-styles'
  style.appendChild(document.createTextNode(css))
  document.head.appendChild(style)
}
export function showToast(titleOrMessage, maybeTypeOrMessage = '', maybeType) {
  try {
    // Ensure styles are present before creating toasts (fixes missing/incorrect styling on first load)
    ensureNotifyStyles()
    const types = ['success', 'error', 'info', 'warning']
    let title = ''
    let message = ''
    let type = 'success'

    if (maybeType !== undefined) {
      // called as showToast(title, message, type)
      title = String(titleOrMessage || '')
      message = String(maybeTypeOrMessage || '')
      type = String(maybeType || 'success')
    } else {
      if (types.includes(String(maybeTypeOrMessage))) {
        // called as showToast(message, type)
        title = ''
        message = String(titleOrMessage || '')
        type = String(maybeTypeOrMessage)
      } else {
        // called as showToast(title, message) or showToast(message)
        title = String(titleOrMessage || '')
        message = String(maybeTypeOrMessage || '')
        type = 'success'
      }
    }

    const el = document.createElement('div')
    el.className = `toast ${type || ''}`

    const icon = document.createElement('div')
    icon.className = 'icon'
    // ensure glyph color is white for visibility against colored backgrounds
    icon.style.color = '#fff'
    // small vertical nudge to better center glyphs
    // mark icon as decorative for screen readers
    icon.setAttribute('aria-hidden', 'true')
    // set glyph per type; use Font Awesome for error for a consistent X mark
    const glyphMap = {
      success: { char: '✓' },
      error: { fa: 'fa-solid fa-xmark' },
      info: { char: 'ℹ' },
      warning: { char: '!' }
    }
    const map = glyphMap[type] || glyphMap.success
    if (map.fa) {
      icon.innerHTML = `<i class="${map.fa}" aria-hidden="true" style="margin-top: 2px;"></i>`
    } else {
      icon.textContent = map.char
    }

    const content = document.createElement('div')
    content.className = 'content'
    if (title) {
      const t = document.createElement('div')
      t.className = 'title'
      t.textContent = title
      content.appendChild(t)
    }
    if (message) {
      const m = document.createElement('div')
      m.className = 'message'
      // render HTML when backend sends markup (e.g. <br>) otherwise use textContent
      try {
        if (/<\/?[a-z][\s\S]*>/i.test(message)) m.innerHTML = message
        else m.textContent = message
      } catch (e) { m.textContent = String(message) }
      content.appendChild(m)
    }

    el.appendChild(icon)
    el.appendChild(content)
    // insert at top so newest is on top
    const first = document.body.querySelector('.toast')
    if (first) document.body.insertBefore(el, first)
    else document.body.appendChild(el)

    // show toast and set up timed hide/remove with progress bar and hover-pause
    requestAnimationFrame(() => el.classList.add('show'))

    const hideDelay = 3200 // ms until hide
    const removeDelay = 3800 // ms until DOM removal

    // add progress bar element
    const progressWrap = document.createElement('div')
    progressWrap.className = 'toast-progress'
    const progressBar = document.createElement('div')
    progressBar.className = 'toast-progress-bar'
    progressWrap.appendChild(progressBar)
    el.appendChild(progressWrap)

    let remaining = hideDelay
    let progStart = Date.now()
    let progDuration = remaining
    let hideTimeout = null
    let removeTimeout = null
    let rafId = null

    function rafLoop() {
      const now = Date.now()
      const elapsed = now - progStart
      const pct = Math.max(0, Math.min(100, ((progDuration - elapsed) / progDuration) * 100))
      progressBar.style.width = pct + '%'
      if (elapsed < progDuration) rafId = requestAnimationFrame(rafLoop)
    }

    function startTimers(ms) {
      // set up hide and remove timeouts relative to now
      hideTimeout = setTimeout(() => {
        el.classList.remove('show')
      }, ms)
      const removeAfter = ms + (removeDelay - hideDelay)
      removeTimeout = setTimeout(() => { try { el.remove() } catch (e) {} }, removeAfter)
      // start progress
      progStart = Date.now()
      progDuration = Math.max(1, ms)
      if (rafId) cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(rafLoop)
    }

    // begin
    startTimers(remaining)

    // pause on hover: clear timers and stop RAF
    el.addEventListener('mouseenter', () => {
      if (hideTimeout) { clearTimeout(hideTimeout); hideTimeout = null }
      if (removeTimeout) { clearTimeout(removeTimeout); removeTimeout = null }
      if (rafId) { cancelAnimationFrame(rafId); rafId = null }
      const now = Date.now()
      const elapsed = now - progStart
      remaining = Math.max(0, progDuration - elapsed)
    })

    // resume on mouseleave
    el.addEventListener('mouseleave', () => {
      startTimers(remaining)
    })
  } catch (e) { console.warn('showToast failed', e) }
}

export function notification (title, text, icon, showCancelButton){

}

export function logUserAction(action, detail, status = 'error') {
  try {
    const csrfToken = getCookie('csrftoken') || ''
    const url = getApiBase().replace(/\/$/, '') + '/api/log/user-action/'
    fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ action, detail, status })
    }).catch(() => {})
  } catch (e) { console.warn('logUserAction failed', e) }
}

export async function exportTableToFormat(format, type = 'audio', opts = {}) {
  try {
    const returnBlob = !!(opts && opts.returnBlob)
    const rows = Array.isArray(opts.rows) ? opts.rows : []
    const columns = Array.isArray(opts.columns) ? opts.columns : []
    // filter out utility/action columns for every export format
    const usedColumns = columns.filter(c => c && !c.isAction && c.key !== 'actions' && c.key !== 'checked')
    const startIndex = typeof opts.startIndex === 'number' ? opts.startIndex : 0
    const rangeStart = (startIndex || 0) + 1
    const rangeEnd = (startIndex || 0) + (rows.length || 0)

    const hdrs = usedColumns.map(c => c.label || c.key)

    // convert rows to exportable strings, with special handling for boolean status
    // helper: resolve value from row, supporting nested props and common patterns
    function resolveRowValue(row, key) {
      if (!row) return undefined
      if (!key) return undefined
      // dot-path support
      if (String(key).includes('.')) {
        const parts = String(key).split('.')
        let cur = row
        for (const p of parts) {
          if (cur && Object.prototype.hasOwnProperty.call(cur, p)) cur = cur[p]
          else { cur = undefined; break }
        }
        if (cur !== undefined) return cur
      }

      // direct property
      if (Object.prototype.hasOwnProperty.call(row, key)) return row[key]

      for (const prop in row) {
        if (!Object.prototype.hasOwnProperty.call(row, prop)) continue
        const v = row[prop]
        if (v && typeof v === 'object') {
          if (Object.prototype.hasOwnProperty.call(v, key)) return v[key]
        }
      }

      // special-case common full name
      const keyLower = String(key || '').toLowerCase()
      if (keyLower === 'full_name' || keyLower === 'fullname' || keyLower.includes('full')) {
        if (row.user && (row.user.first_name || row.user.last_name)) {
          return `${row.user.first_name || ''} ${row.user.last_name || ''}`.trim()
        }
        if (row.user && row.user.name) return row.user.name
      }

      return undefined
    }

    const exportData = rows.map((row, rIdx) => {
      return usedColumns.map((col) => {
        if (col.isIndex) return (startIndex || 0) + rIdx + 1
        const key = col.key
        let val = resolveRowValue(row, key)

        // provide special-case resolution for common UI-derived columns
        const keyLower = String(key || '').toLowerCase()
        try {
          if ((val === undefined || val === null) && keyLower === 'role') {
            val = (row && row.permission) || (row && row.user && (row.user.permission || row.user.role)) || undefined
          }
          if ((val === undefined || val === null) && keyLower === 'status') {
            // prefer top-level is_active, fallback to nested user.is_active
            const s = (row && typeof row.is_active !== 'undefined') ? row.is_active : (row && row.user && typeof row.user.is_active !== 'undefined' ? row.user.is_active : undefined)
            if (typeof s !== 'undefined') val = s
          }
          if ((val === undefined || val === null) && (keyLower === 'group' || keyLower === 'team')) {
            // derive from row.team or row.group_team to match UI helpers
            let derived = ''
            if (Array.isArray(row.team) && row.team.length) {
              const t = row.team[0]
              if (keyLower === 'group') derived = (t && ((t.user_group && (t.user_group.group_name || t.user_group)) || t.user_group)) || ''
              else derived = (t && (t.name || t.team_name)) || ''
            } else if (row.team && typeof row.team === 'object') {
              if (keyLower === 'group') derived = row.team.user_group ? (row.team.user_group.group_name || row.team.user_group) : ''
              else derived = row.team.name || row.team.team_name || ''
            } else if (row.group_team && typeof row.group_team === 'string') {
              const first = row.group_team.split(',').map(s => s.trim()).filter(Boolean)[0] || ''
              if (first) {
                if (keyLower === 'group') {
                  derived = first.includes(' / ') ? first.split(' / ')[0].trim() : ''
                } else {
                  derived = first.includes(' / ') ? (first.split(' / ')[1] || '').trim() : first
                }
              }
            }
            if (derived) val = derived
          }
        } catch (e) { /* ignore */ }

        // Treat null/undefined or empty-string-like values as empty
        if (val === null || val === undefined) return '-'

        // Normalize boolean-like status fields to human labels for export
        try {
          const keyLower = String(key || '').toLowerCase()
          if (keyLower === 'status' || keyLower.includes('status')) {
            if (val === true || String(val).toLowerCase() === 'true' || String(val) === '1') return 'Active'
            if (val === false || String(val).toLowerCase() === 'false' || String(val) === '0') return 'Expired'
            if (String(val).toLowerCase().includes('act')) return 'Active'
            if (String(val).toLowerCase().includes('inact') || String(val).toLowerCase().includes('expire')) return 'Expired'
          }
        } catch (e) { /* ignore */ }

        const s = String(val)
        if (s.trim() === '') return '-'
        return s
      })
    })

    // Allow caller to override the filename prefix via opts.fileNamePrefix
    let fileTypeName = ''
    if (opts && opts.fileNamePrefix) {
      fileTypeName = String(opts.fileNamePrefix)
      if (!fileTypeName.endsWith('_')) fileTypeName += '_'
    } else {
      if (type === 'audit') fileTypeName = 'audit-records_'
      else if (type === 'audio') fileTypeName = 'audio-records_'
      else fileTypeName = (type ? String(type) + '_' : '')
    }

    // Excel (HTML-based .xls)
    if (format === 'excel') {
      const headerBg = '#2980b9'
      const callDirColorMap = {
        'Incoming': '#baf3c7', 'Inbound': '#baf3c7', 'Outgoing': '#add8e6', 'Outbound': '#add8e6', 'Internal': '#fdedbe', 'Block': '#ff7878', 'Tandem': '#add8e6', 'External': '#f0f0f0'
      }
      // map exported status labels to colors: Active=green, Expired=red
      const statusColorMap = { 'Active': '#baf3c7', 'Expired': '#ff7878', 'success': '#baf3c7', 'error': '#ff7878' }

      let html = '<html><head><meta charset="UTF-8"></head><body>'
      html += '<table border="1" cellspacing="0" cellpadding="0">'
      html += '<tr>'
      html += '<td colspan="' + hdrs.length + '" style="text-align:left;font-size:28px;color:#2980b9;padding:8px;font-weight:bold;">' + (type === 'audio' ? 'Audio Records' : type) + '</td>'
      html += '</tr>'
      html += '<tr>'
      html += '<td colspan="' + hdrs.length + '" style="border-bottom:2px solid #2980b9;padding:0;margin:0;">&nbsp;</td>'
      html += '</tr>'
      html += '<thead><tr>'
      hdrs.forEach(h => { html += '<th style="background-color:' + headerBg + ';color:#ffffff;padding:8px;">' + (h || '') + '</th>' })
      html += '</tr></thead><tbody>'

      const custNumIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('customer') || String(h).toLowerCase().includes('number'))
      const extIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('extension') || String(h).toLowerCase().includes('ext'))
      const callDirIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('call direction'))
      const statusIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('status'))

      exportData.forEach(row => {
        html += '<tr>'
        row.forEach((cell, cellIndex) => {
            const raw = (cell === null || cell === undefined) ? '' : String(cell)
            const textEsc = raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            // show '-' for empty values and center it in the cell
            const text = (textEsc.trim() === '') ? '-' : textEsc
            // prevent Excel from converting long numeric-like strings to scientific notation
            const plain = (raw || '').trim()
            const forceAsText = /^\d{15,}$/.test(plain)
            // default: left-aligned, top-aligned for all data cells
            let cellStyle = 'text-align:left;vertical-align:top;'
            if (text === '-') {
              cellStyle = 'text-align:center;vertical-align:top;'
            }
            if (callDirIndex >= 0 && cellIndex === callDirIndex) {
              const bg = callDirColorMap[text] || '#ffffff'
              cellStyle += 'background-color:' + bg + ';'
            } else if (statusIndex >= 0 && cellIndex === statusIndex) {
              const bg = statusColorMap[text] || '#ffffff'
              cellStyle += 'background-color:' + bg + ';'
            }
            // right-align numeric/customer columns, but don't override centered '-'
            if (text !== '-' && ((custNumIndex >= 0 && cellIndex === custNumIndex) || (extIndex >= 0 && cellIndex === extIndex))) {
              cellStyle += "text-align:right;mso-number-format:'@';"
            }
            if (forceAsText) {
              cellStyle += "mso-number-format:'@';"
            }
            html += '<td style="' + cellStyle + '">' + text + '</td>'
          })
        html += '</tr>'
      })

      html += '</tbody></table></body></html>'

      const blob = new Blob([html], { type: 'application/vnd.ms-excel' })
      const dateStr = new Date().toISOString().slice(0, 10)
      const fileName = fileTypeName + dateStr + '_' + rangeStart + '-' + rangeEnd + '.xls'
      if (returnBlob) return { blob, fileName }
      if (window.navigator && window.navigator.msSaveOrOpenBlob) window.navigator.msSaveOrOpenBlob(blob, fileName)
      else {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = fileName
        document.body.appendChild(a)
        a.click()
        a.remove()
        setTimeout(() => URL.revokeObjectURL(url), 3000)
      }
      return
    }

    // CSV
    if (format === 'csv') {
      const BOM = '\uFEFF'
      const escapeCsv = (v) => {
        if (v === null || v === undefined) return ''
        const s = String(v)
        const trimmed = s.trim()
        // keep long digit strings as raw Excel formula to preserve as text (no CSV quoting needed)
        if (/^\d{15,}$/.test(trimmed)) return `="${trimmed}"`
        return '"' + s.replace(/"/g, '""') + '"'
      }
      const csvLines = []
      csvLines.push(hdrs.map(h => escapeCsv(h)).join(','))
      exportData.forEach(r => {
        csvLines.push(r.map(cell => escapeCsv(cell)).join(','))
      })
      const csvContent = BOM + csvLines.join('\r\n')
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const dateStr = new Date().toISOString().slice(0, 10)
      const fileName = fileTypeName + dateStr + '_' + rangeStart + '-' + rangeEnd + '.csv'
      if (returnBlob) return { blob, fileName }
      if (window.navigator && window.navigator.msSaveOrOpenBlob) window.navigator.msSaveOrOpenBlob(blob, fileName)
      else {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = fileName
        document.body.appendChild(a)
        a.click()
        a.remove()
        setTimeout(() => URL.revokeObjectURL(url), 3000)
      }
      return
    }

    // PDF using jsPDF + autoTable (expects window.jspdf and autoTable plugin available)
    if (format === 'pdf') {
      const { jsPDF } = window.jspdf || {}
      if (!jsPDF) {
        console.error('jsPDF not available')
        return
      }
      // always export PDF in landscape mode
      const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
      const titleText = (type === 'audio') ? 'Audio Records' : type

      const descIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('description'))
      const fileNameIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('file name'))
      const callDirIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('call direction'))
      const statusIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('status'))

      // Compute minCellWidth per column so header text fits without wrapping (~1.8mm per char in bold 8.5pt Helvetica + 4mm padding)
      const columnStyles = {}
      hdrs.forEach((h, i) => {
        columnStyles[i] = { minCellWidth: Math.max(10, (h || '').length * 1.8 + 4) }
      })
      if (descIndex >= 0) columnStyles[descIndex] = { ...columnStyles[descIndex], cellWidth: 70 }
      if (fileNameIndex >= 0) columnStyles[fileNameIndex] = { ...columnStyles[fileNameIndex], cellWidth: 60 }

      const callDirColorMap = {
        'Incoming': { bg: [186,243,199], text: [23,21,21] }, 'Inbound': { bg: [186,243,199], text: [23,21,21] }, 'Outgoing': { bg: [173,216,230], text: [23,21,21] }, 'Outbound': { bg: [173,216,230], text: [23,21,21] }, 'Internal': { bg: [253,237,190], text: [23,21,21] }, 'Block': { bg: [255,120,120], text: [255,255,255] }, 'Tandem': { bg: [173,216,230], text: [255,255,255] }, 'External': { bg: [240,240,240], text: [23,21,21] }
      }
      // PDF color mapping for status labels: Active green, Expired red
      const statusColorMap = {
        'Active': { bg: [186,243,199], text: [23,21,21] },
        'Expired': { bg: [255,120,120], text: [255,255,255] },
        'success': { bg: [186,243,199], text: [23,21,21] },
        'error': { bg: [255,120,120], text: [255,255,255] }
      }

      doc.autoTable({
        head: [hdrs],
        body: exportData,
        startY: 22,
        margin: { top: 22, left: 14, right: 14 },
        theme: 'grid',
        styles: { font: 'helvetica', fontSize: 7.5, cellPadding: 2, overflow: 'linebreak' },
        bodyStyles: { halign: 'left', valign: 'top' },
        headStyles: { fillColor: [41,128,185], textColor: [255,255,255], fontSize: 8.5, fontStyle: 'bold' },
        columnStyles: columnStyles,
        tableWidth: 'auto',
        didDrawPage: function (data) {
          const pageWidth = doc.internal.pageSize.getWidth ? doc.internal.pageSize.getWidth() : doc.internal.pageSize.width
          const left = data.settings && data.settings.margin && data.settings.margin.left !== undefined ? data.settings.margin.left : 14
          const right = data.settings && data.settings.margin && data.settings.margin.right !== undefined ? data.settings.margin.right : 14
          const lineStartX = left
          const lineEndX = pageWidth - right
          doc.setFontSize(16)
          doc.setTextColor(41,128,185)
          doc.text(String(titleText), left, 12)
          const pageNum = (typeof data.pageNumber !== 'undefined') ? data.pageNumber : doc.internal.getNumberOfPages()
          doc.setFontSize(10)
          doc.setTextColor(41,128,185)
          if (doc.textAlign) doc.text('Page ' + pageNum, lineEndX, 12, { align: 'right' })
          else doc.text('Page ' + pageNum, lineEndX, 12, null, null, 'right')
          doc.setDrawColor(41,128,185)
          doc.line(lineStartX, 16, lineEndX, 16)
        },
        didParseCell: function (data) {
          const custNumIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('customer') || String(h).toLowerCase().includes('number'))
          const extIndex = hdrs.findIndex(h => String(h).toLowerCase().includes('extension') || String(h).toLowerCase().includes('ext'))
          const cellText = (data && data.cell && Array.isArray(data.cell.text) && data.cell.text.length > 0) ? String(data.cell.text[0]) : ''
          // center '-' explicitly
          if (cellText === '-') {
            data.cell.styles.halign = 'center'
          } else if ((custNumIndex >= 0 && data.column.index === custNumIndex) || (extIndex >= 0 && data.column.index === extIndex)) {
            data.cell.styles.halign = 'right'
          }
          if (callDirIndex >= 0 && data.column.index === callDirIndex && data.section === 'body') {
            const cellValue = data.cell.text[0]
            const colorInfo = callDirColorMap[cellValue]
            if (colorInfo) { data.cell.styles.fillColor = colorInfo.bg; data.cell.styles.textColor = colorInfo.text }
          }
          if (statusIndex >= 0 && data.column.index === statusIndex && data.section === 'body') {
            const cellValue = data.cell.text[0]
            const colorInfo = statusColorMap[cellValue]
            if (colorInfo) { data.cell.styles.fillColor = colorInfo.bg; data.cell.styles.textColor = colorInfo.text }
          }
        }
      })

      const dateStr = new Date().toISOString().slice(0, 10)
      const fileName = fileTypeName + dateStr + '_' + rangeStart + '-' + rangeEnd + '.pdf'
      if (returnBlob) {
        try {
          const blob = doc.output && typeof doc.output === 'function' ? doc.output('blob') : null
          if (blob) return { blob, fileName }
        } catch (e) { console.warn('pdf blob output failed', e) }
        // fallback to save and return nothing
      }
      doc.save(fileName)
      return
    }
  } catch (err) {
    console.error('exportTableToFormat error', err)
  }
}

export async function confirmDelete(title = 'Are you sure?', text = "You won't be able to revert this!", confirmButtonText = 'Yes, delete it!') {
    const swalLib = (typeof Swal !== 'undefined' && Swal) || (typeof window !== 'undefined' && (window.Swal || window.Sweetalert2 || window.SweetAlert || window.sweetAlert))

    if (swalLib && typeof swalLib.fire === 'function') {
        const result = await swalLib.fire({
            title: title,
            text: text,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: confirmButtonText
        })
        return !!(result && result.isConfirmed)
    } else {
        return window.confirm(`${title} ${text}`)
    }
}

export async function notify(title, message, type = 'success') {
    const swalLib = (typeof Swal !== 'undefined' && Swal) || (typeof window !== 'undefined' && (window.Swal || window.Sweetalert2 || window.SweetAlert || window.sweetAlert))

    if (swalLib && typeof swalLib.fire === 'function') {
      ensureNotifyStyles()
      const hasHtml = /<\/?[a-z][\s\S]*>/i.test(String(message || ''))
      const opts = {
        title: title || undefined,
        icon: type,
        confirmButtonColor: '#3085d6',
        confirmButtonText: 'OK',
        allowOutsideClick: false,
        customClass: { popup: 'swal2-custom-popup', title: 'swal2-custom-title', content: 'swal2-custom-content', confirmButton: 'swal2-custom-confirm' }
      }
      if (hasHtml) opts.html = message
      else opts.text = message
      await swalLib.fire(opts)
    } else {
      ensureNotifyStyles()
      showToast(title, message, type)
    }
}

