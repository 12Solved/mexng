import { useEffect, useMemo, useState } from 'react';
import { isAxiosError } from 'axios';
import { createAlertRule, updateAlertRule } from '../services/alertRuleServices';
import type { AlertRule, AlertRuleBody } from '../types/alertRule';
import type { LogLevel } from '../types/log';
import { LOG_LEVELS } from './LogRow';

export interface WorkflowOption {
  id: number;
  name: string;
}

export interface CheckpointOption {
  id: number;
  name: string;
  workflow_id: number | null;
}

interface AlertRuleModalProps {
  // null = create a new rule
  rule: AlertRule | null;
  workflows: WorkflowOption[];
  checkpoints: CheckpointOption[];
  eventTypes: string[];
  onClose: () => void;
  onSaved: () => void;
}

const inputClass =
  'w-full px-3 py-2 text-sm rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-300';

const labelClass = 'block text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-1.5';

function saveErrorMessage(err: unknown): string {
  // Rule routes return readable 404 details ("Workflow not found"); anything else gets a generic message.
  if (isAxiosError(err) && err.response?.status === 404 && typeof err.response.data?.detail === 'string') {
    return `${err.response.data.detail}. It may have been deleted — reload the page and try again.`;
  }
  return 'Failed to save alert rule.';
}

const AlertRuleModal = ({ rule, workflows, checkpoints, eventTypes, onClose, onSaved }: AlertRuleModalProps) => {
  const [eventType, setEventType] = useState(rule?.event_type ?? '');
  const [workflowId, setWorkflowId] = useState<number | null>(rule?.workflow_id ?? null);
  const [checkpointId, setCheckpointId] = useState<number | null>(rule?.checkpoint_id ?? null);
  const [minLevel, setMinLevel] = useState<LogLevel>(rule?.min_level ?? 'WARNING');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  // UI-only guard: with a workflow chosen, only offer its checkpoints. The API doesn't enforce this,
  // so an existing rule may point at a checkpoint outside that list (or one that didn't load).
  // Keep the selected one visible, otherwise the select would show "Any" while still saving it.
  const visibleCheckpoints = useMemo(() => {
    const options = workflowId === null ? checkpoints : checkpoints.filter(cp => cp.workflow_id === workflowId);
    if (checkpointId === null || options.some(cp => cp.id === checkpointId)) return options;
    const selected = checkpoints.find(cp => cp.id === checkpointId);
    const label = selected ? `${selected.name} (other workflow)` : `#${checkpointId}`;
    return [{ id: checkpointId, name: label, workflow_id: selected?.workflow_id ?? null }, ...options];
  }, [checkpoints, workflowId, checkpointId]);

  const handleWorkflowChange = (value: string) => {
    const id = value === '' ? null : Number(value);
    setWorkflowId(id);
    if (id !== null && checkpointId !== null) {
      const cp = checkpoints.find(c => c.id === checkpointId);
      if (cp?.workflow_id !== id) setCheckpointId(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Only NULL means "any event type"; an empty string would never match.
    const trimmed = eventType.trim();
    const body: AlertRuleBody = {
      event_type: trimmed === '' ? null : trimmed,
      workflow_id: workflowId,
      checkpoint_id: checkpointId,
      min_level: minLevel,
    };
    setSaving(true);
    setError(null);
    try {
      if (rule) await updateAlertRule(rule.id, body);
      else await createAlertRule(body);
      onSaved();
    } catch (err) {
      setError(saveErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
      onClick={onClose}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="alert-rule-modal-title"
        onSubmit={handleSubmit}
        onClick={e => e.stopPropagation()}
        className="bg-white dark:bg-slate-900 rounded-xl shadow-xl w-full max-w-md p-6 flex flex-col gap-4 border border-slate-200 dark:border-slate-800"
      >
        <h2 id="alert-rule-modal-title" className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          {rule ? 'Edit alert rule' : 'New alert rule'}
        </h2>

        <div>
          <label htmlFor="alert-rule-event-type" className={labelClass}>Event type</label>
          <input
            id="alert-rule-event-type"
            type="text"
            list="alert-rule-event-types"
            value={eventType}
            onChange={e => setEventType(e.target.value)}
            placeholder="Any"
            className={`${inputClass} font-mono`}
          />
          <datalist id="alert-rule-event-types">
            {eventTypes.map(t => <option key={t} value={t} />)}
          </datalist>
          <p className="mt-1 text-xs text-slate-400">Leave blank to match any event type.</p>
        </div>

        <div>
          <label htmlFor="alert-rule-workflow" className={labelClass}>Workflow</label>
          <select
            id="alert-rule-workflow"
            value={workflowId ?? ''}
            onChange={e => handleWorkflowChange(e.target.value)}
            className={inputClass}
          >
            <option value="">Any</option>
            {workflows.map(wf => <option key={wf.id} value={wf.id}>{wf.name}</option>)}
          </select>
        </div>

        <div>
          <label htmlFor="alert-rule-checkpoint" className={labelClass}>Checkpoint</label>
          <select
            id="alert-rule-checkpoint"
            value={checkpointId ?? ''}
            onChange={e => setCheckpointId(e.target.value === '' ? null : Number(e.target.value))}
            className={inputClass}
          >
            <option value="">Any</option>
            {visibleCheckpoints.map(cp => <option key={cp.id} value={cp.id}>{cp.name}</option>)}
          </select>
        </div>

        <div>
          <label htmlFor="alert-rule-min-level" className={labelClass}>Minimum level</label>
          <select
            id="alert-rule-min-level"
            value={minLevel}
            onChange={e => setMinLevel(e.target.value as LogLevel)}
            className={inputClass}
          >
            {LOG_LEVELS.map(level => <option key={level} value={level}>{level}</option>)}
          </select>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-md transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving…' : rule ? 'Save' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AlertRuleModal;
