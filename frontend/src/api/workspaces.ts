import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { keys } from "./keys";
import type { Invite, InvitePreview, Member, Page, Role, Workspace } from "./types";

export function useWorkspaces() {
  return useQuery({
    queryKey: keys.workspaces,
    queryFn: () => api<Page<Workspace>>("/api/workspaces?limit=100"),
    select: (page) => [...page.items].sort((a, b) => Number(b.is_personal) - Number(a.is_personal)),
  });
}

export function useWorkspace(ws: string) {
  return useQuery({
    queryKey: keys.workspace(ws),
    queryFn: () => api<Workspace>(`/api/workspaces/${ws}`),
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api<Workspace>("/api/workspaces", { method: "POST", body: { name } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.workspaces }),
  });
}

export function useRenameWorkspace(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api<Workspace>(`/api/workspaces/${ws}`, { method: "PATCH", body: { name } }),
    onSuccess: (data) => {
      qc.setQueryData(keys.workspace(ws), data);
      qc.invalidateQueries({ queryKey: keys.workspaces });
    },
  });
}

export function useDeleteWorkspace(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<void>(`/api/workspaces/${ws}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.removeQueries({ queryKey: keys.workspace(ws) });
      qc.invalidateQueries({ queryKey: keys.workspaces });
    },
  });
}

export function useMembers(ws: string) {
  return useQuery({
    queryKey: keys.members(ws),
    queryFn: () => api<Member[]>(`/api/workspaces/${ws}/members`),
  });
}

export function useChangeRole(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) =>
      api<Member>(`/api/workspaces/${ws}/members/${userId}`, { method: "PATCH", body: { role } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.members(ws) }),
  });
}

export function useRemoveMember(ws: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) =>
      api<void>(`/api/workspaces/${ws}/members/${userId}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.members(ws) });
      qc.invalidateQueries({ queryKey: keys.workspaces });
    },
  });
}

export function useCreateInvite(ws: string) {
  return useMutation({
    mutationFn: (role: Role) =>
      api<Invite>(`/api/workspaces/${ws}/invites`, { method: "POST", body: { role } }),
  });
}

export function useInvitePreview(token: string) {
  return useQuery({
    queryKey: keys.invite(token),
    queryFn: () => api<InvitePreview>(`/api/invites/${token}`),
    retry: false,
  });
}

export function useAcceptInvite(token: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<Workspace>(`/api/invites/${token}/accept`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.workspaces }),
  });
}
