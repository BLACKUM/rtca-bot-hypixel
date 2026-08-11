import pytest
from services.github_manager import GithubManager

TOKEN = "github_pat_TESTTOKEN"


@pytest.fixture
def manager():
    gm = GithubManager()
    gm.repo_url = "https://github.com/BLACKUM/rtca-cache.git"
    gm.token = TOKEN
    return gm


@pytest.fixture
def git(manager, mocker):
    return mocker.patch.object(manager, "run_git_command", return_value=(True, ""))


def commands(git):
    return [call.args[0] for call in git.call_args_list]


@pytest.mark.asyncio
async def test_clones_when_directory_exists_but_is_not_a_checkout(manager, git, mocker):
    # docker volume / bind mount creates the directory before anything is cloned
    mocker.patch("os.path.isdir", return_value=False)
    mocker.patch("os.makedirs")

    assert await manager._prepare_repo() is True
    assert commands(git)[0] == ["clone", manager._get_authed_url(), "."]


@pytest.mark.asyncio
async def test_reuses_existing_checkout(manager, git, mocker):
    mocker.patch("os.path.isdir", return_value=True)

    assert await manager._prepare_repo() is True
    assert commands(git) == [
        ["remote", "set-url", "origin", manager._get_authed_url()],
        ["config", "pull.rebase", "false"],
        ["pull", "origin", "main", "--allow-unrelated-histories"],
    ]


@pytest.mark.asyncio
async def test_falls_back_to_init_when_clone_fails(manager, mocker):
    mocker.patch("os.path.isdir", return_value=False)
    mocker.patch("os.makedirs")
    git = mocker.patch.object(manager, "run_git_command", side_effect=[(False, "boom"), (True, ""), (True, ""), (True, "")])

    assert await manager._prepare_repo() is True
    assert commands(git)[1] == ["init"]


@pytest.mark.parametrize("returncode", [0, 1])
@pytest.mark.asyncio
async def test_token_never_reaches_the_log(manager, mocker, returncode):
    process = mocker.AsyncMock()
    process.returncode = returncode
    process.communicate.return_value = (b"", f"fatal: could not read {TOKEN}@github.com".encode())
    mocker.patch("asyncio.create_subprocess_exec", return_value=process)
    log_info = mocker.patch("services.github_manager.log_info")
    log_error = mocker.patch("services.github_manager.log_error")

    ok, output = await manager.run_git_command(["clone", manager._get_authed_url(), "."])

    logged = " ".join(str(call) for call in log_info.call_args_list + log_error.call_args_list)
    assert TOKEN not in logged
    assert "********" in logged
    if not ok:
        assert TOKEN not in output
