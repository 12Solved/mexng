import type { RuleGroupType } from 'react-querybuilder';
import api from '../api/api.ts'

export async function getAllEmails(
  currentPage: number,
  query?: RuleGroupType,
  workflowId?: number,
  runState?: string,
) {
  const body: Record<string, unknown> = {};
  if (query?.rules.length) body.query = query;
  if (workflowId != null) body.workflow_id = workflowId;
  if (runState) body.run_state = runState;
  const res = await api.post(`/emails/?page=${currentPage}`, body);
  return res.data;
}

export async function updateEmailState(emailId: number, state: string) {
  await api.patch(`/emails/${emailId}`, {
    state: state,
  });
}

export async function getEmail(email_id : string){
  const res = await api.get(`/emails/${email_id}`)
  return res.data
}

export async function downloadAttachment(emailId: number, attachmentId: number, filename: string) {
  const res = await api.get(`/emails/${emailId}/attachments/${attachmentId}/download`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 100);
}

export async function downloadAllAttachments(emailId: number, attachments: { id: number; filename: string }[]) {
  for (let i = 0; i < attachments.length; i++) {
    await new Promise(resolve => setTimeout(resolve, i * 120));
    await downloadAttachment(emailId, attachments[i].id, attachments[i].filename);
  }
}

export async function downloadEmail(emailId: number, subject: string) {
  const res = await api.get(`/emails/${emailId}/download`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(res.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${subject}.eml`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 100);
}