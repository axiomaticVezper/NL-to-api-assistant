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