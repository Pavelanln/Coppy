"""
Generate a torchbench test report from a file containing the PR body.
Currently, only supports running tests on specified model names

Testing environment:
- Intel Xeon 8259CL @ 2.50 GHz, 24 Cores with disabled Turbo and HT
- Nvidia Tesla T4
- Nvidia Driver 470.82.01
- Python 3.8
- CUDA 11.3
"""
# Known issues:
# 1. Does not reuse the build artifact in other CI workflows
# 2. CI jobs are serialized because there is only one worker
import os
import boto3
import git  # type: ignore[import]
import pathlib
import argparse
import subprocess
from pathlib import Path

from typing import List, Tuple

TORCHBENCH_CONFIG_NAME = "config.yaml"
TORCHBENCH_USERBENCHMARK_CONFIG_NAME = "ub-config.yaml"
MAGIC_PREFIX = "RUN_TORCHBENCH:"
MAGIC_TORCHBENCH_PREFIX = "TORCHBENCH_BRANCH:"
ABTEST_CONFIG_TEMPLATE = """# This config is automatically generated by run_torchbench.py
start: {control}
end: {treatment}
threshold: 100
direction: decrease
timeout: 720
tests:"""
S3_BUCKET = "ossci-metrics"
S3_PREFIX = "torchbench-pr-test"

class S3Client:
    def __init__(self, bucket=S3_BUCKET, prefix=S3_PREFIX):
        self.s3 = boto3.client('s3')
        self.resource = boto3.resource('s3')
        self.bucket = bucket
        self.prefix = prefix

    def upload_file(self, file_path, filekey_prefix):
        assert file_path.is_file(), f"Specified file path {file_path} does not exist or not file."
        file_name = file_path.name
        s3_key = f"{self.prefix}/{filekey_prefix}/{file_name}"
        print(f"Uploading file {file_name} to S3 with key: {s3_key}")
        response = self.s3.upload_file(str(file_path), self.bucket, s3_key)
        # make the object public
        object_acl = self.resource.ObjectAcl(self.bucket, s3_key)
        object_acl.put(ACL='public-read')

def gen_abtest_config(control: str, treatment: str, models: List[str]) -> str:
    d = {}
    d["control"] = control
    d["treatment"] = treatment
    config = ABTEST_CONFIG_TEMPLATE.format(**d)
    if models == ["ALL"]:
        return config + "\n"
    for model in models:
        config = f"{config}\n  - {model}"
    config = config + "\n"
    return config

def setup_gha_env(name: str, val: str) -> None:
    fname = os.environ["GITHUB_ENV"]
    content = f"{name}={val}\n"
    with open(fname, "a") as fo:
        fo.write(content)

def find_current_branch(repo_path: str) -> str:
    repo = git.Repo(repo_path)
    name: str = repo.active_branch.name
    return name

def deploy_torchbench_config(output_dir: str, config: str, config_name: str = TORCHBENCH_CONFIG_NAME) -> None:
    # Create test dir if needed
    pathlib.Path(output_dir).mkdir(exist_ok=True)
    # TorchBench config file name
    config_path = os.path.join(output_dir, config_name)
    with open(config_path, "w") as fp:
        fp.write(config)

def get_valid_models(torchbench_path: str) -> List[str]:
    benchmark_path = os.path.join(torchbench_path, "torchbenchmark", "models")
    valid_models = [model for model in os.listdir(benchmark_path) if os.path.isdir(os.path.join(benchmark_path, model))]
    return valid_models

def get_valid_userbenchmarks(torchbench_path: str) -> List[str]:
    def is_valid_ub_dir(ub_path: str) -> bool:
        return os.path.isdir(ub_path) and os.path.exists(os.path.join(ub_path, "__init__.py"))
    ub_path = os.path.join(os.path.abspath(torchbench_path), "userbenchmark")
    ubs = list(filter(is_valid_ub_dir, [os.path.join(ub_path, ubdir) for ubdir in os.listdir(ub_path)]))
    valid_ubs = list(map(lambda x: os.path.basename(x), ubs))
    return valid_ubs

def extract_models_from_pr(torchbench_path: str, prbody_file: str) -> Tuple[List[str], List[str]]:
    model_list = []
    userbenchmark_list = []
    pr_list = []
    with open(prbody_file, "r") as pf:
        lines = map(lambda x: x.strip(), pf.read().splitlines())
        magic_lines = list(filter(lambda x: x.startswith(MAGIC_PREFIX), lines))
        if magic_lines:
            # Only the first magic line will be recognized.
            pr_list = list(map(lambda x: x.strip(), magic_lines[0][len(MAGIC_PREFIX):].split(",")))
    valid_models = get_valid_models(torchbench_path)
    valid_ubs = get_valid_userbenchmarks(torchbench_path)
    for pr_bm in pr_list:
        if pr_bm in valid_models or pr_bm == "ALL":
            model_list.append(pr_bm)
        elif pr_bm in valid_ubs:
            userbenchmark_list.append(pr_bm)
        else:
            print(f"The model or benchmark {pr_bm} you specified does not exist in TorchBench suite. Please double check.")
            exit(-1)
    # Shortcut: if pr_list is ["ALL"], run all the model tests
    if "ALL" in model_list:
        model_list = ["ALL"]
    return model_list, userbenchmark_list

