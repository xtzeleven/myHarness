"""`.github/scripts/check-migration-immutability.sh` 端到端测试（backlog G11 / 规则清单 K1）。

临时仓库里真实提交，覆盖：新增版本放行 / 改 删 改名已有版本拦截 / R__ 不管 /
PR 内新增后再改放行 / 理由尾注放行 / 工作区模式（bench 用）/ 坏 base 报错。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".github/scripts/check-migration-immutability.sh"
MIG = "src/main/resources/db/migration"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def _write(repo: Path, name: str, text: str) -> None:
    p = repo / MIG / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _commit(repo: Path, msg: str, *extra: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg, *extra)
    return _git(repo, "rev-parse", "HEAD")


def _check(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=repo, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path):
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    _write(r, "V1__create_orders.sql", "CREATE TABLE orders (id BIGINT);\n")
    _write(r, "R__views.sql", "CREATE VIEW v AS SELECT 1;\n")
    (r / "README.md").write_text("x\n")
    base = _commit(r, "base")
    _git(r, "switch", "-q", "-c", "pr")
    return r, base


def test_new_version_passes(repo):
    r, base = repo
    _write(r, "V2__add_remark.sql", "ALTER TABLE orders ADD remark DECIMAL;\n")
    head = _commit(r, "add v2")
    res = _check(r, base, head)
    assert res.returncode == 0, res.stdout


@pytest.mark.parametrize("change", ["modify", "delete", "rename"])
def test_touching_existing_version_fails(repo, change):
    r, base = repo
    v1 = r / MIG / "V1__create_orders.sql"
    if change == "modify":
        v1.write_text("CREATE TABLE orders (id BIGINT, remark DECIMAL);\n")
    elif change == "delete":
        v1.unlink()
    else:
        v1.rename(r / MIG / "V1__create_order_table.sql")
    head = _commit(r, change)
    res = _check(r, base, head)
    assert res.returncode == 1
    assert "::error::" in res.stdout and "V1__create_orders.sql" in res.stdout


def test_repeatable_migration_and_other_files_pass(repo):
    r, base = repo
    _write(r, "R__views.sql", "CREATE VIEW v AS SELECT 2;\n")
    (r / "README.md").write_text("y\n")
    assert _check(r, base, _commit(r, "repeatable")).returncode == 0


def test_version_added_in_same_pr_can_be_edited(repo):
    r, base = repo
    _write(r, "V2__a.sql", "SELECT 1;\n")
    _commit(r, "add v2")
    _write(r, "V2__a.sql", "SELECT 2;\n")
    assert _check(r, base, _commit(r, "fix v2 before merge")).returncode == 0


def test_review_trailer_allows_with_warning(repo):
    r, base = repo
    _write(r, "V1__create_orders.sql", "-- never deployed\nCREATE TABLE orders (id BIGINT);\n")
    head = _commit(r, "rewrite v1", "--trailer", "Migration-Rewrite-Reviewed: 从未部署过")
    res = _check(r, base, head)
    assert res.returncode == 0
    assert "::warning::" in res.stdout and "从未部署过" in res.stdout


def test_working_tree_mode_catches_uncommitted_edit(repo):
    r, base = repo
    _write(r, "V1__create_orders.sql", "CREATE TABLE orders (id BIGINT, x INT);\n")
    res = _check(r, base)
    assert res.returncode == 1 and "V1__create_orders.sql" in res.stdout


def test_working_tree_mode_ignores_trailer(repo):
    r, base = repo
    _write(r, "V1__create_orders.sql", "changed\n")
    _commit(r, "rewrite", "--trailer", "Migration-Rewrite-Reviewed: x")
    # bench 用工作区模式：没有"理由"通道
    assert _check(r, base).returncode == 1


def test_bad_base_fails_loud(repo):
    r, _ = repo
    res = _check(r, "no-such-ref", "HEAD")
    assert res.returncode != 0
