"""Count-only pilot runner. Dry-run is the default; never print record values."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from pydantic import ValidationError
from .client import JobDivaClient, JobDivaError, _ids
from .config import JobDivaSettings
from .contracts import ContractError, JobDivaContract, READ_OPERATIONS


async def run(args) -> dict:
    contract = JobDivaContract.model_validate_json(Path(args.contract).read_text())
    values = json.loads(Path(args.ids_file).read_text())
    if not isinstance(values, list):
        raise ContractError("Test IDs must be a JSON array")
    ids = _ids(values)
    if not 1 <= len(ids) <= 50:
        raise ContractError("The pilot runner accepts 1 to 50 explicitly selected test IDs")
    parameters = json.loads(Path(args.parameters_file).read_text()) if args.parameters_file else {}
    if not isinstance(parameters, dict):
        raise ContractError("Parameters must be a JSON object")
    if args.operation not in contract.operations or not contract.operations[args.operation].ids_parameter:
        raise ContractError("The pilot runner requires a reviewed ID-based read operation")
    summary = {"mode": "read_only" if args.execute else "dry_run", "operation": args.operation,
               "requested_ids": len(ids), "contract_reviewed": contract.reviewed}
    if not args.execute:
        return summary
    settings = JobDivaSettings()
    async with JobDivaClient(settings, contract) as client:
        count = 0
        async for records in client.read_batches(args.operation, ids, parameters=parameters):
            count += len(records)
        summary["returned_records"] = count
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--operation", choices=sorted(READ_OPERATIONS - {"OpenJobsList"}), required=True)
    parser.add_argument("--ids-file", required=True)
    parser.add_argument("--parameters-file")
    parser.add_argument("--execute", action="store_true", help="Requires JOBDIVA_LIVE_ENABLED=true and a reviewed contract")
    try:
        print(json.dumps(asyncio.run(run(parser.parse_args())), sort_keys=True))
        return 0
    except (JobDivaError, ContractError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (ValidationError, ValueError, OSError):
        # Validation errors can include input values. Do not echo them.
        print("Invalid or unreadable pilot configuration; review it locally without sharing secrets", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
