import api from '../api/api.ts';

export async function getCheckpoints(page = 1) {
  const res = await api.get(`/checkpoints/?page=${page}`);
  return res.data;
}

export async function deleteCheckpoint(id: number) {
  const res = await api.delete(`/checkpoints/${id}`);
  return res.data;
}
