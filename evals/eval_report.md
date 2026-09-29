# Evaluation report

| Case | Task | Type | Pass | Score | Notes |
|---|---|---|---:|---:|---|
| triage-1 | Task 1 | rule | PASS | 1.000 | schema and citation check |
| triage-1 | Task 1 | retrieval_hit_rate | PASS | 1.000 | expected product document cloudsync.md |
| triage-1 | Task 1 | faithfulness | PASS | 0.950 | All claims in the answer are supported by the provided evidence, including the cause of ERR_CONNECTION_TIMEOUT, suggested troubleshooting steps, and UI navigation instructions. |
| triage-1 | Task 1 | answer relevancy | PASS | 0.900 | The answer directly addresses the sync outage and ERR_CONNECTION_TIMEOUT, matching the evidence which lists checking endpoint reachability, credentials, and forcing a sync. The suggested steps are supported by the provided support scenario, making the response highly relevant. |
| triage-1 | Task 1 | context precision | PASS | 0.900 | The retrieved evidence directly covers sync stoppage and ERR_CONNECTION_TIMEOUT, providing matching troubleshooting steps, so the context is highly precise for the ticket. |
| triage-2 | Task 1 | rule | PASS | 1.000 | schema and citation check |
| triage-2 | Task 1 | retrieval_hit_rate | PASS | 1.000 | expected product document analyticshub.md |
| triage-2 | Task 1 | faithfulness | PASS | 1.000 | All steps and recommendations in the answer are directly supported by the provided evidence; no unsupported claims were made. |
| triage-2 | Task 1 | answer relevancy | PASS | 0.950 | The answer directly addresses the dashboard timeout ticket and its steps match the evidence provided in the 'AnalyticsHub: Dashboard Timeout' section, demonstrating high relevancy. |
| triage-2 | Task 1 | context precision | FAIL | 0.400 | The evidence includes the specific Dashboard Timeout guide (relevant) and a related dashboard‑slow section, but also contains unrelated sections on exports, alerts, and general performance diagnostics, lowering context precision. |
| triage-3 | Task 1 | rule | PASS | 1.000 | schema and citation check |
| triage-3 | Task 1 | retrieval_hit_rate | PASS | 1.000 | expected product document securevault.md |
| triage-3 | Task 1 | faithfulness | PASS | 1.000 | All statements in the answer are directly supported by the provided evidence, including the meaning of GROUP_NOT_MAPPED and the step‑by‑step remediation instructions. |
| triage-3 | Task 1 | answer relevancy | PASS | 0.950 | The answer directly addresses the ticket about new users failing SSO with GROUP_NOT_MAPPED, offering the exact steps from the evidence to map the IDP group. It is on-topic and provides the required guidance. |
| triage-3 | Task 1 | context precision | PASS | 0.900 | Evidence includes the exact steps for GROUP_NOT_MAPPED error, directly supporting the answer; extra unrelated sections are present but do not reduce relevance significantly. |
| triage-4 | Task 1 | rule | PASS | 1.000 | schema and citation check |
| triage-4 | Task 1 | faithfulness | PASS | 1.000 | All claims in the answer are directly supported by the evidence provided. |
| triage-4 | Task 1 | answer relevancy | PASS | 0.950 | The answer directly addresses the likely ticket about seat count discrepancies, using the exact steps and explanations provided in the evidence. It is highly relevant to the issue. |
| triage-4 | Task 1 | context precision | PASS | 0.950 | The retrieved evidence directly covers seat definition, deactivation policy, and export steps, matching the answer content, so context precision is very high. |
| triage-5 | Task 1 | rule | PASS | 1.000 | schema and citation check |
| triage-5 | Task 1 | adversarial_clarification | PASS | 1.000 | ambiguous/empty ticket must elicit a clarifying question, not fabricated grounding |
| triage-6 | Task 1 | rule | PASS | 1.000 | schema and citation check |
| triage-6 | Task 1 | adversarial_clarification | PASS | 1.000 | ambiguous/empty ticket must elicit a clarifying question, not fabricated grounding |
| brief-1 | Task 2 | rule | PASS | 1.000 | schema, graceful missing-account, and quote-substring check |
| brief-1 | Task 2 | determinism | PASS | 1.000 | byte-identical model JSON |
| brief-1 | Task 2 | groundedness | PASS | 0.600 | The answer correctly reflects the account health status, escalation notes, performance issue in DataBridge Pro (198 EU‑West users), and inactive usage trend, all present in the evidence for ACC-3336. However, it incorrectly attributes a broken AnalyticsHub Data Sources issue (486 users) and a billing discrepancy on invoice #60685 to ACC-3336; those tickets belong to different accounts (ACC-6296 and ACC-8250). |
| brief-2 | Task 2 | rule | PASS | 1.000 | schema, graceful missing-account, and quote-substring check |
| brief-2 | Task 2 | determinism | PASS | 1.000 | byte-identical model JSON |
| brief-2 | Task 2 | groundedness | PASS | 0.950 | All statements in the answer are backed by the provided account data and ticket excerpts: health status, region, industry, plan tier, usage trend, seat count, and product adoption are present in the account record; performance degradation, sync failures, SSO issues, billing questions, and audit‑log failures are all documented in the ticket list. The recommendation is a logical inference, not an unsupported claim. |
| brief-3 | Task 2 | rule | PASS | 1.000 | schema, graceful missing-account, and quote-substring check |
| brief-3 | Task 2 | determinism | PASS | 1.000 | byte-identical model JSON |
| brief-3 | Task 2 | groundedness | PASS | 0.600 | The answer correctly reflects health status, NPS, usage trend, last login, seat counts, and tickets about SecureVault encryption data loss and audit‑log failures. However, it asserts an open upgrade request for this account and labels escalations as high‑severity without explicit evidence in the provided tickets, reducing groundedness. |
| brief-4 | Task 2 | rule | PASS | 1.000 | schema, graceful missing-account, and quote-substring check |
| brief-4 | Task 2 | determinism | PASS | 1.000 | byte-identical model JSON |
| brief-5 | Task 2 | rule | PASS | 1.000 | schema, graceful missing-account, and quote-substring check |
| brief-5 | Task 2 | determinism | PASS | 1.000 | byte-identical model JSON |
| brief-5 | Task 2 | groundedness | PASS | 0.900 | Answer is largely grounded in the provided account data: health status, escalation notes, usage trend, last login, open tickets, and primary contact details are all supported. The statement that the renewal date is "approaching" is not explicitly present in the evidence (renewal_date is redacted), so that claim lacks direct support. |

Passed **36 / 37** checks.
