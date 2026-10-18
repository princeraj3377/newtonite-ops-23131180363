import { useRef, useState } from 'react'
import { History, LoaderCircle, MessageSquare, RefreshCw, Send } from 'lucide-react'
import { api, getErrorMessage } from '../lib/api'
import { useResource } from '../hooks/useResource'
import './ItemDiscussion.css'

const activityLabels = { created: 'created this work item', updated: 'updated this work item', assigned: 'changed the assignee', claimed: 'claimed this work item', status_changed: 'changed the status', commented: 'added a comment' }

function Timestamp({ value }) {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return null
  return <time dateTime={value} title={date.toLocaleString()}>{date.toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</time>
}

function FeedState({ resource, empty, children }) {
  if (resource.loading) return <p className="feed-state" role="status"><LoaderCircle className="spinner" size={16} /> Loading...</p>
  if (resource.error) return <div className="feed-state feed-error"><p role="alert">{resource.error}</p><button className="secondary-button" onClick={resource.reload}><RefreshCw size={14} /> Try again</button></div>
  if (!resource.data?.length) return <p className="feed-state">{empty}</p>
  return children
}

export default function ItemDiscussion({ itemId, user, refreshKey, disabled, onBusyChange }) {
  const [tab, setTab] = useState('comments')
  const [draft, setDraft] = useState('')
  const [posting, setPosting] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const postingRef = useRef(false)
  const comments = useResource(`/items/${itemId}/comments`)
  const activity = useResource(`/items/${itemId}/activity`, refreshKey)
  const tabs = useRef({})

  async function postComment(event) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || content.length > 2000 || disabled || postingRef.current) return
    postingRef.current = true
    setPosting(true)
    onBusyChange(true)
    setError('')
    setNotice('')
    try {
      await api.post(`/items/${itemId}/comments`, { content })
      setDraft('')
      setNotice('Comment posted.')
      comments.reload()
      activity.reload()
    } catch (failure) {
      setError(!failure.response
        ? 'We could not confirm whether your comment was posted. Refresh comments before trying again.'
        : getErrorMessage(failure))
    } finally {
      postingRef.current = false
      setPosting(false)
      onBusyChange(false)
    }
  }

  function navigateTabs(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const next = event.key === 'Home' ? 'comments' : event.key === 'End' ? 'activity' : tab === 'comments' ? 'activity' : 'comments'
    setTab(next)
    tabs.current[next].focus()
  }

  return <section className="item-discussion" aria-label="Comments and activity">
    <div className="discussion-toolbar"><div className="discussion-tabs" role="tablist" aria-label="Work item updates" onKeyDown={navigateTabs}>
      <button ref={(element) => { tabs.current.comments = element }} id="comments-tab" type="button" role="tab" aria-selected={tab === 'comments'} aria-controls="comments-panel" tabIndex={tab === 'comments' ? 0 : -1} onClick={() => setTab('comments')}><MessageSquare size={15} />Comments{comments.data && <span>{comments.data.length}</span>}</button>
      <button ref={(element) => { tabs.current.activity = element }} id="activity-tab" type="button" role="tab" aria-selected={tab === 'activity'} aria-controls="activity-panel" tabIndex={tab === 'activity' ? 0 : -1} onClick={() => setTab('activity')}><History size={15} />Activity</button>
    </div><button type="button" className="icon-button" aria-label={`Refresh ${tab}`} disabled={posting || (tab === 'comments' ? comments.loading : activity.loading)} onClick={() => { if (tab === 'comments') comments.reload(); else activity.reload() }}><RefreshCw size={15} /></button></div>
    <div id="comments-panel" role="tabpanel" aria-labelledby="comments-tab" hidden={tab !== 'comments'} tabIndex={0}>
      <FeedState resource={comments} empty="No comments yet. Start the conversation."><ol className="comment-list">{comments.data?.map((comment) => <li key={comment.id}><div className="comment-avatar" aria-hidden="true">{(comment.author_name || 'U').slice(0, 1).toUpperCase()}</div><article><div className="comment-meta"><strong>{comment.author_name || `User #${comment.author_id}`}{comment.author_id === user.id && <span> (you)</span>}</strong><Timestamp value={comment.created_at} /></div><p>{comment.content}</p></article></li>)}</ol></FeedState>
      <form className="comment-form" onSubmit={postComment} aria-busy={posting}>
        <label htmlFor="comment-content">Add a comment</label><textarea id="comment-content" value={draft} onChange={(event) => { setDraft(event.target.value); setNotice('') }} placeholder="Share an update or ask a question..." rows={3} maxLength={2000} required disabled={posting || disabled} aria-describedby="comment-limit" />
        {error && <div className="form-alert" role="alert">{error}</div>}{notice && <p className="comment-success" role="status">{notice}</p>}
        <div className="comment-submit"><span id="comment-limit">{draft.length}/2000</span><button className="primary-button" disabled={posting || disabled || !draft.trim()}>{posting ? <LoaderCircle className="spinner" size={15} /> : <Send size={15} />}{posting ? 'Posting...' : 'Post comment'}</button></div>
      </form>
    </div>
    <div id="activity-panel" role="tabpanel" aria-labelledby="activity-tab" hidden={tab !== 'activity'} tabIndex={0}>
      <FeedState resource={activity} empty="No activity recorded yet."><ol className="activity-list">{activity.data?.map((event) => <li key={event.id}><span className="activity-marker" aria-hidden="true">{event.action === 'commented' ? <MessageSquare size={13} /> : <History size={13} />}</span><div><p><strong>{event.actor_name || `User #${event.actor_id}`}</strong> {activityLabels[event.action] || event.action.replaceAll('_', ' ')}</p><p className="activity-details">{event.details}</p><Timestamp value={event.created_at} /></div></li>)}</ol></FeedState>
    </div>
  </section>
}