def find_torchbench_branch(prbody_file: str) -> str:
    branch_name: str = ""
    with open(prbody_file, "r") as pf:
        lines = map(lambda x: x.strip(), pf.read().splitlines())
        magic_lines = list(filter(lambda x: x.startswith(MAGIC_TORCHBENCH_PREFIX), lines))
        if magic_lines:
            # Only the first magic line will be recognized.
            branch_name = magic_lines[0][len(MAGIC_TORCHBENCH_PREFIX):].strip()
    # If not specified, use main as the default branch
    if not branch_name:
        branch_name = "main"
    return branch_name

def run_torchbench(pytorch_path: str, torchbench_path: str, output_dir: str) -> None:
    # Copy system environment so that we will not override
    env = dict(os.environ)
    command = ["python", "bisection.py", "--work-dir", output_dir,
               "--pytorch-src", pytorch_path, "--torchbench-src", torchbench_path,
               "--config", os.path.join(output_dir, TORCHBENCH_CONFIG_NAME),
               "--output", os.path.join(output_dir, "result.txt")]
    print(f"Running torchbench command: {command}")
    subprocess.check_call(command, cwd=torchbench_path, env=env)

def run_userbenchmarks(pytorch_path: str, torchbench_path: str, base_sha: str, head_sha: str,
                       userbenchmark: str, output_dir: str) -> None:
    # Copy system environment so that we will not override
    env = dict(os.environ)
    command = ["python", "./.github/scripts/abtest.py",
               "--pytorch-repo", pytorch_path,
               "--base", base_sha,
               "--head", head_sha,
               "--userbenchmark", userbenchmark,
               "--output-dir", output_dir]
    print(f"Running torchbench userbenchmark command: {command}")
    subprocess.check_call(command, cwd=torchbench_path, env=env)

def process_upload_s3(result_dir):
    # validate result directory
    result_dir = Path(result_dir)
    assert result_dir.exists(), f"Specified result directory doesn't exist."
    # upload all files to S3 bucket oss-ci-metrics
    files = [x for x in result_dir.iterdir() if x.is_file()]
    # upload file to S3 bucket
    s3_client = S3Client()
    filekey_prefix = result_dir.name
    for f in files:
        s3_client.upload_file(f, filekey_prefix)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run TorchBench tests based on PR')
    parser.add_argument('--pr-body', help="The file that contains body of a Pull Request")

    subparsers = parser.add_subparsers(dest='command')
    # parser for setup the torchbench branch name env
    branch_parser = subparsers.add_parser("set-torchbench-branch")
    # parser to run the torchbench branch
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument('--pr-num', required=True, type=str, help="The Pull Request number")
    run_parser.add_argument('--pr-base-sha', required=True, type=str, help="The Pull Request base hash")
    run_parser.add_argument('--pr-head-sha', required=True, type=str, help="The Pull Request head hash")
    run_parser.add_argument('--pytorch-path', required=True, type=str, help="Path to pytorch repository")
    run_parser.add_argument('--torchbench-path', required=True, type=str, help="Path to TorchBench repository")
    # parser to upload results to S3
    upload_parser = subparsers.add_parser("upload-s3")
    upload_parser.add_argument('--result-dir', required=True, type=str, help="Path to benchmark output")
    args = parser.parse_args()

    if args.command == 'set-torchbench-branch':
        branch_name = find_torchbench_branch(args.pr_body)
        # env name: "TORCHBENCH_BRANCH"
        setup_gha_env(MAGIC_TORCHBENCH_PREFIX[:-1], branch_name)
    elif args.command == 'run':
        output_dir: str = os.path.join(os.environ["HOME"], ".torchbench", "bisection", f"pr{args.pr_num}")
        # Assert the current branch in args.torchbench_path is the same as the one specified in pr body
        branch_name = find_torchbench_branch(args.pr_body)
        current_branch = find_current_branch(args.torchbench_path)
        assert branch_name == current_branch, f"Torchbench repo {args.torchbench_path} is on branch {current_branch}, \
                                                but user specified to run on branch {branch_name}."
        print(f"Ready to run TorchBench with benchmark. Result will be saved in the directory: {output_dir}.")
        # Identify the specified models and userbenchmarks
        models, userbenchmarks = extract_models_from_pr(args.torchbench_path, args.pr_body)
        if models:
            torchbench_config = gen_abtest_config(args.pr_base_sha, args.pr_head_sha, models)
            deploy_torchbench_config(output_dir, torchbench_config)
            run_torchbench(pytorch_path=args.pytorch_path, torchbench_path=args.torchbench_path, output_dir=output_dir)
        if userbenchmarks:
            assert len(userbenchmarks) == 1, \
                "We don't support running multiple userbenchmarks in single workflow yet." \
                "If you need, please submit a feature request."
            run_userbenchmarks(pytorch_path=args.pytorch_path, torchbench_path=args.torchbench_path,
                               base_sha=args.pr_base_sha, head_sha=args.pr_head_sha,
                               userbenchmark=userbenchmarks[0], output_dir=output_dir)
        if not models and not userbenchmarks:
            print("Can't parse valid models or userbenchmarks from the pr body. Quit.")
            exit(-1)
    elif args.command == 'upload-s3':
        process_upload_s3(args.result_dir)
    else:
        print(f"The command {args.command} is not supported.")
        exit(-1)
