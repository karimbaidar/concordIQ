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
        "C0120",
        "C0126",
        "C0132",
        "C0138",
        "C0144",
        "C0150",
        "C0156",
        "C0162",
        "C0168",
        "C0174",
        "C0180",
        "C0186",
        "C0192",
        "C0198",
        "C0204",
        "C0210",
        "C0216",
        "C0222",
        "C0228",
        "C0234",
        "C0240",
        "C0246",
        "C0252",
        "C0258",
        "C0264",
        "C0270",
        "C0276",
        "C0282",
        "C0288",
        "C0294",
        "C0300",
        "C0306",
        "C0312",
        "C0318",
        "C0324",
        "C0330",
        "C0336",
        "C0342",
        "C0348",
        "C0354",
        "C0360",
        "C0366",
        "C0372",
        "C0378",
        "C0384",
        "C0390",
        "C0396",
        "C0402",
        "C0408",
        "C0414",
        "C0420",
        "C0426",
        "C0432",
        "C0438",
        "C0444",
        "C0450",
        "C0456",
        "C0462",
        "C0468",
        "C0474",
        "C0480",
        "C0486",
        "C0492",
        "C0498",
        "C0504",
        "C0510",
        "C0516",
        "C0522",
        "C0528",
        "C0534",
        "C0540",
        "C0546",
        "C0552",
        "C0558",
        "C0564",
        "C0570",
        "C0576",
        "C0582",
        "C0588",
        "C0594",
        "C0600",
        "C0606",
        "C0612",
        "C0618",
        "C0624",
        "C0630",
        "C0636",
        "C0642",
        "C0648",
        "C0654",
        "C0660",
        "C0666",
        "C0672",
        "C0678",
        "C0684",
        "C0690",
        "C0696",
        "C0702",
        "C0708",
        "C0714",
        "C0720",
        "C0726",
        "C0732",
        "C0738",
        "C0744",
        "C0750",
        "C0756",
        "C0762",
        "C0768",
        "C0774",
        "C0780",
        "C0786",
        "C0792",
        "C0798",
        "C0804",
        "C0810",
        "C0816",
        "C0822",
        "C0828",
        "C0834",
        "C0840",
        "C0846",
        "C0852",
        "C0858",
        "C0864",
        "C0870",
        "C0876",
        "C0882",
        "C0888",
        "C0894",
        "C0900",
        "C0906",
        "C0912",
        "C0918",
        "C0924",
        "C0930",
        "C0936",
        "C0942",
        "C0948",
        "C0954",
        "C0960",
        "C0966",
        "C0972",
        "C0978",
        "C0984",
        "C0990",
        "C0996",
        "C1002",
        "C1008",
        "C1014",
        "C1020",
        "C1026",
        "C1032",
        "C1038",
        "C1044",
        "C1050",
        "C1056",
        "C1062",
        "C1068",
        "C1074",
        "C1080",
        "C1086",
        "C1092",
        "C1098",
        "C1104",
        "C1110",
        "C1116",
        "C1122",
        "C1128",
        "C1134",
        "C1140",
        "C1146",
        "C1152",
        "C1158",
        "C1164",
        "C1170",
        "C1176",
        "C1182",
        "C1188",
        "C1194",
        "C1200",
        "C1206",
        "C1212",
        "C1218",
        "C1224",
        "C1230",
        "C1236",
        "C1242",
        "C1248",
        "C1254",
        "C1260",
        "C1266",
        "C1272",
        "C1278",
        "C1284",
        "C1290",
        "C1296",
        "C1302",
        "C1308",
        "C1314",
        "C1320",
        "C1326",
        "C1332",
        "C1338",
        "C1344",
        "C1350",
        "C1356",
        "C1362",
        "C1368",
        "C1374",
        "C1380",
        "C1386",
        "C1392",
        "C1398",
        "C1404",
        "C1410",
        "C1416",
        "C1422",
        "C1428",
        "C1434",
        "C1440",
        "C1446",
        "C1452",
        "C1458",
        "C1464",
        "C1470",
        "C1476",
        "C1482",
        "C1488",
        "C1494",
        "C1500",
        "C1506",
        "C1512",
        "C1518",
        "C1524",
        "C1530",
        "C1536",
        "C1542",
        "C1548",
        "C1554",
        "C1560",
        "C1566",
        "C1572",
        "C1578",
        "C1584",
        "C1590",
        "C1596",
        "C1602",
        "C1608",
        "C1614",
        "C1620",
        "C1626",
        "C1632",
        "C1638",
        "C1644",
        "C1650",
        "C1656",
        "C1662",
        "C1668",
        "C1674",
        "C1680",
        "C1686",
        "C1692",
        "C1698",
        "C1704",
        "C1710",
        "C1716",
        "C1722",
        "C1728",
        "C1734",
        "C1740",
        "C1746",
        "C1752",
        "C1758",
        "C1764",
        "C1770",
        "C1776",
        "C1782",
        "C1788",
        "C1794",
        "C1800",
        "C1806",
        "C1812",
        "C1818",
        "C1824",
        "C1830",
        "C1836",
        "C1842",
        "C1848",
        "C1854",
        "C1860",
        "C1866",
        "C1872",
        "C1878",
        "C1884",
        "C1890",
        "C1896",
        "C1902",
        "C1908",
        "C1914",
        "C1920",
        "C1926",
        "C1932",
        "C1938",
        "C1944",
        "C1950",
        "C1956",
        "C1962",
        "C1968",
        "C1974",
        "C1980",
        "C1986",
        "C1992",
        "C1998"
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
        },
        {
          "entity_id": "C0126",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C0132",
          "metric_value": 93000.0
        },
        {
          "entity_id": "C0138",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C0144",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0150",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C0156",
          "metric_value": 75000.0
        },
        {
          "entity_id": "C0162",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C0168",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0174",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0180",
          "metric_value": 145000.0
        },
        {
          "entity_id": "C0186",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C0192",
          "metric_value": 230000.0
        },
        {
          "entity_id": "C0198",
          "metric_value": 132000.0
        },
        {
          "entity_id": "C0204",
          "metric_value": 46000.0
        },
        {
          "entity_id": "C0210",
          "metric_value": 204000.0
        },
        {
          "entity_id": "C0216",
          "metric_value": 122000.0
        },
        {
          "entity_id": "C0222",
          "metric_value": 165000.0
        },
        {
          "entity_id": "C0228",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0234",
          "metric_value": 184000.0
        },
        {
          "entity_id": "C0240",
          "metric_value": 24000.0
        },
        {
          "entity_id": "C0246",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C0252",
          "metric_value": 150000.0
        },
        {
          "entity_id": "C0258",
          "metric_value": 149000.0
        },
        {
          "entity_id": "C0264",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C0270",
          "metric_value": 39000.0
        },
        {
          "entity_id": "C0276",
          "metric_value": 222000.0
        },
        {
          "entity_id": "C0282",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0288",
          "metric_value": 95000.0
        },
        {
          "entity_id": "C0294",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0300",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0306",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0312",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0318",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0324",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C0330",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C0336",
          "metric_value": 48000.0
        },
        {
          "entity_id": "C0342",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0348",
          "metric_value": 80000.0
        },
        {
          "entity_id": "C0354",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C0360",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0366",
          "metric_value": 39000.0
        },
        {
          "entity_id": "C0372",
          "metric_value": 141000.0
        },
        {
          "entity_id": "C0378",
          "metric_value": 199000.0
        },
        {
          "entity_id": "C0384",
          "metric_value": 180000.0
        },
        {
          "entity_id": "C0390",
          "metric_value": 56000.0
        },
        {
          "entity_id": "C0396",
          "metric_value": 199000.0
        },
        {
          "entity_id": "C0402",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0408",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C0414",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C0420",
          "metric_value": 134000.0
        },
        {
          "entity_id": "C0426",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0432",
          "metric_value": 68000.0
        },
        {
          "entity_id": "C0438",
          "metric_value": 100000.0
        },
        {
          "entity_id": "C0444",
          "metric_value": 124000.0
        },
        {
          "entity_id": "C0450",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0456",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0462",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0468",
          "metric_value": 49000.0
        },
        {
          "entity_id": "C0474",
          "metric_value": 213000.0
        },
        {
          "entity_id": "C0480",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0486",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C0492",
          "metric_value": 99000.0
        },
        {
          "entity_id": "C0498",
          "metric_value": 34000.0
        },
        {
          "entity_id": "C0504",
          "metric_value": 118000.0
        },
        {
          "entity_id": "C0510",
          "metric_value": 155000.0
        },
        {
          "entity_id": "C0516",
          "metric_value": 132000.0
        },
        {
          "entity_id": "C0522",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0528",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0534",
          "metric_value": 110000.0
        },
        {
          "entity_id": "C0540",
          "metric_value": 31000.0
        },
        {
          "entity_id": "C0546",
          "metric_value": 49000.0
        },
        {
          "entity_id": "C0552",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0558",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C0564",
          "metric_value": 141000.0
        },
        {
          "entity_id": "C0570",
          "metric_value": 108000.0
        },
        {
          "entity_id": "C0576",
          "metric_value": 207000.0
        },
        {
          "entity_id": "C0582",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0588",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C0594",
          "metric_value": 136000.0
        },
        {
          "entity_id": "C0600",
          "metric_value": 145000.0
        },
        {
          "entity_id": "C0606",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C0612",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C0618",
          "metric_value": 58000.0
        },
        {
          "entity_id": "C0624",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C0630",
          "metric_value": 114000.0
        },
        {
          "entity_id": "C0636",
          "metric_value": 39000.0
        },
        {
          "entity_id": "C0642",
          "metric_value": 78000.0
        },
        {
          "entity_id": "C0648",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C0654",
          "metric_value": 42000.0
        },
        {
          "entity_id": "C0660",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C0666",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0672",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C0678",
          "metric_value": 233000.0
        },
        {
          "entity_id": "C0684",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C0690",
          "metric_value": 168000.0
        },
        {
          "entity_id": "C0696",
          "metric_value": 77000.0
        },
        {
          "entity_id": "C0702",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C0708",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C0714",
          "metric_value": 51000.0
        },
        {
          "entity_id": "C0720",
          "metric_value": 68000.0
        },
        {
          "entity_id": "C0726",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C0732",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0738",
          "metric_value": 38000.0
        },
        {
          "entity_id": "C0744",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0750",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C0756",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C0762",
          "metric_value": 70000.0
        },
        {
          "entity_id": "C0768",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C0774",
          "metric_value": 117000.0
        },
        {
          "entity_id": "C0780",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0786",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0792",
          "metric_value": 87000.0
        },
        {
          "entity_id": "C0798",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0804",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0810",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C0816",
          "metric_value": 46000.0
        },
        {
          "entity_id": "C0822",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C0828",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C0834",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0840",
          "metric_value": 221000.0
        },
        {
          "entity_id": "C0846",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C0852",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0858",
          "metric_value": 195000.0
        },
        {
          "entity_id": "C0864",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0870",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C0876",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C0882",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0888",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0894",
          "metric_value": 80000.0
        },
        {
          "entity_id": "C0900",
          "metric_value": 45000.0
        },
        {
          "entity_id": "C0906",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C0912",
          "metric_value": 24000.0
        },
        {
          "entity_id": "C0918",
          "metric_value": 91000.0
        },
        {
          "entity_id": "C0924",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C0930",
          "metric_value": 115000.0
        },
        {
          "entity_id": "C0936",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C0942",
          "metric_value": 214000.0
        },
        {
          "entity_id": "C0948",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C0954",
          "metric_value": 146000.0
        },
        {
          "entity_id": "C0960",
          "metric_value": 84000.0
        },
        {
          "entity_id": "C0966",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0972",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0978",
          "metric_value": 229000.0
        },
        {
          "entity_id": "C0984",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0990",
          "metric_value": 50000.0
        },
        {
          "entity_id": "C0996",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C1002",
          "metric_value": 88000.0
        },
        {
          "entity_id": "C1008",
          "metric_value": 99000.0
        },
        {
          "entity_id": "C1014",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1020",
          "metric_value": 78000.0
        },
        {
          "entity_id": "C1026",
          "metric_value": 228000.0
        },
        {
          "entity_id": "C1032",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C1038",
          "metric_value": 58000.0
        },
        {
          "entity_id": "C1044",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C1050",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C1056",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C1062",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C1068",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1074",
          "metric_value": 73000.0
        },
        {
          "entity_id": "C1080",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C1086",
          "metric_value": 228000.0
        },
        {
          "entity_id": "C1092",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C1098",
          "metric_value": 108000.0
        },
        {
          "entity_id": "C1104",
          "metric_value": 237000.0
        },
        {
          "entity_id": "C1110",
          "metric_value": 231000.0
        },
        {
          "entity_id": "C1116",
          "metric_value": 209000.0
        },
        {
          "entity_id": "C1122",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C1128",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C1134",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1140",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C1146",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C1152",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C1158",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1164",
          "metric_value": 71000.0
        },
        {
          "entity_id": "C1170",
          "metric_value": 178000.0
        },
        {
          "entity_id": "C1176",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C1182",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C1188",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C1194",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C1200",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C1206",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C1212",
          "metric_value": 30000.0
        },
        {
          "entity_id": "C1218",
          "metric_value": 96000.0
        },
        {
          "entity_id": "C1224",
          "metric_value": 220000.0
        },
        {
          "entity_id": "C1230",
          "metric_value": 43000.0
        },
        {
          "entity_id": "C1236",
          "metric_value": 69000.0
        },
        {
          "entity_id": "C1242",
          "metric_value": 84000.0
        },
        {
          "entity_id": "C1248",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C1254",
          "metric_value": 118000.0
        },
        {
          "entity_id": "C1260",
          "metric_value": 178000.0
        },
        {
          "entity_id": "C1266",
          "metric_value": 71000.0
        },
        {
          "entity_id": "C1272",
          "metric_value": 80000.0
        },
        {
          "entity_id": "C1278",
          "metric_value": 155000.0
        },
        {
          "entity_id": "C1284",
          "metric_value": 69000.0
        },
        {
          "entity_id": "C1290",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C1296",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1302",
          "metric_value": 125000.0
        },
        {
          "entity_id": "C1308",
          "metric_value": 98000.0
        },
        {
          "entity_id": "C1314",
          "metric_value": 106000.0
        },
        {
          "entity_id": "C1320",
          "metric_value": 129000.0
        },
        {
          "entity_id": "C1326",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C1332",
          "metric_value": 179000.0
        },
        {
          "entity_id": "C1338",
          "metric_value": 171000.0
        },
        {
          "entity_id": "C1344",
          "metric_value": 214000.0
        },
        {
          "entity_id": "C1350",
          "metric_value": 72000.0
        },
        {
          "entity_id": "C1356",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C1362",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C1368",
          "metric_value": 136000.0
        },
        {
          "entity_id": "C1374",
          "metric_value": 199000.0
        },
        {
          "entity_id": "C1380",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C1386",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C1392",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C1398",
          "metric_value": 210000.0
        },
        {
          "entity_id": "C1404",
          "metric_value": 228000.0
        },
        {
          "entity_id": "C1410",
          "metric_value": 159000.0
        },
        {
          "entity_id": "C1416",
          "metric_value": 172000.0
        },
        {
          "entity_id": "C1422",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C1428",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C1434",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C1440",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C1446",
          "metric_value": 79000.0
        },
        {
          "entity_id": "C1452",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C1458",
          "metric_value": 234000.0
        },
        {
          "entity_id": "C1464",
          "metric_value": 103000.0
        },
        {
          "entity_id": "C1470",
          "metric_value": 30000.0
        },
        {
          "entity_id": "C1476",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C1482",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C1488",
          "metric_value": 233000.0
        },
        {
          "entity_id": "C1494",
          "metric_value": 238000.0
        },
        {
          "entity_id": "C1500",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C1506",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C1512",
          "metric_value": 175000.0
        },
        {
          "entity_id": "C1518",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C1524",
          "metric_value": 187000.0
        },
        {
          "entity_id": "C1530",
          "metric_value": 178000.0
        },
        {
          "entity_id": "C1536",
          "metric_value": 73000.0
        },
        {
          "entity_id": "C1542",
          "metric_value": 96000.0
        },
        {
          "entity_id": "C1548",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C1554",
          "metric_value": 71000.0
        },
        {
          "entity_id": "C1560",
          "metric_value": 207000.0
        },
        {
          "entity_id": "C1566",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1572",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C1578",
          "metric_value": 136000.0
        },
        {
          "entity_id": "C1584",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C1590",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C1596",
          "metric_value": 100000.0
        },
        {
          "entity_id": "C1602",
          "metric_value": 172000.0
        },
        {
          "entity_id": "C1608",
          "metric_value": 129000.0
        },
        {
          "entity_id": "C1614",
          "metric_value": 111000.0
        },
        {
          "entity_id": "C1620",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C1626",
          "metric_value": 236000.0
        },
        {
          "entity_id": "C1632",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C1638",
          "metric_value": 187000.0
        },
        {
          "entity_id": "C1644",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C1650",
          "metric_value": 195000.0
        },
        {
          "entity_id": "C1656",
          "metric_value": 95000.0
        },
        {
          "entity_id": "C1662",
          "metric_value": 180000.0
        },
        {
          "entity_id": "C1668",
          "metric_value": 98000.0
        },
        {
          "entity_id": "C1674",
          "metric_value": 120000.0
        },
        {
          "entity_id": "C1680",
          "metric_value": 213000.0
        },
        {
          "entity_id": "C1686",
          "metric_value": 106000.0
        },
        {
          "entity_id": "C1692",
          "metric_value": 94000.0
        },
        {
          "entity_id": "C1698",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C1704",
          "metric_value": 149000.0
        },
        {
          "entity_id": "C1710",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C1716",
          "metric_value": 49000.0
        },
        {
          "entity_id": "C1722",
          "metric_value": 88000.0
        },
        {
          "entity_id": "C1728",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C1734",
          "metric_value": 99000.0
        },
        {
          "entity_id": "C1740",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C1746",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C1752",
          "metric_value": 204000.0
        },
        {
          "entity_id": "C1758",
          "metric_value": 114000.0
        },
        {
          "entity_id": "C1764",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C1770",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C1776",
          "metric_value": 76000.0
        },
        {
          "entity_id": "C1782",
          "metric_value": 50000.0
        },
        {
          "entity_id": "C1788",
          "metric_value": 159000.0
        },
        {
          "entity_id": "C1794",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C1800",
          "metric_value": 110000.0
        },
        {
          "entity_id": "C1806",
          "metric_value": 91000.0
        },
        {
          "entity_id": "C1812",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C1818",
          "metric_value": 181000.0
        },
        {
          "entity_id": "C1824",
          "metric_value": 176000.0
        },
        {
          "entity_id": "C1830",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C1836",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C1842",
          "metric_value": 51000.0
        },
        {
          "entity_id": "C1848",
          "metric_value": 189000.0
        },
        {
          "entity_id": "C1854",
          "metric_value": 52000.0
        },
        {
          "entity_id": "C1860",
          "metric_value": 240000.0
        },
        {
          "entity_id": "C1866",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1872",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C1878",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C1884",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C1890",
          "metric_value": 211000.0
        },
        {
          "entity_id": "C1896",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C1902",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C1908",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C1914",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C1920",
          "metric_value": 195000.0
        },
        {
          "entity_id": "C1926",
          "metric_value": 122000.0
        },
        {
          "entity_id": "C1932",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C1938",
          "metric_value": 107000.0
        },
        {
          "entity_id": "C1944",
          "metric_value": 225000.0
        },
        {
          "entity_id": "C1950",
          "metric_value": 24000.0
        },
        {
          "entity_id": "C1956",
          "metric_value": 222000.0
        },
        {
          "entity_id": "C1962",
          "metric_value": 208000.0
        },
        {
          "entity_id": "C1968",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C1974",
          "metric_value": 220000.0
        },
        {
          "entity_id": "C1980",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C1986",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C1992",
          "metric_value": 75000.0
        },
        {
          "entity_id": "C1998",
          "metric_value": 124000.0
        }
      ],
      "entity_count": 333,
      "metric_total": 43347000.0,
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
        "C0120",
        "C0123",
        "C0126",
        "C0129",
        "C0132",
        "C0135",
        "C0138",
        "C0141",
        "C0144",
        "C0147",
        "C0150",
        "C0153",
        "C0156",
        "C0159",
        "C0162",
        "C0165",
        "C0168",
        "C0171",
        "C0174",
        "C0177",
        "C0180",
        "C0183",
        "C0186",
        "C0189",
        "C0192",
        "C0195",
        "C0198",
        "C0201",
        "C0204",
        "C0207",
        "C0210",
        "C0213",
        "C0216",
        "C0219",
        "C0222",
        "C0225",
        "C0228",
        "C0231",
        "C0234",
        "C0237",
        "C0240",
        "C0243",
        "C0246",
        "C0249",
        "C0252",
        "C0255",
        "C0258",
        "C0261",
        "C0264",
        "C0267",
        "C0270",
        "C0273",
        "C0276",
        "C0279",
        "C0282",
        "C0285",
        "C0288",
        "C0291",
        "C0294",
        "C0297",
        "C0300",
        "C0303",
        "C0306",
        "C0309",
        "C0312",
        "C0315",
        "C0318",
        "C0321",
        "C0324",
        "C0327",
        "C0330",
        "C0333",
        "C0336",
        "C0339",
        "C0342",
        "C0345",
        "C0348",
        "C0351",
        "C0354",
        "C0357",
        "C0360",
        "C0363",
        "C0366",
        "C0369",
        "C0372",
        "C0375",
        "C0378",
        "C0381",
        "C0384",
        "C0387",
        "C0390",
        "C0393",
        "C0396",
        "C0399",
        "C0402",
        "C0405",
        "C0408",
        "C0411",
        "C0414",
        "C0417",
        "C0420",
        "C0423",
        "C0426",
        "C0429",
        "C0432",
        "C0435",
        "C0438",
        "C0441",
        "C0444",
        "C0447",
        "C0450",
        "C0453",
        "C0456",
        "C0459",
        "C0462",
        "C0465",
        "C0468",
        "C0471",
        "C0474",
        "C0477",
        "C0480",
        "C0483",
        "C0486",
        "C0489",
        "C0492",
        "C0495",
        "C0498",
        "C0501",
        "C0504",
        "C0507",
        "C0510",
        "C0513",
        "C0516",
        "C0519",
        "C0522",
        "C0525",
        "C0528",
        "C0531",
        "C0534",
        "C0537",
        "C0540",
        "C0543",
        "C0546",
        "C0549",
        "C0552",
        "C0555",
        "C0558",
        "C0561",
        "C0564",
        "C0567",
        "C0570",
        "C0573",
        "C0576",
        "C0579",
        "C0582",
        "C0585",
        "C0588",
        "C0591",
        "C0594",
        "C0597",
        "C0600",
        "C0603",
        "C0606",
        "C0609",
        "C0612",
        "C0615",
        "C0618",
        "C0621",
        "C0624",
        "C0627",
        "C0630",
        "C0633",
        "C0636",
        "C0639",
        "C0642",
        "C0645",
        "C0648",
        "C0651",
        "C0654",
        "C0657",
        "C0660",
        "C0663",
        "C0666",
        "C0669",
        "C0672",
        "C0675",
        "C0678",
        "C0681",
        "C0684",
        "C0687",
        "C0690",
        "C0693",
        "C0696",
        "C0699",
        "C0702",
        "C0705",
        "C0708",
        "C0711",
        "C0714",
        "C0717",
        "C0720",
        "C0723",
        "C0726",
        "C0729",
        "C0732",
        "C0735",
        "C0738",
        "C0741",
        "C0744",
        "C0747",
        "C0750",
        "C0753",
        "C0756",
        "C0759",
        "C0762",
        "C0765",
        "C0768",
        "C0771",
        "C0774",
        "C0777",
        "C0780",
        "C0783",
        "C0786",
        "C0789",
        "C0792",
        "C0795",
        "C0798",
        "C0801",
        "C0804",
        "C0807",
        "C0810",
        "C0813",
        "C0816",
        "C0819",
        "C0822",
        "C0825",
        "C0828",
        "C0831",
        "C0834",
        "C0837",
        "C0840",
        "C0843",
        "C0846",
        "C0849",
        "C0852",
        "C0855",
        "C0858",
        "C0861",
        "C0864",
        "C0867",
        "C0870",
        "C0873",
        "C0876",
        "C0879",
        "C0882",
        "C0885",
        "C0888",
        "C0891",
        "C0894",
        "C0897",
        "C0900",
        "C0903",
        "C0906",
        "C0909",
        "C0912",
        "C0915",
        "C0918",
        "C0921",
        "C0924",
        "C0927",
        "C0930",
        "C0933",
        "C0936",
        "C0939",
        "C0942",
        "C0945",
        "C0948",
        "C0951",
        "C0954",
        "C0957",
        "C0960",
        "C0963",
        "C0966",
        "C0969",
        "C0972",
        "C0975",
        "C0978",
        "C0981",
        "C0984",
        "C0987",
        "C0990",
        "C0993",
        "C0996",
        "C0999",
        "C1002",
        "C1005",
        "C1008",
        "C1011",
        "C1014",
        "C1017",
        "C1020",
        "C1023",
        "C1026",
        "C1029",
        "C1032",
        "C1035",
        "C1038",
        "C1041",
        "C1044",
        "C1047",
        "C1050",
        "C1053",
        "C1056",
        "C1059",
        "C1062",
        "C1065",
        "C1068",
        "C1071",
        "C1074",
        "C1077",
        "C1080",
        "C1083",
        "C1086",
        "C1089",
        "C1092",
        "C1095",
        "C1098",
        "C1101",
        "C1104",
        "C1107",
        "C1110",
        "C1113",
        "C1116",
        "C1119",
        "C1122",
        "C1125",
        "C1128",
        "C1131",
        "C1134",
        "C1137",
        "C1140",
        "C1143",
        "C1146",
        "C1149",
        "C1152",
        "C1155",
        "C1158",
        "C1161",
        "C1164",
        "C1167",
        "C1170",
        "C1173",
        "C1176",
        "C1179",
        "C1182",
        "C1185",
        "C1188",
        "C1191",
        "C1194",
        "C1197",
        "C1200",
        "C1203",
        "C1206",
        "C1209",
        "C1212",
        "C1215",
        "C1218",
        "C1221",
        "C1224",
        "C1227",
        "C1230",
        "C1233",
        "C1236",
        "C1239",
        "C1242",
        "C1245",
        "C1248",
        "C1251",
        "C1254",
        "C1257",
        "C1260",
        "C1263",
        "C1266",
        "C1269",
        "C1272",
        "C1275",
        "C1278",
        "C1281",
        "C1284",
        "C1287",
        "C1290",
        "C1293",
        "C1296",
        "C1299",
        "C1302",
        "C1305",
        "C1308",
        "C1311",
        "C1314",
        "C1317",
        "C1320",
        "C1323",
        "C1326",
        "C1329",
        "C1332",
        "C1335",
        "C1338",
        "C1341",
        "C1344",
        "C1347",
        "C1350",
        "C1353",
        "C1356",
        "C1359",
        "C1362",
        "C1365",
        "C1368",
        "C1371",
        "C1374",
        "C1377",
        "C1380",
        "C1383",
        "C1386",
        "C1389",
        "C1392",
        "C1395",
        "C1398",
        "C1401",
        "C1404",
        "C1407",
        "C1410",
        "C1413",
        "C1416",
        "C1419",
        "C1422",
        "C1425",
        "C1428",
        "C1431",
        "C1434",
        "C1437",
        "C1440",
        "C1443",
        "C1446",
        "C1449",
        "C1452",
        "C1455",
        "C1458",
        "C1461",
        "C1464",
        "C1467",
        "C1470",
        "C1473",
        "C1476",
        "C1479",
        "C1482",
        "C1485",
        "C1488",
        "C1491",
        "C1494",
        "C1497",
        "C1500",
        "C1503",
        "C1506",
        "C1509",
        "C1512",
        "C1515",
        "C1518",
        "C1521",
        "C1524",
        "C1527",
        "C1530",
        "C1533",
        "C1536",
        "C1539",
        "C1542",
        "C1545",
        "C1548",
        "C1551",
        "C1554",
        "C1557",
        "C1560",
        "C1563",
        "C1566",
        "C1569",
        "C1572",
        "C1575",
        "C1578",
        "C1581",
        "C1584",
        "C1587",
        "C1590",
        "C1593",
        "C1596",
        "C1599",
        "C1602",
        "C1605",
        "C1608",
        "C1611",
        "C1614",
        "C1617",
        "C1620",
        "C1623",
        "C1626",
        "C1629",
        "C1632",
        "C1635",
        "C1638",
        "C1641",
        "C1644",
        "C1647",
        "C1650",
        "C1653",
        "C1656",
        "C1659",
        "C1662",
        "C1665",
        "C1668",
        "C1671",
        "C1674",
        "C1677",
        "C1680",
        "C1683",
        "C1686",
        "C1689",
        "C1692",
        "C1695",
        "C1698",
        "C1701",
        "C1704",
        "C1707",
        "C1710",
        "C1713",
        "C1716",
        "C1719",
        "C1722",
        "C1725",
        "C1728",
        "C1731",
        "C1734",
        "C1737",
        "C1740",
        "C1743",
        "C1746",
        "C1749",
        "C1752",
        "C1755",
        "C1758",
        "C1761",
        "C1764",
        "C1767",
        "C1770",
        "C1773",
        "C1776",
        "C1779",
        "C1782",
        "C1785",
        "C1788",
        "C1791",
        "C1794",
        "C1797",
        "C1800",
        "C1803",
        "C1806",
        "C1809",
        "C1812",
        "C1815",
        "C1818",
        "C1821",
        "C1824",
        "C1827",
        "C1830",
        "C1833",
        "C1836",
        "C1839",
        "C1842",
        "C1845",
        "C1848",
        "C1851",
        "C1854",
        "C1857",
        "C1860",
        "C1863",
        "C1866",
        "C1869",
        "C1872",
        "C1875",
        "C1878",
        "C1881",
        "C1884",
        "C1887",
        "C1890",
        "C1893",
        "C1896",
        "C1899",
        "C1902",
        "C1905",
        "C1908",
        "C1911",
        "C1914",
        "C1917",
        "C1920",
        "C1923",
        "C1926",
        "C1929",
        "C1932",
        "C1935",
        "C1938",
        "C1941",
        "C1944",
        "C1947",
        "C1950",
        "C1953",
        "C1956",
        "C1959",
        "C1962",
        "C1965",
        "C1968",
        "C1971",
        "C1974",
        "C1977",
        "C1980",
        "C1983",
        "C1986",
        "C1989",
        "C1992",
        "C1995",
        "C1998"
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
        },
        {
          "entity_id": "C0123",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C0126",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C0129",
          "metric_value": 207000.0
        },
        {
          "entity_id": "C0132",
          "metric_value": 93000.0
        },
        {
          "entity_id": "C0135",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0138",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C0141",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0144",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0147",
          "metric_value": 239000.0
        },
        {
          "entity_id": "C0150",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C0153",
          "metric_value": 135000.0
        },
        {
          "entity_id": "C0156",
          "metric_value": 75000.0
        },
        {
          "entity_id": "C0159",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0162",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C0165",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0168",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0171",
          "metric_value": 58000.0
        },
        {
          "entity_id": "C0174",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0177",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C0180",
          "metric_value": 145000.0
        },
        {
          "entity_id": "C0183",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C0186",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C0189",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0192",
          "metric_value": 230000.0
        },
        {
          "entity_id": "C0195",
          "metric_value": 94000.0
        },
        {
          "entity_id": "C0198",
          "metric_value": 132000.0
        },
        {
          "entity_id": "C0201",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0204",
          "metric_value": 46000.0
        },
        {
          "entity_id": "C0207",
          "metric_value": 219000.0
        },
        {
          "entity_id": "C0210",
          "metric_value": 204000.0
        },
        {
          "entity_id": "C0213",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C0216",
          "metric_value": 122000.0
        },
        {
          "entity_id": "C0219",
          "metric_value": 96000.0
        },
        {
          "entity_id": "C0222",
          "metric_value": 165000.0
        },
        {
          "entity_id": "C0225",
          "metric_value": 171000.0
        },
        {
          "entity_id": "C0228",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0231",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C0234",
          "metric_value": 184000.0
        },
        {
          "entity_id": "C0237",
          "metric_value": 112000.0
        },
        {
          "entity_id": "C0240",
          "metric_value": 24000.0
        },
        {
          "entity_id": "C0243",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C0246",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C0249",
          "metric_value": 236000.0
        },
        {
          "entity_id": "C0252",
          "metric_value": 150000.0
        },
        {
          "entity_id": "C0255",
          "metric_value": 148000.0
        },
        {
          "entity_id": "C0258",
          "metric_value": 149000.0
        },
        {
          "entity_id": "C0261",
          "metric_value": 197000.0
        },
        {
          "entity_id": "C0264",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C0267",
          "metric_value": 53000.0
        },
        {
          "entity_id": "C0270",
          "metric_value": 39000.0
        },
        {
          "entity_id": "C0273",
          "metric_value": 148000.0
        },
        {
          "entity_id": "C0276",
          "metric_value": 222000.0
        },
        {
          "entity_id": "C0279",
          "metric_value": 84000.0
        },
        {
          "entity_id": "C0282",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C0285",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C0288",
          "metric_value": 95000.0
        },
        {
          "entity_id": "C0291",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C0294",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0297",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C0300",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0303",
          "metric_value": 225000.0
        },
        {
          "entity_id": "C0306",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0309",
          "metric_value": 62000.0
        },
        {
          "entity_id": "C0312",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0315",
          "metric_value": 158000.0
        },
        {
          "entity_id": "C0318",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0321",
          "metric_value": 62000.0
        },
        {
          "entity_id": "C0324",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C0327",
          "metric_value": 77000.0
        },
        {
          "entity_id": "C0330",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C0333",
          "metric_value": 158000.0
        },
        {
          "entity_id": "C0336",
          "metric_value": 48000.0
        },
        {
          "entity_id": "C0339",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C0342",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0345",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0348",
          "metric_value": 80000.0
        },
        {
          "entity_id": "C0351",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C0354",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C0357",
          "metric_value": 235000.0
        },
        {
          "entity_id": "C0360",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C0363",
          "metric_value": 214000.0
        },
        {
          "entity_id": "C0366",
          "metric_value": 39000.0
        },
        {
          "entity_id": "C0369",
          "metric_value": 125000.0
        },
        {
          "entity_id": "C0372",
          "metric_value": 141000.0
        },
        {
          "entity_id": "C0375",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0378",
          "metric_value": 199000.0
        },
        {
          "entity_id": "C0381",
          "metric_value": 92000.0
        },
        {
          "entity_id": "C0384",
          "metric_value": 180000.0
        },
        {
          "entity_id": "C0387",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C0390",
          "metric_value": 56000.0
        },
        {
          "entity_id": "C0393",
          "metric_value": 188000.0
        },
        {
          "entity_id": "C0396",
          "metric_value": 199000.0
        },
        {
          "entity_id": "C0399",
          "metric_value": 166000.0
        },
        {
          "entity_id": "C0402",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0405",
          "metric_value": 174000.0
        },
        {
          "entity_id": "C0408",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C0411",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C0414",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C0417",
          "metric_value": 146000.0
        },
        {
          "entity_id": "C0420",
          "metric_value": 134000.0
        },
        {
          "entity_id": "C0423",
          "metric_value": 35000.0
        },
        {
          "entity_id": "C0426",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0429",
          "metric_value": 209000.0
        },
        {
          "entity_id": "C0432",
          "metric_value": 68000.0
        },
        {
          "entity_id": "C0435",
          "metric_value": 148000.0
        },
        {
          "entity_id": "C0438",
          "metric_value": 100000.0
        },
        {
          "entity_id": "C0441",
          "metric_value": 131000.0
        },
        {
          "entity_id": "C0444",
          "metric_value": 124000.0
        },
        {
          "entity_id": "C0447",
          "metric_value": 221000.0
        },
        {
          "entity_id": "C0450",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0453",
          "metric_value": 51000.0
        },
        {
          "entity_id": "C0456",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C0459",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C0462",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0465",
          "metric_value": 152000.0
        },
        {
          "entity_id": "C0468",
          "metric_value": 49000.0
        },
        {
          "entity_id": "C0471",
          "metric_value": 165000.0
        },
        {
          "entity_id": "C0474",
          "metric_value": 213000.0
        },
        {
          "entity_id": "C0477",
          "metric_value": 43000.0
        },
        {
          "entity_id": "C0480",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0483",
          "metric_value": 143000.0
        },
        {
          "entity_id": "C0486",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C0489",
          "metric_value": 110000.0
        },
        {
          "entity_id": "C0492",
          "metric_value": 99000.0
        },
        {
          "entity_id": "C0495",
          "metric_value": 93000.0
        },
        {
          "entity_id": "C0498",
          "metric_value": 34000.0
        },
        {
          "entity_id": "C0501",
          "metric_value": 74000.0
        },
        {
          "entity_id": "C0504",
          "metric_value": 118000.0
        },
        {
          "entity_id": "C0507",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C0510",
          "metric_value": 155000.0
        },
        {
          "entity_id": "C0513",
          "metric_value": 198000.0
        },
        {
          "entity_id": "C0516",
          "metric_value": 132000.0
        },
        {
          "entity_id": "C0519",
          "metric_value": 93000.0
        },
        {
          "entity_id": "C0522",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0525",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C0528",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C0531",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C0534",
          "metric_value": 110000.0
        },
        {
          "entity_id": "C0537",
          "metric_value": 197000.0
        },
        {
          "entity_id": "C0540",
          "metric_value": 31000.0
        },
        {
          "entity_id": "C0543",
          "metric_value": 232000.0
        },
        {
          "entity_id": "C0546",
          "metric_value": 49000.0
        },
        {
          "entity_id": "C0549",
          "metric_value": 88000.0
        },
        {
          "entity_id": "C0552",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0555",
          "metric_value": 98000.0
        },
        {
          "entity_id": "C0558",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C0561",
          "metric_value": 210000.0
        },
        {
          "entity_id": "C0564",
          "metric_value": 141000.0
        },
        {
          "entity_id": "C0567",
          "metric_value": 93000.0
        },
        {
          "entity_id": "C0570",
          "metric_value": 108000.0
        },
        {
          "entity_id": "C0573",
          "metric_value": 111000.0
        },
        {
          "entity_id": "C0576",
          "metric_value": 207000.0
        },
        {
          "entity_id": "C0579",
          "metric_value": 98000.0
        },
        {
          "entity_id": "C0582",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C0585",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C0588",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C0591",
          "metric_value": 87000.0
        },
        {
          "entity_id": "C0594",
          "metric_value": 136000.0
        },
        {
          "entity_id": "C0597",
          "metric_value": 97000.0
        },
        {
          "entity_id": "C0600",
          "metric_value": 145000.0
        },
        {
          "entity_id": "C0603",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C0606",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C0609",
          "metric_value": 59000.0
        },
        {
          "entity_id": "C0612",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C0615",
          "metric_value": 149000.0
        },
        {
          "entity_id": "C0618",
          "metric_value": 58000.0
        },
        {
          "entity_id": "C0621",
          "metric_value": 197000.0
        },
        {
          "entity_id": "C0624",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C0627",
          "metric_value": 175000.0
        },
        {
          "entity_id": "C0630",
          "metric_value": 114000.0
        },
        {
          "entity_id": "C0633",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C0636",
          "metric_value": 39000.0
        },
        {
          "entity_id": "C0639",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C0642",
          "metric_value": 78000.0
        },
        {
          "entity_id": "C0645",
          "metric_value": 107000.0
        },
        {
          "entity_id": "C0648",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C0651",
          "metric_value": 112000.0
        },
        {
          "entity_id": "C0654",
          "metric_value": 42000.0
        },
        {
          "entity_id": "C0657",
          "metric_value": 165000.0
        },
        {
          "entity_id": "C0660",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C0663",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C0666",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0669",
          "metric_value": 168000.0
        },
        {
          "entity_id": "C0672",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C0675",
          "metric_value": 57000.0
        },
        {
          "entity_id": "C0678",
          "metric_value": 233000.0
        },
        {
          "entity_id": "C0681",
          "metric_value": 34000.0
        },
        {
          "entity_id": "C0684",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C0687",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C0690",
          "metric_value": 168000.0
        },
        {
          "entity_id": "C0693",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C0696",
          "metric_value": 77000.0
        },
        {
          "entity_id": "C0699",
          "metric_value": 74000.0
        },
        {
          "entity_id": "C0702",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C0705",
          "metric_value": 39000.0
        },
        {
          "entity_id": "C0708",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C0711",
          "metric_value": 80000.0
        },
        {
          "entity_id": "C0714",
          "metric_value": 51000.0
        },
        {
          "entity_id": "C0717",
          "metric_value": 177000.0
        },
        {
          "entity_id": "C0720",
          "metric_value": 68000.0
        },
        {
          "entity_id": "C0723",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C0726",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C0729",
          "metric_value": 51000.0
        },
        {
          "entity_id": "C0732",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0735",
          "metric_value": 197000.0
        },
        {
          "entity_id": "C0738",
          "metric_value": 38000.0
        },
        {
          "entity_id": "C0741",
          "metric_value": 118000.0
        },
        {
          "entity_id": "C0744",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C0747",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C0750",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C0753",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C0756",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C0759",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C0762",
          "metric_value": 70000.0
        },
        {
          "entity_id": "C0765",
          "metric_value": 131000.0
        },
        {
          "entity_id": "C0768",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C0771",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C0774",
          "metric_value": 117000.0
        },
        {
          "entity_id": "C0777",
          "metric_value": 132000.0
        },
        {
          "entity_id": "C0780",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0783",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C0786",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0789",
          "metric_value": 85000.0
        },
        {
          "entity_id": "C0792",
          "metric_value": 87000.0
        },
        {
          "entity_id": "C0795",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C0798",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C0801",
          "metric_value": 107000.0
        },
        {
          "entity_id": "C0804",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0807",
          "metric_value": 74000.0
        },
        {
          "entity_id": "C0810",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C0813",
          "metric_value": 27000.0
        },
        {
          "entity_id": "C0816",
          "metric_value": 46000.0
        },
        {
          "entity_id": "C0819",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0822",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C0825",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C0828",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C0831",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0834",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0837",
          "metric_value": 144000.0
        },
        {
          "entity_id": "C0840",
          "metric_value": 221000.0
        },
        {
          "entity_id": "C0843",
          "metric_value": 83000.0
        },
        {
          "entity_id": "C0846",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C0849",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0852",
          "metric_value": 173000.0
        },
        {
          "entity_id": "C0855",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C0858",
          "metric_value": 195000.0
        },
        {
          "entity_id": "C0861",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0864",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0867",
          "metric_value": 234000.0
        },
        {
          "entity_id": "C0870",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C0873",
          "metric_value": 34000.0
        },
        {
          "entity_id": "C0876",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C0879",
          "metric_value": 176000.0
        },
        {
          "entity_id": "C0882",
          "metric_value": 113000.0
        },
        {
          "entity_id": "C0885",
          "metric_value": 54000.0
        },
        {
          "entity_id": "C0888",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C0891",
          "metric_value": 110000.0
        },
        {
          "entity_id": "C0894",
          "metric_value": 80000.0
        },
        {
          "entity_id": "C0897",
          "metric_value": 119000.0
        },
        {
          "entity_id": "C0900",
          "metric_value": 45000.0
        },
        {
          "entity_id": "C0903",
          "metric_value": 24000.0
        },
        {
          "entity_id": "C0906",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C0909",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C0912",
          "metric_value": 24000.0
        },
        {
          "entity_id": "C0915",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C0918",
          "metric_value": 91000.0
        },
        {
          "entity_id": "C0921",
          "metric_value": 166000.0
        },
        {
          "entity_id": "C0924",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C0927",
          "metric_value": 136000.0
        },
        {
          "entity_id": "C0930",
          "metric_value": 115000.0
        },
        {
          "entity_id": "C0933",
          "metric_value": 69000.0
        },
        {
          "entity_id": "C0936",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C0939",
          "metric_value": 85000.0
        },
        {
          "entity_id": "C0942",
          "metric_value": 214000.0
        },
        {
          "entity_id": "C0945",
          "metric_value": 37000.0
        },
        {
          "entity_id": "C0948",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C0951",
          "metric_value": 225000.0
        },
        {
          "entity_id": "C0954",
          "metric_value": 146000.0
        },
        {
          "entity_id": "C0957",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C0960",
          "metric_value": 84000.0
        },
        {
          "entity_id": "C0963",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C0966",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C0969",
          "metric_value": 181000.0
        },
        {
          "entity_id": "C0972",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C0975",
          "metric_value": 60000.0
        },
        {
          "entity_id": "C0978",
          "metric_value": 229000.0
        },
        {
          "entity_id": "C0981",
          "metric_value": 156000.0
        },
        {
          "entity_id": "C0984",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C0987",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C0990",
          "metric_value": 50000.0
        },
        {
          "entity_id": "C0993",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C0996",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C0999",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C1002",
          "metric_value": 88000.0
        },
        {
          "entity_id": "C1005",
          "metric_value": 208000.0
        },
        {
          "entity_id": "C1008",
          "metric_value": 99000.0
        },
        {
          "entity_id": "C1011",
          "metric_value": 25000.0
        },
        {
          "entity_id": "C1014",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1017",
          "metric_value": 134000.0
        },
        {
          "entity_id": "C1020",
          "metric_value": 78000.0
        },
        {
          "entity_id": "C1023",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C1026",
          "metric_value": 228000.0
        },
        {
          "entity_id": "C1029",
          "metric_value": 57000.0
        },
        {
          "entity_id": "C1032",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C1035",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C1038",
          "metric_value": 58000.0
        },
        {
          "entity_id": "C1041",
          "metric_value": 203000.0
        },
        {
          "entity_id": "C1044",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C1047",
          "metric_value": 137000.0
        },
        {
          "entity_id": "C1050",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C1053",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C1056",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C1059",
          "metric_value": 88000.0
        },
        {
          "entity_id": "C1062",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C1065",
          "metric_value": 131000.0
        },
        {
          "entity_id": "C1068",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1071",
          "metric_value": 236000.0
        },
        {
          "entity_id": "C1074",
          "metric_value": 73000.0
        },
        {
          "entity_id": "C1077",
          "metric_value": 95000.0
        },
        {
          "entity_id": "C1080",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C1083",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C1086",
          "metric_value": 228000.0
        },
        {
          "entity_id": "C1089",
          "metric_value": 58000.0
        },
        {
          "entity_id": "C1092",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C1095",
          "metric_value": 237000.0
        },
        {
          "entity_id": "C1098",
          "metric_value": 108000.0
        },
        {
          "entity_id": "C1101",
          "metric_value": 40000.0
        },
        {
          "entity_id": "C1104",
          "metric_value": 237000.0
        },
        {
          "entity_id": "C1107",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C1110",
          "metric_value": 231000.0
        },
        {
          "entity_id": "C1113",
          "metric_value": 183000.0
        },
        {
          "entity_id": "C1116",
          "metric_value": 209000.0
        },
        {
          "entity_id": "C1119",
          "metric_value": 45000.0
        },
        {
          "entity_id": "C1122",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C1125",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C1128",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C1131",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C1134",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1137",
          "metric_value": 111000.0
        },
        {
          "entity_id": "C1140",
          "metric_value": 121000.0
        },
        {
          "entity_id": "C1143",
          "metric_value": 218000.0
        },
        {
          "entity_id": "C1146",
          "metric_value": 160000.0
        },
        {
          "entity_id": "C1149",
          "metric_value": 219000.0
        },
        {
          "entity_id": "C1152",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C1155",
          "metric_value": 93000.0
        },
        {
          "entity_id": "C1158",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1161",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C1164",
          "metric_value": 71000.0
        },
        {
          "entity_id": "C1167",
          "metric_value": 194000.0
        },
        {
          "entity_id": "C1170",
          "metric_value": 178000.0
        },
        {
          "entity_id": "C1173",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C1176",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C1179",
          "metric_value": 148000.0
        },
        {
          "entity_id": "C1182",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C1185",
          "metric_value": 87000.0
        },
        {
          "entity_id": "C1188",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C1191",
          "metric_value": 214000.0
        },
        {
          "entity_id": "C1194",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C1197",
          "metric_value": 90000.0
        },
        {
          "entity_id": "C1200",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C1203",
          "metric_value": 194000.0
        },
        {
          "entity_id": "C1206",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C1209",
          "metric_value": 176000.0
        },
        {
          "entity_id": "C1212",
          "metric_value": 30000.0
        },
        {
          "entity_id": "C1215",
          "metric_value": 195000.0
        },
        {
          "entity_id": "C1218",
          "metric_value": 96000.0
        },
        {
          "entity_id": "C1221",
          "metric_value": 209000.0
        },
        {
          "entity_id": "C1224",
          "metric_value": 220000.0
        },
        {
          "entity_id": "C1227",
          "metric_value": 79000.0
        },
        {
          "entity_id": "C1230",
          "metric_value": 43000.0
        },
        {
          "entity_id": "C1233",
          "metric_value": 120000.0
        },
        {
          "entity_id": "C1236",
          "metric_value": 69000.0
        },
        {
          "entity_id": "C1239",
          "metric_value": 94000.0
        },
        {
          "entity_id": "C1242",
          "metric_value": 84000.0
        },
        {
          "entity_id": "C1245",
          "metric_value": 236000.0
        },
        {
          "entity_id": "C1248",
          "metric_value": 104000.0
        },
        {
          "entity_id": "C1251",
          "metric_value": 177000.0
        },
        {
          "entity_id": "C1254",
          "metric_value": 118000.0
        },
        {
          "entity_id": "C1257",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C1260",
          "metric_value": 178000.0
        },
        {
          "entity_id": "C1263",
          "metric_value": 175000.0
        },
        {
          "entity_id": "C1266",
          "metric_value": 71000.0
        },
        {
          "entity_id": "C1269",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C1272",
          "metric_value": 80000.0
        },
        {
          "entity_id": "C1275",
          "metric_value": 115000.0
        },
        {
          "entity_id": "C1278",
          "metric_value": 155000.0
        },
        {
          "entity_id": "C1281",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C1284",
          "metric_value": 69000.0
        },
        {
          "entity_id": "C1287",
          "metric_value": 127000.0
        },
        {
          "entity_id": "C1290",
          "metric_value": 157000.0
        },
        {
          "entity_id": "C1293",
          "metric_value": 171000.0
        },
        {
          "entity_id": "C1296",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1299",
          "metric_value": 41000.0
        },
        {
          "entity_id": "C1302",
          "metric_value": 125000.0
        },
        {
          "entity_id": "C1305",
          "metric_value": 114000.0
        },
        {
          "entity_id": "C1308",
          "metric_value": 98000.0
        },
        {
          "entity_id": "C1311",
          "metric_value": 26000.0
        },
        {
          "entity_id": "C1314",
          "metric_value": 106000.0
        },
        {
          "entity_id": "C1317",
          "metric_value": 144000.0
        },
        {
          "entity_id": "C1320",
          "metric_value": 129000.0
        },
        {
          "entity_id": "C1323",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C1326",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C1329",
          "metric_value": 152000.0
        },
        {
          "entity_id": "C1332",
          "metric_value": 179000.0
        },
        {
          "entity_id": "C1335",
          "metric_value": 30000.0
        },
        {
          "entity_id": "C1338",
          "metric_value": 171000.0
        },
        {
          "entity_id": "C1341",
          "metric_value": 192000.0
        },
        {
          "entity_id": "C1344",
          "metric_value": 214000.0
        },
        {
          "entity_id": "C1347",
          "metric_value": 37000.0
        },
        {
          "entity_id": "C1350",
          "metric_value": 72000.0
        },
        {
          "entity_id": "C1353",
          "metric_value": 72000.0
        },
        {
          "entity_id": "C1356",
          "metric_value": 185000.0
        },
        {
          "entity_id": "C1359",
          "metric_value": 82000.0
        },
        {
          "entity_id": "C1362",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C1365",
          "metric_value": 129000.0
        },
        {
          "entity_id": "C1368",
          "metric_value": 136000.0
        },
        {
          "entity_id": "C1371",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C1374",
          "metric_value": 199000.0
        },
        {
          "entity_id": "C1377",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C1380",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C1383",
          "metric_value": 232000.0
        },
        {
          "entity_id": "C1386",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C1389",
          "metric_value": 37000.0
        },
        {
          "entity_id": "C1392",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C1395",
          "metric_value": 149000.0
        },
        {
          "entity_id": "C1398",
          "metric_value": 210000.0
        },
        {
          "entity_id": "C1401",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1404",
          "metric_value": 228000.0
        },
        {
          "entity_id": "C1407",
          "metric_value": 30000.0
        },
        {
          "entity_id": "C1410",
          "metric_value": 159000.0
        },
        {
          "entity_id": "C1413",
          "metric_value": 112000.0
        },
        {
          "entity_id": "C1416",
          "metric_value": 172000.0
        },
        {
          "entity_id": "C1419",
          "metric_value": 106000.0
        },
        {
          "entity_id": "C1422",
          "metric_value": 182000.0
        },
        {
          "entity_id": "C1425",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C1428",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C1431",
          "metric_value": 58000.0
        },
        {
          "entity_id": "C1434",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C1437",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C1440",
          "metric_value": 193000.0
        },
        {
          "entity_id": "C1443",
          "metric_value": 190000.0
        },
        {
          "entity_id": "C1446",
          "metric_value": 79000.0
        },
        {
          "entity_id": "C1449",
          "metric_value": 92000.0
        },
        {
          "entity_id": "C1452",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C1455",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C1458",
          "metric_value": 234000.0
        },
        {
          "entity_id": "C1461",
          "metric_value": 191000.0
        },
        {
          "entity_id": "C1464",
          "metric_value": 103000.0
        },
        {
          "entity_id": "C1467",
          "metric_value": 239000.0
        },
        {
          "entity_id": "C1470",
          "metric_value": 30000.0
        },
        {
          "entity_id": "C1473",
          "metric_value": 138000.0
        },
        {
          "entity_id": "C1476",
          "metric_value": 116000.0
        },
        {
          "entity_id": "C1479",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C1482",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C1485",
          "metric_value": 91000.0
        },
        {
          "entity_id": "C1488",
          "metric_value": 233000.0
        },
        {
          "entity_id": "C1491",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C1494",
          "metric_value": 238000.0
        },
        {
          "entity_id": "C1497",
          "metric_value": 50000.0
        },
        {
          "entity_id": "C1500",
          "metric_value": 109000.0
        },
        {
          "entity_id": "C1503",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C1506",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C1509",
          "metric_value": 208000.0
        },
        {
          "entity_id": "C1512",
          "metric_value": 175000.0
        },
        {
          "entity_id": "C1515",
          "metric_value": 88000.0
        },
        {
          "entity_id": "C1518",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C1521",
          "metric_value": 63000.0
        },
        {
          "entity_id": "C1524",
          "metric_value": 187000.0
        },
        {
          "entity_id": "C1527",
          "metric_value": 174000.0
        },
        {
          "entity_id": "C1530",
          "metric_value": 178000.0
        },
        {
          "entity_id": "C1533",
          "metric_value": 226000.0
        },
        {
          "entity_id": "C1536",
          "metric_value": 73000.0
        },
        {
          "entity_id": "C1539",
          "metric_value": 184000.0
        },
        {
          "entity_id": "C1542",
          "metric_value": 96000.0
        },
        {
          "entity_id": "C1545",
          "metric_value": 81000.0
        },
        {
          "entity_id": "C1548",
          "metric_value": 29000.0
        },
        {
          "entity_id": "C1551",
          "metric_value": 237000.0
        },
        {
          "entity_id": "C1554",
          "metric_value": 71000.0
        },
        {
          "entity_id": "C1557",
          "metric_value": 85000.0
        },
        {
          "entity_id": "C1560",
          "metric_value": 207000.0
        },
        {
          "entity_id": "C1563",
          "metric_value": 236000.0
        },
        {
          "entity_id": "C1566",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1569",
          "metric_value": 203000.0
        },
        {
          "entity_id": "C1572",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C1575",
          "metric_value": 105000.0
        },
        {
          "entity_id": "C1578",
          "metric_value": 136000.0
        },
        {
          "entity_id": "C1581",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C1584",
          "metric_value": 223000.0
        },
        {
          "entity_id": "C1587",
          "metric_value": 94000.0
        },
        {
          "entity_id": "C1590",
          "metric_value": 133000.0
        },
        {
          "entity_id": "C1593",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C1596",
          "metric_value": 100000.0
        },
        {
          "entity_id": "C1599",
          "metric_value": 49000.0
        },
        {
          "entity_id": "C1602",
          "metric_value": 172000.0
        },
        {
          "entity_id": "C1605",
          "metric_value": 108000.0
        },
        {
          "entity_id": "C1608",
          "metric_value": 129000.0
        },
        {
          "entity_id": "C1611",
          "metric_value": 129000.0
        },
        {
          "entity_id": "C1614",
          "metric_value": 111000.0
        },
        {
          "entity_id": "C1617",
          "metric_value": 72000.0
        },
        {
          "entity_id": "C1620",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C1623",
          "metric_value": 227000.0
        },
        {
          "entity_id": "C1626",
          "metric_value": 236000.0
        },
        {
          "entity_id": "C1629",
          "metric_value": 225000.0
        },
        {
          "entity_id": "C1632",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C1635",
          "metric_value": 117000.0
        },
        {
          "entity_id": "C1638",
          "metric_value": 187000.0
        },
        {
          "entity_id": "C1641",
          "metric_value": 91000.0
        },
        {
          "entity_id": "C1644",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C1647",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C1650",
          "metric_value": 195000.0
        },
        {
          "entity_id": "C1653",
          "metric_value": 115000.0
        },
        {
          "entity_id": "C1656",
          "metric_value": 95000.0
        },
        {
          "entity_id": "C1659",
          "metric_value": 166000.0
        },
        {
          "entity_id": "C1662",
          "metric_value": 180000.0
        },
        {
          "entity_id": "C1665",
          "metric_value": 114000.0
        },
        {
          "entity_id": "C1668",
          "metric_value": 98000.0
        },
        {
          "entity_id": "C1671",
          "metric_value": 167000.0
        },
        {
          "entity_id": "C1674",
          "metric_value": 120000.0
        },
        {
          "entity_id": "C1677",
          "metric_value": 76000.0
        },
        {
          "entity_id": "C1680",
          "metric_value": 213000.0
        },
        {
          "entity_id": "C1683",
          "metric_value": 125000.0
        },
        {
          "entity_id": "C1686",
          "metric_value": 106000.0
        },
        {
          "entity_id": "C1689",
          "metric_value": 112000.0
        },
        {
          "entity_id": "C1692",
          "metric_value": 94000.0
        },
        {
          "entity_id": "C1695",
          "metric_value": 70000.0
        },
        {
          "entity_id": "C1698",
          "metric_value": 200000.0
        },
        {
          "entity_id": "C1701",
          "metric_value": 31000.0
        },
        {
          "entity_id": "C1704",
          "metric_value": 149000.0
        },
        {
          "entity_id": "C1707",
          "metric_value": 42000.0
        },
        {
          "entity_id": "C1710",
          "metric_value": 139000.0
        },
        {
          "entity_id": "C1713",
          "metric_value": 172000.0
        },
        {
          "entity_id": "C1716",
          "metric_value": 49000.0
        },
        {
          "entity_id": "C1719",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C1722",
          "metric_value": 88000.0
        },
        {
          "entity_id": "C1725",
          "metric_value": 110000.0
        },
        {
          "entity_id": "C1728",
          "metric_value": 64000.0
        },
        {
          "entity_id": "C1731",
          "metric_value": 196000.0
        },
        {
          "entity_id": "C1734",
          "metric_value": 99000.0
        },
        {
          "entity_id": "C1737",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C1740",
          "metric_value": 102000.0
        },
        {
          "entity_id": "C1743",
          "metric_value": 59000.0
        },
        {
          "entity_id": "C1746",
          "metric_value": 86000.0
        },
        {
          "entity_id": "C1749",
          "metric_value": 33000.0
        },
        {
          "entity_id": "C1752",
          "metric_value": 204000.0
        },
        {
          "entity_id": "C1755",
          "metric_value": 82000.0
        },
        {
          "entity_id": "C1758",
          "metric_value": 114000.0
        },
        {
          "entity_id": "C1761",
          "metric_value": 154000.0
        },
        {
          "entity_id": "C1764",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C1767",
          "metric_value": 44000.0
        },
        {
          "entity_id": "C1770",
          "metric_value": 217000.0
        },
        {
          "entity_id": "C1773",
          "metric_value": 70000.0
        },
        {
          "entity_id": "C1776",
          "metric_value": 76000.0
        },
        {
          "entity_id": "C1779",
          "metric_value": 238000.0
        },
        {
          "entity_id": "C1782",
          "metric_value": 50000.0
        },
        {
          "entity_id": "C1785",
          "metric_value": 74000.0
        },
        {
          "entity_id": "C1788",
          "metric_value": 159000.0
        },
        {
          "entity_id": "C1791",
          "metric_value": 151000.0
        },
        {
          "entity_id": "C1794",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C1797",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C1800",
          "metric_value": 110000.0
        },
        {
          "entity_id": "C1803",
          "metric_value": 106000.0
        },
        {
          "entity_id": "C1806",
          "metric_value": 91000.0
        },
        {
          "entity_id": "C1809",
          "metric_value": 211000.0
        },
        {
          "entity_id": "C1812",
          "metric_value": 216000.0
        },
        {
          "entity_id": "C1815",
          "metric_value": 140000.0
        },
        {
          "entity_id": "C1818",
          "metric_value": 181000.0
        },
        {
          "entity_id": "C1821",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C1824",
          "metric_value": 176000.0
        },
        {
          "entity_id": "C1827",
          "metric_value": 170000.0
        },
        {
          "entity_id": "C1830",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C1833",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C1836",
          "metric_value": 55000.0
        },
        {
          "entity_id": "C1839",
          "metric_value": 189000.0
        },
        {
          "entity_id": "C1842",
          "metric_value": 51000.0
        },
        {
          "entity_id": "C1845",
          "metric_value": 62000.0
        },
        {
          "entity_id": "C1848",
          "metric_value": 189000.0
        },
        {
          "entity_id": "C1851",
          "metric_value": 124000.0
        },
        {
          "entity_id": "C1854",
          "metric_value": 52000.0
        },
        {
          "entity_id": "C1857",
          "metric_value": 208000.0
        },
        {
          "entity_id": "C1860",
          "metric_value": 240000.0
        },
        {
          "entity_id": "C1863",
          "metric_value": 210000.0
        },
        {
          "entity_id": "C1866",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1869",
          "metric_value": 50000.0
        },
        {
          "entity_id": "C1872",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C1875",
          "metric_value": 66000.0
        },
        {
          "entity_id": "C1878",
          "metric_value": 186000.0
        },
        {
          "entity_id": "C1881",
          "metric_value": 45000.0
        },
        {
          "entity_id": "C1884",
          "metric_value": 36000.0
        },
        {
          "entity_id": "C1887",
          "metric_value": 79000.0
        },
        {
          "entity_id": "C1890",
          "metric_value": 211000.0
        },
        {
          "entity_id": "C1893",
          "metric_value": 212000.0
        },
        {
          "entity_id": "C1896",
          "metric_value": 205000.0
        },
        {
          "entity_id": "C1899",
          "metric_value": 34000.0
        },
        {
          "entity_id": "C1902",
          "metric_value": 89000.0
        },
        {
          "entity_id": "C1905",
          "metric_value": 146000.0
        },
        {
          "entity_id": "C1908",
          "metric_value": 65000.0
        },
        {
          "entity_id": "C1911",
          "metric_value": 108000.0
        },
        {
          "entity_id": "C1914",
          "metric_value": 47000.0
        },
        {
          "entity_id": "C1917",
          "metric_value": 123000.0
        },
        {
          "entity_id": "C1920",
          "metric_value": 195000.0
        },
        {
          "entity_id": "C1923",
          "metric_value": 225000.0
        },
        {
          "entity_id": "C1926",
          "metric_value": 122000.0
        },
        {
          "entity_id": "C1929",
          "metric_value": 27000.0
        },
        {
          "entity_id": "C1932",
          "metric_value": 161000.0
        },
        {
          "entity_id": "C1935",
          "metric_value": 81000.0
        },
        {
          "entity_id": "C1938",
          "metric_value": 107000.0
        },
        {
          "entity_id": "C1941",
          "metric_value": 224000.0
        },
        {
          "entity_id": "C1944",
          "metric_value": 225000.0
        },
        {
          "entity_id": "C1947",
          "metric_value": 62000.0
        },
        {
          "entity_id": "C1950",
          "metric_value": 24000.0
        },
        {
          "entity_id": "C1953",
          "metric_value": 71000.0
        },
        {
          "entity_id": "C1956",
          "metric_value": 222000.0
        },
        {
          "entity_id": "C1959",
          "metric_value": 142000.0
        },
        {
          "entity_id": "C1962",
          "metric_value": 208000.0
        },
        {
          "entity_id": "C1965",
          "metric_value": 213000.0
        },
        {
          "entity_id": "C1968",
          "metric_value": 169000.0
        },
        {
          "entity_id": "C1971",
          "metric_value": 32000.0
        },
        {
          "entity_id": "C1974",
          "metric_value": 220000.0
        },
        {
          "entity_id": "C1977",
          "metric_value": 126000.0
        },
        {
          "entity_id": "C1980",
          "metric_value": 206000.0
        },
        {
          "entity_id": "C1983",
          "metric_value": 163000.0
        },
        {
          "entity_id": "C1986",
          "metric_value": 153000.0
        },
        {
          "entity_id": "C1989",
          "metric_value": 237000.0
        },
        {
          "entity_id": "C1992",
          "metric_value": 75000.0
        },
        {
          "entity_id": "C1995",
          "metric_value": 202000.0
        },
        {
          "entity_id": "C1998",
          "metric_value": 124000.0
        }
      ],
      "entity_count": 666,
      "metric_total": 86040000.0,
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
