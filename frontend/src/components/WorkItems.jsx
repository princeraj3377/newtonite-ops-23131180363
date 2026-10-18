import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ArrowUpRight, CheckCircle2, ClipboardList, LoaderCircle, Plus, RefreshCw, Search, SlidersHorizontal, X } from 'lucide-react'
import { api, getErrorMessage } from '../lib/api'
import { createItemSubmission, itemsPath, itemTypes, label, priorities, statuses, transitions } from '../lib/workItems'
import { useResource } from '../hooks/useResource'
import './WorkItems.css'
import ItemDiscussion from './ItemDiscussion'
import AssignmentControls from './AssignmentControls'

function Options({ values }) {
  return values.map((value) => <option key={value} value={value}>{label(value)}</option>)
}

function LoadState({ resource, children }) {
  if (resource.loading) return <div className="items-empty" role="status"><LoaderCircle className="spinner" size={24} /><p>Loading your workspace…</p></div>
  if (resource.error) return <div className="items-empty"><p role="alert">{resource.error}</p><button className="secondary-button" onClick={resource.reload}><RefreshCw size={15} /> Try again</button></div>
  return children
}

function Modal({ title, onClose, busy, children }) {
  const dialog = useRef(null)
  useEffect(() => {
    const element = dialog.current
    element.showModal()
    return () => element.close()
  }, [])
  return <dialog ref={dialog} className="item-dialog" aria-labelledby="dialog-title" onCancel={(event) => { event.preventDefault(); if (!busy) onClose() }}>
    <div className="dialog-header"><h2 id="dialog-title">{title}</h2><button className="icon-button" aria-label="Close dialog" disabled={busy} onClick={onClose}><X size={20} /></button></div>
    {children}
  </dialog>
}

