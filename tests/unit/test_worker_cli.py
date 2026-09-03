"""Pruebas para el subcomando CLI 'asistpy worker'."""

import os
from unittest.mock import patch

from attendance.adapters.cli.main import build_parser


def test_worker_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["worker"])

    assert args.command == "worker"
    assert args.interval is None
    assert args.nightly_time is None
    assert args.branch_id is None
    assert args.stop_on_error is False
    assert args.run_nightly_on_start is False
    assert args.once is False


def test_worker_parser_custom_args():
    parser = build_parser()
    args = parser.parse_args([
        "worker",
        "--interval", "120",
        "--nightly-time", "22:45",
        "--branch-id", "3",
        "--stop-on-error",
        "--run-nightly-on-start",
        "--once",
    ])

    assert args.command == "worker"
    assert args.interval == 120
    assert args.nightly_time == "22:45"
    assert args.branch_id == 3
    assert args.stop_on_error is True
    assert args.run_nightly_on_start is True
    assert args.once is True


def test_worker_cmd_execution_with_env_fallbacks():
    parser = build_parser()
    args = parser.parse_args(["worker"])

    env_vars = {
        "SYNC_INTERVAL_SECONDS": "180",
        "NIGHTLY_PROCESSING_TIME": "23:15",
        "SYNC_BRANCH_ID": "5",
        "SYNC_STOP_ON_ERROR": "true",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        with patch("attendance.adapters.cli.commands.worker.AttendanceWorker") as mock_worker_cls:
            mock_instance = mock_worker_cls.return_value
            mock_instance.start.return_value = 0

            from attendance.adapters.cli.context import CLIContext

            ctx = CLIContext(backend="memory")
            exit_code = args.func(args, ctx)

            assert exit_code == 0
            mock_worker_cls.assert_called_once()
            _, kwargs = mock_worker_cls.call_args
            assert kwargs["interval_seconds"] == 180
            assert kwargs["nightly_time"] == "23:15"
            assert kwargs["branch_id"] == 5
            assert kwargs["stop_on_error"] is True
