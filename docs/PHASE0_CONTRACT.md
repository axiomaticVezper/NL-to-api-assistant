# Phase 0 Contract — NL to API Assistant

## 1. Domain + Endpoints

Mock SaaS admin platform: customers, subscriptions, invoices, teams.

| Endpoint | Method | Risk tier |
|---|---|---|
| GET /customers/{id} | read | read_only |
| GET /customers/search?email= | read | read_only |
| GET /subscriptions/{customer_id} | read | read_only |
| GET /invoices/{customer_id} | read | read_only |
| GET /teams/{id}/members | read | read_only |
| POST /tickets | create support ticket | low_risk_write |
| PATCH /subscriptions/{id}/plan | change plan | low_risk_write |
| POST /teams/{id}/members | add team member | low_risk_write |
| DELETE /teams/{id}/members/{user_id} | remove team member | low_risk_write |
| POST /subscriptions/{id}/cancel | cancel subscription | high_risk_write |
| POST /invoices/{id}/refund | issue refund | high_risk_write |
| POST /invoices/{id}/refund/reverse | reverse refund (compensating action) | critical_write |
| DELETE /customers/{id} | delete customer | critical_write |

## 2. Roles

| Role | Can request |
|---|---|
| viewer | read_only |
| agent | read_only, low_risk_write, high_risk_write (cannot self-approve — routes to approval queue) |
| approver | read_only, low_risk_write, high_risk_write (+ can approve others' high_risk_write requests) |
| admin | read_only, low_risk_write, high_risk_write, critical_write |

Note: `agent` can *request* high_risk_write actions but cannot self-approve — these route to the approval queue.