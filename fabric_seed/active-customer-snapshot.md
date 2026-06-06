# Active Customer snapshot

Finance, Sales, and Customer Success use different activity windows and signals, producing a material three-way population conflict.

This artifact contains synthetic data only. The fenced JSON is generated from `LocalProvider` and validates as `ReplayScenarioSnapshot`.

```json
{
  "scenario_id": "active-customer",
  "term": "Active Customer",
  "data_classification": "synthetic",
  "concept": {
    "concept_id": "active_customer",
    "canonical_name": "Active Customer",
    "description": "A customer included in current operating and board-level activity reporting.",
    "aliases": [
      "active customers",
      "active enterprise customer",
      "active enterprise customers"
    ],
    "definition_ids": [
      "active_customer_finance",
      "active_customer_sales",
      "active_customer_customer_success"
    ]
  },
  "bindings": [
    {
      "binding_id": "active_customer_finance_v1",
      "definition_id": "active_customer_finance",
      "concept_id": "active_customer",
      "name": "Finance Active Customer",
      "owner": "Finance",
      "rule_text": "Customer with recognized revenue during the trailing 90-day reporting window.",
      "semantic_dimensions": [
        "revenue-recognition",
        "activity-window",
        "customer-population"
      ],
      "source_tables": [
        "customers",
        "revenue_events"
      ],
      "entity_key": "customer_id",
      "grain": "customer",
      "population": "Customers with a recognized revenue event in the trailing 90 days.",
      "time_window_days": 90,
      "filters": [
        "event_type = recognized_revenue",
        "event_date in trailing 90 days"
      ],
      "exclusions": [],
      "sql_template": "SELECT DISTINCT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN revenue_events r ON r.customer_id = c.customer_id WHERE r.event_type = 'recognized_revenue' AND CAST(r.event_date AS DATE) BETWEEN DATE '{period_end}' - INTERVAL 89 DAY AND DATE '{period_end}' ORDER BY entity_id"
    },
    {
      "binding_id": "active_customer_sales_v1",
      "definition_id": "active_customer_sales",
      "concept_id": "active_customer",
      "name": "Sales Active Customer",
      "owner": "Sales",
      "rule_text": "Customer with an open or won opportunity updated during the trailing 180 days.",
      "semantic_dimensions": [
        "pipeline-status",
        "activity-window",
        "customer-population"
      ],
      "source_tables": [
        "customers",
        "opportunities"
      ],
      "entity_key": "customer_id",
      "grain": "customer",
      "population": "Customers represented by current pipeline activity.",
      "time_window_days": 180,
      "filters": [
        "stage in open, won",
        "updated_at in trailing 180 days"
      ],
      "exclusions": [
        "closed_lost opportunities"
      ],
      "sql_template": "SELECT DISTINCT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN opportunities o ON o.customer_id = c.customer_id WHERE o.stage IN ('open', 'won') AND CAST(o.updated_at AS DATE) BETWEEN DATE '{period_end}' - INTERVAL 179 DAY AND DATE '{period_end}' ORDER BY entity_id"
    },
    {
      "binding_id": "active_customer_customer_success_v1",
      "definition_id": "active_customer_customer_success",
      "concept_id": "active_customer",
      "name": "Customer Success Active Customer",
      "owner": "Customer Success",
      "rule_text": "Customer with an active contract and qualifying product usage in the trailing 30 days.",
      "semantic_dimensions": [
        "contract-status",
        "qualifying-usage",
        "activity-window"
      ],
      "source_tables": [
        "customers",
        "contracts",
        "usage_events"
      ],
      "entity_key": "customer_id",
      "grain": "customer",
      "population": "Contracted customers demonstrating recent qualifying usage.",
      "time_window_days": 30,
      "filters": [
        "contract status = active",
        "qualifying = 1",
        "usage in trailing 30 days"
      ],
      "exclusions": [
        "expired contracts",
        "non-qualifying usage"
      ],
      "sql_template": "SELECT DISTINCT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN contracts ct ON ct.customer_id = c.customer_id JOIN usage_events u ON u.customer_id = c.customer_id WHERE ct.status = 'active' AND CAST(ct.start_date AS DATE) <= DATE '{as_of_date}' AND CAST(ct.end_date AS DATE) >= DATE '{as_of_date}' AND u.qualifying = 1 AND CAST(u.event_date AS DATE) BETWEEN DATE '{period_end}' - INTERVAL 29 DAY AND DATE '{period_end}' ORDER BY entity_id"
    }
  ],
  "evaluations": [
    {
      "binding_id": "active_customer_finance_v1",
      "definition_id": "active_customer_finance",
      "concept_id": "active_customer",
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
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0002",
          "metric_value": 56000.0
        },
        {
          "entity_id": "C0003",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0004",
          "metric_value": 219000.0
        },
        {
          "entity_id": "C0006",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0007",
          "metric_value": 119000.0
        },
        {
          "entity_id": "C0008",
          "metric_value": 135000.0
        },
        {
          "entity_id": "C0009",
          "metric_value": 240000.0
        },
        {
          "entity_id": "C0011",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0012",
          "metric_value": 226000.0
        },
        {
          "entity_id": "C0013",
          "metric_value": 67000.0
        },
        {
          "entity_id": "C0014",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0016",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0017",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0018",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0019",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C0021",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C0022",
          "metric_value": 197000.0
        },
        {
          "entity_id": "C0023",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0024",
          "metric_value": 176000.0
        },
        {
          "entity_id": "C0026",
          "metric_value": 124000.0
        },
        {
          "entity_id": "C0027",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C0028",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C0029",
          "metric_value": 233000.0
        },
        {
          "entity_id": "C0031",
          "metric_value": 203000.0
        },
        {
          "entity_id": "C0032",
          "metric_value": 143000.0
        },
        {
          "entity_id": "C0033",
          "metric_value": 119000.0
        },
        {
          "entity_id": "C0034",
          "metric_value": 166000.0
        },
        {
          "entity_id": "C0036",
          "metric_value": 92000.0
        },
        {
          "entity_id": "C0037",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0038",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0039",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0041",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0042",
          "metric_value": 61000.0
        },
        {
          "entity_id": "C0043",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0044",
          "metric_value": 120000.0
        },
        {
          "entity_id": "C0046",
          "metric_value": 141000.0
        },
        {
          "entity_id": "C0047",
          "metric_value": 31000.0
        },
        {
          "entity_id": "C0048",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C0049",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C0051",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C0052",
          "metric_value": 158000.0
        },
        {
          "entity_id": "C0053",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0054",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0056",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0057",
          "metric_value": 53000.0
        },
        {
          "entity_id": "C0058",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C0059",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0061",
          "metric_value": 57000.0
        },
        {
          "entity_id": "C0062",
          "metric_value": 219000.0
        },
        {
          "entity_id": "C0063",
          "metric_value": 235000.0
        },
        {
          "entity_id": "C0064",
          "metric_value": 103000.0
        },
        {
          "entity_id": "C0066",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0067",
          "metric_value": 194000.0
        },
        {
          "entity_id": "C0068",
          "metric_value": 209000.0
        },
        {
          "entity_id": "C0069",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C0071",
          "metric_value": 125000.0
        },
        {
          "entity_id": "C0072",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C0073",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C0074",
          "metric_value": 226000.0
        },
        {
          "entity_id": "C0076",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C0077",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C0078",
          "metric_value": 41000.0
        },
        {
          "entity_id": "C0079",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0081",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C0082",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C0083",
          "metric_value": 45000.0
        },
        {
          "entity_id": "C0084",
          "metric_value": 128000.0
        },
        {
          "entity_id": "C0086",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C0087",
          "metric_value": 100000.0
        },
        {
          "entity_id": "C0088",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0089",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0091",
          "metric_value": 122000.0
        },
        {
          "entity_id": "C0092",
          "metric_value": 42000.0
        },
        {
          "entity_id": "C0093",
          "metric_value": 52000.0
        },
        {
          "entity_id": "C0094",
          "metric_value": 128000.0
        },
        {
          "entity_id": "C0096",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0097",
          "metric_value": 61000.0
        },
        {
          "entity_id": "C0098",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C0099",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C0101",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C0102",
          "metric_value": 135000.0
        },
        {
          "entity_id": "C0103",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0104",
          "metric_value": 70000.0
        },
        {
          "entity_id": "C0106",
          "metric_value": 111000.0
        },
        {
          "entity_id": "C0107",
          "metric_value": 211000.0
        },
        {
          "entity_id": "C0108",
          "metric_value": 168000.0
        },
        {
          "entity_id": "C0109",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0111",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0112",
          "metric_value": 155000.0
        },
        {
          "entity_id": "C0113",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C0114",
          "metric_value": 25000.0
        },
        {
          "entity_id": "C0116",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C0117",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0118",
          "metric_value": 112000.0
        },
        {
          "entity_id": "C0119",
          "metric_value": 198000.0
        }
      ],
      "entity_count": 96,
      "metric_total": 13326000.0,
      "executed_sql": "SELECT DISTINCT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN revenue_events r ON r.customer_id = c.customer_id WHERE r.event_type = 'recognized_revenue' AND CAST(r.event_date AS DATE) BETWEEN DATE '2026-06-01' - INTERVAL 89 DAY AND DATE '2026-06-01' ORDER BY entity_id"
    },
    {
      "binding_id": "active_customer_sales_v1",
      "definition_id": "active_customer_sales",
      "concept_id": "active_customer",
      "period": {
        "start_date": "2026-03-04",
        "end_date": "2026-06-01"
      },
      "entity_ids": [
        "C0001",
        "C0002",
        "C0003",
        "C0005",
        "C0006",
        "C0007",
        "C0009",
        "C0010",
        "C0011",
        "C0013",
        "C0014",
        "C0015",
        "C0017",
        "C0018",
        "C0019",
        "C0021",
        "C0022",
        "C0023",
        "C0025",
        "C0026",
        "C0027",
        "C0029",
        "C0030",
        "C0031",
        "C0033",
        "C0034",
        "C0035",
        "C0037",
        "C0038",
        "C0039",
        "C0041",
        "C0042",
        "C0043",
        "C0045",
        "C0046",
        "C0047",
        "C0049",
        "C0050",
        "C0051",
        "C0053",
        "C0054",
        "C0055",
        "C0057",
        "C0058",
        "C0059",
        "C0061",
        "C0062",
        "C0063",
        "C0065",
        "C0066",
        "C0067",
        "C0069",
        "C0070",
        "C0071",
        "C0073",
        "C0074",
        "C0075",
        "C0077",
        "C0078",
        "C0079",
        "C0081",
        "C0082",
        "C0083",
        "C0085",
        "C0086",
        "C0087",
        "C0089",
        "C0090",
        "C0091",
        "C0093",
        "C0094",
        "C0095",
        "C0097",
        "C0098",
        "C0099",
        "C0101",
        "C0102",
        "C0103",
        "C0105",
        "C0106",
        "C0107",
        "C0109",
        "C0110",
        "C0111",
        "C0113",
        "C0114",
        "C0115",
        "C0117",
        "C0118",
        "C0119"
      ],
      "rows": [
        {
          "entity_id": "C0001",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0002",
          "metric_value": 56000.0
        },
        {
          "entity_id": "C0003",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0005",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C0006",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0007",
          "metric_value": 119000.0
        },
        {
          "entity_id": "C0009",
          "metric_value": 240000.0
        },
        {
          "entity_id": "C0010",
          "metric_value": 180000.0
        },
        {
          "entity_id": "C0011",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0013",
          "metric_value": 67000.0
        },
        {
          "entity_id": "C0014",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0015",
          "metric_value": 81000.0
        },
        {
          "entity_id": "C0017",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0018",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0019",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C0021",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C0022",
          "metric_value": 197000.0
        },
        {
          "entity_id": "C0023",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0025",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0026",
          "metric_value": 124000.0
        },
        {
          "entity_id": "C0027",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C0029",
          "metric_value": 233000.0
        },
        {
          "entity_id": "C0030",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0031",
          "metric_value": 203000.0
        },
        {
          "entity_id": "C0033",
          "metric_value": 119000.0
        },
        {
          "entity_id": "C0034",
          "metric_value": 166000.0
        },
        {
          "entity_id": "C0035",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C0037",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0038",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0039",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0041",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0042",
          "metric_value": 61000.0
        },
        {
          "entity_id": "C0043",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0045",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0046",
          "metric_value": 141000.0
        },
        {
          "entity_id": "C0047",
          "metric_value": 31000.0
        },
        {
          "entity_id": "C0049",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C0050",
          "metric_value": 218000.0
        },
        {
          "entity_id": "C0051",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C0053",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0054",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0055",
          "metric_value": 184000.0
        },
        {
          "entity_id": "C0057",
          "metric_value": 53000.0
        },
        {
          "entity_id": "C0058",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C0059",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0061",
          "metric_value": 57000.0
        },
        {
          "entity_id": "C0062",
          "metric_value": 219000.0
        },
        {
          "entity_id": "C0063",
          "metric_value": 235000.0
        },
        {
          "entity_id": "C0065",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C0066",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0067",
          "metric_value": 194000.0
        },
        {
          "entity_id": "C0069",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C0070",
          "metric_value": 48000.0
        },
        {
          "entity_id": "C0071",
          "metric_value": 125000.0
        },
        {
          "entity_id": "C0073",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C0074",
          "metric_value": 226000.0
        },
        {
          "entity_id": "C0075",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C0077",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C0078",
          "metric_value": 41000.0
        },
        {
          "entity_id": "C0079",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0081",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C0082",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C0083",
          "metric_value": 45000.0
        },
        {
          "entity_id": "C0085",
          "metric_value": 230000.0
        },
        {
          "entity_id": "C0086",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C0087",
          "metric_value": 100000.0
        },
        {
          "entity_id": "C0089",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0090",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0091",
          "metric_value": 122000.0
        },
        {
          "entity_id": "C0093",
          "metric_value": 52000.0
        },
        {
          "entity_id": "C0094",
          "metric_value": 128000.0
        },
        {
          "entity_id": "C0095",
          "metric_value": 43000.0
        },
        {
          "entity_id": "C0097",
          "metric_value": 61000.0
        },
        {
          "entity_id": "C0098",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C0099",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C0101",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C0102",
          "metric_value": 135000.0
        },
        {
          "entity_id": "C0103",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0105",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0106",
          "metric_value": 111000.0
        },
        {
          "entity_id": "C0107",
          "metric_value": 211000.0
        },
        {
          "entity_id": "C0109",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0110",
          "metric_value": 46000.0
        },
        {
          "entity_id": "C0111",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0113",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C0114",
          "metric_value": 25000.0
        },
        {
          "entity_id": "C0115",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C0117",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0118",
          "metric_value": 112000.0
        },
        {
          "entity_id": "C0119",
          "metric_value": 198000.0
        }
      ],
      "entity_count": 90,
      "metric_total": 12230000.0,
      "executed_sql": "SELECT DISTINCT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN opportunities o ON o.customer_id = c.customer_id WHERE o.stage IN ('open', 'won') AND CAST(o.updated_at AS DATE) BETWEEN DATE '2026-06-01' - INTERVAL 179 DAY AND DATE '2026-06-01' ORDER BY entity_id"
    },
    {
      "binding_id": "active_customer_customer_success_v1",
      "definition_id": "active_customer_customer_success",
      "concept_id": "active_customer",
      "period": {
        "start_date": "2026-03-04",
        "end_date": "2026-06-01"
      },
      "entity_ids": [
        "C0001",
        "C0002",
        "C0004",
        "C0005",
        "C0007",
        "C0008",
        "C0010",
        "C0011",
        "C0013",
        "C0014",
        "C0016",
        "C0017",
        "C0019",
        "C0020",
        "C0022",
        "C0023",
        "C0025",
        "C0026",
        "C0028",
        "C0029",
        "C0031",
        "C0032",
        "C0034",
        "C0035",
        "C0037",
        "C0038",
        "C0040",
        "C0041",
        "C0043",
        "C0044",
        "C0046",
        "C0047",
        "C0049",
        "C0050",
        "C0052",
        "C0053",
        "C0055",
        "C0056",
        "C0058",
        "C0059",
        "C0061",
        "C0062",
        "C0064",
        "C0065",
        "C0067",
        "C0068",
        "C0070",
        "C0071",
        "C0073",
        "C0074",
        "C0076",
        "C0077",
        "C0079",
        "C0080",
        "C0082",
        "C0083",
        "C0085",
        "C0086",
        "C0088",
        "C0089",
        "C0091",
        "C0092",
        "C0094",
        "C0095",
        "C0097",
        "C0098",
        "C0100",
        "C0101",
        "C0103",
        "C0104",
        "C0106",
        "C0107",
        "C0109",
        "C0110",
        "C0112",
        "C0113",
        "C0115",
        "C0116",
        "C0118",
        "C0119"
      ],
      "rows": [
        {
          "entity_id": "C0001",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0002",
          "metric_value": 56000.0
        },
        {
          "entity_id": "C0004",
          "metric_value": 219000.0
        },
        {
          "entity_id": "C0005",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C0007",
          "metric_value": 119000.0
        },
        {
          "entity_id": "C0008",
          "metric_value": 135000.0
        },
        {
          "entity_id": "C0010",
          "metric_value": 180000.0
        },
        {
          "entity_id": "C0011",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0013",
          "metric_value": 67000.0
        },
        {
          "entity_id": "C0014",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0016",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0017",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0019",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C0020",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0022",
          "metric_value": 197000.0
        },
        {
          "entity_id": "C0023",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0025",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0026",
          "metric_value": 124000.0
        },
        {
          "entity_id": "C0028",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C0029",
          "metric_value": 233000.0
        },
        {
          "entity_id": "C0031",
          "metric_value": 203000.0
        },
        {
          "entity_id": "C0032",
          "metric_value": 143000.0
        },
        {
          "entity_id": "C0034",
          "metric_value": 166000.0
        },
        {
          "entity_id": "C0035",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C0037",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0038",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0040",
          "metric_value": 211000.0
        },
        {
          "entity_id": "C0041",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0043",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0044",
          "metric_value": 120000.0
        },
        {
          "entity_id": "C0046",
          "metric_value": 141000.0
        },
        {
          "entity_id": "C0047",
          "metric_value": 31000.0
        },
        {
          "entity_id": "C0049",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C0050",
          "metric_value": 218000.0
        },
        {
          "entity_id": "C0052",
          "metric_value": 158000.0
        },
        {
          "entity_id": "C0053",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0055",
          "metric_value": 184000.0
        },
        {
          "entity_id": "C0056",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0058",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C0059",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0061",
          "metric_value": 57000.0
        },
        {
          "entity_id": "C0062",
          "metric_value": 219000.0
        },
        {
          "entity_id": "C0064",
          "metric_value": 103000.0
        },
        {
          "entity_id": "C0065",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C0067",
          "metric_value": 194000.0
        },
        {
          "entity_id": "C0068",
          "metric_value": 209000.0
        },
        {
          "entity_id": "C0070",
          "metric_value": 48000.0
        },
        {
          "entity_id": "C0071",
          "metric_value": 125000.0
        },
        {
          "entity_id": "C0073",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C0074",
          "metric_value": 226000.0
        },
        {
          "entity_id": "C0076",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C0077",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C0079",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0080",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C0082",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C0083",
          "metric_value": 45000.0
        },
        {
          "entity_id": "C0085",
          "metric_value": 230000.0
        },
        {
          "entity_id": "C0086",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C0088",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0089",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0091",
          "metric_value": 122000.0
        },
        {
          "entity_id": "C0092",
          "metric_value": 42000.0
        },
        {
          "entity_id": "C0094",
          "metric_value": 128000.0
        },
        {
          "entity_id": "C0095",
          "metric_value": 43000.0
        },
        {
          "entity_id": "C0097",
          "metric_value": 61000.0
        },
        {
          "entity_id": "C0098",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C0100",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0101",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C0103",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0104",
          "metric_value": 70000.0
        },
        {
          "entity_id": "C0106",
          "metric_value": 111000.0
        },
        {
          "entity_id": "C0107",
          "metric_value": 211000.0
        },
        {
          "entity_id": "C0109",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0110",
          "metric_value": 46000.0
        },
        {
          "entity_id": "C0112",
          "metric_value": 155000.0
        },
        {
          "entity_id": "C0113",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C0115",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C0116",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C0118",
          "metric_value": 112000.0
        },
        {
          "entity_id": "C0119",
          "metric_value": 198000.0
        }
      ],
      "entity_count": 80,
      "metric_total": 11153000.0,
      "executed_sql": "SELECT DISTINCT c.customer_id AS entity_id, c.annual_recurring_revenue AS metric_value FROM customers c JOIN contracts ct ON ct.customer_id = c.customer_id JOIN usage_events u ON u.customer_id = c.customer_id WHERE ct.status = 'active' AND CAST(ct.start_date AS DATE) <= DATE '2026-06-01' AND CAST(ct.end_date AS DATE) >= DATE '2026-06-01' AND u.qualifying = 1 AND CAST(u.event_date AS DATE) BETWEEN DATE '2026-06-01' - INTERVAL 29 DAY AND DATE '2026-06-01' ORDER BY entity_id"
    }
  ],
  "subgraph": {
    "concept_id": "active_customer",
    "nodes": [
      {
        "node_id": "active_customer",
        "node_type": "business_concept",
        "label": "Active Customer",
        "properties": {}
      },
      {
        "node_id": "customer",
        "node_type": "entity_type",
        "label": "Customer",
        "properties": {}
      },
      {
        "node_id": "contract",
        "node_type": "entity_type",
        "label": "Contract",
        "properties": {}
      },
      {
        "node_id": "opportunity",
        "node_type": "entity_type",
        "label": "Opportunity",
        "properties": {}
      },
      {
        "node_id": "usage_event",
        "node_type": "entity_type",
        "label": "Usage Event",
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
        "source": "active_customer",
        "target": "customer",
        "relationship_type": "selects"
      },
      {
        "source": "active_customer",
        "target": "contract",
        "relationship_type": "derived_from"
      },
      {
        "source": "active_customer",
        "target": "opportunity",
        "relationship_type": "derived_from"
      },
      {
        "source": "active_customer",
        "target": "usage_event",
        "relationship_type": "derived_from"
      },
      {
        "source": "active_customer",
        "target": "revenue_event",
        "relationship_type": "derived_from"
      }
    ]
  },
  "authority_rules": [
    {
      "concept_id": "active_customer",
      "semantic_dimension": "revenue-recognition",
      "status": "clear",
      "owner": "Finance",
      "rationale": "Finance governs recognized revenue policy."
    },
    {
      "concept_id": "active_customer",
      "semantic_dimension": "pipeline-status",
      "status": "clear",
      "owner": "Sales",
      "rationale": "Sales governs opportunity stage semantics."
    },
    {
      "concept_id": "active_customer",
      "semantic_dimension": "qualifying-usage",
      "status": "clear",
      "owner": "Customer Success",
      "rationale": "Customer Success governs qualifying adoption signals."
    },
    {
      "concept_id": "active_customer",
      "semantic_dimension": "canonical-active-customer",
      "status": "clear",
      "owner": "Data Governance Council",
      "rationale": "The council owns the cross-domain board metric and can approve a canonical composition."
    }
  ]
}
```
