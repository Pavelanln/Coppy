import argparse
import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Generator, Tuple

from tools.stats.upload_stats_lib import (
    download_gha_artifacts,
    download_s3_artifacts,
    unzip,
    upload_to_s3,
)
from tools.stats.upload_test_stats import process_xml_element

TESTCASE_TAG = "testcase"
TARGET_WORKFLOW = "--rerun-disabled-tests"
SEPARATOR = ";"


def is_rerun_disabled_tests(root: ET.ElementTree) -> bool:
    """
    Check if the test report is coming from rerun_disabled_tests workflow
    """
    skipped = root.find(".//*skipped")
    return skipped is not None and TARGET_WORKFLOW in skipped.attrib.get("message", "")


def process_report(
    report: Path,
) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, Dict[str, int]]]:
    """
    Return a list of disabled tests that should be re-enabled and those that are still
    failing and flaky (skipped)
    """
    root = ET.parse(report)

    # A test should be re-enable if it's green after rerunning in all platforms where it
    # is currently disabled
    success_tests: Dict[str, int] = defaultdict(int)
    # Also keep track of failures because pytest-flakefinder is used to run the same test
    # multiple times, some could fails
    failure_tests: Dict[str, int] = defaultdict(int)
    # Skipped tests are flaky tests (unittest), so we want to keep num_red and num_green
    # here for additional stats
    skipped_tests: Dict[str, Dict[str, int]] = {}

    if not is_rerun_disabled_tests(root):
        return success_tests, failure_tests, skipped_tests

    for test_case in root.iter(TESTCASE_TAG):
        parsed_test_case = process_xml_element(test_case)

        # Under --rerun-disabled-tests mode, a test is skipped when:
        # * it's skipped explicitly inside PyToch code
        # * it's skipped because it's a normal enabled test
        # * or it's falky (num_red > 0 and num_green > 0)
        # * or it's failing (num_red > 0 and num_green == 0)
        #
        # We care only about the latter two here
        skipped = parsed_test_case.get("skipped", None)
        if skipped and "num_red" not in skipped.get("message", ""):
            continue

        name = parsed_test_case.get("name", "")
        classname = parsed_test_case.get("classname", "")
        filename = parsed_test_case.get("file", "")

        if not name or not classname or not filename:
            continue

        # Check if the test is a failure
        failure = parsed_test_case.get("failure", None)

        disabled_test_id = SEPARATOR.join([name, classname, filename])
        # Under --rerun-disabled-tests mode, if a test is not skipped or failed, it's
        # counted as a success. Otherwise, it's still flaky or failing
        if skipped:
            try:
                stats = json.loads(skipped.get("message", ""))
            except json.JSONDecodeError:
                stats = {}

            skipped_tests[disabled_test_id] = {
                "num_green": stats.get("num_green", 0),
                "num_red": stats.get("num_red", 0),
            }
        elif failure:
            failure_tests[disabled_test_id] += 1
        else:
            success_tests[disabled_test_id] += 1

    return success_tests, failure_tests, skipped_tests


def get_test_reports(
    repo: str, workflow_run_id: int, workflow_run_attempt: int
) -> Generator[Path, None, None]:
    """
    Gather all the test reports from S3 and GHA. It is currently not possible to guess which
    test reports are from rerun_disabled_tests workflow because the name doesn't include the
    test config. So, all reports will need to be downloaded and examined
    """
    with TemporaryDirectory() as temp_dir:
        print("Using temporary directory:", temp_dir)
        os.chdir(temp_dir)

        artifact_paths = download_s3_artifacts(
            "test-reports", workflow_run_id, workflow_run_attempt
        )
        for path in artifact_paths:
            unzip(path)

        artifact_paths = download_gha_artifacts(
            "test-report", workflow_run_id, workflow_run_attempt
        )
        for path in artifact_paths:
            unzip(path)

        for report in Path(".").glob("**/*.xml"):
            yield report


def get_disabled_test_name(test_id: str) -> Tuple[str, str, str, str]:
    """
    Follow flaky bot convention here, if that changes, this will also need to be updated
    """
    name, classname, filename = test_id.split(SEPARATOR)
    return f"{name} (__main__.{classname})", name, classname, filename


