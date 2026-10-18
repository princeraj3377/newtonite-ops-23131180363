import { useState } from 'react'
import { Check, LoaderCircle, RefreshCw, UserCheck, UserPlus } from 'lucide-react'
import { useResource } from '../hooks/useResource'

export default function AssignmentControls({ item, team, user, busy, onAssign, onClaim }) {
  const canAssign = team.permissions.includes('assign')
  const canClaim = team.permissions.includes('claim')
  const members = useResource(canAssign ? `/teams/${team.id}/members` : null)
  const [assigneeId, setAssigneeId] = useState(String(item.assignee_id || ''))
  const assignedToMe = item.assignee_id === user.id

  return <section className="assignment-controls" aria-labelledby="assignment-heading">
    <div className="assignment-heading"><h4 id="assignment-heading"><UserCheck size={16} /> Assignment</h4>
      {assignedToMe && <span className="assignment-owned"><Check size={14} /> Assigned to you</span>}
    </div>
    {canAssign && <form className="assignment-form" onSubmit={(event) => { event.preventDefault(); if (assigneeId && !busy) onAssign(Number(assigneeId)) }}>
      <label htmlFor="assignee-select">Assign to a team member</label>
      <div className="assignment-inputs"><select id="assignee-select" value={assigneeId} onChange={(event) => setAssigneeId(event.target.value)} disabled={busy || members.loading || Boolean(members.error)} required>
        <option value="">{members.loading ? 'Loading team members...' : 'Choose a team member'}</option>
        {members.data?.map((member) => <option key={member.id} value={member.id}>{member.name}{member.id === user.id ? ' (you)' : ''} · {member.role}</option>)}
      </select><button className="secondary-button" disabled={busy || members.loading || Boolean(members.error) || !assigneeId || Number(assigneeId) === item.assignee_id}>{busy ? <LoaderCircle size={15} className="spinner" /> : <UserPlus size={15} />}Assign</button></div>
      {members.error && <div className="assignment-error"><p role="alert">{members.error}</p><button type="button" className="text-button" disabled={busy} onClick={members.reload}><RefreshCw size={12} /> Retry loading members</button></div>}
    </form>}
    {canClaim && item.assignee_id === null && <div className="claim-row"><p>Take ownership of this unassigned work item.</p><button type="button" className="secondary-button" disabled={busy} onClick={onClaim}>{busy ? <LoaderCircle size={15} className="spinner" /> : <UserCheck size={15} />}Claim task</button></div>}
    {!canAssign && !assignedToMe && <p className="assignment-note">{item.assignee_id ? 'Already assigned. Ask a team lead to reassign this item.' : !canClaim ? 'Your role can view assignments. Ask a team lead to assign this item.' : ''}</p>}
  </section>
}
