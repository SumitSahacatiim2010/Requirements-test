# Product Requirements Document: Hot-Lead Fast Lane Routing

## 1. Executive Summary
**Purpose:** Intelligently distribute high-priority leads to the fastest-responding sales representatives based on configurable rules.
**Target Metric:** Reduce response time to under 2 minutes for high-priority leads (score >80).

## 2. Feature Configuration
To enable the Hot-Lead Fast Lane, the system must support the following configurations:
* **Hot Lead Threshold:** Composite lead score > 80.
* **SLA Target:** 2 minutes to first contact.
* **Eligible Reps:** SDRs with an active status, who are marked as available, and have a P95 response time of <10 minutes over the last 30 days.

## 3. Algorithm and Processing Logic
When a lead is scored and qualified, the routing engine must execute the following logic:
1. **Condition:** `IF lead.score > 80`
2. **Filter Candidates:** Query reps where `response_time_p95 < 10min AND status='Active' AND available=true`
3. **Sort Candidates:** Order the filtered list by `response_time_avg ASC` (fastest responders first).
4. **Assignment:** Assign the lead to the top rep in the sorted list.
5. **Notification:** Trigger a high-priority multi-channel alert (Phone call + SMS + In-app notification) to the assigned rep.
6. **SLA Tracking:** Start a 2-minute SLA countdown timer.
7. **Fallback:** `ELSE` (if no reps meet criteria or score <= 80), fallback to the standard round-robin routing policy.

## 4. Acceptance Criteria

**AC-LM-006-A: Hot lead assigned within 2 minutes**
* **Given** a lead is scored with `composite_score = 88` and qualified to "MQL"
* **When** the routing engine processes the lead
* **Then** the lead should be assigned to an available eligible SDR within 2 minutes
* **And** the SDR should receive high-priority notifications via In-App, Email, SMS, and Slack
* **And** the SLA timer should start a 2-min countdown

**AC-LM-006-B: Hot lead SLA breach triggers escalation**
* **Given** a hot lead was assigned at time T0
* **When** 5 minutes elapse (T0 + 5 min) and the SDR has not logged any activity
* **Then** an `SLABreached` event should be emitted
* **And** the Sales Manager should receive an alert stating the SLA was missed
* **And** the lead should be auto-reassigned to the next available SDR
* **And** the original SDR should be notified of the reassignment
