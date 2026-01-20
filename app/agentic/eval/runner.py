"""
Evaluation Runner for TDAD (Test-Driven Agent Development)

Executes golden dataset test cases against an agent and collects results.
Supports parallel execution, cost tracking, and detailed reporting.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import UUID

from app.agentic.eval.golden_dataset import GoldenTestCase, GOLDEN_DATASET, load_golden_dataset

logger = logging.getLogger(__name__)


@dataclass
class EvalConfig:
    """Configuration for an evaluation run."""
    agent_id: UUID
    tenant_id: UUID
    categories: list[str] = field(default_factory=list)  # Empty = all
    difficulties: list[str] = field(default_factory=list)  # Empty = all
    max_parallel: int = 5
    timeout_per_case_seconds: int = 60
    stop_on_failure: bool = False
    mock_mode: bool = False  # Use mock responses for testing


@dataclass
class TestCaseResult:
    """Result of running a single test case."""
    test_case_id: str
    passed: bool
    actual_tools: list[str] = field(default_factory=list)
    actual_output: Optional[str] = None
    steps_used: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    error: Optional[str] = None
    failure_reason: Optional[str] = None
    tool_calls_log: list[dict] = field(default_factory=list)


@dataclass
class EvalRunResult:
    """Aggregated results of an evaluation run."""
    eval_id: UUID
    agent_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    results: list[TestCaseResult] = field(default_factory=list)
    error: Optional[str] = None


class EvalRunner:
    """
    Runs evaluation test cases against an agent.

    Example usage:
        runner = EvalRunner(agent_executor_fn)
        result = await runner.run(EvalConfig(
            agent_id=agent_id,
            tenant_id=tenant_id,
            categories=["dcl", "aam"]
        ))
    """

    def __init__(
        self,
        agent_executor: Callable[[str, UUID, UUID], Any],
        on_progress: Optional[Callable[[int, int, TestCaseResult], None]] = None
    ):
        """
        Initialize the eval runner.

        Args:
            agent_executor: Async function that executes an agent query.
                            Signature: (input: str, agent_id: UUID, tenant_id: UUID) -> AgentRunResult
            on_progress: Optional callback for progress updates (current, total, result)
        """
        self.agent_executor = agent_executor
        self.on_progress = on_progress

    async def run(self, config: EvalConfig) -> EvalRunResult:
        """
        Run the evaluation against the golden dataset.

        Args:
            config: Evaluation configuration

        Returns:
            EvalRunResult with all test case outcomes
        """
        import uuid

        # Load test cases based on config
        test_cases = load_golden_dataset(
            categories=config.categories if config.categories else None,
            difficulties=config.difficulties if config.difficulties else None
        )

        result = EvalRunResult(
            eval_id=uuid.uuid4(),
            agent_id=config.agent_id,
            started_at=datetime.utcnow(),
            total_cases=len(test_cases)
        )

        logger.info(f"Starting eval run {result.eval_id} with {len(test_cases)} test cases")

        try:
            if config.mock_mode:
                # Run in mock mode for testing the framework
                results = await self._run_mock(test_cases, config)
            else:
                # Run actual evaluation
                results = await self._run_parallel(test_cases, config)

            result.results = results
            result.passed_cases = sum(1 for r in results if r.passed)
            result.failed_cases = sum(1 for r in results if not r.passed and not r.error)
            result.skipped_cases = sum(1 for r in results if r.error)
            result.pass_rate = result.passed_cases / len(results) if results else 0.0
            result.total_cost_usd = sum(r.cost_usd for r in results)
            result.total_duration_ms = sum(r.duration_ms for r in results)
            result.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Eval run failed: {e}")
            result.error = str(e)
            result.completed_at = datetime.utcnow()

        return result

    async def _run_parallel(
        self,
        test_cases: list[GoldenTestCase],
        config: EvalConfig
    ) -> list[TestCaseResult]:
        """Run test cases with bounded parallelism."""
        semaphore = asyncio.Semaphore(config.max_parallel)
        results = []
        failed = False

        async def run_with_semaphore(tc: GoldenTestCase, index: int) -> TestCaseResult:
            nonlocal failed
            if failed and config.stop_on_failure:
                return TestCaseResult(
                    test_case_id=tc.id,
                    passed=False,
                    error="Skipped due to previous failure"
                )

            async with semaphore:
                result = await self._run_single_case(tc, config)

                if not result.passed and config.stop_on_failure:
                    failed = True

                if self.on_progress:
                    self.on_progress(index + 1, len(test_cases), result)

                return result

        tasks = [run_with_semaphore(tc, i) for i, tc in enumerate(test_cases)]
        results = await asyncio.gather(*tasks)

        return results

    async def _run_single_case(
        self,
        test_case: GoldenTestCase,
        config: EvalConfig
    ) -> TestCaseResult:
        """Run a single test case and evaluate the result."""
        start_time = time.monotonic()

        try:
            # Execute the agent with timeout
            run_result = await asyncio.wait_for(
                self.agent_executor(
                    test_case.input,
                    config.agent_id,
                    config.tenant_id
                ),
                timeout=config.timeout_per_case_seconds
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            # Extract results from agent run
            actual_tools = self._extract_tools(run_result)
            actual_output = self._extract_output(run_result)
            cost_usd = self._extract_cost(run_result)
            steps_used = self._extract_steps(run_result)

            # Evaluate against expected outcomes
            passed, failure_reason = self._evaluate_result(
                test_case, actual_tools, actual_output, cost_usd, steps_used
            )

            return TestCaseResult(
                test_case_id=test_case.id,
                passed=passed,
                actual_tools=actual_tools,
                actual_output=actual_output,
                steps_used=steps_used,
                cost_usd=cost_usd,
                duration_ms=duration_ms,
                failure_reason=failure_reason,
                tool_calls_log=self._extract_tool_log(run_result)
            )

        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return TestCaseResult(
                test_case_id=test_case.id,
                passed=False,
                duration_ms=duration_ms,
                error=f"Timeout after {config.timeout_per_case_seconds}s"
            )
        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return TestCaseResult(
                test_case_id=test_case.id,
                passed=False,
                duration_ms=duration_ms,
                error=str(e)
            )

    async def _run_mock(
        self,
        test_cases: list[GoldenTestCase],
        config: EvalConfig
    ) -> list[TestCaseResult]:
        """Run in mock mode for testing the framework."""
        results = []

        for i, tc in enumerate(test_cases):
            # Simulate some work
            await asyncio.sleep(0.01)

            # Mock result based on difficulty (easy passes, others random)
            import random
            if tc.difficulty == "easy":
                passed = True
            elif tc.difficulty == "medium":
                passed = random.random() > 0.3
            else:
                passed = random.random() > 0.5

            result = TestCaseResult(
                test_case_id=tc.id,
                passed=passed,
                actual_tools=tc.expected_tools if passed else [],
                actual_output=f"Mock output for {tc.id}",
                steps_used=random.randint(1, tc.max_steps),
                cost_usd=random.uniform(0.01, tc.max_cost_usd),
                duration_ms=random.randint(100, 5000),
                failure_reason=None if passed else "Mock failure"
            )
            results.append(result)

            if self.on_progress:
                self.on_progress(i + 1, len(test_cases), result)

        return results

    def _evaluate_result(
        self,
        test_case: GoldenTestCase,
        actual_tools: list[str],
        actual_output: Optional[str],
        cost_usd: float,
        steps_used: int
    ) -> tuple[bool, Optional[str]]:
        """
        Evaluate whether a test case passed.

        Returns:
            Tuple of (passed, failure_reason)
        """
        # Check forbidden tools
        for forbidden in test_case.forbidden_tools:
            if forbidden in actual_tools:
                return False, f"Used forbidden tool: {forbidden}"

        # Check expected tools (at least one must be present, or all if specified)
        if test_case.expected_tools:
            if not any(tool in actual_tools for tool in test_case.expected_tools):
                return False, f"Expected tools not called: {test_case.expected_tools}"

        # Check expected output patterns
        if test_case.expected_output_contains and actual_output:
            output_lower = actual_output.lower()
            for pattern in test_case.expected_output_contains:
                if pattern.lower() not in output_lower:
                    return False, f"Expected output to contain: {pattern}"

        # Check step limit
        if steps_used > test_case.max_steps:
            return False, f"Exceeded max steps: {steps_used} > {test_case.max_steps}"

        # Check cost limit
        if cost_usd > test_case.max_cost_usd:
            return False, f"Exceeded cost limit: ${cost_usd:.2f} > ${test_case.max_cost_usd:.2f}"

        return True, None

    def _extract_tools(self, run_result: Any) -> list[str]:
        """Extract tool names from agent run result."""
        if hasattr(run_result, 'tool_calls'):
            return [tc.get('name', '') for tc in run_result.tool_calls]
        if isinstance(run_result, dict):
            return [tc.get('name', '') for tc in run_result.get('tool_calls', [])]
        return []

    def _extract_output(self, run_result: Any) -> Optional[str]:
        """Extract output text from agent run result."""
        if hasattr(run_result, 'output'):
            return str(run_result.output)
        if isinstance(run_result, dict):
            return str(run_result.get('output', ''))
        return None

    def _extract_cost(self, run_result: Any) -> float:
        """Extract cost from agent run result."""
        if hasattr(run_result, 'cost_usd'):
            return float(run_result.cost_usd)
        if isinstance(run_result, dict):
            return float(run_result.get('cost_usd', 0.0))
        return 0.0

    def _extract_steps(self, run_result: Any) -> int:
        """Extract step count from agent run result."""
        if hasattr(run_result, 'steps_executed'):
            return int(run_result.steps_executed)
        if isinstance(run_result, dict):
            return int(run_result.get('steps_executed', 0))
        return 0

    def _extract_tool_log(self, run_result: Any) -> list[dict]:
        """Extract detailed tool call log from agent run result."""
        if hasattr(run_result, 'tool_calls_log'):
            return run_result.tool_calls_log
        if isinstance(run_result, dict):
            return run_result.get('tool_calls_log', [])
        return []


def create_eval_report(result: EvalRunResult) -> str:
    """
    Generate a human-readable evaluation report.

    Args:
        result: EvalRunResult from a completed evaluation run

    Returns:
        Formatted report string
    """
    lines = [
        "=" * 60,
        "TDAD EVALUATION REPORT",
        "=" * 60,
        f"Eval ID: {result.eval_id}",
        f"Agent ID: {result.agent_id}",
        f"Started: {result.started_at.isoformat()}",
        f"Completed: {result.completed_at.isoformat() if result.completed_at else 'N/A'}",
        "",
        "SUMMARY",
        "-" * 40,
        f"Total Cases: {result.total_cases}",
        f"Passed: {result.passed_cases}",
        f"Failed: {result.failed_cases}",
        f"Skipped: {result.skipped_cases}",
        f"Pass Rate: {result.pass_rate:.1%}",
        f"Total Cost: ${result.total_cost_usd:.2f}",
        f"Total Duration: {result.total_duration_ms}ms",
        "",
    ]

    # Group results by category
    by_category: dict[str, list[TestCaseResult]] = {}
    for r in result.results:
        # Extract category from test_case_id (format: "category-XXX")
        category = r.test_case_id.split("-")[0]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(r)

    for category, results in by_category.items():
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        lines.append(f"{category.upper()}: {passed}/{total} passed")

    lines.append("")
    lines.append("FAILURES")
    lines.append("-" * 40)

    failures = [r for r in result.results if not r.passed]
    if not failures:
        lines.append("No failures!")
    else:
        for f in failures:
            lines.append(f"  {f.test_case_id}: {f.failure_reason or f.error}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
