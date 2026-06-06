# Net Revenue snapshot

Finance and Sales describe Net Revenue differently, but their executable definitions select the same synthetic entities and totals.

This artifact contains synthetic data only. The fenced JSON is generated from `LocalProvider` and validates as `ReplayScenarioSnapshot`.

```json
{
  "scenario_id": "net-revenue",
  "term": "Net Revenue",
  "data_classification": "synthetic",
  "concept": {
    "concept_id": "net_revenue",
    "canonical_name": "Net Revenue",
    "description": "Recognized recurring revenue in the selected analytical period.",
    "aliases": [
      "revenue",
      "booked revenue"
    ],
    "definition_ids": [
      "net_revenue_finance",
      "net_revenue_sales"
    ]
  },
  "bindings": [
    {
      "binding_id": "net_revenue_finance_v1",
      "definition_id": "net_revenue_finance",
      "concept_id": "net_revenue",
      "name": "Finance Net Revenue",
      "owner": "Finance",
      "rule_text": "Sum recognized recurring revenue events during the selected period.",
      "semantic_dimensions": [
        "revenue-recognition",
        "reporting-period"
      ],
      "source_tables": [
        "revenue_events"
      ],
      "entity_key": "customer_id",
      "grain": "customer",
      "population": "Customers with recognized recurring revenue in the period.",
      "time_window_days": null,
      "filters": [
        "event_type = recognized_revenue",
        "event_date in selected period"
      ],
      "exclusions": [],
      "sql_template": "SELECT r.customer_id AS entity_id, SUM(r.amount) AS metric_value FROM revenue_events r WHERE r.event_type = 'recognized_revenue' AND CAST(r.event_date AS DATE) BETWEEN DATE '{period_start}' AND DATE '{period_end}' GROUP BY r.customer_id ORDER BY entity_id"
    },
    {
      "binding_id": "net_revenue_sales_v1",
      "definition_id": "net_revenue_sales",
      "concept_id": "net_revenue",
      "name": "Sales Booked Revenue",
      "owner": "Sales",
      "rule_text": "Customer recurring revenue joined to the customer book for the selected period.",
      "semantic_dimensions": [
        "booked-revenue",
        "reporting-period"
      ],
      "source_tables": [
        "customers",
        "revenue_events"
      ],
      "entity_key": "customer_id",
      "grain": "customer",
      "population": "Customer book entries with recognized recurring revenue in the period.",
      "time_window_days": null,
      "filters": [
        "recognized revenue event in selected period"
      ],
      "exclusions": [],
      "sql_template": "SELECT c.customer_id AS entity_id, SUM(r.amount) AS metric_value FROM customers c INNER JOIN revenue_events r ON c.customer_id = r.customer_id AND r.event_type = 'recognized_revenue' WHERE CAST(r.event_date AS DATE) >= DATE '{period_start}' AND CAST(r.event_date AS DATE) <= DATE '{period_end}' GROUP BY c.customer_id ORDER BY entity_id"
    }
  ],
  "evaluations": [
    {
      "binding_id": "net_revenue_finance_v1",
      "definition_id": "net_revenue_finance",
      "concept_id": "net_revenue",
      "period": {
        "start_date": "2026-03-04",
        "end_date": "2026-06-01"
      },
      "entity_ids": [
        "C0001",
        "C0002",
        "C0003",
        "C0004",
        "C0006",
        "C0007",
        "C0008",
        "C0009",
        "C0011",
        "C0012",
        "C0013",
        "C0014",
        "C0016",
        "C0017",
        "C0018",
        "C0019",
        "C0021",
        "C0022",
        "C0023",
        "C0024",
        "C0026",
        "C0027",
        "C0028",
        "C0029",
        "C0031",
        "C0032",
        "C0033",
        "C0034",
        "C0036",
        "C0037",
        "C0038",
        "C0039",
        "C0041",
        "C0042",
        "C0043",
        "C0044",
        "C0046",
        "C0047",
        "C0048",
        "C0049",
        "C0051",
        "C0052",
        "C0053",
        "C0054",
        "C0056",
        "C0057",
        "C0058",
        "C0059",
        "C0061",
        "C0062",
        "C0063",
        "C0064",
        "C0066",
        "C0067",
        "C0068",
        "C0069",
        "C0071",
        "C0072",
        "C0073",
        "C0074",
        "C0076",
        "C0077",
        "C0078",
        "C0079",
        "C0081",
        "C0082",
        "C0083",
        "C0084",
        "C0086",
        "C0087",
        "C0088",
        "C0089",
        "C0091",
        "C0092",
        "C0093",
        "C0094",
        "C0096",
        "C0097",
        "C0098",
        "C0099",
        "C0101",
        "C0102",
        "C0103",
        "C0104",
        "C0106",
        "C0107",
        "C0108",
        "C0109",
        "C0111",
        "C0112",
        "C0113",
        "C0114",
        "C0116",
        "C0117",
        "C0118",
        "C0119"
      ],
      "rows": [
        {
          "entity_id": "C0001",
          "metric_value": 15250.0
        },
        {
          "entity_id": "C0002",
          "metric_value": 4666.67
        },
        {
          "entity_id": "C0003",
          "metric_value": 7166.67
        },
        {
          "entity_id": "C0004",
          "metric_value": 18250.0
        },
        {
          "entity_id": "C0006",
          "metric_value": 13916.67
        },
        {
          "entity_id": "C0007",
          "metric_value": 9916.67
        },
        {
          "entity_id": "C0008",
          "metric_value": 11250.0
        },
        {
          "entity_id": "C0009",
          "metric_value": 20000.0
        },
        {
          "entity_id": "C0011",
          "metric_value": 16083.33
        },
        {
          "entity_id": "C0012",
          "metric_value": 18833.33
        },
        {
          "entity_id": "C0013",
          "metric_value": 5583.33
        },
        {
          "entity_id": "C0014",
          "metric_value": 5000.0
        },
        {
          "entity_id": "C0016",
          "metric_value": 16083.33
        },
        {
          "entity_id": "C0017",
          "metric_value": 11500.0
        },
        {
          "entity_id": "C0018",
          "metric_value": 5000.0
        },
        {
          "entity_id": "C0019",
          "metric_value": 15166.67
        },
        {
          "entity_id": "C0021",
          "metric_value": 18083.33
        },
        {
          "entity_id": "C0022",
          "metric_value": 16416.67
        },
        {
          "entity_id": "C0023",
          "metric_value": 14166.67
        },
        {
          "entity_id": "C0024",
          "metric_value": 14666.67
        },
        {
          "entity_id": "C0026",
          "metric_value": 10333.33
        },
        {
          "entity_id": "C0027",
          "metric_value": 2416.67
        },
        {
          "entity_id": "C0028",
          "metric_value": 18583.33
        },
        {
          "entity_id": "C0029",
          "metric_value": 19416.67
        },
        {
          "entity_id": "C0031",
          "metric_value": 16916.67
        },
        {
          "entity_id": "C0032",
          "metric_value": 11916.67
        },
        {
          "entity_id": "C0033",
          "metric_value": 9916.67
        },
        {
          "entity_id": "C0034",
          "metric_value": 13833.33
        },
        {
          "entity_id": "C0036",
          "metric_value": 7666.67
        },
        {
          "entity_id": "C0037",
          "metric_value": 13916.67
        },
        {
          "entity_id": "C0038",
          "metric_value": 18916.67
        },
        {
          "entity_id": "C0039",
          "metric_value": 15250.0
        },
        {
          "entity_id": "C0041",
          "metric_value": 13916.67
        },
        {
          "entity_id": "C0042",
          "metric_value": 5083.33
        },
        {
          "entity_id": "C0043",
          "metric_value": 9416.67
        },
        {
          "entity_id": "C0044",
          "metric_value": 10000.0
        },
        {
          "entity_id": "C0046",
          "metric_value": 11750.0
        },
        {
          "entity_id": "C0047",
          "metric_value": 2583.33
        },
        {
          "entity_id": "C0048",
          "metric_value": 9083.33
        },
        {
          "entity_id": "C0049",
          "metric_value": 17666.67
        },
        {
          "entity_id": "C0051",
          "metric_value": 18000.0
        },
        {
          "entity_id": "C0052",
          "metric_value": 13166.67
        },
        {
          "entity_id": "C0053",
          "metric_value": 18916.67
        },
        {
          "entity_id": "C0054",
          "metric_value": 11666.67
        },
        {
          "entity_id": "C0056",
          "metric_value": 11500.0
        },
        {
          "entity_id": "C0057",
          "metric_value": 4416.67
        },
        {
          "entity_id": "C0058",
          "metric_value": 11416.67
        },
        {
          "entity_id": "C0059",
          "metric_value": 3333.33
        },
        {
          "entity_id": "C0061",
          "metric_value": 4750.0
        },
        {
          "entity_id": "C0062",
          "metric_value": 18250.0
        },
        {
          "entity_id": "C0063",
          "metric_value": 19583.33
        },
        {
          "entity_id": "C0064",
          "metric_value": 8583.33
        },
        {
          "entity_id": "C0066",
          "metric_value": 13583.33
        },
        {
          "entity_id": "C0067",
          "metric_value": 16166.67
        },
        {
          "entity_id": "C0068",
          "metric_value": 17416.67
        },
        {
          "entity_id": "C0069",
          "metric_value": 16666.67
        },
        {
          "entity_id": "C0071",
          "metric_value": 10416.67
        },
        {
          "entity_id": "C0072",
          "metric_value": 10250.0
        },
        {
          "entity_id": "C0073",
          "metric_value": 5500.0
        },
        {
          "entity_id": "C0074",
          "metric_value": 18833.33
        },
        {
          "entity_id": "C0076",
          "metric_value": 2166.67
        },
        {
          "entity_id": "C0077",
          "metric_value": 5333.33
        },
        {
          "entity_id": "C0078",
          "metric_value": 3416.67
        },
        {
          "entity_id": "C0079",
          "metric_value": 9666.67
        },
        {
          "entity_id": "C0081",
          "metric_value": 18666.67
        },
        {
          "entity_id": "C0082",
          "metric_value": 3916.67
        },
        {
          "entity_id": "C0083",
          "metric_value": 3750.0
        },
        {
          "entity_id": "C0084",
          "metric_value": 10666.67
        },
        {
          "entity_id": "C0086",
          "metric_value": 10500.0
        },
        {
          "entity_id": "C0087",
          "metric_value": 8333.33
        },
        {
          "entity_id": "C0088",
          "metric_value": 15250.0
        },
        {
          "entity_id": "C0089",
          "metric_value": 14416.67
        },
        {
          "entity_id": "C0091",
          "metric_value": 10166.67
        },
        {
          "entity_id": "C0092",
          "metric_value": 3500.0
        },
        {
          "entity_id": "C0093",
          "metric_value": 4333.33
        },
        {
          "entity_id": "C0094",
          "metric_value": 10666.67
        },
        {
          "entity_id": "C0096",
          "metric_value": 13083.33
        },
        {
          "entity_id": "C0097",
          "metric_value": 5083.33
        },
        {
          "entity_id": "C0098",
          "metric_value": 16833.33
        },
        {
          "entity_id": "C0099",
          "metric_value": 17083.33
        },
        {
          "entity_id": "C0101",
          "metric_value": 10083.33
        },
        {
          "entity_id": "C0102",
          "metric_value": 11250.0
        },
        {
          "entity_id": "C0103",
          "metric_value": 10583.33
        },
        {
          "entity_id": "C0104",
          "metric_value": 5833.33
        },
        {
          "entity_id": "C0106",
          "metric_value": 9250.0
        },
        {
          "entity_id": "C0107",
          "metric_value": 17583.33
        },
        {
          "entity_id": "C0108",
          "metric_value": 14000.0
        },
        {
          "entity_id": "C0109",
          "metric_value": 16083.33
        },
        {
          "entity_id": "C0111",
          "metric_value": 15416.67
        },
        {
          "entity_id": "C0112",
          "metric_value": 12916.67
        },
        {
          "entity_id": "C0113",
          "metric_value": 5416.67
        },
        {
          "entity_id": "C0114",
          "metric_value": 2083.33
        },
        {
          "entity_id": "C0116",
          "metric_value": 3916.67
        },
        {
          "entity_id": "C0117",
          "metric_value": 15416.67
        },
        {
          "entity_id": "C0118",
          "metric_value": 9333.33
        },
        {
          "entity_id": "C0119",
          "metric_value": 16500.0
        }
      ],
      "entity_count": 96,
      "metric_total": 1110500.04,
      "executed_sql": "SELECT r.customer_id AS entity_id, SUM(r.amount) AS metric_value FROM revenue_events r WHERE r.event_type = 'recognized_revenue' AND CAST(r.event_date AS DATE) BETWEEN DATE '2026-03-04' AND DATE '2026-06-01' GROUP BY r.customer_id ORDER BY entity_id"
    },
    {
      "binding_id": "net_revenue_sales_v1",
      "definition_id": "net_revenue_sales",
      "concept_id": "net_revenue",
      "period": {
        "start_date": "2026-03-04",
        "end_date": "2026-06-01"
      },
      "entity_ids": [
        "C0001",
        "C0002",
        "C0003",
        "C0004",
        "C0006",
        "C0007",
        "C0008",
        "C0009",
        "C0011",
        "C0012",
        "C0013",
        "C0014",
        "C0016",
        "C0017",
        "C0018",
        "C0019",
        "C0021",
        "C0022",
        "C0023",
        "C0024",
        "C0026",
        "C0027",
        "C0028",
        "C0029",
        "C0031",
        "C0032",
        "C0033",
        "C0034",
        "C0036",
        "C0037",
        "C0038",
        "C0039",
        "C0041",
        "C0042",
        "C0043",
        "C0044",
        "C0046",
        "C0047",
        "C0048",
        "C0049",
        "C0051",
        "C0052",
        "C0053",
        "C0054",
        "C0056",
        "C0057",
        "C0058",
        "C0059",
        "C0061",
        "C0062",
        "C0063",
        "C0064",
        "C0066",
        "C0067",
        "C0068",
        "C0069",
        "C0071",
        "C0072",
        "C0073",
        "C0074",
        "C0076",
        "C0077",
        "C0078",
        "C0079",
        "C0081",
        "C0082",
        "C0083",
        "C0084",
        "C0086",
        "C0087",
        "C0088",
        "C0089",
        "C0091",
        "C0092",
        "C0093",
        "C0094",
        "C0096",
        "C0097",
        "C0098",
        "C0099",
        "C0101",
        "C0102",
        "C0103",
        "C0104",
        "C0106",
        "C0107",
        "C0108",
        "C0109",
        "C0111",
        "C0112",
        "C0113",
        "C0114",
        "C0116",
        "C0117",
        "C0118",
        "C0119"
      ],
      "rows": [
        {
          "entity_id": "C0001",
          "metric_value": 15250.0
        },
        {
          "entity_id": "C0002",
          "metric_value": 4666.67
        },
        {
          "entity_id": "C0003",
          "metric_value": 7166.67
        },
        {
          "entity_id": "C0004",
          "metric_value": 18250.0
        },
        {
          "entity_id": "C0006",
          "metric_value": 13916.67
        },
        {
          "entity_id": "C0007",
          "metric_value": 9916.67
        },
        {
          "entity_id": "C0008",
          "metric_value": 11250.0
        },
        {
          "entity_id": "C0009",
          "metric_value": 20000.0
        },
        {
          "entity_id": "C0011",
          "metric_value": 16083.33
        },
        {
          "entity_id": "C0012",
          "metric_value": 18833.33
        },
        {
          "entity_id": "C0013",
          "metric_value": 5583.33
        },
        {
          "entity_id": "C0014",
          "metric_value": 5000.0
        },
        {
          "entity_id": "C0016",
          "metric_value": 16083.33
        },
        {
          "entity_id": "C0017",
          "metric_value": 11500.0
        },
        {
          "entity_id": "C0018",
          "metric_value": 5000.0
        },
        {
          "entity_id": "C0019",
          "metric_value": 15166.67
        },
        {
          "entity_id": "C0021",
          "metric_value": 18083.33
        },
        {
          "entity_id": "C0022",
          "metric_value": 16416.67
        },
        {
          "entity_id": "C0023",
          "metric_value": 14166.67
        },
        {
          "entity_id": "C0024",
          "metric_value": 14666.67
        },
        {
          "entity_id": "C0026",
          "metric_value": 10333.33
        },
        {
          "entity_id": "C0027",
          "metric_value": 2416.67
        },
        {
          "entity_id": "C0028",
          "metric_value": 18583.33
        },
        {
          "entity_id": "C0029",
          "metric_value": 19416.67
        },
        {
          "entity_id": "C0031",
          "metric_value": 16916.67
        },
        {
          "entity_id": "C0032",
          "metric_value": 11916.67
        },
        {
          "entity_id": "C0033",
          "metric_value": 9916.67
        },
        {
          "entity_id": "C0034",
          "metric_value": 13833.33
        },
        {
          "entity_id": "C0036",
          "metric_value": 7666.67
        },
        {
          "entity_id": "C0037",
          "metric_value": 13916.67
        },
        {
          "entity_id": "C0038",
          "metric_value": 18916.67
        },
        {
          "entity_id": "C0039",
          "metric_value": 15250.0
        },
        {
          "entity_id": "C0041",
          "metric_value": 13916.67
        },
        {
          "entity_id": "C0042",
          "metric_value": 5083.33
        },
        {
          "entity_id": "C0043",
          "metric_value": 9416.67
        },
        {
          "entity_id": "C0044",
          "metric_value": 10000.0
        },
        {
          "entity_id": "C0046",
          "metric_value": 11750.0
        },
        {
          "entity_id": "C0047",
          "metric_value": 2583.33
        },
        {
          "entity_id": "C0048",
          "metric_value": 9083.33
        },
        {
          "entity_id": "C0049",
          "metric_value": 17666.67
        },
        {
          "entity_id": "C0051",
          "metric_value": 18000.0
        },
        {
          "entity_id": "C0052",
          "metric_value": 13166.67
        },
        {
          "entity_id": "C0053",
          "metric_value": 18916.67
        },
        {
          "entity_id": "C0054",
          "metric_value": 11666.67
        },
        {
          "entity_id": "C0056",
          "metric_value": 11500.0
        },
        {
          "entity_id": "C0057",
          "metric_value": 4416.67
        },
        {
          "entity_id": "C0058",
          "metric_value": 11416.67
        },
        {
          "entity_id": "C0059",
          "metric_value": 3333.33
        },
        {
          "entity_id": "C0061",
          "metric_value": 4750.0
        },
        {
          "entity_id": "C0062",
          "metric_value": 18250.0
        },
        {
          "entity_id": "C0063",
          "metric_value": 19583.33
        },
        {
          "entity_id": "C0064",
          "metric_value": 8583.33
        },
        {
          "entity_id": "C0066",
          "metric_value": 13583.33
        },
        {
          "entity_id": "C0067",
          "metric_value": 16166.67
        },
        {
          "entity_id": "C0068",
          "metric_value": 17416.67
        },
        {
          "entity_id": "C0069",
          "metric_value": 16666.67
        },
        {
          "entity_id": "C0071",
          "metric_value": 10416.67
        },
        {
          "entity_id": "C0072",
          "metric_value": 10250.0
        },
        {
          "entity_id": "C0073",
          "metric_value": 5500.0
        },
        {
          "entity_id": "C0074",
          "metric_value": 18833.33
        },
        {
          "entity_id": "C0076",
          "metric_value": 2166.67
        },
        {
          "entity_id": "C0077",
          "metric_value": 5333.33
        },
        {
          "entity_id": "C0078",
          "metric_value": 3416.67
        },
        {
          "entity_id": "C0079",
          "metric_value": 9666.67
        },
        {
          "entity_id": "C0081",
          "metric_value": 18666.67
        },
        {
          "entity_id": "C0082",
          "metric_value": 3916.67
        },
        {
          "entity_id": "C0083",
          "metric_value": 3750.0
        },
        {
          "entity_id": "C0084",
          "metric_value": 10666.67
        },
        {
          "entity_id": "C0086",
          "metric_value": 10500.0
        },
        {
          "entity_id": "C0087",
          "metric_value": 8333.33
        },
        {
          "entity_id": "C0088",
          "metric_value": 15250.0
        },
        {
          "entity_id": "C0089",
          "metric_value": 14416.67
        },
        {
          "entity_id": "C0091",
          "metric_value": 10166.67
        },
        {
          "entity_id": "C0092",
          "metric_value": 3500.0
        },
        {
          "entity_id": "C0093",
          "metric_value": 4333.33
        },
        {
          "entity_id": "C0094",
          "metric_value": 10666.67
        },
        {
          "entity_id": "C0096",
          "metric_value": 13083.33
        },
        {
          "entity_id": "C0097",
          "metric_value": 5083.33
        },
        {
          "entity_id": "C0098",
          "metric_value": 16833.33
        },
        {
          "entity_id": "C0099",
          "metric_value": 17083.33
        },
        {
          "entity_id": "C0101",
          "metric_value": 10083.33
        },
        {
          "entity_id": "C0102",
          "metric_value": 11250.0
        },
        {
          "entity_id": "C0103",
          "metric_value": 10583.33
        },
        {
          "entity_id": "C0104",
          "metric_value": 5833.33
        },
        {
          "entity_id": "C0106",
          "metric_value": 9250.0
        },
        {
          "entity_id": "C0107",
          "metric_value": 17583.33
        },
        {
          "entity_id": "C0108",
          "metric_value": 14000.0
        },
        {
          "entity_id": "C0109",
          "metric_value": 16083.33
        },
        {
          "entity_id": "C0111",
          "metric_value": 15416.67
        },
        {
          "entity_id": "C0112",
          "metric_value": 12916.67
        },
        {
          "entity_id": "C0113",
          "metric_value": 5416.67
        },
        {
          "entity_id": "C0114",
          "metric_value": 2083.33
        },
        {
          "entity_id": "C0116",
          "metric_value": 3916.67
        },
        {
          "entity_id": "C0117",
          "metric_value": 15416.67
        },
        {
          "entity_id": "C0118",
          "metric_value": 9333.33
        },
        {
          "entity_id": "C0119",
          "metric_value": 16500.0
        }
      ],
      "entity_count": 96,
      "metric_total": 1110500.04,
      "executed_sql": "SELECT c.customer_id AS entity_id, SUM(r.amount) AS metric_value FROM customers c INNER JOIN revenue_events r ON c.customer_id = r.customer_id AND r.event_type = 'recognized_revenue' WHERE CAST(r.event_date AS DATE) >= DATE '2026-03-04' AND CAST(r.event_date AS DATE) <= DATE '2026-06-01' GROUP BY c.customer_id ORDER BY entity_id"
    }
  ],
  "subgraph": {
    "concept_id": "net_revenue",
    "nodes": [
      {
        "node_id": "net_revenue",
        "node_type": "business_concept",
        "label": "Net Revenue",
        "properties": {}
      },
      {
        "node_id": "revenue_event",
        "node_type": "entity_type",
        "label": "Revenue Event",
        "properties": {}
      }
    ],
    "relationships": [
      {
        "source": "net_revenue",
        "target": "revenue_event",
        "relationship_type": "aggregates"
      }
    ]
  },
  "authority_rules": [
    {
      "concept_id": "net_revenue",
      "semantic_dimension": "revenue-recognition",
      "status": "clear",
      "owner": "Finance",
      "rationale": "Finance governs recognized revenue."
    }
  ]
}
```
