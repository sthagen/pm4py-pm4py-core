"""Builders for the reset/inhibitor example models."""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from pm4py.objects.petri_net.obj import Marking, PetriNet, ResetInhibitorNet
from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to


@dataclass(frozen=True)
class Scenario:
    slug: str
    title: str
    description: str
    activities: Dict[str, str]


SCENARIOS: List[Scenario] = [
    Scenario(
        "hospital_discharge",
        "Hospital discharge coordination",
        "A discharge may accumulate unresolved clinical discrepancies. "
        "Clearance resets all discrepancy tokens, while direct clearance is "
        "inhibited whenever one remains.",
        {
            "start": "Register Discharge Request",
            "check": "Review Clinical Readiness",
            "plan": "Prepare Discharge Plan",
            "issue": "Record Clinical Discrepancy",
            "reset": "Resolve All Discrepancies",
            "clean": "Confirm No Discrepancies",
            "authorize": "Authorize Discharge",
            "a1": "Reconcile Medication",
            "a2": "Counsel Patient",
            "b1": "Arrange Transport",
            "b2": "Notify Community Care",
            "join": "Assemble Discharge Package",
            "review": "Perform Final Safety Check",
            "revise": "Revise Discharge Package",
            "close": "Complete Discharge",
        },
    ),
    Scenario(
        "cyber_incident_response",
        "Cybersecurity incident response",
        "New threat indicators can accumulate during triage. Containment "
        "resets them, and recovery without containment is inhibited while "
        "any active indicator exists.",
        {
            "start": "Open Incident",
            "check": "Classify Severity",
            "plan": "Build Response Plan",
            "issue": "Detect Threat Indicator",
            "reset": "Contain All Indicators",
            "clean": "Confirm Clean Environment",
            "authorize": "Authorize Recovery",
            "a1": "Acquire Forensic Images",
            "a2": "Analyze Root Cause",
            "b1": "Restore Core Services",
            "b2": "Rotate Credentials",
            "join": "Reconcile Recovery Evidence",
            "review": "Run Security Validation",
            "revise": "Remediate Validation Finding",
            "close": "Close Incident",
        },
    ),
    Scenario(
        "insurance_claim",
        "Insurance claim adjudication",
        "Fraud or documentation flags can be raised during assessment. A "
        "special review resets all flags, while straight-through approval is "
        "inhibited until the flag place is empty.",
        {
            "start": "Register Claim",
            "check": "Validate Coverage",
            "plan": "Estimate Claim",
            "issue": "Raise Claim Flag",
            "reset": "Complete Special Investigation",
            "clean": "Confirm Flag-Free Claim",
            "authorize": "Authorize Adjudication",
            "a1": "Assess Liability",
            "a2": "Calculate Settlement",
            "b1": "Verify Supporting Evidence",
            "b2": "Contact Claimant",
            "join": "Consolidate Claim Decision",
            "review": "Review Settlement",
            "revise": "Revise Settlement",
            "close": "Issue Claim Decision",
        },
    ),
    Scenario(
        "manufacturing_batch",
        "Manufacturing batch release",
        "Inspection can add multiple defect tokens. Rework resets the whole "
        "defect queue, and clean release is inhibited as long as a defect "
        "token is present.",
        {
            "start": "Open Production Batch",
            "check": "Verify Material Lots",
            "plan": "Configure Production Run",
            "issue": "Record Batch Defect",
            "reset": "Rework Defective Batch",
            "clean": "Confirm Defect-Free Batch",
            "authorize": "Authorize Batch Release",
            "a1": "Package Finished Goods",
            "a2": "Label Shipping Units",
            "b1": "Compile Quality Records",
            "b2": "Approve Certificate",
            "join": "Reconcile Release Package",
            "review": "Audit Batch Release",
            "revise": "Correct Release Package",
            "close": "Release Production Batch",
        },
    ),
    Scenario(
        "loan_underwriting",
        "Loan underwriting",
        "Underwriting exceptions accumulate as tokens. Committee resolution "
        "resets every exception, and automatic approval is inhibited until "
        "no exception remains.",
        {
            "start": "Receive Loan Application",
            "check": "Validate Applicant Identity",
            "plan": "Prepare Credit Assessment",
            "issue": "Raise Underwriting Exception",
            "reset": "Resolve Exceptions in Committee",
            "clean": "Confirm Exception-Free File",
            "authorize": "Authorize Underwriting",
            "a1": "Analyze Credit History",
            "a2": "Calculate Affordability",
            "b1": "Appraise Collateral",
            "b2": "Verify Income",
            "join": "Consolidate Underwriting File",
            "review": "Perform Approval Review",
            "revise": "Revise Loan Conditions",
            "close": "Issue Lending Decision",
        },
    ),
    Scenario(
        "order_fulfillment",
        "Multi-channel order fulfillment",
        "Backorder tokens may build up during allocation. Substitution resets "
        "all backorders, while normal fulfillment is inhibited until there "
        "are none.",
        {
            "start": "Capture Customer Order",
            "check": "Validate Payment",
            "plan": "Plan Inventory Allocation",
            "issue": "Register Backordered Item",
            "reset": "Substitute All Backorders",
            "clean": "Confirm Full Allocation",
            "authorize": "Authorize Fulfillment",
            "a1": "Pick Order Items",
            "a2": "Pack Customer Order",
            "b1": "Book Carrier Capacity",
            "b2": "Prepare Customs Data",
            "join": "Consolidate Shipment",
            "review": "Inspect Shipment",
            "revise": "Repack Shipment",
            "close": "Dispatch Customer Order",
        },
    ),
    Scenario(
        "emergency_evacuation",
        "Emergency-site evacuation",
        "Hazard alerts can accumulate while coordinators assess the site. An "
        "all-clear sweep resets every alert; evacuation completion is "
        "inhibited while any alert remains active.",
        {
            "start": "Activate Emergency Plan",
            "check": "Assess Incident Zone",
            "plan": "Plan Evacuation Routes",
            "issue": "Report Active Hazard",
            "reset": "Clear All Reported Hazards",
            "clean": "Confirm Hazard-Free Routes",
            "authorize": "Authorize Evacuation",
            "a1": "Evacuate Primary Zone",
            "a2": "Sweep Primary Zone",
            "b1": "Evacuate Assisted Persons",
            "b2": "Account for Responders",
            "join": "Consolidate Headcount",
            "review": "Verify Site Clearance",
            "revise": "Repeat Clearance Sweep",
            "close": "Stand Down Emergency",
        },
    ),
]


