"""Spike: Windows subprocess flows (garak, promptfoo via npx) and spawn ProcessPoolExecutor."""
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent


def work(x: int) -> tuple[int, int]:
    return x * x, os.getpid()


def pool_check():
    ctx = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=2, mp_context=ctx) as ex:
        res = list(ex.map(work, range(4)))
    print("pool:", [r[0] for r in res], "distinct pids:", len({r[1] for r in res}), "parent:", os.getpid())


def run_agent():
    return subprocess.Popen([sys.executable, str(HERE / "fake_agent.py"), "8765"], stdout=subprocess.DEVNULL)


def garak_check():
    out = HERE / "garak_out"
    cmd = [sys.executable, "-m", "garak", "--target_type", "rest",
           "--generator_option_file", str(HERE / "garak_rest.json"), "--spec", "probes.dan.Dan_11_0",
           "--report_prefix", str(out / "py_subproc"), "--generations", "1"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("garak rc:", p.returncode, "report exists:", (out / "py_subproc.report.jsonl").exists())


def promptfoo_check():
    print("which npx:", shutil.which("npx"), "| which npx.cmd:", shutil.which("npx.cmd"))
    base = ["npx", "--yes", "promptfoo@0.125.1", "eval", "-c", str(HERE / "promptfooconfig.yaml"),
            "-o", str(HERE / "py_results.json"), "--no-cache"]
    env = {**os.environ, "PROMPTFOO_DISABLE_TELEMETRY": "1", "PROMPTFOO_DISABLE_UPDATE": "1"}
    try:
        p = subprocess.run(base, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        print("promptfoo bare 'npx' rc:", p.returncode)
    except FileNotFoundError as e:
        print("promptfoo bare 'npx' FAILED:", e)
    resolved = [shutil.which("npx")] + base[1:]
    p = subprocess.run(resolved, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    print("promptfoo via shutil.which rc:", p.returncode, "(100 = failed tests expected)",
          "| results written:", (HERE / "py_results.json").exists())


if __name__ == "__main__":
    pool_check()
    agent = run_agent()
    time.sleep(2)
    try:
        garak_check()
        promptfoo_check()
    finally:
        agent.kill()
