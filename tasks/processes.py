"""
Process management tasks for RHCSA exam.
"""

import random
import logging
from tasks.base import BaseTask
from tasks.registry import TaskRegistry
from core.validator import ValidationCheck, ValidationResult
from validators.safe_executor import execute_safe


logger = logging.getLogger(__name__)


@TaskRegistry.register("processes")
class KillProcessTask(BaseTask):
    """Kill a process by name or PID."""

    def __init__(self):
        super().__init__(
            id="proc_kill_001",
            category="processes",
            difficulty="easy",
            points=8
        )
        self.process_name = None
        self.signal = None

    def generate(self, **params):
        """Generate process kill task."""
        processes = ['httpd', 'nginx', 'sleep', 'dd']
        self.process_name = params.get('process', random.choice(processes))
        self.signal = params.get('signal', 'SIGTERM')

        self.description = (
            f"Terminate process:\n"
            f"  - Process name: {self.process_name}\n"
            f"  - Signal: {self.signal}\n"
            f"  - Kill ALL instances of this process\n"
            f"  - Verify the process is no longer running"
        )

        self.hints = [
            f"Kill by name: pkill {self.process_name}",
            f"Or: killall {self.process_name}",
            f"With specific signal: pkill -{self.signal} {self.process_name}",
            f"Find PID first: pgrep {self.process_name} or ps aux | grep {self.process_name}",
            "Then kill: kill <PID>",
            f"Verify: pgrep {self.process_name} (should return nothing)"
        ]

        return self

    def validate(self):
        """Validate process is killed."""
        checks = []
        total_points = 0

        # Check: Process is not running
        result = execute_safe(['pgrep', '-x', self.process_name])

        if not result.success or not result.stdout.strip():
            checks.append(ValidationCheck(
                name="process_killed",
                passed=True,
                points=8,
                message=f"Process '{self.process_name}' successfully terminated"
            ))
            total_points += 8
        else:
            pids = result.stdout.strip().split('\n')
            checks.append(ValidationCheck(
                name="process_killed",
                passed=False,
                points=0,
                max_points=8,
                message=f"Process '{self.process_name}' still running (PIDs: {', '.join(pids)})"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class AdjustProcessPriorityTask(BaseTask):
    """Adjust process priority using nice/renice."""

    def __init__(self):
        super().__init__(
            id="proc_priority_001",
            category="processes",
            difficulty="medium",
            points=10
        )
        self.process_name = None
        self.nice_value = None

    def generate(self, **params):
        """Generate process priority task."""
        self.process_name = params.get('process', 'sleep')
        self.nice_value = params.get('nice', random.choice([-10, -5, 0, 5, 10, 19]))

        self.description = (
            f"Adjust process priority:\n"
            f"  - Process: {self.process_name}\n"
            f"  - Nice value: {self.nice_value}\n"
            f"  - Change priority of ALL running instances\n"
            f"  - Use renice command"
        )

        self.hints = [
            f"Find PIDs: pgrep {self.process_name}",
            f"Renice: renice {self.nice_value} -p <PID>",
            f"For all instances: renice {self.nice_value} $(pgrep {self.process_name})",
            f"Verify: ps -eo pid,ni,comm | grep {self.process_name}",
            "Negative nice values require root (higher priority)",
            "Positive nice values mean lower priority"
        ]

        return self

    def validate(self):
        """Validate process priority."""
        checks = []
        total_points = 0

        # Get PIDs of the process
        result = execute_safe(['pgrep', '-x', self.process_name])

        if result.success and result.stdout.strip():
            pids = result.stdout.strip().split('\n')

            # Check nice value of each PID
            all_correct = True
            for pid in pids:
                ps_result = execute_safe(['ps', '-o', 'ni=', '-p', pid])
                if ps_result.success:
                    try:
                        current_nice = int(ps_result.stdout.strip())
                        if current_nice != self.nice_value:
                            all_correct = False
                            break
                    except ValueError:
                        all_correct = False
                        break
                else:
                    all_correct = False
                    break

            if all_correct:
                checks.append(ValidationCheck(
                    name="priority_adjusted",
                    passed=True,
                    points=10,
                    message=f"All '{self.process_name}' processes have nice value {self.nice_value}"
                ))
                total_points += 10
            else:
                checks.append(ValidationCheck(
                    name="priority_adjusted",
                    passed=False,
                    points=0,
                    max_points=10,
                    message=f"Nice value not correctly set for all '{self.process_name}' processes"
                ))
        else:
            checks.append(ValidationCheck(
                name="process_exists",
                passed=False,
                points=0,
                max_points=10,
                message=f"Process '{self.process_name}' not found"
            ))

        passed = total_points >= (self.points * 0.8)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class StartProcessWithPriorityTask(BaseTask):
    """Start a process with specific nice value."""

    def __init__(self):
        super().__init__(
            id="proc_nice_start_001",
            category="processes",
            difficulty="medium",
            points=10
        )
        self.command = None
        self.nice_value = None
        self.process_name = None

    def generate(self, **params):
        """Generate start with priority task."""
        commands = [
            ('sleep 3600', 'sleep'),
            ('dd if=/dev/zero of=/dev/null', 'dd'),
        ]

        cmd_choice = params.get('command', random.choice(commands))
        if isinstance(cmd_choice, tuple):
            self.command, self.process_name = cmd_choice
        else:
            self.command = cmd_choice
            self.process_name = cmd_choice.split()[0]

        self.nice_value = params.get('nice', random.choice([5, 10, 15, 19]))

        self.description = (
            f"Start a process with specific priority:\n"
            f"  - Command: {self.command}\n"
            f"  - Nice value: {self.nice_value}\n"
            f"  - Process must run in background\n"
            f"  - Verify it's running with correct priority"
        )

        self.hints = [
            f"Start with nice: nice -n {self.nice_value} {self.command} &",
            f"Verify: ps -eo pid,ni,comm | grep {self.process_name}",
            f"Check: pgrep {self.process_name} should show the PID",
            "The & at the end runs it in background"
        ]

        return self

    def validate(self):
        """Validate process started with priority."""
        checks = []
        total_points = 0

        # Check if process is running (5 points)
        result = execute_safe(['pgrep', '-x', self.process_name])

        if result.success and result.stdout.strip():
            checks.append(ValidationCheck(
                name="process_running",
                passed=True,
                points=5,
                message=f"Process '{self.process_name}' is running"
            ))
            total_points += 5

            # Check nice value (5 points)
            pids = result.stdout.strip().split('\n')
            # Check the first PID's nice value
            ps_result = execute_safe(['ps', '-o', 'ni=', '-p', pids[0]])

            if ps_result.success:
                try:
                    current_nice = int(ps_result.stdout.strip())
                    if current_nice == self.nice_value:
                        checks.append(ValidationCheck(
                            name="correct_priority",
                            passed=True,
                            points=5,
                            message=f"Process has correct nice value: {self.nice_value}"
                        ))
                        total_points += 5
                    else:
                        checks.append(ValidationCheck(
                            name="correct_priority",
                            passed=False,
                            points=0,
                            max_points=5,
                            message=f"Nice value is {current_nice}, expected {self.nice_value}"
                        ))
                except ValueError:
                    checks.append(ValidationCheck(
                        name="correct_priority",
                        passed=False,
                        points=0,
                        max_points=5,
                        message=f"Could not determine nice value"
                    ))
        else:
            checks.append(ValidationCheck(
                name="process_running",
                passed=False,
                points=0,
                max_points=5,
                message=f"Process '{self.process_name}' is not running"
            ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class FindProcessByUserTask(BaseTask):
    """Find and manage processes owned by a specific user."""

    def __init__(self):
        super().__init__(
            id="proc_find_user_001",
            category="processes",
            difficulty="exam",
            points=12
        )
        self.username = None
        self.action = None

    def generate(self, **params):
        """Generate find process by user task."""
        self.username = params.get('username', 'apache')
        actions = ['list', 'count', 'kill']
        self.action = params.get('action', random.choice(actions))

        if self.action == 'list':
            task_desc = f"List all processes owned by user '{self.username}'"
            verify = "Use: ps -u {username}"
        elif self.action == 'count':
            task_desc = f"Count processes owned by user '{self.username}'"
            verify = "Use: ps -u {username} --no-headers | wc -l"
        else:  # kill
            task_desc = f"Terminate all processes owned by user '{self.username}'"
            verify = "Use: pkill -u {username}"

        self.description = (
            f"Process management by user:\n"
            f"  - Task: {task_desc}\n"
            f"  - User: {self.username}\n"
            f"  - Use appropriate ps/pkill commands"
        )

        self.hints = [
            f"List user processes: ps -u {self.username}",
            f"Kill user processes: pkill -u {self.username}",
            f"Or: killall -u {self.username}",
            f"Find PIDs: pgrep -u {self.username}",
            f"Verify: ps -u {self.username} (should show nothing if killed)"
        ]

        return self

    def validate(self):
        """Validate process management by user."""
        checks = []
        total_points = 0

        # For kill action, verify no processes remain
        if self.action == 'kill':
            result = execute_safe(['pgrep', '-u', self.username])

            if not result.success or not result.stdout.strip():
                checks.append(ValidationCheck(
                    name="user_processes_killed",
                    passed=True,
                    points=12,
                    message=f"All processes for user '{self.username}' terminated"
                ))
                total_points += 12
            else:
                pids = result.stdout.strip().split('\n')
                checks.append(ValidationCheck(
                    name="user_processes_killed",
                    passed=False,
                    points=0,
                    max_points=12,
                    message=f"User '{self.username}' still has {len(pids)} process(es) running"
                ))
        else:
            # For list/count, just verify the user exists and command works
            result = execute_safe(['id', self.username])

            if result.success:
                checks.append(ValidationCheck(
                    name="user_exists",
                    passed=True,
                    points=12,
                    message=f"User '{self.username}' exists (task verification)"
                ))
                total_points += 12
            else:
                checks.append(ValidationCheck(
                    name="user_exists",
                    passed=False,
                    points=0,
                    max_points=12,
                    message=f"User '{self.username}' not found"
                ))

        passed = total_points >= (self.points * 0.7)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class BackgroundProcessTask(BaseTask):
    """Run a process in the background."""

    def __init__(self):
        super().__init__(
            id="process_background_001",
            category="processes",
            difficulty="medium",
            points=8
        )
        self.command = None
        self.output_file = None

    def generate(self, **params):
        self.command = params.get('command', 'sleep 300')
        self.output_file = params.get('output', '/tmp/bg_process.pid')

        self.description = (
            f"Run a process in the background:\n"
            f"  - Command: {self.command}\n"
            f"  - Run in background (don't block terminal)\n"
            f"  - Save the process ID to: {self.output_file}\n"
            f"  - Process should continue running"
        )

        self.hints = [
            f"Run in background: {self.command} &",
            f"Get last background PID: echo $! > {self.output_file}",
            f"Or: nohup {self.command} & echo $! > {self.output_file}",
            "List background jobs: jobs",
            "Verify process: ps -p $(cat /tmp/bg_process.pid)"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check 1: PID file exists (3 points)
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="pid_file_exists",
                passed=True,
                points=3,
                message=f"PID file exists"
            ))
            total_points += 3

            # Check 2: PID is valid and process running (5 points)
            try:
                with open(self.output_file, 'r') as f:
                    pid = f.read().strip()
                    if pid.isdigit():
                        result = execute_safe(['ps', '-p', pid])
                        if result.success and pid in result.stdout:
                            checks.append(ValidationCheck(
                                name="process_running",
                                passed=True,
                                points=5,
                                message=f"Process {pid} is running"
                            ))
                            total_points += 5
                        else:
                            checks.append(ValidationCheck(
                                name="process_running",
                                passed=False,
                                points=0,
                                max_points=5,
                                message=f"Process {pid} is not running"
                            ))
                    else:
                        checks.append(ValidationCheck(
                            name="process_running",
                            passed=False,
                            points=0,
                            max_points=5,
                            message=f"Invalid PID in file"
                        ))
            except Exception:
                checks.append(ValidationCheck(
                    name="process_running",
                    passed=False,
                    points=0,
                    max_points=5,
                    message=f"Could not read PID file"
                ))
        else:
            checks.append(ValidationCheck(
                name="pid_file_exists",
                passed=False,
                points=0,
                max_points=3,
                message=f"PID file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)


@TaskRegistry.register("processes")
class FindResourceHogTask(BaseTask):
    """Find processes using the most resources."""

    def __init__(self):
        super().__init__(
            id="process_resource_001",
            category="processes",
            difficulty="medium",
            points=8
        )
        self.resource_type = None
        self.output_file = None

    def generate(self, **params):
        self.resource_type = params.get('resource', random.choice(['cpu', 'memory']))
        self.output_file = params.get('output', f'/tmp/top_{self.resource_type}.txt')

        if self.resource_type == 'cpu':
            sort_key = 'CPU usage'
            ps_sort = '-pcpu'
        else:
            sort_key = 'memory usage'
            ps_sort = '-pmem'

        self.description = (
            f"Find top processes by {self.resource_type}:\n"
            f"  - List top 10 processes by {sort_key}\n"
            f"  - Save the output to: {self.output_file}\n"
            f"  - Include PID, user, and command"
        )

        self.hints = [
            f"Using ps: ps aux --sort={ps_sort} | head -11 > {self.output_file}",
            "Or use top in batch mode: top -b -n 1 | head -20",
            f"ps columns: -o pid,user,%cpu,%mem,comm",
            "Sort by CPU: --sort=-%cpu, by memory: --sort=-%mem"
        ]

        return self

    def validate(self):
        checks = []
        total_points = 0

        # Check: Output file exists and has content
        if validate_file_exists(self.output_file):
            checks.append(ValidationCheck(
                name="output_exists",
                passed=True,
                points=4,
                message=f"Output file exists"
            ))
            total_points += 4

            try:
                with open(self.output_file, 'r') as f:
                    content = f.read()
                    lines = content.strip().split('\n')
                    if len(lines) >= 5:  # At least header + some processes
                        checks.append(ValidationCheck(
                            name="has_processes",
                            passed=True,
                            points=4,
                            message=f"File contains process list ({len(lines)} lines)"
                        ))
                        total_points += 4
                    else:
                        checks.append(ValidationCheck(
                            name="has_processes",
                            passed=False,
                            points=0,
                            max_points=4,
                            message=f"File has insufficient content"
                        ))
            except Exception:
                checks.append(ValidationCheck(
                    name="has_processes",
                    passed=False,
                    points=0,
                    max_points=4,
                    message=f"Could not read file"
                ))
        else:
            checks.append(ValidationCheck(
                name="output_exists",
                passed=False,
                points=0,
                max_points=4,
                message=f"Output file not found"
            ))

        passed = total_points >= (self.points * 0.6)
        return ValidationResult(self.id, passed, total_points, self.points, checks)
