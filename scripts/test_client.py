#!/usr/bin/env python3
"""Test script for Teraslice API client."""

import argparse
import sys
from ts_topy.client import TerasliceClient


def main():
    """Test the Teraslice client."""
    parser = argparse.ArgumentParser(description="Test Teraslice API client")
    parser.add_argument("url", nargs="?", default="http://localhost:5678", help="Teraslice master URL")
    parser.add_argument("--size", type=int, help="Number of items to fetch (for jobs and execution contexts)")
    args = parser.parse_args()

    print(f"Testing Teraslice client with URL: {args.url}")
    if args.size:
        print(f"Fetch size: {args.size}")
    print()

    try:
        with TerasliceClient(args.url, timeout=10) as client:
            # Test cluster state (includes nodes and workers)
            print("=" * 60)
            print("CLUSTER STATE")
            print("=" * 60)
            cluster_state = client.fetch_cluster_state()
            print(f"Total nodes: {cluster_state.total_nodes}")
            print(f"Total worker slots: {cluster_state.total_workers}")
            print(f"Active workers: {cluster_state.active_workers}")
            print(f"Available slots: {cluster_state.available_workers}")
            print("\nNodes:")
            for node_name, node in cluster_state.nodes.items():
                print(f"  - {node_name}: {node.hostname} (v{node.teraslice_version})")
                total = node.total if node.total is not None else "N/A"
                print(f"    Workers: {len(node.active)}/{total} active")
            print()

            # Test controllers
            print("=" * 60)
            print("CONTROLLERS")
            print("=" * 60)
            controllers = client.fetch_controllers()
            print(f"Total controllers: {len(controllers)}")
            for ctrl in controllers:
                print(f"\n  {ctrl.name}")
                print(f"    Ex ID: {ctrl.ex_id}")
                print(f"    Job ID: {ctrl.job_id}")
                print(f"    Workers: {ctrl.workers_active} active, {ctrl.workers_available} available")
                print(f"    Processed: {ctrl.processed}, Failed: {ctrl.failed}, Queued: {ctrl.queued}")
                if ctrl.started:
                    print(f"    Started: {ctrl.started}")
            print()

            # Test jobs
            print("=" * 60)
            print("JOBS")
            print("=" * 60)
            jobs = client.fetch_jobs(size=args.size)
            print(f"Total jobs returned: {len(jobs)}")
            for job in jobs:
                print(f"\n  {job.name}")
                print(f"    Job ID: {job.job_id}")
                print(f"    Lifecycle: {job.lifecycle}")
                print(f"    Workers: {job.workers}")
                print(f"    Active: {job.active}")
                print(f"    Operations: {len(job.operations)}")
                for i, op in enumerate(job.operations):
                    print(f"      {i+1}. {op.op}")
            print()

            # Test execution contexts
            print("=" * 60)
            print("EXECUTION CONTEXTS")
            print("=" * 60)
            ex_contexts = client.fetch_execution_contexts(size=args.size)
            print(f"Total execution contexts returned: {len(ex_contexts)}")
            for ex in ex_contexts:
                print(f"\n  {ex.name}")
                print(f"    Ex ID: {ex.ex_id}")
                print(f"    Job ID: {ex.job_id}")
                print(f"    Status: {ex.status}")
                print(f"    Lifecycle: {ex.lifecycle}")
                print(f"    Workers: {ex.workers}, Slicers: {ex.slicers}")
                print(f"    Has errors: {ex.has_errors}")
                if ex.slicer_hostname and ex.slicer_port:
                    print(f"    Slicer: {ex.slicer_hostname}:{ex.slicer_port}")
                if ex.slicer_stats:
                    stats = ex.slicer_stats
                    print(f"    Stats: {stats.processed} processed, {stats.failed} failed, {stats.queued} queued")
            print()

            print("=" * 60)
            print("SUCCESS - All endpoints working!")
            print("Models parsed correctly!")
            print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