def build_model(
    scenario: Scenario,
) -> Tuple[ResetInhibitorNet, Marking, Marking]:
    """Build a bounded workflow net containing functional reset/inhibitor arcs."""
    net = ResetInhibitorNet(scenario.title)
    place_names = (
        "source",
        "registered",
        "checked",
        "gate",
        "open_items",
        "authorized",
        "branch_a_start",
        "branch_a_middle",
        "branch_a_done",
        "branch_b_start",
        "branch_b_middle",
        "branch_b_done",
        "joined",
        "reviewed",
        "sink",
    )
    places = {
        name: ResetInhibitorNet.Place(name) for name in place_names
    }
    net.places.update(places.values())

    transitions = {
        key: ResetInhibitorNet.Transition(key, label)
        for key, label in scenario.activities.items()
    }
    net.transitions.update(transitions.values())

    def arc(source, target, arc_type=None):
        return add_arc_from_to(
            places[source] if source in places else transitions[source],
            places[target] if target in places else transitions[target],
            net,
            type=arc_type,
        )

    arc("source", "start")
    arc("start", "registered")
    arc("registered", "check")
    arc("check", "checked")
    arc("checked", "plan")
    arc("plan", "gate")

    # Recording an item keeps the case at the decision gate and adds a token.
    arc("gate", "issue")
    arc("issue", "gate")
    arc("issue", "open_items")

    # The exceptional route clears an arbitrary number of accumulated items.
    arc("gate", "reset")
    arc("open_items", "reset", "reset")
    arc("reset", "authorized")

    # Straight-through processing is possible only when the item place is empty.
    arc("gate", "clean")
    arc("open_items", "clean", "inhibitor")
    arc("clean", "authorized")

    # Authorization starts two independent work streams.
    arc("authorized", "authorize")
    arc("authorize", "branch_a_start")
    arc("authorize", "branch_b_start")
    arc("branch_a_start", "a1")
    arc("a1", "branch_a_middle")
    arc("branch_a_middle", "a2")
    arc("a2", "branch_a_done")
    arc("branch_b_start", "b1")
    arc("b1", "branch_b_middle")
    arc("branch_b_middle", "b2")
    arc("b2", "branch_b_done")

    arc("branch_a_done", "join")
    arc("branch_b_done", "join")
    arc("join", "joined")
    arc("joined", "review")
    arc("review", "reviewed")
    arc("reviewed", "revise")
    arc("revise", "reviewed")
    arc("reviewed", "close")
    arc("close", "sink")

    return (
        net,
        Marking({places["source"]: 1}),
        Marking({places["sink"]: 1}),
    )


def scenario_by_slug(slug: str) -> Scenario:
    """Return a scenario by its artifact stem."""
    return next(item for item in SCENARIOS if item.slug == slug)

