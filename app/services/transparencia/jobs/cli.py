import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import Any

from app.database import SessionLocal
from app.main import init_db
from app.services.transparencia.jobs.service import (
    TransparenciaCargaJobConflictError,
    TransparenciaCargaJobNotFoundError,
    get_job,
    list_jobs,
    queue_job_run,
    run_job,
    seed_parana_beneficio_jobs,
)


def _job_summary(job: Any) -> dict[str, Any]:
    return {
        "id": int(job.id),
        "job_code": str(job.job_code),
        "status": str(job.status),
        "total_items": int(job.total_items),
        "pending_items": int(job.pending_items),
        "running_items": int(job.running_items),
        "success_items": int(job.success_items),
        "failed_items": int(job.failed_items),
        "started_at": job.started_at.isoformat() if job.started_at is not None else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at is not None else None,
    }


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=True, indent=2, default=str))


def init_db_command(_: argparse.Namespace) -> int:
    init_db()
    _print_json({"ok": True})
    return 0


def seed_command(_: argparse.Namespace) -> int:
    with SessionLocal() as db:
        created_count, existing_count, jobs = seed_parana_beneficio_jobs(db)
        _print_json(
            {
                "created_count": created_count,
                "existing_count": existing_count,
                "jobs": [_job_summary(job) for job in jobs],
            }
        )
    return 0


def list_jobs_command(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        total, jobs = list_jobs(
            db,
            status=args.status,
            limit=args.limit,
            offset=args.offset,
        )
        _print_json(
            {
                "total": total,
                "limit": args.limit,
                "offset": args.offset,
                "jobs": [_job_summary(job) for job in jobs],
            }
        )
    return 0


def show_job_command(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        job = get_job(db, args.job_id)
        if job is None:
            raise TransparenciaCargaJobNotFoundError(f"Job {args.job_id} not found")
        _print_json(_job_summary(job))
    return 0


def queue_job_command(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        job = queue_job_run(db, args.job_id)
        _print_json(_job_summary(job))
    return 0


def run_job_command(args: argparse.Namespace) -> int:
    with SessionLocal() as db:
        job = queue_job_run(db, args.job_id)
        _print_json({"queued": _job_summary(job)})
    asyncio.run(run_job(args.job_id))
    with SessionLocal() as db:
        job = get_job(db, args.job_id)
        if job is None:
            raise TransparenciaCargaJobNotFoundError(f"Job {args.job_id} not found")
        _print_json({"final": _job_summary(job)})
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.services.transparencia.jobs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db_parser = subparsers.add_parser("init-db")
    init_db_parser.set_defaults(func=init_db_command)

    seed_parser = subparsers.add_parser("seed")
    seed_parser.set_defaults(func=seed_command)

    list_parser = subparsers.add_parser("list-jobs")
    list_parser.add_argument("--status")
    list_parser.add_argument("--limit", type=int, default=100)
    list_parser.add_argument("--offset", type=int, default=0)
    list_parser.set_defaults(func=list_jobs_command)

    show_parser = subparsers.add_parser("show-job")
    show_parser.add_argument("job_id", type=int)
    show_parser.set_defaults(func=show_job_command)

    queue_parser = subparsers.add_parser("queue-job")
    queue_parser.add_argument("job_id", type=int)
    queue_parser.set_defaults(func=queue_job_command)

    run_parser = subparsers.add_parser("run-job")
    run_parser.add_argument("job_id", type=int)
    run_parser.set_defaults(func=run_job_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (TransparenciaCargaJobConflictError, TransparenciaCargaJobNotFoundError, ValueError) as exc:
        parser.exit(status=1, message=f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
