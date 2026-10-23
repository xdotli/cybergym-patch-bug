# SPDX-License-Identifier: BSD-3-Clause
"""cybergym_patch_bug: fix the bug; the server imports your module and grades it."""

import json
import os
import shutil
import subprocess
import tempfile
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata, State

try:
    from ..models import CybergymPatchBugAction, CybergymPatchBugObservation
except ImportError:
    from models import CybergymPatchBugAction, CybergymPatchBugObservation

TASKS_DIR = os.environ.get(
    "PATCH_BUG_TASKS",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks"),
)
MAX_STEPS = 200
CMD_TIMEOUT_S = 30
OUTPUT_CAP = 20000
SECRET_FILES = ("answer.sha256", "index.json", "hidden_tests.py", "reference_fix.py")


class CybergymPatchBugEnvironment(Environment):
    """Submit the corrected module; hidden tests decide the reward."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        with open(os.path.join(TASKS_DIR, "index.json"), encoding="utf-8") as handle:
            self._index = json.load(handle)
        self._tasks = self._index["tasks"]
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._task = None
        self._workspace = None
        self._steps_left = 0
        self._done = False
        self._reward = 0.0

    # -- task provider -----------------------------------------------------
    def list_splits(self):
        splits = []
        for task in self._tasks:
            if task["split"] not in splits:
                splits.append(task["split"])
        return splits

    def num_tasks(self, split: str) -> int:
        return sum(1 for task in self._tasks if task["split"] == split)

    def get_task(self, split: str, index: int):
        ids = [task["task_id"] for task in self._tasks if task["split"] == split]
        return {"id": ids[index], "index": index, "split": split}

    # -- environment -------------------------------------------------------
    def reset(self, seed=None, episode_id=None, split=None, index=0, **kwargs):
        split = split or "train"
        candidates = [task for task in self._tasks if task["split"] == split]
        if not candidates:
            raise ValueError(f"unknown split {split!r}")
        index = int(index) % len(candidates)
        self._task = candidates[index]
        self._state = State(episode_id=str(episode_id or uuid4()), step_count=0)
        self._workspace = tempfile.mkdtemp(prefix="oe-ep-", dir="/tmp")
        src = os.path.join(TASKS_DIR, self._task["task_id"])
        for name in sorted(os.listdir(src)):
            if name in SECRET_FILES:
                continue
            path = os.path.join(src, name)
            if os.path.isfile(path):
                shutil.copy(path, os.path.join(self._workspace, name))
        self._steps_left = MAX_STEPS
        self._done = False
        self._reward = 0.0
        return CybergymPatchBugObservation(
            task_id=self._task["task_id"],
            challenge=self._read_challenge(),
            output="",
            message="Episode ready. Explore with cmd; finish with answer (the full module source).",
            steps_left=self._steps_left,
            done=False,
            reward=0.0,
        )

    def _read_challenge(self):
        path = os.path.join(self._workspace, "challenge.txt")
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                return handle.read()
        return ""

    def _grade(self, answer: str):
        task_dir = os.path.join(TASKS_DIR, self._task["task_id"])
        grading = tempfile.mkdtemp(prefix="oe-grade-", dir="/tmp")
        try:
            module_path = os.path.join(grading, "submission.py")
            with open(module_path, "w", encoding="utf-8", errors="replace") as handle:
                handle.write(answer)
            script = (
                "import importlib.util, json, sys, traceback\n"
                "spec = importlib.util.spec_from_file_location('submission', sys.argv[1])\n"
                "mod = importlib.util.module_from_spec(spec)\n"
                "try:\n"
                "    spec.loader.exec_module(mod)\n"
                "except Exception:\n"
                "    print(json.dumps({'ok': False, 'why': 'import failed', 'detail': traceback.format_exc(limit=2)})); raise SystemExit\n"
                "public_src = ''.join(line for line in open(sys.argv[2]).read().splitlines(True) if not line.startswith(('from buggy', 'import buggy')))\n"
                "hidden_src = open(sys.argv[3]).read()\n"
                "ns = vars(mod).copy()\n"
                "try:\n"
                "    exec(public_src, ns)\n"
                "except AssertionError:\n"
                "    print(json.dumps({'ok': False, 'why': 'a public test failed (regression)'})); raise SystemExit\n"
                "except Exception:\n"
                "    print(json.dumps({'ok': False, 'why': 'a public test raised'})); raise SystemExit\n"
                "try:\n"
                "    exec(hidden_src, ns)\n"
                "except AssertionError:\n"
                "    print(json.dumps({'ok': False, 'why': 'a hidden test failed: the bug is still there (or another one was introduced)'})); raise SystemExit\n"
                "except Exception:\n"
                "    print(json.dumps({'ok': False, 'why': 'a hidden test raised'})); raise SystemExit\n"
                "print(json.dumps({'ok': True, 'why': 'public and hidden tests all pass'}))\n"
            )
            proc = subprocess.run(
                ["/usr/bin/env", "python3", "-c", script, module_path,
                 os.path.join(task_dir, "tests_public.py"),
                 os.path.join(task_dir, "hidden_tests.py")],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
            )
            out = proc.stdout.decode("utf-8", "replace").strip().splitlines()
            verdict = None
            for line in reversed(out):
                if line.startswith("{"):
                    import json as _json
                    verdict = _json.loads(line)
                    break
            if verdict is None:
                return 0.0, "grading produced no verdict\n" + (proc.stderr.decode("utf-8", "replace")[-512:])
            text = f"{verdict.get('why', '')}\n"
            if verdict.get("detail"):
                text += verdict["detail"][:512] + "\n"
            return (1.0 if verdict.get("ok") else 0.0), text
        except subprocess.TimeoutExpired:
            return 0.0, "grading timed out\n"
        finally:
            shutil.rmtree(grading, ignore_errors=True)

    def step(self, action: CybergymPatchBugAction, timeout_s=None, **kwargs):
        if self._done or self._workspace is None:
            return CybergymPatchBugObservation(
                task_id=self._task["task_id"] if self._task else "",
                challenge="",
                output="The episode has ended. Reset to start another task.",
                message="ended",
                steps_left=0,
                done=True,
                reward=self._reward,
            )
        self._state.step_count += 1

        if action.answer:
            self._reward, text = self._grade(action.answer)
            self._done = True
            self._steps_left = 0
            return CybergymPatchBugObservation(
                task_id=self._task["task_id"],
                challenge="",
                output=text,
                message="final answer graded",
                steps_left=0,
                done=True,
                reward=self._reward,
            )

        command = (action.cmd or "").strip()
        if command == "done":
            self._done = True
            self._steps_left = 0
            return CybergymPatchBugObservation(
                task_id=self._task["task_id"],
                challenge="",
                output="Episode closed without a final answer (reward 0).",
                message="gave up",
                steps_left=0,
                done=True,
                reward=0.0,
            )

        self._steps_left -= 1
        try:
            proc = subprocess.run(
                ["/bin/sh", "-c", command],
                cwd=self._workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=CMD_TIMEOUT_S,
            )
            output = proc.stdout.decode("utf-8", "replace")
            if proc.returncode != 0:
                output += f"\n[exit {proc.returncode}]"
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or b"").decode("utf-8", "replace")) + "\n[timeout]"
        except Exception as exc:  # noqa: BLE001
            output = f"[error] {type(exc).__name__}: {exc}"

        if self._steps_left <= 0:
            self._done = True
            output += "\n[step budget exhausted; episode closed with reward 0]"

        return CybergymPatchBugObservation(
            task_id=self._task["task_id"],
            challenge="",
            output=output[:OUTPUT_CAP],
            message="",
            steps_left=self._steps_left,
            done=self._done,
            reward=self._reward,
        )

    @property
    def state(self) -> State:
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name="cybergym_patch_bug",
            description="Defensive fixing: submit the corrected module; hidden tests grade it.",
            version="1.0.0",
        )

    def close(self):
        if self._workspace and os.path.isdir(self._workspace):
            shutil.rmtree(self._workspace, ignore_errors=True)
