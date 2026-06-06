# Churned Customer snapshot

Finance and Customer Success produce different churn populations, while shared and ambiguous authority requires a governed refusal.

This artifact contains synthetic data only. The fenced JSON is generated from `LocalProvider` and validates as `ReplayScenarioSnapshot`.

```json
{
  "scenario_id": "churned-customer",
  "term": "Churned Customer",
  "data_classification": "synthetic",
  "concept": {
    "concept_id": "churned_customer",
    "canonical_name": "Churned Customer",
    "description": "A customer treated as lost for retention and financial reporting.",
    "aliases": [
      "churn",
      "churned customers",
      "lost customer"
    ],
    "definition_ids": [
      "churned_customer_finance",
      "churned_customer_customer_success"
    ]
  },
  "bindings": [
    {
      "binding_id": "churned_customer_finance_v1",
      "definition_id": "churned_customer_finance",
      "concept_id": "churned_customer",
      "name": "Finance Churned Customer",
      "owner": "Finance",
      "rule_text": "Customer whose contract term ended without renewal by the reporting date.",
      "semantic_dimensions": [
        "churn-effective-date",
        "contract-renewal"
      ],
      "source_tables": [
        "customers",
        "churn_events"
      ],
      "entity_key": "customer_id",
      "grain": "customer",
      "population": "Customers with a recorded Finance churn date on or before period end.",
      "time_window_days": null,
      "filters": [
        "finance_churn_date is populated",
        "finance_churn_date <= period end"
      ],
      "exclusions": [],
      "sql_template": "SELECT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN churn_events ce ON ce.customer_id = c.customer_id WHERE TRY_CAST(ce.finance_churn_date AS DATE) IS NOT NULL AND TRY_CAST(ce.finance_churn_date AS DATE) <= DATE '{period_end}' ORDER BY entity_id"
    },
    {
      "binding_id": "churned_customer_customer_success_v1",
      "definition_id": "churned_customer_customer_success",
      "concept_id": "churned_customer",
      "name": "Customer Success Churned Customer",
      "owner": "Customer Success",
      "rule_text": "Customer whose inactivity threshold and operational grace period elapsed by the reporting date.",
      "semantic_dimensions": [
        "churn-effective-date",
        "inactivity-threshold",
        "grace-period"
      ],
      "source_tables": [
        "customers",
        "churn_events"
      ],
      "entity_key": "customer_id",
      "grain": "customer",
      "population": "Customers with a recorded Customer Success churn date on or before period end.",
      "time_window_days": null,
      "filters": [
        "cs_churn_date is populated",
        "cs_churn_date <= period end"
      ],
      "exclusions": [],
      "sql_template": "SELECT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN churn_events ce ON ce.customer_id = c.customer_id WHERE TRY_CAST(ce.cs_churn_date AS DATE) IS NOT NULL AND TRY_CAST(ce.cs_churn_date AS DATE) <= DATE '{period_end}' ORDER BY entity_id"
    }
  ],
  "evaluations": [
    {
      "binding_id": "churned_customer_finance_v1",
      "definition_id": "churned_customer_finance",
      "concept_id": "churned_customer",
      "period": {
        "start_date": "2026-03-04",
        "end_date": "2026-06-01"
      },
      "entity_ids": [
        "C0006",
        "C0012",
        "C0018",
        "C0024",
        "C0030",
        "C0036",
        "C0042",
        "C0048",
        "C0054",
        "C0060",
        "C0066",
        "C0072",
        "C0078",
        "C0084",
        "C0090",
        "C0096",
        "C0102",
        "C0108",
        "C0114",
        "C0120"
      ],
      "rows": [
        {
          "entity_id": "C0006",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0012",
          "metric_value": 226000.0
        },
        {
          "entity_id": "C0018",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0024",
          "metric_value": 176000.0
        },
        {
          "entity_id": "C0030",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0036",
          "metric_value": 92000.0
        },
        {
          "entity_id": "C0042",
          "metric_value": 61000.0
        },
        {
          "entity_id": "C0048",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C0054",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0060",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C0066",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0072",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C0078",
          "metric_value": 41000.0
        },
        {
          "entity_id": "C0084",
          "metric_value": 128000.0
        },
        {
          "entity_id": "C0090",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0096",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0102",
          "metric_value": 135000.0
        },
        {
          "entity_id": "C0108",
          "metric_value": 168000.0
        },
        {
          "entity_id": "C0114",
          "metric_value": 25000.0
        },
        {
          "entity_id": "C0120",
          "metric_value": 171000.0
        }
      ],
      "entity_count": 20,
      "metric_total": 2559000.0,
      "executed_sql": "SELECT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN churn_events ce ON ce.customer_id = c.customer_id WHERE TRY_CAST(ce.finance_churn_date AS DATE) IS NOT NULL AND TRY_CAST(ce.finance_churn_date AS DATE) <= DATE '2026-06-01' ORDER BY entity_id"
    },
    {
      "binding_id": "churned_customer_customer_success_v1",
      "definition_id": "churned_customer_customer_success",
      "concept_id": "churned_customer",
      "period": {
        "start_date": "2026-03-04",
        "end_date": "2026-06-01"
      },
      "entity_ids": [
        "C0003",
        "C0006",
        "C0009",
        "C0012",
        "C0015",
        "C0018",
        "C0021",
        "C0024",
        "C0027",
        "C0030",
        "C0033",
        "C0036",
        "C0039",
        "C0042",
        "C0045",
        "C0048",
        "C0051",
        "C0054",
        "C0057",
        "C0060",
        "C0063",
        "C0066",
        "C0069",
        "C0072",
        "C0075",
        "C0078",
        "C0081",
        "C0084",
        "C0087",
        "C0090",
        "C0093",
        "C0096",
        "C0099",
        "C0102",
        "C0105",
        "C0108",
        "C0111",
        "C0114",
        "C0117",
        "C0120"
      ],
      "rows": [
        {
          "entity_id": "C0003",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0006",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0009",
          "metric_value": 240000.0
        },
        {
          "entity_id": "C0012",
          "metric_value": 226000.0
        },
        {
          "entity_id": "C0015",
          "metric_value": 81000.0
        },
        {
          "entity_id": "C0018",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0021",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C0024",
          "metric_value": 176000.0
        },
        {
          "entity_id": "C0027",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C0030",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0033",
          "metric_value": 119000.0
        },
        {
          "entity_id": "C0036",
          "metric_value": 92000.0
        },
        {
          "entity_id": "C0039",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0042",
          "metric_value": 61000.0
        },
        {
          "entity_id": "C0045",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0048",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C0051",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C0054",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0057",
          "metric_value": 53000.0
        },
        {
          "entity_id": "C0060",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C0063",
          "metric_value": 235000.0
        },
        {
          "entity_id": "C0066",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0069",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C0072",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C0075",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C0078",
          "metric_value": 41000.0
        },
        {
          "entity_id": "C0081",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C0084",
          "metric_value": 128000.0
        },
        {
          "entity_id": "C0087",
          "metric_value": 100000.0
        },
        {
          "entity_id": "C0090",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0093",
          "metric_value": 52000.0
        },
        {
          "entity_id": "C0096",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0099",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C0102",
          "metric_value": 135000.0
        },
        {
          "entity_id": "C0105",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0108",
          "metric_value": 168000.0
        },
        {
          "entity_id": "C0111",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0114",
          "metric_value": 25000.0
        },
        {
          "entity_id": "C0117",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0120",
          "metric_value": 171000.0
        }
      ],
      "entity_count": 40,
      "metric_total": 5491000.0,
      "executed_sql": "SELECT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN churn_events ce ON ce.customer_id = c.customer_id WHERE TRY_CAST(ce.cs_churn_date AS DATE) IS NOT NULL AND TRY_CAST(ce.cs_churn_date AS DATE) <= DATE '2026-06-01' ORDER BY entity_id"
    }
  ],
  "subgraph": {
    "concept_id": "churned_customer",
    "nodes": [
      {
        "node_id": "churned_customer",
        "node_type": "business_concept",
        "label": "Churned Customer",
        "properties": {}
      },
      {
        "node_id": "contract",
        "node_type": "entity_type",
        "label": "Contract",
        "properties": {}
      },
      {
        "node_id": "usage_event",
        "node_type": "entity_type",
        "label": "Usage Event",
        "properties": {}
      },
      {
        "node_id": "churn_event",
        "node_type": "entity_type",
        "label": "Churn Event",
        "properties": {}
      }
    ],
    "relationships": [
      {
        "source": "churned_customer",
        "target": "contract",
        "relationship_type": "derived_from"
      },
      {
        "source": "churned_customer",
        "target": "usage_event",
        "relationship_type": "derived_from"
      },
      {
        "source": "churned_customer",
        "target": "churn_event",
        "relationship_type": "materialized_as"
      }
    ]
  },
  "authority_rules": [
    {
      "concept_id": "churned_customer",
      "semantic_dimension": "churn-effective-date",
      "status": "shared",
      "owner": null,
      "rationale": "Finance and Customer Success use the date for different governed processes."
    },
    {
      "concept_id": "churned_customer",
      "semantic_dimension": "grace-period",
      "status": "ambiguous",
      "owner": null,
      "rationale": "No approved enterprise owner or precedence rule exists."
    }
  ]
}
```
