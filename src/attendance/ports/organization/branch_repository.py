"""Puerto BranchRepository para persistencia y consulta de sucursales."""

from typing import Protocol

from attendance.domain.organization.branch import Branch


class BranchRepository(Protocol):
    """Contrato de persistencia y catálogo para sucursales."""

    def save(self, branch: Branch) -> Branch: ...

    def get_by_id(self, branch_id: int) -> Branch | None: ...

    def get_by_code(self, code: str) -> Branch | None: ...

    def list_all(self, active_only: bool = False) -> list[Branch]: ...

    def delete(self, branch_id: int) -> bool: ...
