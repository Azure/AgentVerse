"""MAF workflow that routes uploaded local files through Foundry prompt agents."""

from __future__ import annotations

from agent_framework import Case, Default, Executor, WorkflowBuilder, WorkflowContext, handler
from typing_extensions import Never

from agentverse.contracts import DocumentContext, DocumentTriageRequest, TriageResult
from agentverse.formatter import format_triage_result
from agentverse.foundry_service import FoundryTriageService


class FoundryIntakeExecutor(Executor):
    def __init__(self) -> None:
        super().__init__(id="content_understanding_intake_agent")
        self._service = FoundryTriageService()

    @handler
    async def handle_request(self, request: DocumentTriageRequest, ctx: WorkflowContext[DocumentContext]) -> None:
        await ctx.send_message(self._service.intake(request))


class FoundrySpecialistExecutor(Executor):
    def __init__(self, route: str) -> None:
        super().__init__(id=f"foundry_{route}_agent")
        self._route = route
        self._service = FoundryTriageService()

    @handler
    async def handle_context(self, context: DocumentContext, ctx: WorkflowContext[TriageResult]) -> None:
        if context.route != self._route and self._route != "manual_review":
            raise RuntimeError(f"{self.id} received unexpected route {context.route}")
        await ctx.send_message(self._service.recommend(context))


class FoundryFinalizerExecutor(Executor):
    def __init__(self) -> None:
        super().__init__(id="foundry_human_review_summary")

    @handler
    async def handle_result(self, result: TriageResult, ctx: WorkflowContext[Never, str]) -> None:
        await ctx.yield_output(format_triage_result(result))


def route_is(expected_route: str):
    def condition(message: object) -> bool:
        return isinstance(message, DocumentContext) and message.route == expected_route

    return condition


intake = FoundryIntakeExecutor()
financial = FoundrySpecialistExecutor("financial")
medical = FoundrySpecialistExecutor("medical")
supply = FoundrySpecialistExecutor("supply")
manual_review = FoundrySpecialistExecutor("manual_review")
finalizer = FoundryFinalizerExecutor()

workflow = (
    WorkflowBuilder(
        name="Foundry Upload Triage Workflow",
        description="Upload-driven document triage workflow using Content Understanding and Foundry prompt agents.",
        start_executor=intake,
    )
    .add_switch_case_edge_group(
        intake,
        [
            Case(condition=route_is("financial"), target=financial),
            Case(condition=route_is("medical"), target=medical),
            Case(condition=route_is("supply"), target=supply),
            Default(target=manual_review),
        ],
    )
    .add_edge(financial, finalizer)
    .add_edge(medical, finalizer)
    .add_edge(supply, finalizer)
    .add_edge(manual_review, finalizer)
    .build()
)
