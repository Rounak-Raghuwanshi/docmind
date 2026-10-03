import { useOutletContext } from "react-router-dom";
import type { Role, Workspace } from "@/api/types";

export function useCurrentWorkspace(): Workspace {
  return useOutletContext<Workspace>();
}

const rank: Record<Role, number> = { viewer: 1, editor: 2, owner: 3 };

export function hasRole(workspace: Workspace, minimum: Role): boolean {
  return rank[workspace.role] >= rank[minimum];
}
