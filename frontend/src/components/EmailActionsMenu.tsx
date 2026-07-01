import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { downloadEmail } from '../services/emailServices';
import { rerunAllWorkflowRuns, runNewWorkflows } from '../services/runsServices';
import type { Email } from '../types/email';

const menuItemClass = "w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2";

export function EmailActionsMenu({ email }: { email: Email }) {
  const [open, setOpen] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [loading, setLoading] = useState<string | null>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        menuRef.current && !menuRef.current.contains(e.target as Node) &&
        btnRef.current && !btnRef.current.contains(e.target as Node)
      ) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const handleOpen = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    setMenuPos({ top: rect.bottom + window.scrollY + 4, left: rect.right + window.scrollX - 208 });
    setOpen(o => !o);
  };

  const run = async (action: () => Promise<unknown>, key: string, successMsg?: string) => {
    setLoading(key);
    try {
      await action();
      if (successMsg) toast.success(successMsg);
    } catch (e) {
      toast.error('Action failed. Please try again.');
    } finally {
      setLoading(null);
      setOpen(false);
    }
  };

  return (
    <div className="flex justify-end">
      <button
        ref={btnRef}
        onClick={handleOpen}
        className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
      >
        ···
      </button>
      {open && createPortal(
        <div
          ref={menuRef}
          style={{ position: 'absolute', top: menuPos.top, left: menuPos.left, zIndex: 9999 }}
          className="w-52 bg-white border border-gray-200 rounded-lg py-1 overflow-hidden"
          onClick={e => e.stopPropagation()}
        >
          <button className={menuItemClass} onClick={() => run(() => downloadEmail(email.id, email.subject ?? 'email'), 'download', 'Email downloaded.')} disabled={loading === 'download'}>
            {loading === 'download' ? 'Downloading…' : 'Download email'}
          </button>
          <button className={menuItemClass} onClick={() => navigate(`/logs/?email_id=${email.id}`)}>
            View logs
          </button>
          <div className="border-t border-gray-100 my-1" />
          <button className={menuItemClass} onClick={() => run(() => rerunAllWorkflowRuns(String(email.id)), 'rerun', 'Re-run queued.')} disabled={loading === 'rerun'}>
            {loading === 'rerun' ? 'Queuing…' : 'Re-run all workflows'}
          </button>
          <button className={menuItemClass} onClick={() => run(() => runNewWorkflows(String(email.id)), 'new', 'New workflows queued.')} disabled={loading === 'new'}>
            {loading === 'new' ? 'Queuing…' : 'Run with new workflows'}
          </button>
        </div>,
        document.body
      )}
    </div>
  );
}
