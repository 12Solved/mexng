import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { downloadEmail, getEmail } from '../services/emailServices';
import type { Email } from '../types/email';
import DOMPurify from 'dompurify';
import type { WorkflowRun } from '../types/workflowRun';
import { RunState } from '../types/workflowRun';
import { getAllWorkflowRuns, rerunAllWorkflowRuns, rerunWorkflowRun, runNewWorkflows, runAllWorkflows } from '../services/runsServices';
import { AttachmentsPanel } from '../components/AttachmentPanel';
import { DownloadIcon, SpinnerIcon } from '../assets/icons';
import { useHtmlDarkClass } from '../hooks/useHtmlDarkClass';

const SingleEmailPage = () => {
  const { id } = useParams();
  const isDark = useHtmlDarkClass();
  const [email, setEmail] = useState<Email | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [emailError, setEmailError] = useState<string | null>(null)
  const [emailDownloading, setEmailDownloading] = useState(false)
  const [rerunningId, setRerunningId] = useState<number | null>(null)
  const [dryRunningId, setDryRunningId] = useState<number | null>(null)
  const [rerunningAll, setRerunningAll] = useState(false)
  const [runningNew, setRunningNew] = useState(false)
  const [dryRunning, setDryRunning] = useState(false)
  const navigate = useNavigate();

  const fetchWorkflowRuns = async () => {
    try {
      if (!id) return
      const data: WorkflowRun[] = await getAllWorkflowRuns(id);
      setWorkflowRuns(data);
    } catch (error) {
      toast.error('Failed to load workflow runs.');
    }
  };

  const fetchEmail = async () => {
    try {
      if (!id) return
      const result = await getEmail(id)
      setEmail(result)
    } catch (error) {
      toast.error('Failed to load email.');
      setEmailError('Failed to load email.')
    }
  };

  useEffect(() => {
    fetchEmail();
    fetchWorkflowRuns();
  }, [id])

  if (emailError) return <div className="p-6 text-sm text-red-500 dark:text-red-400">{emailError}</div>;
  if (!email) return <div className="p-6 text-sm text-slate-500 dark:text-slate-400">Loading...</div>;

  const handleDownloadEmail = async () => {
    setEmailDownloading(true)
    try {
      await downloadEmail(email.id, email.subject)
      toast.success('Email downloaded.')
    } catch (e) {
      toast.error('Download failed.')
    } finally {
      setEmailDownloading(false)
    }
  }

  const handleRerun = async (run: WorkflowRun) => {
    if (!id) return
    setRerunningId(run.id)
    try {
      const result = await rerunWorkflowRun(id, run.id)
      if (result.already_queued) {
        toast.info('Re-run already queued.')
      } else {
        toast.success('Re-run queued.')
      }
      await fetchWorkflowRuns()
      fetchEmail()
    } catch (e) {
      toast.error('Re-run failed.')
    } finally {
      setRerunningId(null)
    }
  }

  const handleDryRun = async (run: WorkflowRun) => {
    if (!id) return
    setDryRunningId(run.id)
    try {
      const result = await rerunWorkflowRun(id, run.id, { "@dry_run": true })
      if (result.already_queued) {
        toast.info('Dry run already queued.')
      } else {
        toast.success('Dry run queued.')
      }
      await fetchWorkflowRuns()
      fetchEmail()
    } catch (e) {
      toast.error('Dry run failed.')
    } finally {
      setDryRunningId(null)
    }
  }

  const handleRerunAll = async () => {
    if (!id) return
    setRerunningAll(true)
    try {
      const result = await rerunAllWorkflowRuns(id)
      if (result.queued > 0 && result.already_queued > 0) {
        toast.success(`${result.queued} queued, ${result.already_queued} already queued.`)
      } else if (result.queued > 0) {
        toast.success(`${result.queued} workflow(s) queued for re-run.`)
      } else {
        toast.info('All workflows already queued.')
      }
      await fetchWorkflowRuns()
      await fetchEmail()
    } catch (e) {
      toast.error('Re-run all failed.')
    } finally {
      setRerunningAll(false)
    }
  }

  const handleRunNewWorkflows = async () => {
    if (!id) return
    setRunningNew(true)
    try {
      await runNewWorkflows(id)
      toast.success('New workflows queued.')
      await fetchWorkflowRuns()
      await fetchEmail()
    } catch (e) {
      toast.error('Failed to run new workflows.')
    } finally {
      setRunningNew(false)
    }
  }

  const handleDryRunAll = async () => {
    if (!id) return
    setDryRunning(true)
    try {
      const result = await runAllWorkflows(id, { "@dry_run": true })
      if (result.queued > 0 && result.already_queued > 0) {
        toast.success(`${result.queued} dry run(s) queued, ${result.already_queued} already queued.`)
      } else if (result.queued > 0) {
        toast.success(`${result.queued} dry run(s) queued.`)
      } else {
        toast.info('All dry runs already queued.')
      }
      await fetchWorkflowRuns()
      await fetchEmail()
    } catch (e) {
      toast.error('Dry run queueing failed.')
    } finally {
      setDryRunning(false)
    }
  }

  const groupedByWorkflow = Object.values(
    workflowRuns.reduce((acc, run) => {
      const key = run.workflow_id;
      if (!acc[key]) acc[key] = [];
      acc[key].push(run);
      return acc;
    }, {} as Record<number, WorkflowRun[]>)
  ).map(runs => runs.sort((a, b) => b.id - a.id));

  const { run_summary } = email;

  return (
    <div className="max-w-7xl mx-auto py-6 px-4">
      <div className="flex items-center gap-2 mb-6 text-sm text-slate-500 dark:text-slate-400">
        <Link to="/" className="hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
          Inbox
        </Link>
        <span className="text-slate-300 dark:text-slate-600">/</span>
        <span className="text-slate-800 dark:text-slate-100">Email details</span>
      </div>

      <div className="bg-card dark:bg-slate-900 border border-border dark:border-slate-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4 mb-5">
          <h1 className="text-lg font-medium text-card-foreground dark:text-slate-50">{email?.subject}</h1>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm mb-5 text-card-foreground dark:text-slate-200">
          <div className="flex gap-2">
            <span className="text-muted-foreground dark:text-slate-500 w-16 shrink-0">From</span>
            <span className="min-w-0 break-all">{email?.sender}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-muted-foreground dark:text-slate-500 w-16 shrink-0">To</span>
            <span className="min-w-0 break-all">{email?.recipient}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-muted-foreground dark:text-slate-500 w-16 shrink-0">Date</span>
            <span>{new Date(email?.date).toLocaleString()}</span>
          </div>
          <div className="flex gap-2">
            <span className="text-muted-foreground dark:text-slate-500 w-16 shrink-0">ID</span>
            <span className="font-mono text-xs text-muted-foreground dark:text-slate-500 min-w-0 break-all">{email?.message_id}</span>
          </div>
        </div>

        {email.html_body ? (
          <iframe
            srcDoc={`
            <style>
              html, body { margin: 0; padding: 0; overflow: hidden; background: ${isDark ? '#0f172a' : '#ffffff'}; }
            </style>
            ${DOMPurify.sanitize(email.html_body)}
            `}
            className="w-full border-0 min-h-96 rounded-md ring-1 ring-slate-200/80 dark:ring-slate-700/80"
            sandbox="allow-same-origin"
            onLoad={(e) => {
              const iframe = e.currentTarget;
              iframe.style.height = iframe.contentDocument?.body.scrollHeight + 'px';
            }}
          />
        ) : (
          <p className="text-sm text-muted-foreground dark:text-slate-400 leading-relaxed">{email.body}</p>
        )}
        <button
          onClick={handleDownloadEmail}
          disabled={emailDownloading}
          className={`mt-4 flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md border border-border transition-colors cursor-pointer text-foreground ${
            emailDownloading ? 'opacity-50 cursor-wait' : 'hover:bg-muted hover:border-input'
          }`}
        >
          {emailDownloading ? <SpinnerIcon /> : <DownloadIcon />}
          {emailDownloading ? 'Downloading…' : 'Download email'}
        </button>
        <AttachmentsPanel emailId={email.id} attachments={email.attachments} />
      </div>

      {run_summary && (
        <div className="mt-3">
          <p className="text-xs text-muted-foreground dark:text-slate-500 mb-2">Workflow runs</p>
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: 'Success', value: run_summary.success, className: 'text-green-600 dark:text-green-400' },
              { label: 'Failed', value: run_summary.failed, className: 'text-red-500 dark:text-red-400' },
              { label: 'Skipped', value: run_summary.skipped, className: 'text-slate-500 dark:text-slate-400' },
              { label: 'Re-run', value: run_summary.re_run, className: 'text-blue-600 dark:text-blue-400' },
            ].map(({ label, value, className }) => (
              <div key={label} className="bg-slate-100 dark:bg-slate-800 border border-transparent dark:border-slate-700/80 rounded-lg p-3">
                <p className="text-xs text-muted-foreground dark:text-slate-500 mb-1">{label}</p>
                <p className={`text-2xl font-medium ${className}`}>{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className='gap-3 flex flex-wrap'>
        <button onClick={() => navigate(`/logs/?email_id=${email.id}`)} className='rounded-md text-lg font-medium text-card-foreground dark:text-slate-100 mt-3 p-3 bg-slate-200 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors'>
          View all logs
        </button>
        <button
          onClick={handleRerunAll}
          disabled={rerunningAll}
          className='rounded-md text-lg font-medium text-card-foreground dark:text-slate-100 mt-3 p-3 bg-slate-200 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors'
        >
          {rerunningAll ? 'Queuing…' : 'Re-run all'}
        </button>
        <button
          onClick={handleRunNewWorkflows}
          disabled={runningNew}
          className='rounded-md text-lg font-medium text-card-foreground dark:text-slate-100 mt-3 p-3 bg-slate-200 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors'
        >
          {runningNew ? 'Queuing…' : 'Run with new workflows'}
        </button>
        <button
          onClick={handleDryRunAll}
          disabled={dryRunning}
          className='rounded-md text-lg font-medium text-card-foreground dark:text-slate-100 mt-3 p-3 bg-slate-200 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 hover:cursor-pointer hover:bg-slate-300 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors'
        >
          {dryRunning ? 'Queueing…' : 'Queue dry run for all'}
        </button>
      </div>

      <div className='flex flex-col gap-4 mt-4'>
        {groupedByWorkflow.map((runs) => {
          const latest = runs[0];
          const history = runs.slice(1);
          return (
            <div key={latest.workflow_id}>
              <div className='flex items-center gap-2'>
                <div className='flex-1 text-slate-800 dark:text-white text-sm bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 rounded-md px-3 py-2 hover:cursor-pointer transition-colors' onClick={() => navigate(`/logs/?email_id=${email.id}&workflow_id=${latest.workflow_id}`)}>
                  {latest.workflow_name}
                </div>
                <span className='text-xs font-medium px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-muted-foreground dark:text-slate-400 border border-border dark:border-slate-600 whitespace-nowrap'>
                  {latest.state}
                </span>
                <button
                  disabled={dryRunningId === latest.id}
                  onClick={() => handleDryRun(latest)}
                  className='text-xs font-medium px-3 py-2 rounded-md border border-border dark:border-slate-600 bg-card dark:bg-slate-800 hover:bg-muted dark:hover:bg-slate-700 text-card-foreground dark:text-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap'
                >
                  {dryRunningId === latest.id ? 'Queuing…' : 'Dry run'}
                </button>
                <button
                  disabled={rerunningId === latest.id || latest.state === RunState.re_run}
                  onClick={() => handleRerun(latest)}
                  className='text-xs font-medium px-3 py-2 rounded-md border border-border dark:border-slate-600 bg-card dark:bg-slate-800 hover:bg-muted dark:hover:bg-slate-700 text-card-foreground dark:text-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap'
                >
                  {rerunningId === latest.id ? 'Queuing…' : 'Re-run'}
                </button>
              </div>
              {history.length > 0 && (
                <div className='flex flex-col gap-1 mt-1 pl-3 border-l-2 border-slate-200 dark:border-slate-700'>
                  {history.map(run => (
                    <div key={run.id} className='flex items-center gap-2 text-xs text-muted-foreground dark:text-slate-500'>
                      <span className='font-mono'>#{run.id}</span>
                      <span className='text-slate-300 dark:text-slate-600'>·</span>
                      <span>{run.state}</span>
                      <span className='text-slate-300 dark:text-slate-600'>·</span>
                      <span>{new Date(run.created_at).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default SingleEmailPage