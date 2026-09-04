"""Adaptador en memoria para BranchRepository."""

from attendance.domain.organization.branch import Branch
from attendance.ports.organization.branch_repository import BranchRepository


class InMemoryBranchRepository(BranchRepository):
    """Implementación en memoria del repositorio de sucursales."""

    def __init__(self, initial_branches: list[Branch] | None = None) -> None:
        self._branches: dict[int, Branch] = {}
        self._next_id = 1
        if initial_branches:
            for b in initial_branches:
                self.save(b)

    def save(self, branch: Branch) -> Branch:
        existing: Branch | None = None
        if branch.id is not None:
            existing = self._branches.get(branch.id)
        if existing is None and branch.code:
            cleaned = branch.code.strip().upper()
            existing = next(
                (b for b in self._branches.values() if b.code and b.code.strip().upper() == cleaned),
                None,
            )

        if existing is not None and existing.id is not None:
            branch.id = existing.id
            self._branches[existing.id] = branch
            return branch

        if branch.id is None:
            branch.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, branch.id + 1)
        self._branches[branch.id] = branch
        return branch

    def save_all(self, branches: list[Branch]) -> list[Branch]:
        return [self.save(b) for b in branches]

    def get_by_id(self, branch_id: int) -> Branch | None:
        return self._branches.get(branch_id)

    def get_by_code(self, code: str) -> Branch | None:
        cleaned = code.strip().upper()
        return next(
            (b for b in self._branches.values() if b.code and b.code.strip().upper() == cleaned),
            None,
        )

    def get_by_name(self, name: str) -> Branch | None:
        cleaned = name.strip().lower()
        return next(
            (b for b in self._branches.values() if b.name.strip().lower() == cleaned),
            None,
        )

    def exists_by_id(self, branch_id: int) -> bool:
        return branch_id in self._branches

    def exists_by_code(self, code: str) -> bool:
        return self.get_by_code(code) is not None

    def list_all(self, active_only: bool = False) -> list[Branch]:
        branches = list(self._branches.values())
        if active_only:
            branches = [b for b in branches if b.active]
        return sorted(branches, key=lambda b: (b.name.lower(), b.id or 0))

    def count(self, active_only: bool = False) -> int:
        return len(self.list_all(active_only=active_only))

    def delete(self, branch_id: int) -> bool:
        if branch_id in self._branches:
            del self._branches[branch_id]
            return True
        return False