function CreateItem({ team, onClose, onCreated }) {
  const [draft, setDraft] = useState({ title: '', description: '', item_type: 'task', priority: 'medium' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [submit] = useState(createItemSubmission)
  const update = (event) => setDraft({ ...draft, [event.target.name]: event.target.value })

  async function save(event) {
    event.preventDefault()
    if (busy) return
    const payload = { ...draft, title: draft.title.trim(), description: draft.description.trim(), team_id: team.id }
    if (payload.title.length < 3 || !payload.description) {
      setError('Add a title of at least 3 characters and a description.')
      return
    }
    setBusy(true)
    setError('')
    try { onCreated(await submit(payload)) }
    catch (failure) { setError(getErrorMessage(failure)) }
    finally { setBusy(false) }
  }

  return <Modal title="New work item" busy={busy} onClose={onClose}>
    <p className="dialog-description">Create a work item for <strong>{team.name}</strong>.</p>
    <form className="item-form" onSubmit={save} aria-busy={busy}>
      {error && <div className="form-alert" role="alert">{error}</div>}
      <fieldset disabled={busy}>
        <label htmlFor="item-title">Title</label><input id="item-title" name="title" value={draft.title} onChange={update} placeholder="What needs to get done?" minLength={3} maxLength={200} required autoFocus />
        <label htmlFor="item-description">Description</label><textarea id="item-description" name="description" value={draft.description} onChange={update} placeholder="Add the details your team needs…" rows={5} required />
        <div className="form-columns"><div><label htmlFor="item-type">Type</label><select id="item-type" name="item_type" value={draft.item_type} onChange={update}><Options values={itemTypes} /></select></div><div><label htmlFor="item-priority">Priority</label><select id="item-priority" name="priority" value={draft.priority} onChange={update}><Options values={priorities} /></select></div></div>
      </fieldset>
      <div className="dialog-actions"><button type="button" className="secondary-button" disabled={busy} onClick={onClose}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? <LoaderCircle className="spinner" size={16} /> : <Plus size={16} />}{busy ? 'Creating…' : 'Create work item'}</button></div>
    </form>
  </Modal>
}

function ItemDetails({ itemId, team, user, onClose, onChanged }) {
  const resource = useResource(`/items/${itemId}`)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [commentBusy, setCommentBusy] = useState(false)
  const [activityRevision, setActivityRevision] = useState(0)
  const mutationPending = useRef(false)
  const item = resource.data
  async function updateItem(action, payload, message) {
    if (mutationPending.current || commentBusy || !item) return
    mutationPending.current = true
    setBusy(true)
    setError('')
    try {
      await api.patch(`/items/${itemId}/${action}`, { ...payload, expected_version: item.version })
      resource.reload()
      setActivityRevision((value) => value + 1)
      onChanged(message)
    } catch (failure) {
      setError(getErrorMessage(failure))
      // Reload the latest version before a user retries a conflicted write.
      if (failure.response?.status === 409) {
        resource.reload()
        setActivityRevision((value) => value + 1)
      }
    } finally { mutationPending.current = false; setBusy(false) }
  }
  const changeStatus = (status) => updateItem('status', { status }, 'Work item status updated.')
  return <Modal title={`Work item #${itemId}`} busy={busy || commentBusy} onClose={onClose}>
    {error && <div className="form-alert" role="alert">{error}</div>}
    <LoadState resource={resource}>{item && <div className="item-details">
      <div className="detail-badges"><span className={`item-badge status-${item.status}`}>{label(item.status)}</span><span className={`item-badge priority-${item.priority}`}>{label(item.priority)} priority</span></div>
      <h3>{item.title}</h3><p className="item-description">{item.description}</p>
      <dl><div><dt>Team</dt><dd>{team.name}</dd></div><div><dt>Type</dt><dd>{label(item.item_type)}</dd></div><div><dt>Assignee</dt><dd>{item.assignee_name || (item.assignee_id ? `User #${item.assignee_id}` : 'Unassigned')}</dd></div></dl>
      <AssignmentControls key={item.version} item={item} team={team} user={user} busy={busy || commentBusy} onAssign={(assignee_id) => updateItem('assign', { assignee_id }, 'Work item assignment updated.')} onClaim={() => updateItem('claim', {}, 'Work item assigned to you.')} />
      {team.permissions.includes('edit') && transitions[item.status]?.length > 0 && <div className="status-actions"><p>Move this item to</p><div>{transitions[item.status].map((status) => <button key={status} className="secondary-button" disabled={busy || commentBusy} onClick={() => changeStatus(status)}>{busy ? <LoaderCircle className="spinner" size={14} /> : <ArrowUpRight size={14} />}{label(status)}</button>)}</div></div>}
    </div>}</LoadState>
    <ItemDiscussion key={itemId} itemId={itemId} user={user} refreshKey={activityRevision} disabled={busy || !item} onBusyChange={setCommentBusy} />
  </Modal>
}

export default function WorkItems({ user }) {
  const teams = useResource('/teams')
  const [params, setParams] = useSearchParams()
  const [creating, setCreating] = useState(false)
  const [selectedItem, setSelectedItem] = useState(null)
  const [notice, setNotice] = useState('')
  const filters = Object.fromEntries(['q', 'status', 'priority', 'item_type'].map((key) => [key, params.get(key) || '']))
  const [search, setSearch] = useState(filters.q)
  useEffect(() => {
    const timer = setTimeout(() => setSearch(filters.q), 250)
    return () => clearTimeout(timer)
  }, [filters.q])
  const team = teams.data?.find((entry) => String(entry.id) === params.get('team')) || (!params.get('team') ? teams.data?.[0] : null)
  const items = useResource(team ? itemsPath(team.id, { ...filters, q: search }) : null)
  const rows = items.data || []
  const filtered = Object.values(filters).some(Boolean)

  function setFilter(key, value) {
    setParams((previous) => {
      const next = new URLSearchParams(previous)
      if (value) next.set(key, value)
      else next.delete(key)
      return next
    }, { replace: true })
    setNotice('')
  }

  function clearFilters() {
    setParams(team ? { team: String(team.id) } : {}, { replace: true })
    setSearch('')
  }

  return <main className="items-workspace">
    <div className="items-heading"><div><span className="eyebrow">YOUR TEAM’S WORKSPACE</span><h1>Work items<span className="heading-dot">.</span></h1><p>Keep the work moving, {user.name.split(' ')[0]}.</p></div><button className="primary-button" disabled={!team?.permissions.includes('create')} onClick={() => setCreating(true)}><Plus size={18} /> New work item</button></div>
    <LoadState resource={teams}>
      {teams.data?.length === 0 ? <div className="items-empty items-panel"><ClipboardList size={32} /><h2>No teams yet</h2><p>Ask your workspace administrator to add you to a team.</p></div> : teams.data && <>
        <div className="team-toolbar"><div><label htmlFor="team-filter">Workspace team</label><select id="team-filter" value={team?.id || ''} onChange={(event) => setFilter('team', event.target.value)}>{!team && <option value="">Select a team</option>}{teams.data.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}</select></div>{team && <span className="team-role">{label(team.role)} access</span>}</div>
        {!team ? <div className="form-alert" role="alert">This team is unavailable. Select one of your teams above.</div> : <>
          {notice && <div className="items-notice" role="status"><CheckCircle2 size={17} />{notice}<button className="icon-button" aria-label="Dismiss notification" onClick={() => setNotice('')}><X size={16} /></button></div>}
          <section className="items-panel" aria-label="Work items">
            <div className="items-filters"><div className="search-field"><Search size={17} /><input aria-label="Search work items" placeholder="Search title or description…" maxLength={200} value={filters.q} onChange={(event) => setFilter('q', event.target.value)} /></div><div className="filter-selects"><SlidersHorizontal size={16} aria-hidden="true" /><select aria-label="Filter by status" value={filters.status} onChange={(event) => setFilter('status', event.target.value)}><option value="">All statuses</option><Options values={statuses} /></select><select aria-label="Filter by priority" value={filters.priority} onChange={(event) => setFilter('priority', event.target.value)}><option value="">All priorities</option><Options values={priorities} /></select><select aria-label="Filter by type" value={filters.item_type} onChange={(event) => setFilter('item_type', event.target.value)}><option value="">All types</option><Options values={itemTypes} /></select></div></div>
            <div className="results-toolbar"><span role="status">{items.loading || search !== filters.q ? 'Finding work items…' : items.error ? 'Unable to load items' : `${rows.length} work item${rows.length === 1 ? '' : 's'}${filtered ? ' matching your filters' : ''}`}</span><div>{filtered && <button className="text-button" onClick={clearFilters}>Clear filters</button>}<button className="icon-button" aria-label="Refresh work items" disabled={items.loading} onClick={items.reload}><RefreshCw size={16} /></button></div></div>
            <LoadState resource={items}>{!items.loading && !items.error && (rows.length ? <div className="items-table-scroll"><table className="items-table"><thead><tr><th scope="col">Work item</th><th scope="col">Status</th><th scope="col">Priority</th><th scope="col">Type</th><th scope="col">Created</th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}><td><button className="item-title-button" onClick={() => setSelectedItem(item.id)}><span className="item-id">#{item.id}</span><span>{item.title}</span><ArrowUpRight size={15} /></button></td><td><span className={`item-badge status-${item.status}`}><span className="badge-dot" />{label(item.status)}</span></td><td><span className={`item-badge priority-${item.priority}`}>{label(item.priority)}</span></td><td className="type-cell">{label(item.item_type)}</td><td className="date-cell">{new Date(item.created_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })}</td></tr>)}</tbody></table></div> : <div className="items-empty"><span className="empty-icon"><ClipboardList size={28} /></span><h2>{filtered ? 'No matching work items' : 'A clear start for your team.'}</h2><p>{filtered ? 'Try another search or clear your filters.' : 'Create your first work item to get things moving.'}</p>{filtered ? <button className="secondary-button" onClick={clearFilters}>Clear filters</button> : team.permissions.includes('create') && <button className="secondary-button" onClick={() => setCreating(true)}><Plus size={16} /> Create work item</button>}</div>)}</LoadState>
          </section><p className="items-footnote">Showing work items for {team.name}. Newest first.</p>
        </>}
      </>}
    </LoadState>
    {creating && team && <CreateItem team={team} onClose={() => setCreating(false)} onCreated={(item) => { setCreating(false); clearFilters(); items.reload(); setNotice(`Work item #${item.id} created.`) }} />}
    {selectedItem && team && <ItemDetails itemId={selectedItem} team={team} user={user} onClose={() => setSelectedItem(null)} onChanged={(message) => { items.reload(); setNotice(message) }} />}
  </main>
}
