REQUIREMENT_ITEM_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "RequirementItem",
    "type": "object",
    "required": [
        "req_id",
        "title",
        "source",
        "feature",
        "rat_scope",
        "preconditions",
        "expected",
        "acceptance",
        "observability",
        "priority",
    ],
    "properties": {
        "req_id": {"type": "string"},
        "title": {"type": "string"},
        "source": {
            "type": "object",
            "required": ["type", "doc_id"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "PRD",
                        "3GPP",
                        "GSMA",
                        "GCF",
                        "PTCRB",
                        "OPERATOR",
                        "INTERNAL_SPEC",
                        "BUG_LESSON",
                    ],
                },
                "doc_id": {"type": "string"},
                "section": {"type": "string"},
                "lang": {"type": "string", "enum": ["zh", "en", "mixed"]},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        },
        "feature": {"type": "string"},
        "rat_scope": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["2G", "3G", "4G", "5G", "IMS", "IRAT", "POWER", "RF", "ANDROID_STACK"],
            },
        },
        "preconditions": {"type": "array", "items": {"type": "string"}},
        "trigger": {"type": "array", "items": {"type": "string"}},
        "expected": {"type": "array", "items": {"type": "string"}},
        "acceptance": {
            "type": "object",
            "required": ["pass_fail"],
            "properties": {
                "pass_fail": {"type": "array", "items": {"type": "string"}},
                "kpi": {"type": "array", "items": {"type": "string"}},
            },
        },
        "constraints": {"type": "array", "items": {"type": "string"}},
        "observability": {
            "type": "object",
            "required": ["signals", "logs", "counters"],
            "properties": {
                "signals": {"type": "array", "items": {"type": "string"}},
                "logs": {"type": "array", "items": {"type": "string"}},
                "counters": {"type": "array", "items": {"type": "string"}},
                "must_capture": {"type": "array", "items": {"type": "string"}},
            },
        },
        "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
}

TEST_OBJECTIVE_REQUIRED_KEYS = [
    "objective_id",
    "linked_reqs",
    "goal",
    "success_criteria",
    "evidence",
    "priority",
]

TESTCASE_REQUIRED_KEYS = [
    "tc_id",
    "objective_id",
    "title",
    "tags",
    "preconditions",
    "steps",
    "expected",
    "pass_fail",
    "observability",
    "trace",
]

SCRIPTSPEC_REQUIRED_KEYS = [
    "script_id",
    "tc_id",
    "harness",
    "dependencies",
    "inputs",
    "actions_mapping",
    "artifacts",
    "timeouts",
]

DEFAULT_ACTION_VOCABULARY = [
    "SET_DEVICE_STATE",
    "SET_NETWORK_PROFILE",
    "TRIGGER_ATTACH",
    "TRIGGER_REGISTRATION",
    "TRIGGER_CALL",
    "MOVE_RF_CONDITION",
    "WAIT",
    "CHECK",
    "COLLECT_LOG",
]

DEFAULT_ASSERTION_VOCABULARY = [
    "ASSERT_SIP_REGISTER_200",
    "ASSERT_IMS_REGISTERED",
    "ASSERT_ATTACH_SUCCESS",
    "ASSERT_NO_RESTART_STORM",
]

DEFAULT_CAPABILITIES = {
    "harnesses": ["ANDROID_UIA", "PY_AT", "QXDM", "AMARISOFT_API"],
    "actions_supported": {
        "SET_DEVICE_STATE": ["adb", "uia"],
        "TRIGGER_REGISTRATION": ["at", "adb"],
        "CHECK": ["logcat_parser", "ims_api"],
        "COLLECT_LOG": ["diag", "qxdm"],
    },
}

REQUIREMENT_LIST_SCHEMA = {
    "type": "array",
    "items": REQUIREMENT_ITEM_SCHEMA,
}

PERSONA_REVIEW_SCHEMA = {
    "type": "object",
    "required": ["reviews"],
    "properties": {
        "reviews": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "req_id",
                    "issues",
                    "rewrite_suggestion",
                    "scores",
                    "must_observe",
                    "open_questions",
                ],
                "properties": {
                    "req_id": {"type": "string"},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "rewrite_suggestion": {"type": "string"},
                    "scores": {"type": "object"},
                    "must_observe": {"type": "array", "items": {"type": "string"}},
                    "open_questions": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}

SYNTHESIS_SCHEMA = {
    "type": "object",
    "required": ["final_requirements", "conflicts", "questions_to_ask", "assumptions"],
    "properties": {
        "final_requirements": REQUIREMENT_LIST_SCHEMA,
        "conflicts": {"type": "array", "items": {"type": "object"}},
        "questions_to_ask": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
}

TEST_DESIGN_SCHEMA = {
    "type": "object",
    "required": ["objectives", "coverage_matrices", "design_notes", "de_scoped"],
    "properties": {
        "objectives": {"type": "array", "items": {"type": "object"}},
        "coverage_matrices": {"type": "array", "items": {"type": "object"}},
        "design_notes": {"type": "array", "items": {"type": "string"}},
        "de_scoped": {"type": "array", "items": {"type": "string"}},
    },
}

TESTCASE_SCHEMA = {
    "type": "object",
    "required": ["testcases"],
    "properties": {"testcases": {"type": "array", "items": {"type": "object"}}},
}

SCRIPT_PLAN_SCHEMA = {
    "type": "object",
    "required": ["scripts", "gaps", "recommended_framework_extensions"],
    "properties": {
        "scripts": {"type": "array", "items": {"type": "object"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "recommended_framework_extensions": {"type": "array", "items": {"type": "string"}},
    },
}

INTEGRATED_MATRIX_SCHEMA = {
    "type": "object",
    "required": ["integrated_matrix"],
    "properties": {
        "integrated_matrix": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["req_id", "objective_id", "scenario", "key_configuration", "pass_criteria"],
                "properties": {
                    "row_id": {"type": "string"},
                    "req_id": {"type": "string"},
                    "objective_id": {"type": "string"},
                    "scenario": {"type": "string"},
                    "key_configuration": {"type": "object"},
                    "pass_criteria": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}
