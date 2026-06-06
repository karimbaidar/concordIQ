# Concord IQ ontology seed

This is a synthetic, human-readable seed for a tiny Fabric ontology. Use the
snapshot documents as semantic evidence and the CSV files as definition and
authority reference data.

## Business concepts

- **Active Customer** (`active_customer`): A customer included in current operating and board-level activity reporting.
- **Net Revenue** (`net_revenue`): Recognized recurring revenue in the selected analytical period.
- **Churned Customer** (`churned_customer`): A customer treated as lost for retention and financial reporting.

## Entity and concept nodes

- `active_customer`: Active Customer (business_concept)
- `churn_event`: Churn Event (entity_type)
- `churned_customer`: Churned Customer (business_concept)
- `contract`: Contract (entity_type)
- `customer`: Customer (entity_type)
- `net_revenue`: Net Revenue (business_concept)
- `opportunity`: Opportunity (entity_type)
- `revenue_event`: Revenue Event (entity_type)
- `usage_event`: Usage Event (entity_type)

## Relationships

- `active_customer` --derived_from--> `contract`
- `active_customer` --derived_from--> `opportunity`
- `active_customer` --derived_from--> `revenue_event`
- `active_customer` --derived_from--> `usage_event`
- `active_customer` --selects--> `customer`
- `churned_customer` --derived_from--> `contract`
- `churned_customer` --derived_from--> `usage_event`
- `churned_customer` --materialized_as--> `churn_event`
- `net_revenue` --aggregates--> `revenue_event`

## Suggested ontology setup

1. Create entity types for Business Concept, Metric Definition, Business Unit,
   Source Table, and Authority Rule.
2. Add the concept IDs and descriptions above.
3. Add definition ownership and operational dimensions from
   `metric_definitions.csv`.
4. Add governance ownership from `authority_rules.csv`.
5. Add the three snapshot markdown files as searchable semantic documents.
6. Publish the ontology before using its MCP endpoint.