def prepare_record(
    workflow_id: int,
    workflow_run_attempt: int,
    name: str,
    classname: str,
    filename: str,
    flaky: bool,
    num_red: int = 0,
    num_green: int = 0,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Prepare the record to save onto S3
    """
    key = (
        workflow_id,
        workflow_run_attempt,
        name,
        classname,
        filename,
    )

    record = {
        "workflow_id": workflow_id,
        "workflow_run_attempt": workflow_run_attempt,
        "name": name,
        "classname": classname,
        "filename": filename,
        "flaky": flaky,
        "num_green": num_green,
        "num_red": num_red,
    }

    return key, record


def save_results(
    workflow_id: int,
    workflow_run_attempt: int,
    success_tests: Dict[str, int],
    failure_tests: Dict[str, int],
    skipped_tests: Dict[str, Dict[str, int]],
) -> None:
    """
    Save the result to S3, so it can go to Rockset
    """
    should_be_enabled_tests = {
        name
        for name in success_tests.keys()
        if name not in failure_tests and name not in skipped_tests
    }
    records = {}

    # Log the results
    print(f"The following {len(should_be_enabled_tests)} tests should be re-enabled:")

    for test_id in should_be_enabled_tests:
        disabled_test_name, name, classname, filename = get_disabled_test_name(test_id)
        print(f"  {disabled_test_name} from {filename}")

        key, record = prepare_record(
            workflow_id=workflow_id,
            workflow_run_attempt=workflow_run_attempt,
            name=name,
            classname=classname,
            filename=filename,
            flaky=False,
        )
        records[key] = record

    # Log the results
    print(f"The following {len(failure_tests) + len(skipped_tests)} are still flaky:")

    # Consolidate failure and skipped tests
    for test_id, count in failure_tests.items():
        # Also see if there is any success
        num_green = success_tests.get(test_id, 0)
        num_red = count

        if test_id not in skipped_tests:
            skipped_tests[test_id] = defaultdict(int)

        skipped_tests[test_id]["num_green"] += num_green
        skipped_tests[test_id]["num_red"] += num_red

    for test_id, stats in skipped_tests.items():
        num_green = stats.get("num_green", 0)
        num_red = stats.get("num_red", 0)

        disabled_test_name, name, classname, filename = get_disabled_test_name(test_id)
        print(
            f"  {disabled_test_name} from {filename}, failing {num_red}/{num_red + num_green}"
        )

        key, record = prepare_record(
            workflow_id=workflow_id,
            workflow_run_attempt=workflow_run_attempt,
            name=name,
            classname=classname,
            filename=filename,
            flaky=True,
            num_green=num_green,
            num_red=num_red,
        )
        records[key] = record

    upload_to_s3(
        workflow_id,
        workflow_run_attempt,
        "rerun_disabled_tests",
        list(records.values()),
    )


def main(repo: str, workflow_run_id: int, workflow_run_attempt: int) -> None:
    """
    Find the list of all disabled tests that should be re-enabled
    """
    # A test should be re-enable if it's green after rerunning in all platforms where it
    # is currently disabled
    success_tests: Dict[str, int] = defaultdict(int)
    # Also keep track of failures because pytest-flakefinder is used to run the same test
    # multiple times, some could fails
    failure_tests: Dict[str, int] = defaultdict(int)
    # Skipped tests are flaky tests (unittest), so we want to keep num_red and num_green
    # here for additional stats
    skipped_tests: Dict[str, Dict[str, int]] = {}

    for report in get_test_reports(
        args.repo, args.workflow_run_id, args.workflow_run_attempt
    ):
        success, failure, skipped = process_report(report)

        # A test should be re-enable if it's green after rerunning in all platforms where it
        # is currently disabled. So they all need to be aggregated here
        for name, count in success.items():
            success_tests[name] += count

        for name, count in failure.items():
            failure_tests[name] += count

        for name, stats in skipped.items():
            if name not in failure_tests:
                skipped_tests[name] = stats.copy()
            else:
                skipped_tests[name]["num_green"] += stats["num_green"]
                skipped_tests[name]["num_red"] += stats["num_red"]

    save_results(
        workflow_run_id,
        workflow_run_attempt,
        success_tests,
        failure_tests,
        skipped_tests,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload test artifacts from GHA to S3")
    parser.add_argument(
        "--workflow-run-id",
        type=int,
        required=True,
        help="id of the workflow to get artifacts from",
    )
    parser.add_argument(
        "--workflow-run-attempt",
        type=int,
        required=True,
        help="which retry of the workflow this is",
    )
    parser.add_argument(
        "--repo",
        type=str,
        required=True,
        help="which GitHub repo this workflow run belongs to",
    )

    args = parser.parse_args()
    main(args.repo, args.workflow_run_id, args.workflow_run_attempt)
