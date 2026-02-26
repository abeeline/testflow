import sys
from pathlib import Path

# Ensure project root is importable when running from cookbook subdirectory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pocketflow import AsyncFlow, AsyncParallelBatchFlow
from nodes import (
    AssembleResultNode,
    FinalizeTestCaseNode,
    HarnessMapperNode,
    IntakeNode,
    ReqParseNode,
    ScriptWriterNode,
    SynthesisNode,
    TestCaseBatchGenNode,
    TestCaseSupervisorNode,
    TestDesignSupervisorNode,
    TestDesignNode,
    TriPersonaReviewNode,
)


class TestCaseParallelFlow(AsyncParallelBatchFlow):
    async def prep_async(self, shared):
        integrated = shared.get("test_design_spec", {}).get("integrated_matrix", [])
        if not isinstance(integrated, list) or not integrated:
            integrated = []
        chunk_size = int(shared.get("testcase_chunk_size", 16))
        if chunk_size <= 0:
            chunk_size = 16
        chunks = [integrated[i : i + chunk_size] for i in range(0, len(integrated), chunk_size)]
        if not chunks:
            chunks = [[]]
        shared["_testcase_batches"] = {}
        return [
            {"batch_index": idx, "batch_total": len(chunks), "integrated_chunk": chunk}
            for idx, chunk in enumerate(chunks)
        ]


def create_system_test_flow() -> AsyncFlow:
    intake = IntakeNode()
    req_parse = ReqParseNode()
    tri = TriPersonaReviewNode()
    synth = SynthesisNode()
    design = TestDesignNode()
    design_sup = TestDesignSupervisorNode()
    cases_parallel = TestCaseParallelFlow(start=TestCaseBatchGenNode())
    cases_finalize = FinalizeTestCaseNode()
    case_sup = TestCaseSupervisorNode()
    mapper = HarnessMapperNode()
    writer = ScriptWriterNode()
    assemble = AssembleResultNode()

    intake >> req_parse >> tri >> synth >> design
    design >> design_sup
    design_sup - "retry" >> design
    design_sup >> cases_parallel >> cases_finalize >> case_sup
    case_sup - "retry" >> cases_parallel
    case_sup >> mapper >> writer >> assemble
    return AsyncFlow(start=intake)


def create_requirement_analysis_flow() -> AsyncFlow:
    intake = IntakeNode()
    req_parse = ReqParseNode()
    tri = TriPersonaReviewNode()
    synth = SynthesisNode()
    intake >> req_parse >> tri >> synth
    return AsyncFlow(start=intake)


def create_test_design_flow() -> AsyncFlow:
    design = TestDesignNode()
    sup = TestDesignSupervisorNode()
    design >> sup
    sup - "retry" >> design
    return AsyncFlow(start=design)


def create_test_case_flow() -> AsyncFlow:
    parallel = TestCaseParallelFlow(start=TestCaseBatchGenNode())
    finalize = FinalizeTestCaseNode()
    sup = TestCaseSupervisorNode()
    parallel >> finalize >> sup
    sup - "retry" >> parallel
    return AsyncFlow(start=parallel)


def create_script_flow() -> AsyncFlow:
    mapper = HarnessMapperNode()
    writer = ScriptWriterNode()
    mapper >> writer
    return AsyncFlow(start=mapper)
